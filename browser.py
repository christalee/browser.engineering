import socket
import ssl
import re


def show(body, entities):
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
          # print(m.start(), m.end(), m.group(0))
          entity = m.group(0)
          if entity in entities:
            chars = entities[entity]['characters']
            print(chars, end="")
          i += len(entity) - 1
      else:
        print(c, end="")
    i += 1


def load(url, entities):
  body = url.request()
  if url.view_source:
    print(body)
  else:
    show(body, entities)


class URL:
  def __init__(self, url):
    self.view_source = False
    if url.startswith('data:'):
      self.scheme, url = url.split(':', 1)
    else:
      if url.startswith('view-source:'):
        self.view_source = True
        _, url = url.split(":", 1)
      self.scheme, url = url.split("://", 1)
    assert self.scheme in ['http', 'https', 'file', 'data']
    if self.scheme == 'http':
      self.port = 80
      self.get_host_path(url)
    elif self.scheme == 'https':
      self.port = 443
      self.get_host_path(url)
    elif self.scheme == 'file':
      self.port = 0
      self.get_host_path(url)
    elif self.scheme == "data":
      self.port = 0
      self.host, self.path = url.split(',', 1)
    if ":" in self.host:
      self.host, port = self.host.split(":", 1)
      self.port = int(port)
    # print(self.scheme, self.host, self.port, self.path)

  def get_host_path(self, url):
    if '/' not in url:
      url = url + '/'
    self.host, url = url.split('/', 1)
    self.path = '/' + url

  def request(self):
    if self.scheme == 'file':
      with open(self.path, 'r', encoding="utf-8") as f:
        return f.read()
    if self.scheme == "data" and self.host == "text/html":
      return self.path
    s = socket.socket(
      family=socket.AF_INET,
      type=socket.SOCK_STREAM,
      proto=socket.IPPROTO_TCP
    )
    if self.scheme == 'https':
      ctx = ssl.create_default_context()
      s = ctx.wrap_socket(s, server_hostname=self.host)
    s.connect((self.host, self.port))

    r = f"GET {self.path} HTTP/1.1\r\n"
    request_headers = '\r\n'.join([f"Host: {self.host}", "Connection: close", "User-Agent: christalee"])
    r += request_headers
    r += '\r\n\r\n'
    s.send(r.encode('utf-8'))

    response = s.makefile('r', encoding='utf-8', newline='\r\n')
    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    # print(version, status, explanation)
    response_headers = {}
    while True:
      line = response.readline()
      if line == '\r\n':
        break
      header, value = line.split(":", 1)
      response_headers[header.casefold()] = value.strip()
    assert 'transfer-encoding' not in response_headers
    assert 'content-encoding' not in response_headers
    content = response.read()
    s.close()

    return content


if __name__ == "__main__":
  import sys, json

  with open('entities.json', 'r', encoding='utf-8') as f:
    entities = json.load(f)
  if len(sys.argv) > 1:
    load(URL(sys.argv[1]), entities)
  else:
    load(URL('file://localhost/Users/christalee/Documents/software/projects/browser.engineering/example.txt'), entities)
