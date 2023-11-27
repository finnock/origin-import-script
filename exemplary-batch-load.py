import os.path

from pylabhelper import biologic
import originpro as op

# # Read in File ##
base_path = os.path.split(op.get_lt_str('fname'))[0]
sample_name = 'JaOe2019 - 4Ly'
layers = 4

file_list = {
    f"Initial OCV":  f"chargedischargeStandardprotokoll_01_OCV_C01.mpt",
    f"Initial PEIS":  f"chargedischargeStandardprotokoll_02_PEIS_C01.mpt",
    f"CD 10mA":  f"chargedischargeStandardprotokoll_03_MB_C01.mpt",
    f"CD 5mA":  f"chargedischargeStandardprotokoll_04_MB_C01.mpt",
    f"CD 1mA":  f"chargedischargeStandardprotokoll_05_MB_C01.mpt",
    f"CD 0.5mA":  f"chargedischargeStandardprotokoll_06_MB_C01.mpt",
    f"CD 0.1mA":  f"chargedischargeStandardprotokoll_07_MB_C01.mpt",
    f"Final OCV":  f"chargedischargeStandardprotokoll_08_OCV_C01.mpt",
    f"Final PEIS":  f"chargedischargeStandardprotokoll_09_PEIS_C01.mpt",
}

full_measurement_list = [
    'Initial OCV',
    'CD 10mA',
    'CD 5mA',
    'CD 1mA',
    'CD 0.5mA',
    'CD 0.1mA',
    'Final OCV',
]

ocv_list = [
    'Initial OCV',
    'Final OCV',
]

cd_list = [
    'CD 10mA',
    'CD 5mA',
    'CD 1mA',
    'CD 0.5mA',
    'CD 0.1mA',
]

eis_measurements = [
    'Initial PEIS',
    'Final PEIS',
]

# ################# Read in Files #################

for name, file_name in file_list.items():
    file_list[name] = biologic.load_mpt(base_path + '/' + file_name)

print('Finished reading all files BiologicFile Objects')

for name in cd_list:
    file_list[name].crop_columns_to(['time/s', 'cycle_number', 'half_cycle', 'Ewe/V', 'Ece/V', 'Ewe-Ece/V', 'I/mA'])
    file_list[name].shift_time_to_zero()
    file_list[name].resolution_crop(delta_time=10, delta_pot=0.01)

print('Finished cropping all files in the \'cd_list\'')

for name in ocv_list:
    file_list[name].crop_columns_to(['time/s', 'Ewe/V', 'Ece/V', 'Ewe-Ece/V'])
    file_list[name].resolution_crop(delta_time=10, delta_pot=0.01)

print('Finished cropping all files in the \'ocv_list\'')

for name in cd_list:
    file_list[name].shift_cycles()
    file_list[name].extract_cycles()
    file_list[name].calculate_charge_discharge_capacitances()

print('Finished calculating the capacitances from all files in \'cd_list\'')

# ################# Output Workbooks and Graphs #################

full_measurement_data = map(lambda index: file_list[index], full_measurement_list)
biologic.op_list_of_files_to_workbook(full_measurement_data, f"{sample_name} Full Measurement", sample_name)

for name in cd_list:
    biologic.op_mb_charge_discharge_data_to_workbook(file_list[name], f"{sample_name} {name}", name)

full_cap_data = map(lambda index: file_list[index], cd_list)
biologic.op_capacitances_workbook(full_cap_data, 'Capacitances', sample_name, layers)

