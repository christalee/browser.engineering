import unittest
import json
from unittest.mock import patch
import io
import re
import time
import gzip

from browser import Browser
from url import URL
from test_utils import socket, ssl


class TestBrowserLex(unittest.TestCase):
  # Tests for lex()
  def test_lex_no_tags(self):
    body = 'Hello, world!'
    text = Browser().lex(body)

    self.assertEqual(text, body)

  def test_lex_tags(self):
    body = '<pre>Hello, world!</pre>'
    text = Browser().lex(body)

    self.assertEqual(text, 'Hello, world!')

  def test_lex_entities(self):
    body = '&lt;div&gt;'
    text = Browser().lex(body)

    self.assertEqual(text, '<div>')

  def test_lex_invalid_entities(self):
    body = '&asdf;'
    text = Browser().lex(body)

    self.assertEqual(text, '')

  def test_lex_unicode(self):
    body = '🍐🪄'
    text = Browser().lex(body)

    self.assertEqual(text, body)


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
    Browser().load(URL(url))

    self.assertIn('New socket opened!', mock_stdout.getvalue())
    self.assertIn('<Body text>', mock_stdout.getvalue())

  def test_load_https(self, mock_stdout):
    ssl.patch().start()
    url = "https://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"&lt;Body text&gt;"
    )
    Browser().load(URL(url))

    self.assertIn('New socket opened!', mock_stdout.getvalue())
    self.assertIn('<Body text>', mock_stdout.getvalue())

  def test_load_entities(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"&lt;Body text&gt;"
    )
    Browser().load(URL(url))

    self.assertIn('<Body text>', mock_stdout.getvalue())

  def test_load_view_source(self, mock_stdout):
    url = "view-source:http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text</pre>"
    )
    Browser().load(URL(url))

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
    Browser().load(URL(url1))
    Browser().load(URL(url2))

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
    Browser().load(URL(url1))
    Browser().load(URL(url2))

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
    Browser().load(URL(url1))

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
    Browser().load(URL(url1))

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
    Browser().load(URL(url1))

    self.assertIn(f"Redirecting to: {url2}", mock_stdout.getvalue())
    self.assertIn(f"Redirecting to: {url3}", mock_stdout.getvalue())
    self.assertIn(f"Redirecting to: {url4}", mock_stdout.getvalue())
    self.assertNotIn(f"Redirecting to: {url5}", mock_stdout.getvalue())
    self.assertIn("Too many redirects, sorry", mock_stdout.getvalue())

  def test_load_cache_no_header(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Header1: Value1\r\n\r\n" + b"<pre>Body text</pre>"
    )
    Browser().load(URL(url))
    time.sleep(1)
    Browser().load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertNotIn('Returning content from cache:', mock_stdout.getvalue())

  def test_load_cache_expired(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Cache-Control: max-age=0\r\n\r\n" + b"<pre>Body text</pre>"
    )
    Browser().load(URL(url))
    time.sleep(1)
    Browser().load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertNotIn('Returning content from cache:', mock_stdout.getvalue())

  def test_load_cache_header_present_ok(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Cache-Control: max-age=10\r\n\r\n" + b"<pre>Body text</pre>"
    )
    Browser().load(URL(url))
    time.sleep(1)
    Browser().load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertIn('Returning content from cache:', mock_stdout.getvalue())

  def test_load_cache_header_present_not_ok(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 404 Not Found\r\n" + b"Cache-Control: max-age=10\r\n\r\n" + b"<pre>Body text</pre>"
    )
    Browser().load(URL(url))
    time.sleep(1)
    Browser().load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertNotIn('Returning content from cache:', mock_stdout.getvalue())

  def test_load_cache_header_present_no_store(self, mock_stdout):
    url = "http://browser.engineering/examples/cache_header_present_no_store.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Cache-Control: no-store, max-age=10\r\n\r\n" + b"<pre>Body text</pre>"
    )
    Browser().load(URL(url))
    time.sleep(1)
    Browser().load(URL(url))

    body_text = re.findall(r'Body text', mock_stdout.getvalue())
    self.assertEqual(len(body_text), 2)
    self.assertNotIn('Returning content from cache:', mock_stdout.getvalue())

  def test_load_content_length_present(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Content-Length: 5\r\n\r\n" + b"Body text"
    )
    Browser().load(URL(url))

    self.assertIn('Body ', mock_stdout.getvalue())
    self.assertNotIn('text', mock_stdout.getvalue())

  def test_load_compression_non_chunked(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    body = gzip.compress(b"Body text")
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Content-Encoding: gzip\r\n\r\n" + body
    )
    Browser().load(URL(url))

    self.assertIn("Body text", mock_stdout.getvalue())

  def test_load_compression_chunked(self, mock_stdout):
    url = "http://browser.engineering/examples/example1-simple.html"
    body_content = gzip.compress(b"Body text")
    body = bytes(f"{hex(len(body_content))}\r\n", encoding='utf-8') + body_content + bytes(f"\r\n{hex(0)}\r\n\r\n",
                                                                                           encoding='utf-8')
    socket.respond(
      url, b"HTTP/1.0 200 OK\r\n" + b"Content-Encoding: gzip\r\n" + b"Transfer-Encoding: chunked\r\n\r\n" + body
    )
    Browser().load(URL(url))

    self.assertIn("Body text", mock_stdout.getvalue())
