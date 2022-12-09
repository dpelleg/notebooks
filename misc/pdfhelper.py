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

    def make_blank_textbox():
        return TextBox('', None, None, None, None)

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
