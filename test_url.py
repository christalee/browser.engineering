import unittest

from url import URL
from test_utils import socket, ssl


class TestBrowserURL(unittest.TestCase):
  # Tests for URL parsing
  def test_url_http_parse(self):
    result = URL('http://www.example.com/index.html')

    self.assertEqual(result.view_source, False)
    self.assertEqual(result.scheme, 'http')
    self.assertEqual(result.host, 'www.example.com')
    self.assertEqual(result.port, 80)
    self.assertEqual(result.path, '/index.html')

  def test_url_https_parse(self):
    result = URL('https://www.example.com/index.html')

    self.assertEqual(result.view_source, False)
    self.assertEqual(result.scheme, 'https')
    self.assertEqual(result.host, 'www.example.com')
    self.assertEqual(result.port, 443)
    self.assertEqual(result.path, '/index.html')

  def test_url_port_parse(self):
    result = URL('http://www.example.com:8080/index.html')

    self.assertEqual(result.view_source, False)
    self.assertEqual(result.scheme, 'http')
    self.assertEqual(result.host, 'www.example.com')
    self.assertEqual(result.port, 8080)
    self.assertEqual(result.path, '/index.html')

  def test_url_file_parse_host(self):
    result = URL('file://localhost/path/to/file.txt')

    self.assertEqual(result.view_source, False)
    self.assertEqual(result.scheme, 'file')
    self.assertEqual(result.host, 'localhost')
    self.assertEqual(result.port, 0)
    self.assertEqual(result.path, '/path/to/file.txt')

  def test_url_file_parse_no_host(self):
    result = URL('file:///path/to/file.txt')

    self.assertEqual(result.view_source, False)
    self.assertEqual(result.scheme, 'file')
    self.assertEqual(result.host, 'localhost')
    self.assertEqual(result.port, 0)
    self.assertEqual(result.path, '/path/to/file.txt')

  def test_url_data_parse(self):
    result = URL('data:text/html,Hello, world!')

    self.assertEqual(result.view_source, False)
    self.assertEqual(result.scheme, 'data')
    self.assertEqual(result.host, 'text/html')
    self.assertEqual(result.port, 0)
    self.assertEqual(result.path, 'Hello, world!')

  def test_url_view_source(self):
    result = URL('view-source:https://www.example.com/index.html')

    self.assertEqual(result.view_source, True)
    self.assertEqual(result.scheme, 'https')
    self.assertEqual(result.host, 'www.example.com')
    self.assertEqual(result.port, 443)
    self.assertEqual(result.path, '/index.html')


class TestBrowserRequest(unittest.TestCase):
  def setUp(self):
    socket.patch().start()

  def tearDown(self):
    socket.patch().stop()

  def test_request_file(self):
    content = URL(
      'file://localhost/Users/christalee/Documents/software/projects/browser.engineering/example.txt').request()

    self.assertEqual(content, 'This is an example file full of text.')

  def test_request_data(self):
    content = URL('data:text/html,Hello, world!').request()

    self.assertEqual(content, 'Hello, world!')

  def test_request_http(self):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"Body text"
    )
    content = URL(url).request()

    self.assertEqual(content, 'Body text')

  def test_request_https(self):
    ssl.patch().start()
    url = "https://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"Body text"
    )
    content = URL(url).request()

    self.assertEqual(content, 'Body text')
