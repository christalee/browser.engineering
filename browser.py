import json
import re
import tkinter as tk
from typing import Dict
import emoji
from PIL import ImageTk, Image

from url import URL

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
SCROLLBAR_WIDTH = 12

emoji_dict = {}


class Browser:
  def __init__(self):
    self.screen_width = WIDTH
    self.screen_height = HEIGHT
    self.text = ''
    self.display_list = []
    self.doc_height = 0
    self.scroll = 0

    self.window = tk.Tk()
    self.canvas = tk.Canvas(
      self.window,
      width=self.screen_width,
      height=self.screen_height
    )
    self.canvas.pack(fill=tk.BOTH, expand=True)

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
    top_of_last_screen = self.doc_height - self.screen_height
    self.scroll = min(top_of_last_screen, self.scroll + SCROLL_STEP)
    self.draw()

  def scrollup(self, e):
    self.scroll = max(0, self.scroll - SCROLL_STEP)
    self.draw()

  def resize(self, e):
    self.screen_width, self.screen_height = e.width, e.height
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
      elif cursor_x >= self.screen_width - HSTEP - SCROLLBAR_WIDTH:
        cursor_x = HSTEP
        cursor_y += VSTEP

    self.display_list = display_list
    if display_list:
      self.doc_height = display_list[-1][1]

  def draw(self):
    self.canvas.delete('all')
    for x, y, c in self.display_list:
      # omit characters above the viewport
      if y + VSTEP < self.scroll:
        continue
      # omit characters below the viewport
      if y > self.scroll + self.screen_height:
        continue
      if emoji.is_emoji(c):
        # TODO make this handle multi-char emoji, e.g. 😮‍💨
        # This format string is magic; TODO find an explainer
        emoji_png = '{:04x}'.format(ord(c)).upper()
        if emoji_png not in emoji_dict:
          image = Image.open(f'openmoji-72x72-color/{emoji_png}.png')
          emoji_dict[emoji_png] = ImageTk.PhotoImage(image.resize((20, 20)))
        self.canvas.create_image(x, y - self.scroll, image=emoji_dict[emoji_png])
      else:
        self.canvas.create_text(x, y - self.scroll, text=c)

    if self.doc_height > self.screen_height:
      self.draw_scrollbar()

  def draw_scrollbar(self):
    percent_shown = self.screen_height / self.doc_height
    percent_offset = self.scroll / self.doc_height
    y_total = percent_shown * self.screen_height

    x0 = self.screen_width - SCROLLBAR_WIDTH
    x1 = self.screen_width
    y0 = percent_offset * self.screen_height
    y1 = y0 + y_total

    self.canvas.create_rectangle(x0, y0, x1, y1, fill="blue")

  def load(self, url: URL, num_redirects: int = 0):
    body = url.request(num_redirects)
    if body:
      if url.view_source:
        self.text = body
      else:
        self.text = self.lex(body)
    else:
      self.text = ''

    print(self.text)
    self.layout()
    self.draw()

  def lex(self, body: str):
    with open('entities.json', 'r', encoding='utf-8') as f:
      entities = json.load(f)
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
  tk.mainloop()
