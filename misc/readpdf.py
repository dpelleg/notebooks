from PyPDF2 import PdfReader
import re
import pysnooper
import pickle

c=0
prev_x = 0

class Cell:
    '''A cell of text inside of a table'''
    def __init__(self):
        self.all_x = []    # a list of the X offsets of text fragments in this cell
        self.text = ''     # the text of the cell
        self.has_linebreaks = False

    def max_x(self):
        return max(self.all_x)

    def min_x(self):
        return min(self.all_x)

    def add_text(self, text, x, linebreaks=False):
        if re.search(r'\S$', self.text) and re.search(r'^\S', text):   # add a spacer
            text = " " + text
        self.text += text
        self.all_x.append(x)
        self.has_linebreaks = linebreaks

    def __str__(self):
        return self.text

def clip(x):
    tol = 1
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
    glue = False

#@pysnooper.snoop('log.txt', color=False, relative_time=True)
def visitor_body_delta_vector(text, cm, tm, fontDict, fontSize):
    global curr_cell, curr_row, table, baseline_y, prev_x, prev_y, glue
    # skip spacers
    if re.match(r'^\s*$', text):
        return

    if False and re.search(r'גודל', text):
        glue = True

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
            bound_cands.append(x)
        else:    # stay at the same cell
            curr_cell.add_text(text, x, linebreaks=True)
            handled = True
    if dx < 0 and dy == 0:      # moving left
        if h_y == 0:    # on the baseline height. Move to a new cell, unless ...
            if curr_cell.has_linebreaks and glue:           # this is a hack to deal with bad dumps from the Haifa municipality
                curr_cell.add_text(text, x)
                glue = False
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
        bound_cands.append(x)
    if dx == 0 and dy < 0:         # moving straight down
        if True or h_y >= 0:       # same cell
            curr_cell.add_text(text, x)
            handled = True
        else:
            print("?")

    if not handled:
        curr_cell.add_text(text, x)

    prev_x = x
    prev_y = y
    return

c=0
@pysnooper.snoop('log.txt', color=False, relative_time=True)
def visitor_body_boundaries(text, cm, tm, fontDict, fontSize):
    global c
    global curr_cell, curr_row, table
    # skip spacers
    if re.match(r'^\s*$', text):
        return
    right_border = boundaries[curr_cell]
    left_border = boundaries[curr_cell+1] if curr_cell+1 < len(boundaries) else 0
    x = tm[4]
    if x<=right_border and x > left_border:     # add to current cell
        curr_row[-1] += text
    elif x<=left_border:                        # move to next cell
        curr_cell += 1
        curr_row.append(text)
    else:                       # start a new row
        table.append(curr_row)
        curr_cell = 0
        curr_row = [text]
#        if c > 5:
#            exit(1)
        c+=1
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

@pysnooper.snoop('log.txt')
def visitor_body2(text, cm, tm, fontDict, fontSize):
    global table, curr_row, first_row, append_next
    if append_next:
        if len(curr_row) == 0:
            curr_row = ['']
        curr_row[-1] += text
        append_next = False
        return
    if text == '':   # move to next cell
        curr_row.append('')
    elif text == "\n":   # this might either mean move to next row, if we've seen enough cells, or else a intra-cell line break
        ncells = len(curr_row)
        if first_row or ncells >= ncells_in_row: # move to next row
            first_row = False
            table.append(curr_row)
            curr_row = []
        else:       # append following text to current cell
            append_next = True
    else:
        if len(curr_row) == 0:
            curr_row = ['']
        curr_row[-1] += text

reader = PdfReader("rptPirsum.pdf")

bound_cands = []
table = []
#for page in reader.pages:
for i in range(len(reader.pages)):
    curr_row = []
    curr_cell = None
    baseline_y = None
    glue = False

    print(i)

    reader.pages[i].extract_text(visitor_text=visitor_body_delta_vector)
    #reader.pages[i].extract_text(visitor_text=visitor_body_dump_struct)


with open('table.pickle', 'wb') as handle:
    pickle.dump(table, handle)
