import numpy as np
import pandas
import pylabhelper.math as lm
import re
from textwrap import wrap
import warnings
from pylabhelper.BiologicFile import BiologicFile

try:
    import originpro as op
except ImportError:
    op = None
    print('Package \'originpro\' not found, no origin functionality')


def load_mpt(path):
    return BiologicFile(path)

def op_mpt_file_to_workbook(mpt, work_book_name):
    if op:
        work_book = op.new_book()

        work_book.lname = work_book_name
        work_book.name = work_book_name

        sheet = work_book.add_sheet(work_book_name)

        sheet.from_df(mpt.data)

        work_book[0].destroy()

def op_list_of_files_to_workbook(list_of_mpt, work_book_name, comment):
    if op:
        list_of_data = map(lambda mpt: mpt.data_cropped, list_of_mpt)
        full_df = pandas.concat(list_of_data)

        work_book = op.new_book()
        work_book.name = work_book_name
        work_book.lname = work_book_name

        sheet = work_book.add_sheet(f"{work_book_name} {comment}")

        sheet.from_list(0, list(full_df['time/s']), 'Time', 's', '', 'X')
        sheet.from_list(1, list(full_df['Ewe/V']), 'Potential Working', 'V', f"WE {comment}", 'Y')
        sheet.from_list(2, list(full_df['Ece/V']), 'Potential Counter', 'V', f"CE {comment}", 'Y')
        sheet.from_list(3, list(full_df['Ewe-Ece/V']), 'Potential Full Cell', 'V', f"Full Cell {comment} mA", 'Y')

        work_book[0].destroy()

        graph = op.new_graph(template='Single-Line-FullCell')
        graph.set_int('aa', 1)
        graph.lname = f"{work_book_name} Overview FullCell"
        graph.name = f"{work_book_name} Overview FullCell"

        plot = graph[0].add_plot(sheet, coly=3, colx=0, type='line')

        graph = op.new_graph(template='Double-Line-EceEwe')
        graph.set_int('aa', 1)
        graph.lname = f"{work_book_name} Overview Separated"
        graph.name = f"{work_book_name} Overview Separated"

        plot = graph[0].add_plot(sheet, coly=1, colx=0, type='line')
        plot = graph[0].add_plot(sheet, coly=2, colx=0, type='line')


