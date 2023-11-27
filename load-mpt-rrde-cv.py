from pylabhelper import biologic
import os

# # Read in File ##
path = 'C:/Users/Jan/Desktop/PaEl0088_Ar-RRDE_05_CV-RCA.mpt'
# path = op.get_lt_str('fname')
# base_path, file_name = os.path.split(path)
# file_name, _ = os.path.splitext(file_name)

# ################# Read in Files #################

file = biologic.load_mpt(path)
# file.crop_columns_to(['time/s', 'cycle_number', 'half_cycle', 'Ewe/V', 'Ece/V', 'Ewe-Ece/V', 'I/mA'])
# file.resolution_crop(delta_time=10, delta_pot=0.01)
# file.shift_cycles()
# file.extract_cycles()
# file.calculate_charge_discharge_capacitances()

# ################# Output Workbooks #################

biologic.op_mpt_file_to_workbook(file, 'test')
