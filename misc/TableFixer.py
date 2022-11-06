import copy
import pandas
import re
import pandas as pd

# text file with column headers, one per line
colnames_file = 'colnames-haifa.txt'

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
            rejects_idx.append(idx)
            continue
        if len(line) > 20:  # too long to process
            rejects_idx.append(idx)
        if len(line) < pad_len:
            line += [''] * (pad_len - len(line))
        #print(idx, end = ' ')
        fix_line(line)
        if len(line) > 15:  # too long after processing
            rejects_idx.append(idx)
            continue
    # remove the rejects
    rejects_idx.reverse() # go from high to low
    rejects = []
    for i in rejects_idx:
        #print("rejecting " + str(i))
        rejects.append(table.pop(i))
    return rejects

def fix_quote_name(line):
    '''
    Fix cases with RASHEI TEIVOT,
    Where a quote sign appears on a cell by its own, but really is there to connect the previous and following cells.
    Notable example: בע״מ
    '''
    if re.match(r'\s*"\s*$', line[5]):
        # merge cells 5 and 6
        # 6 is 5 after the pop
        line[4] += despaced(line.pop(5)) + line.pop(5)

def fix_line(line):
    # Go over the various fixes to a line. Note that the order is important (first we fix the earlier cells = on the right of the table and the beginning of the list)
    for i, s in enumerate(line):
        line[i] = line[i].strip()
    fix_house_number(line)
    fix_quote_name(line)
    fix_tree_sizes(line)
    fix_ils_sign(line)

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
    if line[8] in ['שכונת מורדות לינקולן', 'גבעת זמר', 'ענבר', 'טיילת פתאל']:
        line.insert(9, '')


def table_to_df(table_):
    table_ = table_[3:]          # strip header lines (we'll read the column names from a file)
    table = copy.deepcopy(table_)
    rej = fix_table(table)

    with open(colnames_file, 'r') as rf:
        colnames = list(map(lambda s: s.strip(), rf.readlines()))

    df = pd.DataFrame(data=table)
    df.rename(columns=dict(enumerate(colnames)), inplace=True)
    return df, rej
