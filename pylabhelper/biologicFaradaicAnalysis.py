
import pandas as pd
from sklearn.linear_model import LinearRegression
from progress.bar import Bar
import numpy as np
import pandas
import pylabhelper.math as lm
import re
import time
import datetime


def read_mpt(path, columns: object = {
                     'time/s': 'time',
                     'Ewe/V': 'potential',
                     '<I>/mA': 'current',
                     'half_cycle number': 'half_cycle'
                 }):
    """Read a biologic mpt file into a pandas dataframe, extracting the cycles as they are described in the data."""
    file_contents = open(path).readlines()

    # check if ASCII file
    if not "EC-Lab ASCII FILE" in file_contents[0]:
        raise Exception('Only EC-Lab ASCII Files supported')

    # check if CV file
    if not "Cyclic Voltammetry" in file_contents[3]:
        raise Exception('File ist not a cyclic voltammetry file')

    # extract number of header lines from file
    header_lines = int(re.findall('Nb header lines : ([0-9]+)', file_contents[1])[0])

    # slice header off file
    header = file_contents[:(header_lines-1)]

    # extract measurement speed
    matching = [s for s in header if "dE/dt" in s]
    speed = lm.to_float(matching[0][5:-3])

    # extract acquisition timestamp
    keyword = 'Acquisition started on'
    time_format = "%m/%d/%Y %H:%M:%S.%f"
    matching = [s for s in header if keyword in s]
    #  - extract the data after the keyword (assuming \n as delimiter in the end
    time_str = matching[0][len(keyword + ' : '):-1]
    timestamp = time.mktime(datetime.datetime.strptime(time_str, time_format).timetuple())

    # extract vertice potentials
    matching = [s for s in header if "Ei (V)" in s]
    start_vertice = lm.to_float(re.findall('([\-0-9]+[,\.][0-9]+)', matching[0])[0])

    matching = [s for s in header if "E1 (V)" in s]
    first_vertice = lm.to_float(re.findall('([\-0-9]+[,\.][0-9]+)', matching[0])[0])

    matching = [s for s in header if "E2 (V)" in s]
    second_vertice = lm.to_float(re.findall('([\-0-9]+[,\.][0-9]+)', matching[0])[0])

    matching = [s for s in header if "Ef (V)" in s]
    final_vertice = lm.to_float(re.findall('([\-0-9]+[,\.][0-9]+)', matching[0])[0])

    # slice ec data off file
    cv_data = list(map(lambda el: el.split('\t'), file_contents[header_lines:]))
    cv_df = pandas.DataFrame(cv_data)
    cv_df.columns = file_contents[header_lines-1].split('\t')[:-1]

    # Select only desired columns
    cv_df = cv_df[columns.keys()]
    cv_df = cv_df.rename(columns=columns)

    # convert columns to float and int
    # todo: put desired type in columns object as parameter...
    cv_df['potential'] = cv_df['potential'].apply(lambda x: lm.to_float(x))
    cv_df['time'] = cv_df['time'].apply(lambda x: lm.to_float(x))
    cv_df['current'] = cv_df['current'].apply(lambda x: lm.to_float(x))
    cv_df['half_cycle'] = cv_df['half_cycle'].apply(lambda x: int(lm.to_float(x)))

    return {
        'speed': speed,
        'start_vertice': start_vertice,
        'first_vertice': first_vertice,
        'second_vertice': second_vertice,
        'final_vertice': final_vertice,
        'path': path,
        'open_circuit_potential': cv_df['potential'][0],
        'data': cv_df,
        'timestamp': timestamp
    }

