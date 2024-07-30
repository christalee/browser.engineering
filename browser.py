import json
import re
import tkinter
from typing import Dict

from url import URL

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100


def layout(text):
  display_list = []
  cursor_x, cursor_y = HSTEP, VSTEP
  for c in text:
    display_list.append((cursor_x, cursor_y, c))
    cursor_x += HSTEP
    if c == '\n':
      cursor_x = HSTEP
      cursor_y += 1.5 * VSTEP
    elif cursor_x >= WIDTH - HSTEP:
      cursor_x = HSTEP
      cursor_y += VSTEP

  return display_list


class Browser:
  def __init__(self):
    self.window = tkinter.Tk()
    self.canvas = tkinter.Canvas(
      self.window,
      width=WIDTH,
      height=HEIGHT
    )
    self.canvas.pack()
    self.display_list = []
    self.scroll = 0
    self.window.bind("<Down>", self.scrolldown)
    self.window.bind("<Up>", self.scrollup)

  def scrolldown(self, e):
    self.scroll += SCROLL_STEP
    self.draw()

  def scrollup(self, e):
    self.scroll -= SCROLL_STEP
    self.draw()

  def draw(self):
    self.canvas.delete('all')
    for x, y, c in self.display_list:
      # omit characters above the viewport
      if y + VSTEP < self.scroll:
        continue
      # omit characters below the viewport
      if y > self.scroll + HEIGHT:
        continue
      self.canvas.create_text(x, y - self.scroll, text=c)

  def load(self, url: URL, num_redirects: int = 0):
    with open('entities.json', 'r', encoding='utf-8') as f:
      entities = json.load(f)
    body = url.request(num_redirects)
    text = ''
    cursor_x, cursor_y = HSTEP, VSTEP
    if body:
      if url.view_source:
        text = body
      else:
        text = self.lex(body, entities)

    print(text)
    self.display_list = layout(text)
    self.draw()

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
