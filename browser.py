import tkinter as tk
import argparse

from url import URL
from layout import paint_tree, DocumentLayout, VSTEP, SCROLLBAR_WIDTH
from parser import HTMLParser

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100


class Browser:
  def __init__(self):
    self.screen_width = WIDTH
    self.screen_height = HEIGHT
    self.tokens = []
    self.display_list = []
    self.doc_height = 0
    self.scroll = 0
    self.document = None

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
    bottom_of_last_screen = self.doc_height + (2 * VSTEP) - self.screen_height
    self.scroll = min(bottom_of_last_screen, self.scroll + SCROLL_STEP)
    self.draw()

  def scrollup(self, e):
    self.scroll = max(0, self.scroll - SCROLL_STEP)
    self.draw()

  def redraw(self):
    self.document = DocumentLayout(self.tokens, self.screen_width)
    self.document.layout()
    self.display_list = []
    paint_tree(self.document, self.display_list)
    if self.display_list:
      self.doc_height = self.display_list[-1].top
    self.draw()

  def resize(self, e):
    self.screen_width, self.screen_height = e.width, e.height
    self.redraw()

  def draw(self):
    self.canvas.delete('all')
    for cmd in self.display_list:
      # omit characters above the viewport
      if cmd.bottom < self.scroll:
        continue
      # omit characters below the viewport
      if cmd.top > self.scroll + self.screen_height:
        continue
      cmd.execute(self.scroll, self.canvas)

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
        parser = HTMLParser('')
        parser.add_element("pre")
        for word in body.split(' '):
          parser.add_text(word + " ")
        self.tokens = parser.finish()
      else:
        self.tokens = HTMLParser(body).parse()

    self.redraw()


if __name__ == "__main__":
  TEST_FILE = 'file://localhost/Users/christalee/Documents/software/projects/browser.engineering/example.html'
  parser = argparse.ArgumentParser()
  parser.add_argument("url", help="URL(s) to open", nargs="*", default=[TEST_FILE])

  args = parser.parse_args()
  for url in args.url:
    Browser().load(URL(url))
  tk.mainloop()
