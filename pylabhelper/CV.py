import os.path
import pylabhelper.biologic as biologic
import numpy as np
import pylabhelper.math as lm
import pandas as pd
import scipy.signal as sp_sig
from datetime import datetime


class CV:

    def __init__(self, path):
        """ Creating a CV object from a measurement file """

        self.path = path
        self.filename, self.extension = os.path.splitext(os.path.basename(path))

        if self.extension == '.mpt':
            data = biologic.read_mpt(path)

            self.start_vertice = data['start_vertice']
            self.first_vertice = data['first_vertice']
            self.second_vertice = data['second_vertice']
            self.final_vertice = data['final_vertice']
            self.speed = data['speed']
            self.ocp = data['open_circuit_potential']
            self.original_data = data['data']

            self.data, self.cycle_count = self._create_recycled_data()
            self.original_cycle_count = len(self.original_data.cycle.unique())
            self.interp_data = self._create_interpolated_data()

            self.timestamp = data['timestamp'] + self.data['time'][0]
            self.datetime = datetime.fromtimestamp(self.timestamp).strftime("%d-%m-%Y %H:%M:%S")

    def _extract_cycle_keys(self):
        fv = self.first_vertice
        sv = self.second_vertice
        th = abs(fv - sv) * 0.01

        max_keys, _ = sp_sig.find_peaks(self.original_data.potential,
                                        height=(fv - th, fv + th),
                                        distance=10, width=10)
        min_keys, _ = sp_sig.find_peaks(self.original_data.potential * (-1),
                                        height=(-(sv + th), -(sv - th)),
                                        distance=10, width=10)

        # for cycle_number in self.original_data.half_cycle.unique():
        #     if self.first_vertice > self.second_vertice:
        #         # Cycle is upper - lower - upper
        #         cycle_df = self.original_data[self.original_data.half_cycle == cycle_number]
        #         max_keys.append(cycle_df.potential.idxmax())
        #
        #         # Possibility 1      Possibility 2          Possibility 3
        #         # EOC in between     EOC smaller than L     EOC bigger than U
        #         #                                            S          E
        #         #                                            \          /
        #         #  U1  U2  U3         U1  U2  U3              \U1  U2  /U3
        #         #  /\  /\  /\         /\  /\  /\               \  /\  /
        #         #  S \/  \/ E        /  \/  \/  \               \/  \/
        #         #    L1  L2         /   L1  L2   \              L1  L2
        #         #  ____----         S            E
        #
        #         # ignore data before first maximum
        #         min_keys.append(cycle_df.loc[cycle_df.potential.idxmax():].potential.idxmin())
        #     else:
        #         # Cycle is lower - upper - lower
        #         raise Exception(f"direction not yet defined FV {self.first_vertice} SV {self.second_vertice}")

        return [list(max_keys), list(min_keys)]

    def _create_recycled_data(self):
        max_keys, min_keys = self._extract_cycle_keys()
        data = self.original_data.copy()

        if max_keys[0] > min_keys[0]:
            min_keys.pop(0)

        data.loc[0: max_keys[0], 'half_cycle'] = 'start'
        data.loc[0: max_keys[0], 'direction'] = 'up'
        for max_key_index in range(len(max_keys) - 1):
            data.loc[max_keys[max_key_index]: max_keys[max_key_index + 1], 'half_cycle'] = max_key_index + 1
            data.loc[max_keys[max_key_index]: min_keys[max_key_index], 'direction'] = 'down'
            data.loc[min_keys[max_key_index]: max_keys[max_key_index + 1], 'direction'] = 'up'

        data.loc[max_keys[-1]:, 'half_cycle'] = 'end'
        data.loc[max_keys[-1]:min_keys[-1], 'direction'] = 'down'
        data.loc[min_keys[-1]:, 'direction'] = 'up'

        return data, (len(max_keys)-1)

    def _create_interpolated_data(self):
        # Prepare the cycles list for return
        cycles_df = []

        if self.first_vertice > self.second_vertice:
            # First extreme is upper vertex
            # --> Cycle is upper - lower - upper
            #TODO: resolution and method as option value from UI!!!
            resolution = 0.001
            interpolation_method = 'interp1d'

            interp_potential_down = np.linspace(self.first_vertice, self.second_vertice,
                                                round((self.first_vertice - self.second_vertice) / resolution) + 1)
            interp_potential_up = np.flipud(interp_potential_down)

            for cycle_number in self.data.cycle.unique()[1:-1]:
                cycle = self.data[self.data.cycle == cycle_number]

                down = cycle[cycle.direction == 'down']
                down = down.drop_duplicates(subset='potential', keep='last')

                up = cycle[cycle.direction == 'up']
                up = up.drop_duplicates(subset='potential', keep='last')

                down = down.sort_values(by=['potential'])
                up = up.sort_values(by=['potential'])

                interp_current_down = lm.interpolate(down.potential, down.current, interp_potential_down,
                                                     method=interpolation_method)
                interp_current_up = lm.interpolate(up.potential, up.current, interp_potential_up,
                                                   method=interpolation_method)

                interp_down = {
                    'potential': interp_potential_down,
                    'current': interp_current_down,
                    'direction': 'down',
                    'half_cycle': cycle_number
                }
                interp_up = {
                    'potential': interp_potential_up,
                    'current': interp_current_up,
                    'direction': 'up',
                    'half_cycle': cycle_number
                }

                # Append to the cycles list
                cycles_df.append(pd.DataFrame(interp_down))
                cycles_df.append(pd.DataFrame(interp_up))
        else:
            # First extreme is lower vertex
            # --> Cycle is lower - upper - lower
            raise Exception('direction yet unimplemented')

        return pd.concat(cycles_df).reset_index(drop=True)

    def get_cycle(self, cycle_number):
        return self.data[self.data.cycle == cycle_number]

    def cycles(self):
        for cycle_number in range(1, self.cycle_count + 1):
            yield self.get_cycle(cycle_number)

    def get_original_cycle(self, cycle_number):
        return self.original_data[self.original_data.cycle == cycle_number]

    def original_cycles(self):
        for cycle_number in range(1, self.original_cycle_count + 1):
            yield self.get_original_cycle(cycle_number)

    def get_interpolated_cycle(self, cycle_number):
        return self.interp_data[self.interp_data.cycle == cycle_number]

    def interpolated_cycles(self):
        for cycle_number in range(1, self.cycle_count + 1):
            yield self.get_interpolated_cycle(cycle_number)

