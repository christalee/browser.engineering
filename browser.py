import tkinter as tk
import emoji
from PIL import ImageTk, Image
import argparse

from url import URL
from layout import Layout, VSTEP, SCROLLBAR_WIDTH
from parser import HTMLParser

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100

emoji_dict = {}


class Browser:
  def __init__(self):
    self.screen_width = WIDTH
    self.screen_height = HEIGHT
    self.tokens = []
    self.display_list = []
    self.doc_height = 0
    self.scroll = 0
    self.layout = None

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
    self.window.bind("<MouseWheel>", self.scrollmouse)

  def scrollmouse(self, e):
    if e.delta < 0:
      self.scrolldown(e)
    else:
      self.scrollup(e)

  def scrolldelta(self, e):
    if e.num == 5:
      self.scrolldown(e)
    elif e.num == 4:
      self.scrollup(e)

  def scrolldown(self, e):
    bottom_of_last_screen = self.doc_height + self.layout.size + VSTEP - self.screen_height
    self.scroll = min(bottom_of_last_screen, self.scroll + SCROLL_STEP)
    self.draw()

  def scrollup(self, e):
    self.scroll = max(0, self.scroll - SCROLL_STEP)
    self.draw()

  def resize(self, e):
    self.screen_width, self.screen_height = e.width, e.height
    self.layout = Layout(self.tokens, self.screen_width)
    self.display_list = self.layout.display_list
    if self.display_list:
      self.doc_height = self.display_list[-1][1]
    self.draw()

  def draw(self):
    self.canvas.delete('all')
    for x, y, c, f in self.display_list:
      # omit characters above the viewport
      if y + VSTEP < self.scroll:
        continue
      # omit characters below the viewport
      if y > self.scroll + self.screen_height:
        continue
      if emoji.is_emoji(c):
        codepoints = []
        for char in c:
          # This format string is magic; TODO find an explainer
          codepoints.append('{:04x}'.format(ord(char)).upper())
        emoji_png = '-'.join(codepoints)
        if emoji_png not in emoji_dict:
          image = Image.open(f'openmoji-72x72-color/{emoji_png}.png')
          emoji_dict[emoji_png] = ImageTk.PhotoImage(image.resize((16, 16)))
        self.canvas.create_image(x, y - self.scroll, anchor="nw", image=emoji_dict[emoji_png])
      else:
        self.canvas.create_text(x, y - self.scroll, text=c, anchor="nw", font=f)

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
        self.tokens = body.split()
      else:
        self.tokens = HTMLParser(body).parse()
    else:
      self.tokens = []

    self.layout = Layout(self.tokens, self.screen_width)
    self.display_list = self.layout.display_list
    if self.display_list:
      self.doc_height = self.display_list[-1][1]
    self.draw()


if __name__ == "__main__":
  TEST_FILE = 'file://localhost/Users/christalee/Documents/software/projects/browser.engineering/example.txt'
  parser = argparse.ArgumentParser()
  parser.add_argument("url", help="URL(s) to open", nargs="*", default=[TEST_FILE])

  args = parser.parse_args()
  for url in args.url:
    Browser().load(URL(url))
  tk.mainloop()
