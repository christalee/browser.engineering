import unittest
import json
from unittest.mock import patch
import io
import re
import time

from browser import URL, show, load
from test_utils import socket, ssl


@patch('sys.stdout', new_callable=io.StringIO)
class TestBrowserShow(unittest.TestCase):
  # Tests for show()
  def setUp(self):
    self.entities = {}
    with open('entities.json', 'r', encoding='utf-8') as f:
      self.entities = json.load(f)

  def test_show_no_tags(self, mock_stdout):
    body = 'Hello, world!'
    show(body, self.entities)

    self.assertEqual(mock_stdout.getvalue(), body)

  def test_show_tags(self, mock_stdout):
    body = '<pre>Hello, world!</pre>'
    show(body, self.entities)

    self.assertEqual(mock_stdout.getvalue(), 'Hello, world!')

  def test_show_entities(self, mock_stdout):
    body = '&lt;div&gt;'
    show(body, self.entities)

    self.assertEqual(mock_stdout.getvalue(), '<div>')

  def test_show_invalid_entities(self, mock_stdout):
    body = '&asdf;'
    show(body, self.entities)

    self.assertEqual(mock_stdout.getvalue(), '')

  def test_show_unicode(self, mock_stdout):
    body = '🍐🪄'
    show(body, self.entities)

    self.assertEqual(mock_stdout.getvalue(), body)


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


