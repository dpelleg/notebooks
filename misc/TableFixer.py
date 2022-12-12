import copy
import pandas
import re
import pandas as pd
import warnings
from pdfhelper import *

# Written by Dan Pelleg

def spaced(s):
    '''Add space at the begining of a string unless there is already one there'''
    if re.match(r'\s+', s):   # there is a space already
        return s
    return " " + s

def despaced(s):
    '''Remove any space at the end of the string'''
    return s.rstrip(' ')

def fix_table(table):
    '''Clean up an excel-to-pdf table'''
    rejects_idx = []   # save indices of rows to remove
    pad_len = 12    # number of cells to pad to

    for idx, line in enumerate(table):
        if len(line) < 5: # too short
            if len(line) == 1 and line[0] == 'Data1ToExcel':
                rejects_idx.append(('header', idx))
            else:
                rejects_idx.append((None, idx))
            continue
        if len(line) > 20:  # too long to process
            rejects_idx.append(None, idx)
        if len(line) < pad_len:
            line += [Cell()] * (pad_len - len(line))#  as a TextBox
        fix_line(line)
        if len(line) > 15:  # too long after processing
            rejects_idx.append((None, idx))
            continue
    # remove the rejects
    rejects_idx.sort(key=lambda e: e[1], reverse=True) # go from high to low
    rejects = []
    rejects_idx_ret = []
    for i in rejects_idx:
        reason, idx = i
        if reason is None:
            rejects.append(table.pop(idx))
            rejects_idx_ret.append(idx)
        else:
            table.pop(idx)

    return rejects, rejects_idx_ret

def merge(line, idx1, idx2, f):
    line[idx1].text += f(line[idx2].text)
    line[idx1].tbs.extend(line[idx2].tbs)
    line.pop(idx2)

def fix_quote_name(line, cell_idx):
    '''
    Fix cases with RASHEI TEIVOT,
    Where a quote sign appears on a cell by its own, but really is there to connect the previous and following cells.
    Notable example: בע״מ
    '''
#    if re.match(r'\s*"\s*$', line[5]):
    if re.match(r'^\s*".?.?\s*$', line[cell_idx].text):
        # merge cells 5 and 6
        # 6 is 5 after the pop
        #line[4] += despaced(line.pop(5)) + line.pop(5)
        merge(line, cell_idx-1, cell_idx, despaced)

def fix_line(line):
    # Go over the various fixes to a line. Note that the order is important (first we fix the earlier cells = on the right of the table and the beginning of the list)
    for i, s in enumerate(line):
        line[i].text = line[i].text.strip()

    fix_house_number(line)
    fix_quote_name(line, 5)
    fix_quote_name(line, 9)
    fix_tree_sizes(line)
    fix_ils_sign(line)
    # if the "comments" cell  (הערות לבקשה) is empty, then the cells after it need to be shifted
    # we identify this by this cell being all digits. This corresponds to the content of the 3xfollowing cell - number of trees
    if len(line) >= 13 and re.match(r'\d+$', line[12].text):
        line.insert(10, Cell())

def fix_tree_sizes(line):
    # Re-attach a phrase which often gets split into two cells
    if re.search(r'גודל\s*$', line[10].text) and re.match(r'\s*\d+$', line[11].text):
        merge(line, 10, 11, spaced)

def fix_ils_sign(line):
    # The symbol for New Israeli Shekel is often put into its own cell, but should really attach to the previous cell
    if re.match(r'\s*₪\s*$', line[11].text):
        merge(line, 10, 11, spaced)

def fix_house_number(line):
    '''Patch a missing house number'''
    if line[8].text in ['שכונת מורדות לינקולן', 'גבעת זמר', 'ענבר', 'טיילת פתאל', 'אבא חושי אוניברסיטת חיפה']:
        line.insert(9, Cell())

def strip_cells(table):
    ret = [ [ c.text.strip() for c in line ] for line in table ]
    return ret

def table_to_cell_list(table_, colnames):
    cells = []
    for j, r in enumerate(table_):
        for i, C in enumerate(r):
            column = colnames[i]
            for tb in C.tbs:
                d = tb_to_dict(tb)
                d['col'] = column
                d['col_idx'] = i
                cells.append(d)

    df = pd.DataFrame(data=cells)
    return df

def tb_to_dict(tb):
    d = {}
    txt_nows = tb.text.strip()
    x = tb.tm[4]
    y = tb.tm[5]
    d['len'] = len(tb.text)
    d['int'] = bool(re.match('\d+$', txt_nows))
    d['has_digit'] = bool(re.search('\d', txt_nows))
    d['starts_ws'] = bool(re.match('\s', tb.text))
    d['ends_ws'] = bool(re.search('\s$', tb.text))
    d['all_letters'] = bool(re.match(r'^[A-Za-z\u05D0-\u05EA ]+$', tb.text))
    d['dx'] = tb.dx
    d['dy'] = tb.dy
    d['h_y'] = tb.h_y
    d['dx_raw'] = tb.dx_raw
    d['dy_raw'] = tb.dy_raw
    d['h_y_raw'] = tb.h_y_raw
    d['x'] = x
    d['y'] = y
    d['text'] = tb.text
    return d

def table_to_df(table_, colnames_file):
    return table_to_helper(table_, colnames_file, output='df')

def table_to_helper(table_, colnames_file, output='df'):
    table_ = table_[3:]          # strip header lines (we'll read the column names from a file)
    table = copy.deepcopy(table_)
    rej, rej_idx = fix_table(table)

    if rej_idx and min(rej_idx) < 10:
        warnings.warn('There are rejected lines near the top of the list')

    with open(colnames_file, 'r') as rf:
        colnames = list(map(lambda s: s.strip(), rf.readlines()))

    if output == 'df':
        # strip the TextBox wrappers
        text_table = strip_cells(table)
        df = pd.DataFrame(data=text_table)
        df.rename(columns=dict(enumerate(colnames)), inplace=True)
        return df, rej
    else:
        ret = table_to_cell_list(table, colnames)
        return ret, rej
