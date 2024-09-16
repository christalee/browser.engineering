from PIL import ImageTk, Image

emoji_dict = {}


class DrawText:
  def __init__(self, x1, y1, text, font, color):
    self.top = y1
    self.left = x1
    self.text = text
    self.font = font
    self.bottom = y1 + font.metrics("linespace")
    self.color = color

  def execute(self, scroll, canvas):
    canvas.create_text(
      self.left,
      self.top - scroll,
      text=self.text,
      font=self.font,
      anchor="nw",
      fill=self.color
    )


class DrawRect:
  def __init__(self, x1, y1, x2, y2, color):
    self.top = y1
    self.left = x1
    self.bottom = y2
    self.right = x2
    self.color = color

  def execute(self, scroll, canvas):
    canvas.create_rectangle(
      self.left,
      self.top - scroll,
      self.right,
      self.bottom - scroll,
      width=0,
      fill=self.color
    )


class DrawEmoji:
  def __init__(self, x1, y1, char):
    self.top = y1
    self.left = x1
    self.bottom = y1 + 16
    self.emoji = char

  def execute(self, scroll, canvas):
    codepoints = []
    for char in self.emoji:
      # This format string is magic; TODO find an explainer
      codepoints.append('{:04x}'.format(ord(char)).upper())
    emoji_png = '-'.join(codepoints)
    if emoji_png not in emoji_dict:
      image = Image.open(f'openmoji-72x72-color/{emoji_png}.png')
      emoji_dict[emoji_png] = ImageTk.PhotoImage(image.resize((16, 16)))

    canvas.create_image(self.left,
                        self.top - scroll,
                        anchor="nw",
                        image=emoji_dict[emoji_png]
                        )
