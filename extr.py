import fileinput
import logging
from multiprocessing import Process, Queue
import concurrent.futures
from queue import Empty
import requests
import sys
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urlsplit

logging.basicConfig(level=logging.INFO)


class Producer(object):
    def __init__(self, timeout=30, max_workers=5):
        self.timeout = timeout
        self.max_workers = max_workers

    def load_url(self, url):
        """load url with requests library"""
        res = requests.get(url, timeout=self.timeout)  # IO blocking
        logging.info("got markup: {}".format(res.status_code))
        if res.status_code == 200:
            return url, res.text
        res.close()

    def run(self, urls, queue):
        """start sending urls to queue concurrently with threading parallelism"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.load_url, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    res = future.result()
                    queue.put(res)
                except Exception as exc:
                    logging.info('got exception with concurent crawl {}'.format(repr(exc)))
                else:
                    logging.info('loaded {0} page {1} bytes'.format(url, len(res[1])))
        queue.put(None)


class Consumer(object):

    def __init__(self, timeout=30):
        self.timeout = timeout # how much to wait results from producer

    def normalize(self, a, url):
        """normalize found urls to valid representation"""
        href = a['href']
        if not href:
            return None
        if href.startswith('#'):
            return None
        if href.startswith('//'):
            href = "{0.scheme}:{1}".format(urlsplit(url), href)
        elif href.startswith('/'):
            href = "{0.scheme}://{0.netloc}{1}".format(urlsplit(url), href)
        elif not urlsplit(href).scheme:
            href = "{0.scheme}://{0.netloc}/{1}".format(urlsplit(url), href)
        if not (href.startswith('http://') or href.startswith('https://')):
            return None
        return href

    def run(self, markupq, outq):
        """search markup for anchor tags and output normalized urls to outq"""
        for markup in drain(markupq, self.timeout):
            if markup is None:
                outq.put(None)
                return
            try:
                for l in BeautifulSoup(markup[1], 'html.parser', parse_only=SoupStrainer('a', href=True)): # CPU bound
                    logging.info("extracted link: {}".format(l['href']))
                    u = self.normalize(l, markup[0])
                    if u:
                        outq.put(u)
            except Exception:
                continue


def drain(q, timeout=10):
    """helper function to drain queues"""
    while True:
        try:
            yield q.get(timeout=timeout)
        except Empty:
            break


def runprocesses(urls):
    """run producer and consumer as two separate processes"""
    markupq = Queue()
    outq = Queue()
    p = Producer()
    c = Consumer()
    pt = Process(target=p.run, args=(urls, markupq))
    ct = Process(target=c.run, args=(markupq, outq))
    pt.start()
    ct.start()
    for item in drain(outq):
        if item is None:
            break
        yield item
    try:
        pt.join()
        ct.join()
    except KeyboardInterrupt:
        logging.info("exiting")


if __name__ == "__main__":
    # take all input files into one list of urls
    urls = fileinput.input()
    if not urls:
        print("arguments empty")
        sys.exit(1)
    with open('extracted_links.txt','w') as f:
        for item in runprocesses(map(str.rstrip, urls)):
            print(item, file=f)
