import tkinter as tk
from typing import List, Union, Literal, Dict
from tkinter import font as tkfont
from parser import Element, Text

HSTEP, VSTEP = 13, 18
SCROLLBAR_WIDTH = 12
FONTS = {}
MEASURES = {}


def get_font(size, weight, style):
  key = (size, weight, style)
  if key not in FONTS:
    if "fixed_width" in style:
      s = style.replace("fixed_width", "").strip()
      font = tkfont.Font(
        family="Courier",
        size=size,
        weight=weight,
        slant=s
      )
    else:
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


class Layout:
  def __init__(self, tree, screen_width: int):
    self.centering = False
    self.superscript = False
    self.pre = False
    self.screen_width = screen_width
    self.line = []
    self.display_list = []
    self.cursor_x = HSTEP
    self.cursor_y: int = VSTEP
    self.size: int = 16
    self.weight: Literal['normal', 'bold'] = "normal"
    self.style: Literal['roman', 'italic', 'roman fixed_width', "italic fixed_width"] = "roman"
    # TODO figure out a more elegant way of identifying view-source mode
    if isinstance(tree, list):
      for tok in tree:
        self.recurse(tok)
    else:
      self.recurse(tree)
    self.flush()

  def open_tag(self, element: Element):
    if element.tag == "i":
      if "fixed_width" in self.style:
        self.style = "italic fixed_width"
      else:
        self.style = "italic"
    elif element.tag == "b":
      self.weight = "bold"
    elif element.tag == "small":
      self.size -= 2
    elif element.tag == "big":
      self.size += 4
    elif element.tag == "br":
      self.flush()
    elif element.tag == 'h1':
      self.size = int(self.size * 1.5)
      if "title" in element.attributes.get('class', ''):
        self.centering = True
    elif element.tag == "sup":
      self.size = int(self.size / 2)
      self.superscript = True
    elif element.tag == "pre":
      self.style += " fixed_width"
      self.pre = True

  def close_tag(self, element: Element):
    if element.tag == "i":
      if "fixed_width" in self.style:
        self.style = "roman fixed_width"
      else:
        self.style = "roman"
    elif element.tag == "b":
      self.weight = "normal"
    elif element.tag == "small":
      self.size += 2
    elif element.tag == "big":
      self.size -= 4
    elif element.tag == "p":
      self.flush()
    elif element.tag == "h1":
      self.size = int(self.size / 1.5)
      self.centering = False
    elif element.tag == "sup":
      self.size = int(self.size * 2)
      self.superscript = False
    elif element.tag == "pre":
      self.style = self.style.replace("fixed_width", "").strip()
      self.pre = False

  def recurse(self, tree):
    # This presents view-source with a fixed_width font
    if isinstance(tree, str):
      self.style += " fixed_width"
      self.word(tree)
    elif isinstance(tree, Text):
      words = []
      if self.pre:
        word = ''
        for c in tree.text:
          if c == ' ' or c == '\n':
            if word:
              words.append(word)
            word = ''
            words.append(c)
          else:
            word += c
        if word:
          words.append(word)
      else:
        words = tree.text.split()
      for word in words:
        self.word(word)
    else:
      self.open_tag(tree)
      for child in tree.children:
        self.recurse(child)
      self.close_tag(tree)

  def word(self, word):
    space = get_measure(" ", self.size, self.weight, self.style)
    width = get_measure(word, self.size, self.weight, self.style)
    if self.pre:
      if word == '\n':
        self.flush()
      else:
        self.line.append({"x": self.cursor_x,
                          "word": word,
                          "size": self.size,
                          "weight": self.weight,
                          "style": self.style,
                          "centering": self.centering,
                          "superscript": self.superscript
                          })
        self.cursor_x += width
    elif self.cursor_x + width + space < self.screen_width - SCROLLBAR_WIDTH:
      # If there's still room on this line, add to self.line and advance cursor_x
      self.line.append({"x": self.cursor_x,
                        "word": word,
                        "size": self.size,
                        "weight": self.weight,
                        "style": self.style,
                        "centering": self.centering,
                        "superscript": self.superscript
                        })
      self.cursor_x += width + space
    else:
      if u"\u00AD" in word:
        parts = word.split(u"\u00AD")
        hyphen = get_measure("-", self.size, self.weight, self.style)
        taken = []
        count = 0
        for part in parts:
          part_width = get_measure(part, self.size, self.weight, self.style)
          if self.cursor_x + part_width + hyphen < self.screen_width - SCROLLBAR_WIDTH:
            self.line.append({"x": self.cursor_x,
                              "word": part,
                              "size": self.size,
                              "weight": self.weight,
                              "style": self.style,
                              "centering": self.centering,
                              "superscript": self.superscript
                              })
            self.cursor_x += part_width
            taken.append(part)
            count += 1
          else:
            # We've fit all the parts we can fit onto the line (plus hyphen) so break
            break

        leftovers = ''.join([p for p in parts if p not in taken])
        if count > 0:
          self.line.append({
            "x": self.cursor_x,
            "word": "-",
            "size": self.size,
            "weight": self.weight,
            "style": self.style,
            "centering": self.centering,
            "superscript": self.superscript
          })
        nextline = {
          "word": leftovers,
          "size": self.size,
          "weight": self.weight,
          "style": self.style,
          "centering": self.centering,
          "superscript": self.superscript
        }
        self.flush(nextline)
      else:
        # Otherwise, finish this line
        self.flush()

  def flush(self, nextline: Dict[str, Union[int, str, bool]] = None):
    if not self.line:
      return

    centering = any([entry['centering'] for entry in self.line])
    if centering:
      last_entry = self.line[-1]
      last_length = get_measure(last_entry['word'], last_entry['size'], last_entry['weight'], last_entry["style"])
      line_length = (last_entry["x"] - self.line[0]["x"]) + last_length
      delta_x = (self.screen_width - line_length) / 2
    else:
      delta_x = 0

    fonts = [get_font(entry['size'], entry['weight'], entry['style']) for entry in self.line]
    metrics = [font.metrics() for font in fonts]
    max_ascent = max([metric["ascent"] for metric in metrics])
    baseline = self.cursor_y + 1.25 * max_ascent

    for i, entry in enumerate(self.line):
      font = fonts[i]
      if entry["superscript"]:
        y = baseline - max_ascent
      else:
        y = baseline - font.metrics("ascent")
      # delta_x is zero if not centering
      self.display_list.append((entry['x'] + delta_x, y, entry['word'], font))

    max_descent = max([metric['descent'] for metric in metrics])
    self.cursor_y = baseline + 1.25 * max_descent
    self.cursor_x = HSTEP
    if nextline:
      nextline["x"] = self.cursor_x
      self.line = [nextline]
      self.cursor_x += get_measure(nextline["word"] + " ",
                                   nextline["size"],
                                   nextline["weight"],
                                   nextline["style"])
    else:
      self.line = []
