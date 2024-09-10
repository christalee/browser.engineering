import socket
import ssl
import re
import datetime
import gzip

sockets = {}
cache = {}
MAX_REDIRECTS = 3


class URL:
  def __init__(self, url: str):
    self.view_source = False
    self.is_malformed = False
    try:
      if url.startswith('data:'):
        self.scheme, url = url.split(':', 1)
      elif url.startswith("about:"):
        self.is_malformed = True
        self.scheme, url = url.split(":", 1)
      else:
        if url.startswith('view-source:'):
          self.view_source = True
          _, url = url.split(":", 1)
        self.scheme, url = url.split("://", 1)
      assert self.scheme in ['http', 'https', 'file', 'data', 'about']

      self.get_host_path(url)
      if self.scheme == 'http':
        self.port = 80
      elif self.scheme == 'https':
        self.port = 443
      elif self.scheme == 'file':
        self.port = 0
        if not self.host:
          self.host = 'localhost'
      elif self.scheme == "data":
        self.port = 0
        # These are bad names for what is really the MIME type and content
        self.host, self.path = url.split(',', 1)
      elif self.scheme == 'about':
        self.port = 0
      if ":" in self.host:
        self.host, port = self.host.split(":", 1)
        self.port = int(port)

      self.socket = sockets.get((self.host, self.port), None)

    except:
      self.is_malformed = True

  def get_host_path(self, url: str):
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
    s.connect((self.host, self.port))
    if self.scheme == 'https':
      ctx = ssl.create_default_context()
      s = ctx.wrap_socket(s, server_hostname=self.host)

    return s

  def handle_http(self, num_redirects: int = 0):
    if self.socket is None or self.socket.fileno() == -1:
      print("New socket opened!")
      self.socket = self.open_socket()
    sockets[(self.host, self.port)] = self.socket

    r = f"GET {self.path} HTTP/1.1\r\n"
    request_headers = '\r\n'.join([f"Host: {self.host}", "Accept-Encoding: gzip", "User-Agent: christalee"])
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

    if status.startswith('3') and 'location' in response_headers:
      url = response_headers['location']
      if "://" not in url:
        url = f"{self.scheme}://{self.host}{url}"
      if num_redirects < MAX_REDIRECTS:
        print(f"Redirecting to: {url}")
        return URL(url).request(num_redirects + 1)
      else:
        print(f"Too many redirects, sorry")
        return None

    url = f"{self.scheme}://{self.host}{self.path}"
    cache_control = ''
    if 'cache-control' in response_headers and status == '200':
      cache_control = response_headers['cache-control']
      if 'max-age' in cache_control:
        m = re.search(r'max-age=(\d*)', cache_control)
        if m and url in cache:
          max_age = int(m.group(1))
          timestamp_content = cache[url]
          content_age = datetime.datetime.now() - timestamp_content['timestamp']
          if content_age.total_seconds() < max_age:
            print(f"Returning content from cache: {url}")
            return timestamp_content['content']

    if 'content-length' in response_headers:
      content_length = int(response_headers['content-length'])
    else:
      content_length = -1

    if 'transfer-encoding' in response_headers and response_headers['transfer-encoding'] == 'chunked':
      content = b''
      while True:
        size = raw_response.readline().strip().decode(encoding='utf-8')
        if size == '0' or not size:
          raw_response.readline()
          break
        else:
          length = int(size, 16)
        line = raw_response.read(length)
        # need to read past \r\n
        raw_response.read(2)
        content += line
    else:
      content = raw_response.read(content_length)

    if 'content-encoding' in response_headers and response_headers['content-encoding'] == 'gzip':
      content = gzip.decompress(content)

    content = content.decode(encoding='utf-8')
    raw_response.close()

    if 'no-store' not in cache_control:
      cache[url] = {'timestamp': datetime.datetime.now(), 'content': content}

    return content

  def request(self, num_redirects: int = 0):
    if self.is_malformed:
      return None
    elif self.scheme == 'file':
      with open(self.path, 'r', encoding="utf-8") as f:
        return f.read()
    if self.scheme == "data" and self.host == "text/html":
      return self.path
    if self.scheme == 'http' or 'https':
      return self.handle_http(num_redirects)

  def resolve(self, url):
    if "://" in url:
      return URL(url)
    if not url.startswith("/"):
      dir, _ = self.path.rsplit("/", 1)
      while url.startswith("../"):
        _, url = url.split("/", 1)
        if "/" in dir:
          dir, _ = dir.rsplit("/", 1)
      url = f"{dir}/{url}"
    if url.startswith("//"):
      return URL(f"{self.scheme}:{url}")
    else:
      return URL(f"{self.scheme}://{self.host}:{str(self.port)}{url}")
