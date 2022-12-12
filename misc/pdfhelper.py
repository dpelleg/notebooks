import re

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

    def make_blank_textbox():
        return TextBox('', None, None, None, None)

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

    def add_text(self, tb, x, pad=True, linebreaks=False):
        if pad and re.search(r'\S$', self.text) and re.search(r'^\S', tb.text):   # add a spacer
            tb.text = " " + tb.text
        self.text += tb.text
        self.tbs.append(tb)
        self.all_x.append(x)
        self.has_linebreaks = linebreaks

    def __str__(self):
        return self.text

def preprocess_cell_data(cells):
    '''
    Given a dataframe where each row represents a Cell, prepare it for fitting/prediction
    '''
    cells['len'] = cells['len'].astype('float')

    # drop the output variable
    #y = cells['col']    # used for debugging
    y = cells['col_idx']
    X = cells.drop(columns=['col', 'col_idx'])

    # drop input variables which only complicate things
    to_drop = ['y', 'text']
    X = X.drop(to_drop,axis=1)

    return X, y
