import json
import re
import tkinter
from typing import Dict

from url import URL

WIDTH, HEIGHT = 800, 600


class Browser:
  def __init__(self):
    self.window = tkinter.Tk()
    self.canvas = tkinter.Canvas(
      self.window,
      width=WIDTH,
      height=HEIGHT
    )
    self.canvas.pack()

  def load(self, url: URL, num_redirects: int = 0):
    with open('entities.json', 'r', encoding='utf-8') as f:
      entities = json.load(f)
    body = url.request(num_redirects)
    if body:
      if url.view_source:
        print(body)
      else:
        text = self.lex(body, entities)
        print(text)
    for c in text:
      self.canvas.create_text(100, 100, text=c)

  def lex(self, body: str, entities: Dict[str, Dict[str, str]]):
    text = ''
    in_tag = False
    i = 0
    while i < len(body):
      c = body[i]
      if c == "<":
        in_tag = True
      elif c == ">":
        in_tag = False
      elif not in_tag:
        if c == "&":
          m = re.search(r"&.*?;", body[i:])
          if m:
            entity = m.group(0)
            if entity in entities:
              text += entities[entity]['characters']
            i += len(entity) - 1
        else:
          text += c
      i += 1

    return text


if __name__ == "__main__":
  import sys

  if len(sys.argv) > 1:
    for url in sys.argv[1:]:
      Browser().load(URL(url))
  else:
    Browser().load(URL('file://localhost/Users/christalee/Documents/software/projects/browser.engineering/example.txt'))
  tkinter.mainloop()