def op_mb_charge_discharge_data_to_workbook(mpt_file, work_book_name, comment):
    if op:
        work_book = op.new_book()
        work_book.name = work_book_name
        work_book.lname = work_book_name

        sheet_all_cycles = work_book.add_sheet(f"All Cycles")
        cycle_sheets = []

        sheet_all_cycles.from_list(0, list(mpt_file.data_cropped['time/s']), 'Time', 's', '', 'X')
        sheet_all_cycles.from_list(1, list(mpt_file.data_cropped['Ewe/V']), 'Potential Working', 'V', f"WE {comment}", 'Y')
        sheet_all_cycles.from_list(2, list(mpt_file.data_cropped['Ece/V']), 'Potential Counter', 'V', f"CE {comment}", 'Y')
        sheet_all_cycles.from_list(3, list(mpt_file.data_cropped['Ewe-Ece/V']), 'Potential Full Cell', 'V', f"Full Cell {comment}", 'Y')

        for cycle_number, cycle in zip(mpt_file.cycle_numbers, mpt_file.cycles):
            cycle_sheet = work_book.add_sheet(f"Cycle {cycle_number}")

            cycle_sheet.from_list(0, list(cycle['time/s']), 'Time', 's', '', 'X')
            cycle_sheet.from_list(1, list(cycle['Ewe/V']),
                                  'Potential Working', 'V', f"WE {comment} Cycle {cycle_number}", 'Y')
            cycle_sheet.from_list(2, list(cycle['Ece/V']),
                                  'Potential Counter', 'V', f"CE {comment} Cycle {cycle_number}", 'Y')
            cycle_sheet.from_list(3, list(cycle['Ewe-Ece/V']),
                                  'Potential Full Cell', 'V', f"Full Cell {comment} Cycle {cycle_number}", 'Y')
            cycle_sheets.append(cycle_sheet)

        sheet_capacitances = work_book.add_sheet(f"Capacitances")

        sheet_capacitances.from_list(0, list(mpt_file.capacitances['Cycle Number']), 'Cycle', '', '', 'X')
        sheet_capacitances.from_list(1, list(mpt_file.capacitances['Current']), 'Current', 'mA', '', 'N')
        sheet_capacitances.from_list(2, list(mpt_file.capacitances['Ideal Charge Capacitance']), 'Ideal Charge Capacitance', 'mF', '', 'Y')
        sheet_capacitances.from_list(3, list(mpt_file.capacitances['Ideal Discharge Capacitance']), 'Ideal Discharge Capacitance', 'mF', '', 'Y')
        sheet_capacitances.from_list(4, list(mpt_file.capacitances['Charge Ideality']), 'Charge Ideality', '', '', 'Y')
        sheet_capacitances.from_list(5, list(mpt_file.capacitances['Discharge Ideality']), 'Discharge Ideality', '', '', 'Y')
        sheet_capacitances.from_list(6, list(mpt_file.capacitances['Faradayic Efficiency']), 'Faradayic Efficiency', '', '', 'Y')
        sheet_capacitances.from_list(7, list(mpt_file.capacitances['Discharge Polarity Gap']), 'Discharge Polarity Gap', 'V', '', 'Y')

        work_book[0].destroy()


        graph = op.new_graph(template='Single-Line-FullCell')
        graph.set_int('aa', 1)
        graph.lname = f"{work_book_name} Overview FullCell"
        graph.name = f"{work_book_name} Overview FullCell"

        plot = graph[0].add_plot(sheet_all_cycles, coly=3, colx=0, type='line')
        graph[0].rescale()

        graph = op.new_graph(template='Double-Line-EceEwe')
        graph.set_int('aa', 1)
        graph.lname = f"{work_book_name} Overview Separated"
        graph.name = f"{work_book_name} Overview Separated"

        plot = graph[0].add_plot(sheet_all_cycles, coly=1, colx=0, type='line')
        plot = graph[0].add_plot(sheet_all_cycles, coly=2, colx=0, type='line')
        graph[0].rescale()

        graph = op.new_graph(template='Multiline CD Stacked')
        graph.set_int('aa', 1)
        graph.lname = f"{work_book_name} Stacked"
        graph.name = f"{work_book_name} Stacked"

        for cycle_sheet in cycle_sheets:
            plot = graph[0].add_plot(cycle_sheet, coly=3, colx=0, type='line')
        graph[0].group()
        graph[0].rescale()



def op_capacitances_workbook(list_of_mpt, work_book_name, comment, layer):
    if op:
        list_of_data = map(lambda mpt: mpt.capacitances, list_of_mpt)
        full_cap_df = pandas.concat(list_of_data)

        work_book = op.new_book()
        work_book.name = work_book_name
        work_book.lname = work_book_name

        sheet = work_book.add_sheet(f"{work_book_name} {comment}")

        sheet.from_list(0, list(full_cap_df['Cycle Number']),                   'Cycle', '', '', 'N')
        sheet.from_list(1, [layer] * len(list(full_cap_df['Cycle Number'])),    'Current', 'mA', '', 'N')
        sheet.from_list(2, list(full_cap_df['Current']),                        'Current', 'mA', '', 'X')
        sheet.from_list(3, list(full_cap_df['Ideal Charge Capacitance']),       'Ideal Charge Capacitance', 'mF', comment, 'Y')
        sheet.from_list(4, list(full_cap_df['Ideal Discharge Capacitance']),    'Ideal Discharge Capacitance', 'mF', comment, 'Y')
        sheet.from_list(5, list(full_cap_df['Charge Ideality']),                'Charge Ideality', '', comment, 'Y')
        sheet.from_list(6, list(full_cap_df['Discharge Ideality']),             'Discharge Ideality', '', comment, 'Y')
        sheet.from_list(7, list(full_cap_df['Faradayic Efficiency']),           'Faradayic Efficiency', 'mF/mF', comment, 'Y')
        sheet.from_list(8, list(full_cap_df['Discharge Polarity Gap']),         'Discharge Polarity Gap', 'V', comment, 'Y')

        work_book[0].destroy()

    # # file
    # work_book.set_str('tree.file.name', filename)
    # work_book.set_str('tree.file.extension', extension)
    # work_book.set_str('tree.file.path', path)
    # work_book.set_float('tree.file.timestamp', timestamp)
    #
    # # measurement
    # work_book.set_float('tree.measurement.charge_current', charge_current)
