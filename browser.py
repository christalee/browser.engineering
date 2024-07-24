import socket
import ssl
import re
import json

sockets = {}
MAX_REDIRECTS = 3


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
          entity = m.group(0)
          if entity in entities:
            print(entities[entity]['characters'], end="")
          i += len(entity) - 1
      else:
        print(c, end="")
    i += 1


def load(url, num_redirects):
  with open('entities.json', 'r', encoding='utf-8') as f:
    entities = json.load(f)
  body = url.request(num_redirects)
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

    self.get_host_path(url)
    if self.scheme == 'http':
      self.port = 80
    elif self.scheme == 'https':
      self.port = 443
    elif self.scheme == 'file':
      self.port = 0
    elif self.scheme == "data":
      self.port = 0
      # These are bad names for what is really the MIME type and content
      self.host, self.path = url.split(',', 1)
    if ":" in self.host:
      self.host, port = self.host.split(":", 1)
      self.port = int(port)

    self.socket = sockets.get((self.host, self.port), None)

  def get_host_path(self, url):
    if '/' not in url:
      url = url + '/'
    self.host, url = url.split('/', 1)
    self.path = '/' + url

  def open_socket(self):
    s = socket.socket(
      family=socket.AF_INET,
      type=socket.SOCK_STREAM,
      proto=socket.IPPROTO_TCP
    )
    if self.scheme == 'https':
      ctx = ssl.create_default_context()
      s = ctx.wrap_socket(s, server_hostname=self.host)
    s.connect((self.host, self.port))

    return s

  def handle_http(self, num_redirects):
    if self.socket is None or self.socket.fileno() == -1:
      print("New socket opened!")
      self.socket = self.open_socket()
    sockets[(self.host, self.port)] = self.socket

    r = f"GET {self.path} HTTP/1.1\r\n"
    request_headers = '\r\n'.join([f"Host: {self.host}", "User-Agent: christalee"])
    r += request_headers
    r += '\r\n\r\n'
    self.socket.send(r.encode('utf-8'))

    raw_response = self.socket.makefile('rb', newline='\r\n')
    statusline = raw_response.readline().decode(encoding='utf-8')
    version, status, explanation = statusline.split(" ", 2)

    response_headers = {}
    while True:
      line = raw_response.readline().decode(encoding='utf-8')
      if line == '\r\n':
        break
      header, value = line.split(":", 1)
      response_headers[header.casefold()] = value.strip()
    assert 'transfer-encoding' not in response_headers
    assert 'content-encoding' not in response_headers

    if status.startswith('3') and 'location' in response_headers:
      url = response_headers['location']
      if "://" not in url:
        url = url.lstrip("/")
        url = f"{self.scheme}://{self.host}/{url}"
      if num_redirects < MAX_REDIRECTS:
        print(f"Redirecting to: {url}")
        load(URL(url), num_redirects=num_redirects + 1)
      else:
        print(f"Too many redirects, sorry")

    if 'content-length' in response_headers:
      content_length = int(response_headers['content-length'])
    else:
      content_length = -1
    content = raw_response.read(content_length).decode(encoding='utf-8')
    raw_response.close()

    return content

  def request(self, num_redirects):
    if self.scheme == 'file':
      with open(self.path, 'r', encoding="utf-8") as f:
        return f.read()
    if self.scheme == "data" and self.host == "text/html":
      return self.path
    if self.scheme == 'http' or 'https':
      return self.handle_http(num_redirects)


if __name__ == "__main__":
  import sys

  if len(sys.argv) > 1:
    for url in sys.argv[1:]:
      load(URL(url), num_redirects=0)
  else:
    load(URL('file://localhost/Users/christalee/Documents/software/projects/browser.engineering/example.txt'),
         num_redirects=0)
