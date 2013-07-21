# python3

import unittest
import urllib.request
import json
import re
import code
import os
from unittest.mock import MagicMock
import collections

class Posts:
  DB = []

  @classmethod
  def add(klass, post):
    klass.DB.append(post)

  @classmethod
  def all(klass):
    return klass.DB

  @classmethod
  def clear(klass):
    klass.DB = []

  @classmethod
  def save_all(klass, posts):
    klass.clear()
    for post in posts:
      klass.add(post)

class FoChanClient:
  @classmethod
  def fetch(klass, board):
    url = "https://api.4chan.org/{0}/catalog.json".format(board)
    return urllib.request.urlopen(url).read().decode('utf-8')

class Parser:
  def __init__(self, resp):
    self.json = json.loads(resp)

  def pages(self):
    return self.json

  def threads(self):
    threads = []
    for page in self.pages():
      for thread in page["threads"]:
        threads.append(thread)
    return threads

  def posts(self):
    posts_with_text = []

    posts_with_last_replies = self._nodes_with_key(self.threads(), "last_replies")
    com_posts = self._nodes_with_key(self.threads(), "com")
    posts_with_text = self._nodes_with_key(self.threads(), "com") + self._nodes_with_key(posts_with_last_replies, "com")

    return posts_with_text

  def _nodes_with_key(self, nodes, key):
    result = []
    for node in nodes:
      if key in node:
        result.append(node)

    return result

class Controller:
  def __init__(self, board):
    api_response = FoChanClient.fetch(board)
    parser = Parser(api_response)
    Posts.save_all(parser.posts())

  def matches(self, word):
    self.word = word
    self.matches = []
    posts = Posts.all()
    for post in posts:
      if word in post["com"]:
        self.matches.append(post)

    return self.matches

  def sort_by_freq(self):
    sorted_matches = []
    matches_with_frequency = {}

    for post in self.matches:
      freq_in_post = post["com"].count(self.word)
      if freq_in_post in matches_with_frequency:
        matches_with_frequency[freq_in_post].append(post)
      else:
        matches_with_frequency[freq_in_post] = [post]

    ordered_mwf = collections.OrderedDict(sorted(matches_with_frequency.items(), reverse=True))
    # code.interact(local=locals())
    return ordered_mwf

  def count_by_post(self):
    return len(self.matches)

  def count_by_word(self):
    count = 0
    for post in self.matches:
      count += post["com"].count(self.word)

    return count

class Printer:
  def __init__(self, controller):
    self.controller = controller

  def headers(self):
    post_count = self.controller.count_by_post()
    word_count = self.controller.count_by_word()
    print("Pattern '{0}'. Posts count {1}, Repeats {2}".format(self.controller.word, post_count, word_count))

  def posts_with_context(self):
    # sorted by WORD frequency
    for freq, posts in self.controller.sort_by_freq().items():
      print("==== Frequency {0} ====".format(freq))
      for post in posts:
        post_info = { 'author': post["name"], 'context': self._interpret(post["com"], freq) }
        print("~~~~ {0} ~~~~".format(post_info["author"]))
        print(post_info["context"])

  def _interpret(self, text, freq):
    word = self.controller.word
    text.replace("<br>", "\n")
    text = re.sub('<[^>]*>', '', text)

    context_chars = 50
    word_index = text.index(word)
    if freq == 1:
      text = text[max(0, word_index-context_chars):min(word_index+context_chars, len(text))]

    # highlight the word
    text = re.sub(word, "\033[32m{0}\033[0m".format(word), text)
    return text

class Live(unittest.TestCase):
  def test_live(self):
    if os.environ.get('LIVE') == 'true':
        word = os.environ.get('WORD', ' no ')

        random = Controller("b")
        no = random.matches(word)
        printer = Printer(random)
        printer.headers()
        printer.posts_with_context()

class TestSequenceFunctions(unittest.TestCase):

  if os.environ.get('LIVE') != 'true':
    FoChanClient.fetch = MagicMock(return_value=open("catalog.json", "r").read())

  def tearDown(self):
    Posts.clear()

  def test_adding_and_getting_from_database(self):
    Posts.add("imagine its a json")
    self.assertEqual(len(Posts.all()), 1)

  def test_should_have_correct_pages(self):
    parser = Parser(FoChanClient.fetch('b'))
    self.assertEqual(len(parser.pages()), 16)

  def test_should_have_correct_threads(self):
    parser = Parser(FoChanClient.fetch('b'))
    # the magic number is 238 = 15 * 16
    self.assertEqual(len(parser.threads()), 240)

  def test_should_save_all_posts(self):
    parser = Parser(FoChanClient.fetch('b'))
    posts = parser.posts()
    Posts.save_all(posts)
    posts_count = len(posts)
    saved_posts_count = len(Posts.all())
    self.assertEqual(posts_count, saved_posts_count)

  def test_should_count_post_matches(self):
    random = Controller("b")
    no = random.matches("no")
    self.assertEqual(random.count_by_post(), 126)
    self.assertEqual(len(no), 126)

  def test_should_count_word_matches(self):
    random = Controller("b")
    no = random.matches("no")
    self.assertEqual(random.count_by_word(), 229)
    self.assertTrue(random.count_by_word() > len(no))

if __name__ == '__main__':
  unittest.main()
