from parser import Element


def style(node):
  node.style = {}
  if isinstance(node, Element) and "style" in node.attributes:
    pairs = CSSParser(node.attributes['style']).body()
    for prop, value in pairs.items():
      node.style[prop] = value
  for child in node.children:
    style(child)


class CSSParser:
  def __init__(self, s):
    self.s = s
    self.i = 0

  def whitespace(self):
    while self.i < len(self.s) and self.s[self.i].isspace():
      self.i += 1

  def word(self):
    start = self.i
    while self.i < len(self.s):
      if self.s[self.i].isalnum() or self.s[self.i] in '#-.%':
        self.i += 1
      else:
        break
    if not (self.i > start):
      raise Exception(f"parsing error: made no progress at position {self.i}")

    return self.s[start:self.i]

  def literal(self, literal):
    if not (self.i < len(self.s) and self.s[self.i] == literal):
      raise Exception(f"parsing error: literal {literal} not found at position {self.i}")
    self.i += 1

  def ignore_until(self, chars):
    while self.i < len(self.s):
      if self.s[self.i] in chars:
        return self.s[self.i]
      else:
        self.i += 1
    return None

  def pair(self):
    prop = self.word()
    self.whitespace()
    self.literal(":")
    self.whitespace()
    val = self.word()
    return prop.casefold(), val

  def body(self):
    pairs = {}
    while self.i < len(self.s):
      try:
        prop, val = self.pair()
        pairs[prop] = val
        self.whitespace()
        self.literal(";")
        self.whitespace()
      except Exception as e:
        print(e)
        why = self.ignore_until([';'])
        if why == ';':
          self.literal(';')
          self.whitespace()
        else:
          break
    return pairs
