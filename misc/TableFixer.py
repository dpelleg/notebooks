import copy
import pandas
import re
import pandas as pd
import warnings

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
            line += [''] * (pad_len - len(line))
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

def fix_quote_name(line, cell_idx):
    '''
    Fix cases with RASHEI TEIVOT,
    Where a quote sign appears on a cell by its own, but really is there to connect the previous and following cells.
    Notable example: בע״מ
    '''
#    if re.match(r'\s*"\s*$', line[5]):
    if re.match(r'^\s*".?.?\s*$', line[cell_idx]):
        # merge cells 5 and 6
        # 6 is 5 after the pop
        #line[4] += despaced(line.pop(5)) + line.pop(5)
        line[cell_idx-1] += despaced(line.pop(cell_idx))

def fix_line(line):
    # Go over the various fixes to a line. Note that the order is important (first we fix the earlier cells = on the right of the table and the beginning of the list)
    for i, s in enumerate(line):
        line[i] = line[i].strip()

    fix_house_number(line)
    fix_quote_name(line, 5)
    fix_quote_name(line, 9)
    fix_tree_sizes(line)
    fix_ils_sign(line)
    # if the "comments" cell  (הערות לבקשה) is empty, then the cells after it need to be shifted
    # we identify this by this cell being all digits. This corresponds to the content of the 3xfollowing cell - number of trees
    if len(line) >= 13 and re.match(r'\d+$', line[12]):
        line.insert(10, '')


def fix_tree_sizes(line):
    # Re-attach a phrase which often gets split into two cells
    if re.search(r'גודל\s*$', line[10]) and re.match(r'\s*\d+$', line[11]):
        line[10] += spaced(line.pop(11))

def fix_ils_sign(line):
    # The symbol for New Israeli Shekel is often put into its own cell, but should really attach to the previous cell
    if re.match(r'\s*₪\s*$', line[11]):
        line[10] += spaced(line.pop(11))

def fix_house_number(line):
    '''Patch a missing house number'''
    if line[8] in ['שכונת מורדות לינקולן', 'גבעת זמר', 'ענבר', 'טיילת פתאל', 'אבא חושי אוניברסיטת חיפה']:
        line.insert(9, '')

def table_to_df(table_, colnames_file):
    table_ = table_[3:]          # strip header lines (we'll read the column names from a file)
    table = copy.deepcopy(table_)
    rej, rej_idx = fix_table(table)

    if rej_idx and min(rej_idx) < 10:
        warnings.warn('There are rejected lines near the top of the list')

    with open(colnames_file, 'r') as rf:
        colnames = list(map(lambda s: s.strip(), rf.readlines()))

    df = pd.DataFrame(data=table)
    df.rename(columns=dict(enumerate(colnames)), inplace=True)
    return df, rej
