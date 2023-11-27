import math

from pylabhelper.CV import CV
from typing import List
import numpy as np
from sklearn.linear_model import LinearRegression
import pandas as pd
from scipy.optimize import curve_fit


def read_cv_file(path):
    return CV(path)


def fitting_function(speed, capacitive, faradayic):
    current = capacitive * (speed + np.power(speed, 2)) + faradayic * (np.power(speed, 1/2) + np.power(speed, 3/2))
    return current


def fc_analysis(files: List[CV], cycle_number, cutoff=-1):

    # Sort cycles list by speed
    files.sort(key=lambda item: item.speed)

    lin_reg_list = []
    f_reg_list = []

    speeds = []
    cycles = []
    for file in files:
        speeds.append(file.speed)
        cycles.append(file.interp_data[file.interp_data['half_cycle'] == cycle_number])

    x = np.sqrt(speeds).reshape((-1, 1))
    speeds_squared = np.sqrt(speeds)

    fc_data = {
        'index': [],
        'potential': [],
        'faradayic': [],
        'capacitive': [],
        'direction': [],
        'rSq': []
    }

    for index, row in cycles[0].iterrows():
        y = []
        for speed_index in range(len(speeds)):
            y.append(cycles[speed_index].current[index])

        popt, pcov = curve_fit(fitting_function, np.array(speeds)[:cutoff], y[:cutoff])

        capacitive_error = np.sqrt(np.diag(pcov))[0]
        faradayic_error = np.sqrt(np.diag(pcov))[1]
        capacitive = popt[0]
        faradayic = popt[1]

        f_reg_list.append([row.potential] + y + [capacitive_error, faradayic_error, faradayic, capacitive, row.direction])

    for index, row in cycles[0].iterrows():
        y = []
        for speed_index in range(len(speeds)):
            y.append(cycles[speed_index].current[index] / np.sqrt(speeds[speed_index]))

        model = LinearRegression().fit(x[:cutoff], y[:cutoff])
        rSq = model.score(x[:cutoff], y[:cutoff])
        faradayic = model.intercept_
        capacitive = model.coef_[0]

        fc_data['index'].append(index)
        fc_data['potential'].append(row['potential'])
        fc_data['faradayic'].append(faradayic)
        fc_data['capacitive'].append(capacitive)
        fc_data['direction'].append(row['direction'])
        fc_data['rSq'].append(rSq)

        lin_reg_list.append([cycles[speed_index].potential[index]] + y + [rSq, faradayic, capacitive, row['direction']])

    return \
        pd.DataFrame(fc_data),\
        pd.DataFrame(
            lin_reg_list,
            columns=['potential'] + list(speeds_squared) + ['rSq', 'faradayic', 'capacitive', 'direction']
        ),\
        pd.DataFrame(
            f_reg_list,
            columns=['potential'] + list(speeds) + ['capacitive_error', 'faradayic_error', 'faradayic', 'capacitive', 'direction']
        )


class FCAnalysis:

    def __init__(self, cvs: List[CV], cycle_number, coefficient_order):
        self._cvs = cvs

        # Sort cycles list by speed
        self._cvs.sort(key=lambda item: item.speed)

        self._speeds = []
        self._cycles = []

        for cv in self._cvs:
            self._speeds.append(cv.speed)
            self._cycles.append(cv.get_interpolated_cycle(cycle_number))

        coefficient_order = coefficient_order

        def regression_function(speed, *params):
            if(len(params) is not coefficient_order * 2 ):
                raise Exception(f"Argument Count Error. Is: {len(params)} Should: {coefficient_order*2} Params: {params}")

            cap_params = params[0:coefficient_order]
            far_params = params[coefficient_order:coefficient_order*2]

            current = 0
            for cap_param, far_param, power in zip(cap_params, far_params, range(coefficient_order)):
                current = current +\
                          (cap_param * np.power(speed, 1 + power)) + \
                          (far_param * np.power(speed, 1/2 + power))

            return current

        self._regression_function = regression_function

        def capacitive_current(speed, *cs):
            current = 0

            for c, index in zip(cs, range(len(cs))):
                current = (c * np.power(speed, index + 1))

            return current

        def faradayic_current(speed, *fs):
            current = 0

            for f, index in zip(fs, range(len(fs))):
                current = (f * np.power(speed, index + 1/2))

            return current

        self._regression_data = {
            'index': [],
            'potential': [],
            'currents': [],
            'fitted_currents': [],
            'faradayic_coefficients': [],
            'capacitive_coefficients': [],
            'faradayic_errors': [],
            'capacitive_errors': [],
            'rSq': [],
        }

        for index, row in self._cycles[0].iterrows():
            currents = []
            for speed_index in range(len(self._speeds)):
                currents.append(self._cycles[speed_index].current[index])

            popt, pcov = curve_fit(self._regression_function, np.array(self._speeds), currents, p0=np.ones(coefficient_order*2))

            pcov_diag = np.sqrt(np.diag(pcov))
            capacitive_error = pcov_diag[0:coefficient_order]
            faradayic_error = pcov_diag[coefficient_order:coefficient_order*2]

            capacitive = popt[0:coefficient_order]
            faradayic = popt[coefficient_order:coefficient_order*2]

            residuals = currents - self._regression_function(np.array(self._speeds), *popt)
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((currents - np.mean(currents))**2)
            rSq = 1 - (ss_res / ss_tot)

            self._regression_data['index'].append(index)
            self._regression_data['potential'].append(row.potential)
            self._regression_data['currents'].append(currents)
            self._regression_data['fitted_currents'].append(self._regression_function(np.array(self._speeds), *popt))
            self._regression_data['faradayic_coefficients'].append(faradayic)
            self._regression_data['capacitive_coefficients'].append(capacitive)
            self._regression_data['faradayic_errors'].append(faradayic_error)
            self._regression_data['capacitive_errors'].append(capacitive_error)
            self._regression_data['rSq'].append(rSq)

        self._regression_data = pd.DataFrame(self._regression_data)

    def potential(self):
        return self._regression_data.potential

    def currents(self, index):
        return self._regression_data.loc[index].currents

    def fitted_currents(self, index):
        return self._regression_data.loc[index].fitted_currents

    def faradayic_contribution(self, speed):
        pass

    def capacitive_contribution(self, speed):
        pass
