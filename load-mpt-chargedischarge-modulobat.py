from pylabhelper import biologic
import originpro as op
import os

# # Read in File ##
path = op.get_lt_str('fname')
base_path, file_name = os.path.split(path)
file_name, _ = os.path.splitext(file_name)

# ################# Read in Files #################

file = biologic.load_mpt(path)
file.crop_columns_to(['time/s', 'cycle_number', 'half_cycle', 'Ewe/V', 'Ece/V', 'Ewe-Ece/V', 'I/mA'])
file.resolution_crop(delta_time=10, delta_pot=0.01)
file.shift_cycles()
file.extract_cycles()
file.calculate_charge_discharge_capacitances()

# ################# Output Workbooks #################

biologic.op_mb_charge_discharge_data_to_workbook(file, file_name, file_name)
