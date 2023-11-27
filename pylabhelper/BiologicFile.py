import numpy as np
import pandas
import pylabhelper.math as lm
import re
from textwrap import wrap
import warnings


class BiologicFile:

    def __init__(self, path):
        self.header, self.data, self.history = self._load_mpt(path)

        # produced in resolution_crop()
        self.data_cropped = None

        # produced in extract_cycles()
        self.cycles = None
        self.cycle_numbers = []
        self.half_cycles = None
        self.half_cycle_numbers = []

        # produced in calculate_charge_discharge_capacitances()
        self.capacitances = None

    def resolution_crop(self, **kwargs):
        # kwargs:
        #   delta_time in s
        #   delta_pot in V

        if 'resolution_crop' in self.history:
            warnings.warn('File is already resolution cropped')  # TODO: add filename or identifier

        if 'delta_time' not in kwargs:
            raise Exception('delta_time needs to be set')

        if 'delta_pot' not in kwargs:
            raise Exception('delta_pot needs to be set')

        # get a copy of the DataFrame
        self.data_cropped = self.data.copy()

        # get the cropping arguments
        delta_time = kwargs.get('delta_time')  # in s
        delta_pot = kwargs.get('delta_pot')  # in V

        # set the values from the first row as initial values
        compare_time = self.data_cropped.iloc[0]['time/s']
        compare_pot = self.data_cropped.iloc[0]['Ewe-Ece/V']

        # walk over ec_df and drop all rows with too small deviation
        for df_index in self.data_cropped[1:].index:
            current_time = self.data_cropped.loc[df_index, 'time/s']
            current_pot = self.data_cropped.loc[df_index, 'Ewe-Ece/V']
            diff_time = abs(current_time - compare_time)
            diff_pot = abs(current_pot - compare_pot)
            if diff_time < delta_time and diff_pot < delta_pot:
                self.data_cropped.drop(df_index, inplace=True)
            else:
                compare_time = current_time
                compare_pot = current_pot

        # set the history
        self.history['resolution_crop'] = {'delta_time': delta_time, 'delta_pot': delta_pot}

    def shift_time_to_zero(self):
        start_time = self.data.loc[self.data.index[0], 'time/s']
        self.data['time/s'] = self.data['time/s'].subtract(start_time)

        self.history['time_shifted'] = True

    def shift_cycles(self):
        # check if ec_data has half_cycle information
        if "cycle_number" not in self.data.columns:
            raise Exception('Data does not contain half_cycle information')

        # Shift Cycle Data up by 1
        self.data['cycle_number'] = self.data['cycle_number'].shift(-1)
        self.data.loc[self.data.index[-1], 'cycle_number'] = self.data['cycle_number'].iloc[-2]

        # check if ec_df has half_cycle information
        if "half_cycle" in self.data.columns:
            self.data['half_cycle'] = self.data['half_cycle'].shift(-1)
            self.data.loc[self.data.index[-1], 'half_cycle'] = self.data['half_cycle'].iloc[-2]

        # set the history
        self.history['cycles_shifted'] = True

    def extract_cycles(self):
        # check if ec_df has half_cycle information
        if "cycle_number" not in self.data.columns:
            raise Exception('Data does not contain cycle information')

        # extract cycles in separate DataFrames
        cycles = []
        for cycle_number in self.data['cycle_number'].unique():
            cycle_df = self.data[
                # All data where half_cycle is the given value
                self.data['cycle_number'] == cycle_number
                ].copy()
            cycles.append(cycle_df)
            self.cycle_numbers.append(int(cycle_number) + 1)

        # Prepend last row of previous half_cycle on current half_cycle
        #
        #   /\  /\        /\  /\
        #  /  \   \  =>  /  \/  \
        #   C1  C2        C1  C2
        for index, cycle_df in enumerate(cycles):
            if index > 0:
                last_row_previous_cycle = pandas.DataFrame(cycles[index - 1].iloc[[-1]])
                cycles[index] = pandas.concat([last_row_previous_cycle, cycle_df], ignore_index=True)
                cycles[index].iloc[0]['cycle_number'] = cycle_df.iloc[0]['cycle_number']
                cycles[index].iloc[0]['half_cycle'] = cycle_df.iloc[0]['half_cycle']

        # Start every half_cycle from t=0 instead of the overall measurement time
        for index, cycle_df in enumerate(cycles):
            start_time = cycle_df.loc[cycle_df.index[0], 'time/s']
            cycles[index]['time/s'] = cycle_df['time/s'].subtract(start_time)

        # repeat for half cycles
        if "half_cycle" in self.data.columns:
            half_cycles = []
            for half_cycle_number in self.data['half_cycle'].unique():
                cycle_df = self.data[
                    # All data where half_cycle is the given value
                    self.data['half_cycle'] == half_cycle_number
                    ].copy()
                half_cycles.append(cycle_df)
                self.half_cycle_numbers.append(int(half_cycle_number) + 1)

            for index, cycle_df in enumerate(half_cycles):
                if index > 0:
                    last_row_previous_cycle = pandas.DataFrame(half_cycles[index - 1].iloc[[-1]])
                    half_cycles[index] = pandas.concat([last_row_previous_cycle, cycle_df], ignore_index=True)
                    half_cycles[index].iloc[0]['cycle_number'] = cycle_df.iloc[0]['cycle_number']
                    half_cycles[index].iloc[0]['half_cycle'] = cycle_df.iloc[0]['half_cycle']

            for index, cycle in enumerate(half_cycles):
                start_time = cycle.loc[cycle.index[0], 'time/s']
                half_cycles[index]['time/s'] = cycle['time/s'].subtract(start_time)

            # save the extracted cycles as list of DataFrames
            self.half_cycles = half_cycles

        # save the extracted cycles as list of DataFrames
        self.cycles = cycles

        # set the history
        self.history['cycles_extracted'] = True

    def calculate_charge_discharge_capacitances(self, **kwargs):
        if "Modulo Bat" not in self.header['file_type']:
            raise Exception('Not a Modulo Bat file')

        # check if cycles extracted
        if "cycles_extracted" not in self.history:
            raise Exception('Cycle Data not extracted')

        # extract the charge current used
        # TODO: this works only for Modulobat. find out if there is a better way.
        self.header['charge_current'] = lm.to_float(self.header['technique'].loc['ctrl1_val', 1])
        #charge_current = lm.to_float(self.header['technique'].loc['ctrl1_val', 1])

        # Calculate Charge Capacitances

        self.capacitances = pandas.DataFrame(columns=['Cycle',
                                                      'Cycle Number'
                                                      'Current',
                                                      'Ideal Charge Capacitance',
                                                      'Ideal Discharge Capacitance',
                                                      'Charge Ideality',
                                                      'Discharge Ideality',
                                                      'Faradayic Efficiency',
                                                      'Discharge Polarity Gap',
                                                      ]).set_index('Cycle')

        for cycle in self.half_cycles:
            cycle_number = int(cycle.loc[0, 'cycle_number']) + 1
            ideal_capacitance = self._calculate_ideal_capacitance_from_halfcycle(cycle, self.header['charge_current'])
            cycle = self._calculate_step_capacitances_from_halfcycle(cycle)
            cycle, r_squared = self._calculate_ideality_deviation_from_halfcycle(cycle)
            polarity_gap = cycle.loc[0, 'Ewe-Ece/V'] - cycle.loc[1, 'Ewe-Ece/V']

            # Take 2nd point of current half_cycle as current indicator to see if charge or discharge
            charge_cycle = cycle.astype(float).loc[1, 'I/mA'] > 0

            if charge_cycle:
                self.capacitances.loc[cycle_number, 'Ideal Charge Capacitance'] = ideal_capacitance
                self.capacitances.loc[cycle_number, 'Charge Ideality'] = r_squared

            if not charge_cycle:
                self.capacitances.loc[cycle_number, 'Ideal Discharge Capacitance'] = ideal_capacitance
                self.capacitances.loc[cycle_number, 'Discharge Ideality'] = r_squared
                self.capacitances.loc[cycle_number, 'Discharge Polarity Gap'] = polarity_gap

            self.capacitances.loc[cycle_number, 'Current'] = self.header['charge_current']
            self.capacitances.loc[cycle_number, 'Cycle Number'] = cycle_number

        self.capacitances['Faradayic Efficiency'] = \
            self.capacitances['Ideal Discharge Capacitance'] / self.capacitances['Ideal Charge Capacitance']

        self.history['capacitances'] = True

    def crop_columns_to(self, list_of_columns):
        self.data = self.data[list_of_columns]

    @staticmethod
    def _calculate_ideal_capacitance_from_halfcycle(half_cycle, charge_current):
        potential_start = float(half_cycle.loc[0, 'Ewe-Ece/V'])
        time_start = float(half_cycle.loc[0, 'time/s'])

        last_index = half_cycle.index[-1]
        potential_end = float(half_cycle.loc[last_index, 'Ewe-Ece/V'])
        time_end = float(half_cycle.loc[last_index, 'time/s'])

        time_delta = time_end - time_start
        potential_delta = abs(potential_end - potential_start)

        # charge_current is in mA --> capacitance is in mF (should be identical to current / slope)
        capacitance = (charge_current * time_delta) / potential_delta

        return capacitance

    @staticmethod
    def _calculate_step_capacitances_from_halfcycle(half_cycle):
        half_cycle['E_delta/V'] = half_cycle['Ewe-Ece/V'].diff()
        half_cycle['time_delta/s'] = half_cycle['time/s'].diff()
        half_cycle['step_capacitance/mF'] = half_cycle['I/mA'] * half_cycle['time_delta/s'] / half_cycle['E_delta/V']

        # charge_current is in mA --> capacitance is in mF
        return half_cycle

    @staticmethod
    def _calculate_ideality_deviation_from_halfcycle(half_cycle):
        potential_start = float(half_cycle.loc[0, 'Ewe-Ece/V'])
        time_start = float(half_cycle.loc[0, 'time/s'])

        last_index = half_cycle.index[-1]
        potential_end = float(half_cycle.loc[last_index, 'Ewe-Ece/V'])
        time_end = float(half_cycle.loc[last_index, 'time/s'])

        time_delta = time_end - time_start
        potential_delta = potential_end - potential_start

        # slope in V / s
        slope = potential_delta / time_delta

        # intercept in V
        intercept = potential_end - (slope * time_end)

        half_cycle['ideal_potential'] = intercept + slope * half_cycle['time/s']
        half_cycle['residual-squared'] = (half_cycle['Ewe-Ece/V'] - half_cycle['ideal_potential']) ** 2
        residuals_squared_sum = half_cycle['residual-squared'].sum()
        value_mean = half_cycle['Ewe-Ece/V'].mean()
        half_cycle['values-squared'] = (half_cycle['Ewe-Ece/V'] - value_mean) ** 2
        values_squared_sum = half_cycle['values-squared'].sum()
        r_squared = 1 - (residuals_squared_sum / values_squared_sum)

        return half_cycle, r_squared

    @staticmethod
    def _load_mpt(path):
        file_contents = open(path).readlines()

        ## Handle Header ##

        # check if ASCII file
        if not "EC-Lab ASCII FILE" in file_contents[0]:
            raise Exception('Only EC-Lab ASCII Files supported')

        # check if lines 2 and 4 are empty
        if len(file_contents[2]) > 1:
            raise Exception(
                'Unexpected EC-Lab ASCII File format (line 2 and 4 are non empty). File copied before measurement was finished?')

        if len(file_contents[4]) > 1:
            if file_contents[3][:-1] == 'DISK CHANNEL SETTING':
                file_type = 'RRDE'
            else:
                raise Exception(
                    'Unexpected EC-Lab ASCII File format (line 2 and 4 are non empty). File copied before measurement was finished?')
        else:
            file_type = file_contents[3][:-1]

        # extract number of header lines from file
        header_lines = int(re.findall('Nb header lines : ([0-9]+)', file_contents[1])[0])

        # slice header off file
        header = file_contents[5:(header_lines - 1)]

        header_object = {
            'file_type': file_type
        }

        # Extract Header Data

        flags = []

        for line_number, line in enumerate(header):
            # Cut off trailing \n
            line = line[:-1]

            if len(line) == 0:
                continue

            # Cut off leading \t
            if line[0] == '\t':
                line = line[1:]

            # Is tere a : in the line?
            if ':' not in line:
                flags.append(line)
                continue

            if ':' in line:
                # Split line @ ':'
                patches = line.split(' :', 1)

                # If there is no trailing space after the ':' omit the line
                if len(patches[1]) == 0:
                    continue

                header_object[patches[0]] = patches[1][1:]

                if patches[0] == 'Cycle Definition':
                    technique_start = line_number + 1
                    break

        # Extract Technique Data

        technique = header[technique_start:-1]

        for index, line in enumerate(technique):
            technique[index] = wrap(line, width=20)

        technique_df = pandas.DataFrame(technique)
        technique_df = technique_df.set_index([0])

        # Extract EC Data

        ec_data = list(map(lambda el: el.split('\t'), file_contents[header_lines:]))
        ec_df = pandas.DataFrame(ec_data)
        ec_df.columns = file_contents[header_lines - 1].replace(' ', '_').split('\t')[:-1]
        ec_df = ec_df.astype(np.float64)

        header_object['flags'] = flags
        header_object['technique'] = technique_df

        return header_object, ec_df, {'mpt': True}
