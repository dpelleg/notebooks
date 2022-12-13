from PyPDF2 import PdfReader
import re
import pysnooper
import pandas as pd
from TableFixer import table_to_df, table_to_helper
from pdfhelper import Cell, TextBox, pred_cells_from_table
import pickle
import argparse

# Written by Dan Pelleg

'''
Read the excel-to-PDF file found at
https://www.haifa.muni.il/development-and-construction/engineering-administration/uprooting-trees/

Typical usage:
python readpdf.py -m col_classifier.pkl -i rptPirsum.pdf

Then the output is stored at table.csv

'''
c=0
prev_x = 0

def clip(x, tol=1):
    # clip a near-zero value to zero
    if abs(x) < tol:
        x = 0
    return x

def add_to_current_cell(tb):
    global table, curr_row
    assert(True)
    add_to = curr_row[-1]
    if not (False and re.match(r'["מח]$', tb.text)) and re.search(r'\S$', add_to.text) and re.search(r'^\S', tb.text):   # add a spacer
        tb.text = " " + tb.text
    curr_row[-1] += tb

def new_cell(tb, x):
    global curr_row, curr_cell
    curr_row.append(curr_cell)
    curr_cell = Cell()
    curr_cell.add_text(tb, x)

def new_row(tb, x):
    global table, curr_row, curr_cell
    # first add the text in the current cell to the end of the current row
    new_cell(tb, x)
    table.append(curr_row)
    curr_row = []

#@pysnooper.snoop('log.txt', color=False, relative_time=True)
def visitor_body_delta_vector(text, cm, tm, fontDict, fontSize):
    global curr_cell, curr_row, table, baseline_y, prev_x, prev_y

    # skip spacers
    if re.match(r'^\s*$', text):
        return

    handled = False

    x = tm[4]
    y = tm[5]

    tb = TextBox(text, cm, tm, fontDict, fontSize)

    if baseline_y is None: # first call
        prev_x = x
        prev_y = y
        baseline_y = y
        curr_cell = Cell()
        curr_cell.add_text(tb, x)
        curr_row = []
        return

    # calculate amount of movement in each dimension and above the Y baseline
    dx = (x - prev_x)
    dy = (y - prev_y)
    h_y = (y - baseline_y)
    tb.dx_raw = dx
    tb.dy_raw = dy
    tb.h_y_raw = h_y
    dx = clip(dx)
    dy = clip(dy)
    h_y = clip(h_y)
    tb.dx = dx
    tb.dy = dy
    tb.h_y = h_y

    if dx > 0 and dy < 0:      # moving right and down
        if y < baseline_y:     # move from end of previous row to start of a new row
            baseline_y = y
            new_row(tb, x)
            handled = True
        else:    # stay at the same cell
            curr_cell.add_text(tb, x, pad=True, linebreaks=True)
            handled = True
    if dx < 0 and dy == 0:      # moving left
        if h_y == 0:    # on the baseline height. Move to a new cell, unless ...
            dx_to_cell_left = x - curr_cell.min_x()
            if dx_to_cell_left >= -2:               # this is a hack to deal with bad dumps from the Haifa municipality
                curr_cell.add_text(tb, x)
                handled = True
            elif dx > -9 and len(text) <= 2 and not re.match(r'^\d+$', text):               # this is a hack to deal with bad dumps from the Haifa municipality
                curr_cell.add_text(tb, x, pad=False)
                handled = True
            else:
                new_cell(tb, x)
                handled = True
        else:           # still at same cell
            curr_cell.add_text(tb, x)
            handled = True
    if dx < 0 and dy > 0:  # moving left and up - create a new cell
        new_cell(tb, x)
        handled = True
    if dx == 0 and dy < 0:         # moving straight down
        curr_cell.add_text(tb, x)
        handled = True

    if not handled:
        curr_cell.add_text(tb, x)
        handled = True

    prev_x = x
    prev_y = y
    return

def visitor_body_dump_struct(text, cm, tm, fontDict, fontSize):
    global c, prev_x
    if False and re.match(r'^\s*$', text):
        return
    x = tm[4]
    y = tm[5]
    xr = x + fontSize*len(text)
    xl = x - fontSize*len(text)
    dx = x - prev_x
    prev_x = x
    print(",".join([x, y, xr, xl]))
    #print("dx={:0.0f} x={:0.0f} got |{}|".format(dx, x, text))

parser = argparse.ArgumentParser(description="Read an excel-to-PDF file and save it as a dataframe")
parser.add_argument("-i", "--input", default='rptPirsum.pdf', help="name of input PDF file")
parser.add_argument("-o", "--output", default='df.csv', help="name of output CSV file")
parser.add_argument("-c", "--colnames", default='colnames-haifa.txt', help='text file with column headers, one per line')
parser.add_argument("-m", "--model", help='ML model file to predict columns')
parser.add_argument("-C", "--Cells", action='store_true', help="instead of a table, output a list of cell features")
parser.add_argument("-d", "--debug", action='store_true', help="debug mode")
config = vars(parser.parse_args())

reader = PdfReader(config['input'])

table = []
debug = config['debug']
pred_model = None
if config['model']:
    with open(config['model'], 'rb') as file:
        pred_model = pickle.load(file)

if debug:
    pagelist = [0]
else:
    pagelist = range(len(reader.pages))
for i in pagelist:
    curr_row = []
    curr_cell = None
    baseline_y = None

    if i % 10 == 0:
        print(i, end ='...', flush=True)

    reader.pages[i].extract_text(visitor_text=visitor_body_delta_vector)
print()

if debug:
    with open('table.pickle', 'wb') as f:
        pickle.dump(table, f)
    if pred_model is not None:
        df, rej = pred_cells_from_table(table, config['colnames'], pred_model)
    elif config['Cells']:
        df, rej = table_to_helper(table, config['colnames'], output='cell_list')
    else:
        df, rej = table_to_df(table, config['colnames'])
    if len(rej) > 0:
        print("rejects:")
        for r in rej:
            print(r)
    if pred_model is not None:
        df.to_csv('table.csv', index=False)
    elif config['Cells']:
        df.to_csv('cells.csv', index=False)
    else:
        print(df.head())
else:
    if pred_model is not None:
        df, rej = pred_cells_from_table(table, config['colnames'], pred_model)
        df.to_csv('table.csv', index=False)
    elif config['Cells']:
        df, rej = table_to_helper(table, config['colnames'], output='cell_list')
        df.to_csv('cells.csv', index=False)
    else:
        df, rej = table_to_df(table, config['colnames'])
        df.to_csv('df.csv', index=False)
    print("Data saved, {} lines process, {} lines rejected".format(len(df), len(rej)))
