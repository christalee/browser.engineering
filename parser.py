import json
import re
from typing import Union, Dict


def print_tree(node, indent=0):
  print(" " * indent, node)
  for child in node.children:
    print_tree(child, indent + 2)


class Text:
  def __init__(self, text: str, parent: Union["Text", "Element"]):
    self.text = text
    self.children = []
    self.parent = parent

  def __repr__(self):
    return self.text


class Element:
  def __init__(self, tag: str, attributes: Dict[str, str], parent: Union['Text', 'Element']):
    self.tag = tag
    self.attributes = attributes
    self.children = []
    self.parent = parent

  def __repr__(self):
    return f"<{self.tag} {self.attributes}>"


class HTMLParser:
  SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
  ]

  def __init__(self, body):
    self.body = body
    self.unfinished = []

  def get_attributes(self, text):
    parts = text.split()
    tag = parts[0].casefold()
    attributes = {}
    for pair in parts[1:]:
      if pair.startswith("/"):
        continue
      if "=" in pair:
        key, value = pair.split("=", 1)
        attributes[key.casefold()] = value.strip("'\"")
      else:
        attributes[pair.casefold()] = ""

    return tag, attributes

  def add_text(self, text):
    if text.isspace():
      return
    parent = self.unfinished[-1]
    node = Text(text, parent)
    parent.children.append(node)

  def add_element(self, tag):
    tag, attributes = self.get_attributes(tag)
    if tag.startswith("!"):
      return
    elif tag in self.SELF_CLOSING_TAGS:
      parent = self.unfinished[-1]
      node = Element(tag, attributes, parent)
      parent.children.append(node)
    elif tag.startswith("/"):
      if len(self.unfinished) == 1:
        return
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    else:
      parent = self.unfinished[-1] if self.unfinished else None
      node = Element(tag, attributes, parent)
      self.unfinished.append(node)

  def finish(self):
    while len(self.unfinished) > 1:
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    if self.unfinished:
      return self.unfinished.pop()
    else:
      return []

  def parse(self):
    with open('entities.json', 'r', encoding='utf-8') as f:
      entities = json.load(f)

    buffer = ''
    in_tag = False
    i = 0
    while i < len(self.body):
      c = self.body[i]
      if c == "<":
        in_tag = True
        if buffer:
          self.add_text(buffer)
        buffer = ""
      elif c == ">":
        in_tag = False
        self.add_element(buffer)
        buffer = ''
      elif not in_tag and c == "&":
        m = re.search(r"&.*?;", self.body[i:])
        if m:
          entity = m.group(0)
          if entity in entities:
            buffer += entities[entity]['characters']
          i += len(entity) - 1
      else:
        buffer += c
      i += 1

    if not in_tag and buffer:
      self.add_text(buffer)

    return self.finish()
