import re
import copy
import pandas as pd

class TextBox:
    '''Represents a box on the space of a document, containing a string of text'''
    def __init__(self, text, cm, tm, fontDict, fontSize, dx=None, dy=None, h_y=None):
        self.text = text
        self.cm = cm
        self.tm = tm
        self.fontDict = fontDict
        self.fontSize = fontSize
        self.dx = dx
        self.dy = dy
        self.h_y = h_y
        self.dx_raw = None
        self.dy_raw = None
        self.h_y_raw = None

    def make_blank_textbox(text=''):
        return TextBox(text, None, None, None, None)

    def to_dict(self):
        d = {}
        txt_nows = self.text.strip()
        x = self.tm[4]
        y = self.tm[5]
        d['len'] = len(self.text)
        d['int'] = bool(re.match('\d+$', txt_nows))
        d['has_digit'] = bool(re.search('\d', txt_nows))
        d['starts_ws'] = bool(re.match('\s', self.text))
        d['ends_ws'] = bool(re.search('\s$', self.text))
        d['all_letters'] = bool(re.match(r'^[A-Za-z\u05D0-\u05EA ]+$', self.text))
        d['dx'] = self.dx
        d['dy'] = self.dy
        d['h_y'] = self.h_y
        d['dx_raw'] = self.dx_raw
        d['dy_raw'] = self.dy_raw
        d['h_y_raw'] = self.h_y_raw
        d['x'] = x
        d['y'] = y
        d['text'] = self.text
        return d


class Cell:
    '''Helper class to represent a cell of text inside of a table'''
    def __init__(self):
        self.all_x = []    # a list of the X offsets of text fragments in this cell
        self.text = ''     # the text of the cell
        self.has_linebreaks = False
        self.tbs = []      # a list of all constituent TextBox elements

    def max_x(self):
        return max(self.all_x)

    def min_x(self):
        return min(self.all_x)

    def add_text(self, tb, x=None, pad=True, linebreaks=False):
        if pad and re.search(r'\S$', self.text) and re.search(r'^\S', tb.text):   # add a spacer
            tb.text = " " + tb.text
        self.text += tb.text
        self.tbs.append(tb)
        self.all_x.append(x)
        self.has_linebreaks = linebreaks

    def __str__(self):
        return self.text

def preprocess_tbs_data(tbs):
    '''
    Given a dataframe where each row represents a TextBox, prepare it for fitting/prediction
    '''
    tbs['len'] = tbs['len'].astype('float')

    # drop the output variable
    out_var = 'col_idx'
    #out_var = 'col'    # used for debugging
    if out_var in tbs.columns:
        y = tbs[out_var]
    else:
        y = None
    X = tbs.drop(columns=['col', 'col_idx'], errors='ignore')

    # drop input variables which only complicate things
    to_drop = ['y', 'text']      # This is the column y (vertical displacement), not the output variable
    X = X.drop(to_drop, axis=1)

    if y:
        return X, y
    else:
        return X

def read_colnames(colnames_file):
    with open(colnames_file, 'r') as rf:
        colnames = list(map(lambda s: s.strip(), rf.readlines()))
    return colnames

def pred_cells_from_table(table_, colnames_file, pred_model):
    colnames = read_colnames(colnames_file)

    ret = []
    rej = []

    table_ = table_[3:]          # strip header lines (we'll read the column names from a file)
    table = copy.deepcopy(table_)
    for j, r in enumerate(table_):   # for each row in table
        tbs = []
        for i, C in enumerate(r):    # for each Cell in row
            for tb in C.tbs:         # for each TextBox in Cell
                d = tb.to_dict()
                tbs.append(d)
        df = pd.DataFrame(data=tbs)
        pred_row = predict_cells(df, pred_model)
        fixed_row = fix_row_indices(pred_row, colnames)
        # the excel-to-pdf page header shows up as a row, drop it
        if 'Data1ToExcel' in fixed_row.values():
            continue
        if fixed_row is None:
            rej.append(j)
        else:
            ret.append(fixed_row)
    ret = pd.DataFrame(data=ret)
    return ret, rej

def check_monotonically_nondecreasing(v):
    prev = v[0]
    for i in range(1, len(v)):
        if v[i] < prev:
            return False
        prev = v[i]
    return True

def predict_cells(df, pred_model):
    data = preprocess_tbs_data(df)
    pred = pred_model.predict(data)
    data['pred'] = pred
    data['text'] = df['text']
    return data

def fix_row_indices(row, colnames):
    # map a list of TextBoxen, each with a predicted column index, into a dictionary of columns

    # create a list of empty cells
    cells = [Cell() for _ in colnames]
    # add each piece of text to the corresponding cell

    prev_pred_col = None     # remember where we added the previous piece of text
    for index, tb in row.iterrows():
        d = tb.to_dict()
        pred_col = d['pred']
        # the text we see goes along the page monotonically. So jumping back to a previous column should not happen
        # if we see this, heuristically bump the text to the last seen column
        if prev_pred_col is not None:
            if pred_col < prev_pred_col:
                pred_col = prev_pred_col
        cells[pred_col].add_text(TextBox.make_blank_textbox(d['text']))
        prev_pred_col = pred_col

    # reformat as a dictionary of columns
    ret = {}
    for i, c in enumerate(colnames):
        ret[c] = cells[i].text

    return ret