@patch('sys.stdout', new_callable=io.StringIO)
class TestBrowserLoad(unittest.TestCase):
  # Tests for load()

  # When these tests run all in a suite, the global sockets dict is populated and may cause
  # tests with similar URLs to reuse sockets. Specific tests which assert on new sockets or socket reuse
  # messages have unique hostnames to prevent this. JFYI
  # potential TODO: import sockets from browser and reset it as part of of setUp()?

  def setUp(self):
    socket.patch().start()

  def tearDown(self):
    socket.patch().stop()

  def test_load_http(self, mock_stdout):
    url = "http://load.http/examples/load_http.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"&lt;Body text&gt;"
    )
    load(URL(url))

    self.assertIn('New socket opened!', mock_stdout.getvalue())
    self.assertIn('<Body text>', mock_stdout.getvalue())

  def test_load_https(self, mock_stdout):
    ssl.patch().start()
    url = "https://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"&lt;Body text&gt;"
    )
    load(URL(url))

    self.assertIn('New socket opened!', mock_stdout.getvalue())
    self.assertIn('<Body text>', mock_stdout.getvalue())

  def test_load_entities(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"&lt;Body text&gt;"
    )
    load(URL(url))

    self.assertIn('<Body text>', mock_stdout.getvalue())

  def test_load_view_source(self, mock_stdout):
    url = "view-source:http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url))

    self.assertIn("<pre>Body text</pre>", mock_stdout.getvalue())

  def test_load_new_sockets(self, mock_stdout):
    url1 = "http://load_new_sockets.org/examples/load_new_sockets.html"
    url2 = "http://other_host.org/examples/load_new_sockets.html"
    socket.respond(
      url1, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text 1</pre>"
    )
    socket.respond(
      url2, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Example text 2</pre>"
    )
    load(URL(url1))
    load(URL(url2))

    new_sockets = re.findall(r'New socket opened!', mock_stdout.getvalue())
    self.assertEqual(len(new_sockets), 2)

  def test_load_reused_sockets(self, mock_stdout):
    url1 = "http://load_reused_sockets.org/examples/load_reused_sockets.html"
    url2 = "http://load_reused_sockets.org/examples/load_reused_sockets2.html"
    socket.respond(
      url1, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text 1</pre>"
    )
    socket.respond(
      url2, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Example text 2</pre>"
    )
    load(URL(url1))
    load(URL(url2))

    new_sockets = re.findall(r'New socket opened!', mock_stdout.getvalue())
    self.assertEqual(len(new_sockets), 1)

  def test_load_redirect_full_url(self, mock_stdout):
    url1 = "http://browser.engineering/examples/redirect.html"
    url2 = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url1, b"HTTP/1.0 301 Moved Permanently\r\n" + bytes(f"Location: {url2}\r\n\r\n",
                                                          encoding='utf-8') + b"<h2>Moved Permanently</h2>"
    )
    socket.respond(
      url2, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url1))

    self.assertIn(f"Redirecting to: {url2}", mock_stdout.getvalue())
    self.assertIn("Body text", mock_stdout.getvalue())

  def test_load_redirect_partial_url(self, mock_stdout):
    url1 = "http://browser.engineering/examples/redirect.html"
    url2_path = "/examples/example1-simple.html"
    url2 = f"http://browser.engineering{url2_path}"
    socket.respond(
      url1, b"HTTP/1.0 301 Moved Permanently\r\n" + bytes(f"Location: {url2_path}\r\n\r\n",
                                                          encoding='utf-8') + b"<h2>Moved Permanently</h2>"
    )
    socket.respond(
      url2, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url1))

    self.assertIn(f"Redirecting to: {url2}", mock_stdout.getvalue())
    self.assertIn("Body text", mock_stdout.getvalue())

  def test_load_too_many_redirects(self, mock_stdout):
    url1 = "http://browser.engineering/examples/redirect.html"
    url2 = "http://browser.engineering/examples/redirect2.html"
    url3 = "http://browser.engineering/examples/redirect3.html"
    url4 = "http://browser.engineering/examples/redirect4.html"
    url5 = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url1, b"HTTP/1.0 301 Moved Permanently\r\n" + bytes(f"Location: {url2}\r\n\r\n",
                                                          encoding='utf-8') + b"<h2>Moved Permanently</h2>"
    )
    socket.respond(
      url2, b"HTTP/1.0 301 Moved Permanently\r\n" + bytes(f"Location: {url3}\r\n\r\n",
                                                          encoding='utf-8') + b"<h2>Moved Permanently</h2>"
    )
    socket.respond(
      url3, b"HTTP/1.0 301 Moved Permanently\r\n" + bytes(f"Location: {url4}\r\n\r\n",
                                                          encoding='utf-8') + b"<h2>Moved Permanently</h2>"
    )
    socket.respond(
      url4, b"HTTP/1.0 301 Moved Permanently\r\n" + bytes(f"Location: {url5}\r\n\r\n",
                                                          encoding='utf-8') + b"<h2>Moved Permanently</h2>"
    )
    socket.respond(
      url5, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url1))

    self.assertIn(f"Redirecting to: {url2}", mock_stdout.getvalue())
    self.assertIn(f"Redirecting to: {url3}", mock_stdout.getvalue())
    self.assertIn(f"Redirecting to: {url4}", mock_stdout.getvalue())
    self.assertNotIn(f"Redirecting to: {url5}", mock_stdout.getvalue())
    self.assertIn("Too many redirects, sorry", mock_stdout.getvalue())

  def test_cache_no_header(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url))
    time.sleep(1)
    load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertNotIn('Returning content from cache:', mock_stdout.getvalue())

  def test_cache_expired(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Cache-Control: max-age=0\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url))
    time.sleep(1)
    load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertNotIn('Returning content from cache:', mock_stdout.getvalue())

  def test_cache_header_present_ok(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Cache-Control: max-age=10\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url))
    time.sleep(1)
    load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertIn('Returning content from cache:', mock_stdout.getvalue())

  def test_cache_header_present_not_ok(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 404 Not Found\r\n" + b"Cache-Control: max-age=10\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url))
    time.sleep(1)
    load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertNotIn('Returning content from cache:', mock_stdout.getvalue())

  def test_cache_header_present_no_store(self, mock_stdout):
    url = "http://browser.engineering/examples/cache_header_present_no_store.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Cache-Control: no-store, max-age=10\r\n\r\n" + b"<pre>Body text</pre>"
    )
    load(URL(url))
    time.sleep(1)
    load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertNotIn('Returning content from cache:', mock_stdout.getvalue())

  def test_content_length_present(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Content-Length: 5\r\n\r\n" + b"Body text"
    )
    load(URL(url))

    self.assertIn('Body ', mock_stdout.getvalue())
    self.assertNotIn('text', mock_stdout.getvalue())
