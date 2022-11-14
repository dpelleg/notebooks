from PyPDF2 import PdfReader
import re
import pysnooper
import pandas as pd
from TableFixer import table_to_df
import pickle

# Written by Dan Pelleg

'''
Read the excel-to-PDF file found at
https://www.haifa.muni.il/development-and-construction/engineering-administration/uprooting-trees/
'''
c=0
prev_x = 0

class Cell:
    '''Helper class to represent a cell of text inside of a table'''
    def __init__(self):
        self.all_x = []    # a list of the X offsets of text fragments in this cell
        self.text = ''     # the text of the cell
        self.has_linebreaks = False

    def max_x(self):
        return max(self.all_x)

    def min_x(self):
        return min(self.all_x)

    def add_text(self, text, x, pad=True, linebreaks=False):
        if pad and re.search(r'\S$', self.text) and re.search(r'^\S', text):   # add a spacer
            text = " " + text
        self.text += text
        self.all_x.append(x)
        self.has_linebreaks = linebreaks

    def __str__(self):
        return self.text

def clip(x, tol=1):
    # clip a near-zero value to zero
    if abs(x) < tol:
        x = 0
    return x

def add_to_current_cell(text):
    global table, curr_row
    assert(True)
    add_to = curr_row[-1]
    if not (False and re.match(r'["מח]$', text)) and re.search(r'\S$', add_to) and re.search(r'^\S', text):   # add a spacer
        text = " " + text
    curr_row[-1] += text

def new_cell(text, x):
    global curr_row, curr_cell
    curr_row.append(str(curr_cell))
    curr_cell = Cell()
    curr_cell.add_text(text, x)

def new_row(text, x):
    global table, curr_row, curr_cell
    # first add the text in the current cell to the end of the current row
    new_cell(text, x)
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

    if baseline_y is None: # first call
        prev_x = x
        prev_y = y
        baseline_y = y
        curr_cell = Cell()
        curr_cell.add_text(text, x)
        curr_row = []
        return

    # calculate amount of movement in each dimension and above the Y baseline
    dx = clip(x - prev_x)
    dy = clip(y - prev_y)
    h_y = clip(y - baseline_y)

    if dx > 0 and dy < 0:      # moving right and down
        if y < baseline_y:     # move from end of previous row to start of a new row
            baseline_y = y
            new_row(text, x)
            handled = True
        else:    # stay at the same cell
            curr_cell.add_text(text, x, pad=True, linebreaks=True)
            handled = True
    if dx < 0 and dy == 0:      # moving left
        if h_y == 0:    # on the baseline height. Move to a new cell, unless ...
            dx_to_cell_left = x - curr_cell.min_x()
            if dx_to_cell_left >= -2:               # this is a hack to deal with bad dumps from the Haifa municipality
                curr_cell.add_text(text, x)
                handled = True
            elif dx > -9 and len(text) <= 2 and not re.match(r'^\d+$', text):               # this is a hack to deal with bad dumps from the Haifa municipality
                curr_cell.add_text(text, x, pad=False)
                handled = True
            else:
                new_cell(text, x)
                handled = True
        else:           # still at same cell
            curr_cell.add_text(text, x)
            handled = True
    if dx < 0 and dy > 0:  # moving left and up - create a new cell
        new_cell(text, x)
        handled = True
    if dx == 0 and dy < 0:         # moving straight down
        curr_cell.add_text(text, x)
        handled = True

    if not handled:
        curr_cell.add_text(text, x)
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
    print("dx={:0.0f} x={:0.0f} got |{}|".format(dx, x, text))


reader = PdfReader("rptPirsum.pdf")

table = []
debug = False
#debug = True
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
    for r in table:
        print(r)
    df, rej = table_to_df(table)
    if len(rej) > 0:
        print("rejects:")
        for r in rej:
            print(r)
    print(df.head())
else:
    df, rej = table_to_df(table)
    df.to_pickle('df.pickle')
    print("Data saved, {} lines process, {} lines rejected".format(len(df), len(rej)))
