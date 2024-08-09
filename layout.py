from typing import List, Union, Literal
from tkinter import font

HSTEP, VSTEP = 13, 18
SCROLLBAR_WIDTH = 12


class Text:
  def __init__(self, text: str):
    self.text = text


class Tag:
  def __init__(self, tag: str):
    self.tag = tag


class Layout:
  def __init__(self, tokens: List[Union[Tag, Text]], screen_width: int, rtl: bool = False):
    self.rtl = rtl
    self.screen_width = screen_width
    self.display_list = []
    if self.rtl:
      self.cursor_x = self.screen_width - HSTEP - SCROLLBAR_WIDTH
    else:
      self.cursor_x = HSTEP
    self.cursor_y: int = VSTEP
    self.size: int = 16
    self.weight: Literal['normal', 'bold'] = "normal"
    self.style: Literal['roman', 'italic'] = "roman"
    for t in tokens:
      self.token(t)

  def token(self, t):
    if isinstance(t, str): \
      self.word(t)
    elif isinstance(t, Text):
      for w in t.text.split(" "):
        self.word(w)
    elif t.tag == "i":
      self.style = "italic"
    elif t.tag == "/i":
      self.style = "roman"
    elif t.tag == "b":
      self.weight = "bold"
    elif t.tag == "/b":
      self.weight = "normal"
    elif t.tag == "small":
      self.size -= 2
    elif t.tag == "/small":
      self.size += 2
    elif t.tag == "big":
      self.size += 4
    elif t.tag == "/big":
      self.size -= 4

  def word(self, w):
    f = font.Font(
      size=self.size,
      weight=self.weight,
      slant=self.style
    )
    if '\n' in w:
      newlines = w.split('\n')
      for w in newlines[:-1]:
        self.display_list.append((self.cursor_x, self.cursor_y, w, f))
        self.cursor_y += 1.5 * VSTEP
        if self.rtl:
          self.cursor_x = self.screen_width - HSTEP - SCROLLBAR_WIDTH
        else:
          self.cursor_x = HSTEP
      last = newlines[-1]
      if last:
        self.display_word(last, f)
    else:
      self.display_word(w, f)

  def display_word(self, w, f):
    space = f.measure(" ")
    linebreak = f.metrics("linespace") * 1.25
    width = f.measure(w)
    if self.rtl:
      if self.cursor_x - (width + space) > 0:
        self.display_list.append((self.cursor_x, self.cursor_y, w, f))
      else:
        self.cursor_x = self.screen_width - HSTEP - SCROLLBAR_WIDTH
        self.cursor_y += linebreak
        self.display_list.append((self.cursor_x, self.cursor_y, w, f))
      self.cursor_x -= (width + space)
    else:
      if self.cursor_x + width + space < self.screen_width - SCROLLBAR_WIDTH:
        self.display_list.append((self.cursor_x, self.cursor_y, w, f))
      else:
        self.cursor_x = HSTEP
        self.cursor_y += linebreak
        self.display_list.append((self.cursor_x, self.cursor_y, w, f))
      self.cursor_x += width + space
