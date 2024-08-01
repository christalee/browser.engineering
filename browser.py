import json
import re
import tkinter
from typing import Dict

from url import URL

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100


class Browser:
  def __init__(self):
    self.width = WIDTH
    self.height = HEIGHT
    self.window = tkinter.Tk()
    self.canvas = tkinter.Canvas(
      self.window,
      width=self.width,
      height=self.height
    )
    self.canvas.pack(fill=tkinter.BOTH, expand=True)
    self.text = ''
    self.display_list = []
    self.scroll = 0
    self.window.bind("<Down>", self.scrolldown)
    self.window.bind("<Up>", self.scrollup)
    self.window.bind("<Button-4>", self.scrolldelta)
    self.window.bind("<Button-5>", self.scrolldelta)
    self.window.bind("<Configure>", self.resize)
    # self.window.bind("<MouseWheel>", self.scrolldelta)

  def scrolldelta(self, e):
    if e.num == 5:
      self.scrolldown(e)
    elif e.num == 4:
      self.scrollup(e)

  def scrolldown(self, e):
    self.scroll += SCROLL_STEP
    self.draw()

  def scrollup(self, e):
    self.scroll = max(0, self.scroll - SCROLL_STEP)
    self.draw()

  def resize(self, e):
    self.width, self.height = e.width, e.height
    self.layout()
    self.draw()

  def layout(self):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in self.text:
      display_list.append((cursor_x, cursor_y, c))
      cursor_x += HSTEP
      if c == '\n':
        cursor_x = HSTEP
        cursor_y += 1.5 * VSTEP
      elif cursor_x >= self.width - HSTEP:
        cursor_x = HSTEP
        cursor_y += VSTEP

    self.display_list = display_list

  def draw(self):
    self.canvas.delete('all')
    for x, y, c in self.display_list:
      # omit characters above the viewport
      if y + VSTEP < self.scroll:
        continue
      # omit characters below the viewport
      if y > self.scroll + self.height:
        continue
      self.canvas.create_text(x, y - self.scroll, text=c)

  def load(self, url: URL, num_redirects: int = 0):
    with open('entities.json', 'r', encoding='utf-8') as f:
      entities = json.load(f)
    body = url.request(num_redirects)
    if body:
      if url.view_source:
        self.text = body
      else:
        self.text = self.lex(body, entities)

    print(self.text)
    self.layout()
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
