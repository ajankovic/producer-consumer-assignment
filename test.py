import unittest
from unittest import mock
from extr import Consumer, Producer, drain, runprocesses
from queue import Queue

BLOG_RESPONSE = """<html>
<body>
<a href="/blog/test">test page</a>
<a href="http://someotherwebsite.com">test page</a>
</body></html>"""

TEST_RESPONSE = """<html>
<body>
<a href="#blabla">test page</a>
<a href="http://testwebsite.com">test page</a>
</body></html>"""

EXTRACTED_URLS = ['http://someotherwebsite.com', 'http://ajankovic.com/blog/test', 'http://testwebsite.com']

# mock calls to requests.get
def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, text, status_code):
            self.text = text
            self.status_code = status_code

    if args[0] == 'http://ajankovic.com/blog/':
        return MockResponse(BLOG_RESPONSE, 200)
    elif args[0] == 'http://test.com':
        return MockResponse(TEST_RESPONSE, 200)
    else:
        return MockResponse('<html><body><a href="test">test</a></body></html>', 200)

    return MockResponse({}, 404)

class ConsumerTest(unittest.TestCase):
    def test_normalize_valid_url(self):
        c = Consumer()
        a = {'href':'http://ajankovic.com/blog/'}
        url = 'http://ajankovic.com'
        self.assertEqual('http://ajankovic.com/blog/', c.normalize(a, url))

    def test_normalize_relative_url(self):
        c = Consumer()
        a = {'href':'blog/'}
        url = 'http://ajankovic.com'
        self.assertEqual('http://ajankovic.com/blog/', c.normalize(a, url))

    def test_normalize_relative_root_url(self):
        c = Consumer()
        a = {'href':'/blog/'}
        url = 'http://ajankovic.com'
        self.assertEqual('http://ajankovic.com/blog/', c.normalize(a, url))
        a = {'href':'//ajankovic.com/blog/'}
        url = 'https://ajankovic.com'
        self.assertEqual('https://ajankovic.com/blog/', c.normalize(a, url))

    def test_normalize_invalid_url(self):
        c = Consumer()
        a = {'href':'skype:ajankovic?chat'}
        url = 'http://ajankovic.com'
        self.assertIsNone(c.normalize(a, url))

    @mock.patch('extr.requests.get', side_effect=mocked_requests_get)
    def test_run(self, mock_get):
        c = Consumer()
        markupq = Queue()
        markupq.put(('http://ajankovic.com/blog/', BLOG_RESPONSE))
        markupq.put(('http://test.com', TEST_RESPONSE))
        markupq.put(None)
        outq = Queue()

        c.run(markupq, outq)
        for item in drain(outq):
            if item is None:
                break
            self.assertIn(item, EXTRACTED_URLS)


class ProducerTest(unittest.TestCase):
    @mock.patch('extr.requests.get', side_effect=mocked_requests_get)
    def test_load_url(self, mock_get):
        p = Producer()
        url = 'http://ajankovic.com/blog/'
        markup = p.load_url(url)
        self.assertEqual(url, markup[0])
        self.assertEqual(BLOG_RESPONSE, markup[1])

        self.assertIn(mock.call(url, timeout=30), mock_get.call_args_list)

    @mock.patch('extr.requests.get', side_effect=mocked_requests_get)
    def test_run(self, mock_get):
        p = Producer()
        q = Queue()
        websites = ['http://ajankovic.com/blog/', 'http://test.com']
        extracted = [BLOG_RESPONSE, TEST_RESPONSE]
        p.run(websites, q)
        for item in drain(q):
            if item is None:
                break
            self.assertIn(item[1], extracted)

class MainTest(unittest.TestCase):
    @mock.patch('extr.requests.get', side_effect=mocked_requests_get)
    def test_runprocesses(self, mock_get):
        urls = ['http://ajankovic.com/blog/', 'http://test.com']
        for item in runprocesses(urls):
            self.assertIn(item, EXTRACTED_URLS)


if __name__ == '__main__':
    unittest.main(verbosity=2)