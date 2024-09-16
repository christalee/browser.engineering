import tkinter as tk
from typing import Union, Literal, Dict
from tkinter import font as tkfont

from css import INHERITED_PROPERTIES
from parser import Element, Text
from draw import DrawText, DrawRect, DrawEmoji
import emoji

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


def paint_tree(layout_object, display_list):
  display_list.extend(layout_object.paint())

  for child in layout_object.children:
    paint_tree(child, display_list)


class DocumentLayout:
  def __init__(self, node, screen_width):
    self.node = node
    self.parent = None
    self.previous = None
    self.children = []

    self.width = 0
    self.height = 0
    self.x = 0
    self.y = 0
    self.screen_width = screen_width

  def layout(self):
    child = BlockLayout(self.node, self, None)
    self.children.append(child)
    self.width = self.screen_width - (2 * HSTEP)
    self.x = HSTEP
    self.y = VSTEP
    child.layout()
    self.height = child.height

  def paint(self):
    return []


class BlockLayout:
  BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside", "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote", "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset", "legend", "details", "summary"
  ]

  def __init__(self, node, parent, previous):
    self.node = node
    self.parent = parent
    self.previous = previous
    self.children = []
    self.display_list = []
    self.line = []

    self.x = None
    self.y = None
    self.width = None
    self.height = None

    self.centering = False
    self.superscript = False
    self.pre = False

    self.cursor_x: int = HSTEP
    self.cursor_y: int = VSTEP

  def __repr__(self):
    return f"BlockLayout[{self.layout_mode()}](x={self.x}, y={self.y}, width={self.width}, height={self.height}, node={self.node})"

  def layout_mode(self):
    if isinstance(self.node, Text):
      return "inline"
    elif any([isinstance(child, Element) and child.tag in self.BLOCK_ELEMENTS for child in self.node.children]):
      return "block"
    elif self.node.children:
      return "inline"
    else:
      return "block"

  def layout(self):
    self.x = self.parent.x
    if self.previous:
      self.y = self.previous.y + self.previous.height
    else:
      self.y = self.parent.y
    self.width = self.parent.width

    mode = self.layout_mode()
    if mode == "block":
      previous = None
      for child in self.node.children:
        if isinstance(child, Element) and child.tag == "head":
          continue
        nxt = BlockLayout(child, self, previous)
        self.children.append(nxt)
        previous = nxt
    else:
      self.cursor_x = 0
      self.cursor_y = 0

      self.line = []
      self.recurse(self.node)
      self.flush()

    for child in self.children:
      child.layout()

    if mode == "block":
      self.height = sum([child.height for child in self.children])
    else:
      self.height = self.cursor_y

  def paint(self):
    cmds = []
    bgcolor = self.node.style.get('background-color', 'transparent')
    if bgcolor != "transparent":
      x2 = self.x + self.width
      y2 = self.y + self.height
      cmds.append(DrawRect(self.x, self.y, x2, y2, bgcolor))
    # if isinstance(self.node, Element) and (
    #   self.node.tag == "pre" or (self.node.tag == "nav" and "links" in self.node.attributes.get('class', ''))):
    #   x2 = self.x + self.width
    #   y2 = self.y + self.height
    #   cmds.append(DrawRect(self.x, self.y, x2, y2, "light gray"))
    if isinstance(self.node, Element) and self.node.tag == "li" and \
      isinstance(self.node.parent, Element) and self.node.parent.tag == "ul":
      x2 = self.x + 4
      y1 = self.y + (self.height / 2) - 2
      y2 = y1 + 4
      cmds.append(DrawRect(self.x, y1, x2, y2, "black"))
    if self.layout_mode() == "inline":
      for x, y, word, font, color in self.display_list:
        if emoji.is_emoji(word):
          cmds.append(DrawEmoji(x, y, word))
        else:
          cmds.append(DrawText(x, y, word, font, color))
    return cmds

  def open_tag(self, element: Element):
    if element.tag == "br":
      self.flush()
    elif element.tag == 'h1':
      if "title" in element.attributes.get('class', ''):
        self.centering = True
    elif element.tag == "sup":
      self.superscript = True
    elif element.tag == "pre":
      self.pre = True

  def close_tag(self, element: Element):
    if element.tag == "p":
      self.flush()
    elif element.tag == "h1":
      self.centering = False
    elif element.tag == "sup":
      self.superscript = False
    elif element.tag == "pre":
      self.pre = False

  def recurse(self, tree):
    if isinstance(tree, Text):
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
        self.word(tree, word)
    else:
      self.open_tag(tree)
      for child in tree.children:
        self.recurse(child)
      self.close_tag(tree)

  def create_word(self, word, x=None, size=None, weight=None, style=None, centering=None, superscript=None, color=None):
    return {
      "x": x if x else self.cursor_x,
      "word": word,
      "size": size if size else 16,
      "weight": weight if weight else "normal",
      "style": style if style else "roman",
      "color": color if color else "black",
      "centering": centering if centering else self.centering,
      "superscript": superscript if superscript else self.superscript
    }

  def word(self, node, word):
    weight = node.style['font-weight']
    style = node.style['font-style']
    if style == "normal":
      style = "roman"
    if self.pre:
      style += " fixed_width"
    size = int(float(node.style['font-size'][:-2]) * .75)
    color = node.style['color']

    space = get_measure(" ", size, weight, style)
    width = get_measure(word, size, weight, style)
    if self.pre:
      if word == '\n':
        self.flush()
      else:
        self.line.append(self.create_word(word, size=size, weight=weight, style=style, color=color))
        # Because spaces are explicitly included in the wordlist during pre tags, don't include a space
        self.cursor_x += width
    elif self.cursor_x + width + space < self.width - SCROLLBAR_WIDTH:
      # If there's still room on this line, add to self.line and advance cursor_x
      self.line.append(self.create_word(word, size=size, weight=weight, style=style, color=color))
      self.cursor_x += width + space
    else:
      # If soft hyphens are present in the word, consider splitting on them
      if u"\u00AD" in word:
        parts = word.split(u"\u00AD")
        hyphen = get_measure("-", size, weight, style)
        taken = []
        count = 0
        for part in parts:
          part_width = get_measure(part, size, weight, style)
          if self.cursor_x + part_width + hyphen < self.width - SCROLLBAR_WIDTH:
            # If it fits, add the part to the line
            self.line.append(self.create_word(part, size=size, weight=weight, style=style, color=color))
            self.cursor_x += part_width
            taken.append(part)
            count += 1
          else:
            # We've fit all the parts we can fit onto the line (plus hyphen) so break
            break

        leftovers = ''.join([p for p in parts if p not in taken])
        if count > 0:
          # Don't add a hyphen unless some parts are added to the line
          self.line.append(self.create_word("-", size=size, weight=weight, style=style, color=color))
        # Set x explicitly to something terrible so we notice if x isn't updated before usage
        nextline = self.create_word(leftovers, x=-1, size=size, weight=weight, style=style, color=color)
        self.flush(nextline)
      else:
        # If there's no more room on this line, finish it with current word starting the next line
        # Set x explicitly to something terrible so we notice if x isn't updated before usage
        nextline = self.create_word(word, x=-1, size=size, weight=weight, style=style, color=color)
        self.flush(nextline)

  def flush(self, nextline: Dict[str, Union[int, str, bool]] = None):
    if not self.line:
      return

    centering = any([entry['centering'] for entry in self.line])
    if centering:
      # Measure the last word
      last_entry = self.line[-1]
      last_length = get_measure(last_entry['word'], last_entry['size'], last_entry['weight'], last_entry["style"])
      # Determine the line length, including the last word
      line_length = (last_entry["x"] - self.line[0]["x"]) + last_length
      # Calculate how much to shift each word's x to center
      delta_x = (self.width - line_length) / 2
    else:
      delta_x = 0

    fonts = [get_font(entry['size'], entry['weight'], entry['style']) for entry in self.line]
    metrics = [font.metrics() for font in fonts]
    max_ascent = max([metric["ascent"] for metric in metrics])
    baseline = self.cursor_y + 1.25 * max_ascent

    for i, entry in enumerate(self.line):
      font = fonts[i]
      if entry["superscript"]:
        y = self.y + baseline - max_ascent
      else:
        y = self.y + baseline - font.metrics("ascent")
      # delta_x is zero if not centering
      x = self.x + entry['x'] + delta_x
      if isinstance(self.node, Element) and self.node.tag == "li":
        x += HSTEP
      self.display_list.append((x, y, entry['word'], font, entry['color']))

    max_descent = max([metric['descent'] for metric in metrics])
    self.cursor_y = baseline + 1.25 * max_descent
    self.cursor_x = 0
    if nextline:
      # Here we update nextline's x field
      nextline["x"] = self.cursor_x
      self.line = [nextline]
      self.cursor_x += get_measure(nextline["word"] + " ",
                                   nextline["size"],
                                   nextline["weight"],
                                   nextline["style"])
    else:
      self.line = []