def interpolate_cycles(measured_data, cycle_keys, upper_vertice, lower_vertice, resolution,
                       interpolation_method='interp1d'):
    # Prepare the cycles list for return
    cycles_df = []

    max_keys, min_keys = cycle_keys

    file_data = measured_data['data']

    interp_potential_down = np.linspace(upper_vertice, lower_vertice, round((upper_vertice-lower_vertice)/resolution)+1)
    interp_potential_up = np.flipud(interp_potential_down)

    if max_keys[0] < min_keys[0]:
        # First extreme is upper vertex
        # --> Cycle is upper - lower - upper
        for max_key_index in range(len(max_keys)-1):
            # Get Measured X and Y Data and Interpolate
            down = file_data[max_keys[max_key_index]: min_keys[max_key_index] + 1]
            down = down.drop_duplicates(subset='potential', keep='last')

            up = file_data[min_keys[max_key_index]: max_keys[max_key_index + 1] + 1]
            up = up.drop_duplicates(subset='potential', keep='last')

            down = down.sort_values(by=['potential'])
            up = up.sort_values(by=['potential'])
            interp_current_down = lm.interpolate(down.potential, down.current, interp_potential_down,
                                                 method=interpolation_method)
            interp_current_up = lm.interpolate(up.potential, up.current, interp_potential_up,
                                               method=interpolation_method)

            # Stitch Interpolated Data together
            cycle = {
                'potential': np.concatenate([interp_potential_down[:-1], interp_potential_up]),
                'current': np.concatenate([interp_current_down[:-1], interp_current_up]),
                'half_cycle': max_key_index+1
            }

            # Append to the cycles list
            cycles_df.append(pd.DataFrame(cycle))
    else:
        # First extreme is lower vertex
        # --> Cycle is lower - upper - lower
        print(max_keys)
        print(min_keys)

        raise Exception('direction yet unimplemented')

    return {
        'path': measured_data['path'],
        'speed': measured_data['speed'],
        'data': pd.concat(cycles_df)
    }


def read_mpt_series(path_list, resolution):
    # prepare the loading bar
    bar = Bar('Processing', max=len(path_list))

    # prepare data object
    series_data = []
    original_data = []

    for path in path_list:
        # read the files data into an object
        file_data = read_mpt(path)
        cycle_keys = extract_cycle_keys(file_data)
        measurement = interpolate_cycles(file_data,
                                         cycle_keys,
                                         file_data['first_vertice'],
                                         file_data['second_vertice'],
                                         resolution)

        original = {
            'path': file_data['path'],
            'speed': file_data['speed'],
            'data': reset_cycles(file_data)
        }

        speed = measurement['speed']
        series_data.append(measurement)
        original_data.append(original)
        bar.next()

    bar.finish()

    print("finished reading {file_count} files".format(file_count=len(path_list)))

    series_data.sort(key=lambda file_data: file_data['speed'])

    print("sorted list by measurement speed")

    interp_series = {
        'half_cycle': series_data[0]['data'].cycle.values,
        'potential': series_data[0]['data'].potential.values,
    }

    for file_data in series_data:
        cycle = file_data['data']
        interp_series[file_data['speed']] = cycle.current.values

    print("finished converting to pandas data frame")
    interp_series_df = pd.DataFrame.from_dict(interp_series, orient='index').transpose()

    return interp_series_df, original_data
    #return interp_series, original_data


def fc_analysis(data, cycle_number, cutoff=-1):
    x = np.sqrt(list(data.columns.values[2:])).reshape((-1, 1))
    cycle = data[data.cycle == cycle_number]

    fc_data = {
        'index': [],
        'potential': [],
        'faradayic': [],
        'capacitive': [],
        'rSq': []
    }

    speeds = data.columns.values[2:]

    for index, row in cycle.iterrows():
        y = []
        for speed in speeds:
            y.append(row[speed] / np.sqrt(speed))
        model = LinearRegression().fit(x[:cutoff], y[:cutoff])
        rSq = model.score(x[:cutoff], y[:cutoff])
        faradayic = model.intercept_
        capacitive = model.coef_[0]

        fc_data['index'].append(index)
        fc_data['potential'].append(row['potential'])
        fc_data['faradayic'].append(faradayic)
        fc_data['capacitive'].append(capacitive)
        fc_data['rSq'].append(rSq)

    return pd.DataFrame(fc_data)