import tkinter as tk
from typing import List, Union, Literal
from tkinter import font as tkfont

HSTEP, VSTEP = 13, 18
SCROLLBAR_WIDTH = 12
FONTS = {}
MEASURES = {}


def get_font(size, weight, style):
  key = (size, weight, style)
  if key not in FONTS:
    font = tkfont.Font(
      size=size,
      weight=weight,
      slant=style
    )
    label = tk.Label(font=font)
    FONTS[key] = (font, label)
  return FONTS[key][0]


def get_measure(s, size, weight, style):
  key = (s, size, weight, style)
  font = get_font(size, weight, style)
  if key not in MEASURES:
    measure = font.measure(s)
    MEASURES[key] = measure
  return MEASURES[key]


class Text:
  def __init__(self, text: str):
    self.text = text

  def __repr__(self):
    return self.text


class Tag:
  def __init__(self, tag: str):
    self.tag = tag

  def __repr__(self):
    return self.tag


class Layout:
  def __init__(self, tokens: List[Union[Tag, Text]], screen_width: int, rtl: bool = False):
    self.rtl = rtl
    self.screen_width = screen_width
    self.line = []
    self.display_list = []
    if self.rtl:
      self.cursor_x = self.screen_width - HSTEP - SCROLLBAR_WIDTH
    else:
      self.cursor_x = HSTEP
    self.cursor_y: int = VSTEP
    self.size: int = 16
    self.weight: Literal['normal', 'bold'] = "normal"
    self.style: Literal['roman', 'italic'] = "roman"
    for tok in tokens:
      self.token(tok)
    self.flush()

  def token(self, tok):
    if isinstance(tok, str): \
      self.word(tok)
    elif isinstance(tok, Text):
      for word in tok.text.split(" "):
        self.word(word)
    elif tok.tag == "i":
      self.style = "italic"
    elif tok.tag == "/i":
      self.style = "roman"
    elif tok.tag == "b":
      self.weight = "bold"
    elif tok.tag == "/b":
      self.weight = "normal"
    elif tok.tag == "small":
      self.size -= 2
    elif tok.tag == "/small":
      self.size += 2
    elif tok.tag == "big":
      self.size += 4
    elif tok.tag == "/big":
      self.size -= 4
    elif tok.tag == "br" or tok.tag == "br /":
      self.flush()
    elif tok.tag == "/p":
      self.flush()

  def word(self, word):
    font = get_font(self.size, self.weight, self.style)
    if '\n' in word:
      newlines = word.split('\n')
      for w in newlines[:-1]:
        self.line.append((self.cursor_x, w, font))
        self.flush()
      last = newlines[-1]
      if last:
        self.display_word(last, font)
    else:
      self.display_word(word, font)

  def display_word(self, word, font):
    space = get_measure(" ", self.size, self.weight, self.style)
    width = get_measure(word, self.size, self.weight, self.style)
    if self.rtl:
      if self.cursor_x - (width + space) > 0:
        # If there's still room on this line, add to self.line and advance cursor_x
        self.line.append((self.cursor_x, word, font))
        self.cursor_x -= (width + space)
      else:
        # Otherwise, finish this line
        self.flush()
    else:
      if self.cursor_x + width + space < self.screen_width - SCROLLBAR_WIDTH:
        # If there's still room on this line, add to self.line and advance cursor_x
        self.line.append((self.cursor_x, word, font))
        self.cursor_x += width + space
      else:
        # Otherwise, finish this line
        self.flush()

  def flush(self):
    if not self.line:
      return
    metrics = [font.metrics() for x, word, font in self.line]
    max_ascent = max([metric["ascent"] for metric in metrics])
    baseline = self.cursor_y + 1.25 * max_ascent
    for x, word, font in self.line:
      y = baseline - font.metrics("ascent")
      self.display_list.append((x, y, word, font))
    max_descent = max([metric['descent'] for metric in metrics])
    self.cursor_y = baseline + 1.25 * max_descent
    if self.rtl:
      self.cursor_x = self.screen_width - HSTEP - SCROLLBAR_WIDTH
    else:
      self.cursor_x = HSTEP
    self.line = []
