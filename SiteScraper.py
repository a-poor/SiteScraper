"""
SiteScraper.py
Created by Austin Poor

Built for recursively scraping a website using Requests
and BeautifulSoup.

It casts a pretty wide net and the information it gathers can be noisy
but it seems to be a good way to quickly gather a lot of information.


How it works:

Creates a list of sites that have been visited, are being visited, and will be visited.
Goes to the start_url and grabs all of the links from the <a> tags on the page and
adds them to the set to be visited. Then, until it runs out of links to visit or until 
the cycle_limit is reached, it moves the links to be visited to the links currently being
visited, and saves the joined <p> tags (to the database or json file), then grabs all of
the <a> tag links and if they haven't been visited yet, adds them to the links to visit,
and finally adds the current link to the set of visited links.


For command line arguments:
args go directly in the class initialization, kwargs get split between __init__ and scrape

Format:
> ipython SiteScraper.py source_name start_url allowed_domain base_url cycle_limit json_filename='' tsv_filename='' db_filename=''

Examples:
> ipython SiteScraper.py msnbc https://www.msnbc.com/ msnbc.com https://www.msnbc.com db_filename=db/sitescraper.db
> ipython SiteScraper.py vox https://www.vox.com/ vox.com https://www.vox.com db_filename=db/sitescraper.db
> ipython SiteScraper.py breitbart https://www.breitbart.com/ breitbart.com https://www.breitbart.com db_filename=db/sitescraper.db
> ipython SiteScraper.py fox https://www.foxnews.com/ foxnews.com https://www.foxnews.com db_filename=db/sitescraper.db

"""

import sys
import re
from time import localtime, strftime, sleep
import json
import sqlite3

import requests
from bs4 import BeautifulSoup

class SiteScraper:
    """
    Custom built webscraper for pulling articles from news sites
    and save them to a sqlite database or a json file.
    """
    def __init__(self, source_name, start_url, allowed_domain=None, base_url=None, cycle_limit=3):
        """
        source_name    => title of the source for the database (required)
        start_url      => entry point for scraping; NOTE: this page content isn't saved. (required)
        allowed_domain => only visit sites with this in the url
        base_url       => if the link partial, what to add to the start of the url
        cycle_limit    => max depth for searching
        """
        self.source_name = source_name
        self.start_url = start_url
        if allowed_domain:
            self.allowed_domain = allowed_domain
        else:
            partial_url = re.findall(r'\..*\.\w{3}', allowed_domain)[0]
            if partial_url.startswith('.'):
                self.allowed_domain = partial_url[1:]
            else:
                self.allowed_domain = partial_url
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = 'http://www.' + self.allowed_domain
        
        self.cycle_limit = cycle_limit

        # Create some attributes to store the urls    
        self.links_searched = set()
        self.links_searching = set()
        self.links_to_search = set()
        self.links_to_search.add(start_url)

        # Create an attribute to store the data pulled
        self.data = []
        return

    def timestamp(self):
        """ """
        return strftime('%y/%m/%d %H:%M:%S', localtime())

    def clean_text(self, unclean_text):
        """ """
        # Turn all whitespace into single spaces
        text = re.sub(r'\s+', ' ', unclean_text)
        # Remove all weird characters
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def add_data(self, url, text):
        """ """
        self.data.append({
            'timestamp': self.timestamp(),
            'source': self.source_name,
            'url': url,
            'text': self.clean_text(text)
        })
        return

    def soup_page(self, url):
        """ """
        response = requests.get(url)
        return BeautifulSoup(response.content)

    def parse_Ps(self, soup):
        """ """
        ps = soup.find_all('p')
        p_text = [p.text for p in ps]
        return ' '.join(p_text)

    def parse_As(self, soup):
        """ """
        As = soup.find_all('a')
        try:
            all_links = [link.attrs['href'] for link in As if 'href' in link.attrs]
        except:
            print(As[0].attrs)
            raise 
        for link in all_links:
            # clean_link = self.process_link(link)
            if link not in self.links_searched or link not in self.links_searching:
                    self.links_to_search.add(link)     
        return

    def process_link(self, link):
        """ """
        if link in ['', '/', '//']:
            # self.links_searched.add(link)
            return None
        elif self.allowed_domain in link:
            if link.startswith('http'):
                return link
            else:
                return 'https:' + link
        elif link.startswith('/'):
            return self.base_url + link
        elif re.search(r'\.\w*%s\w*\.' % self.source_name, link):
            if link.startswith('http'):
                return link
            else:
                return 'https:' + link
        else:
            # print('Couldn\'t parse link: ', link)
            return None

    def parse_page(self, url):
        """ """
        soup = self.soup_page(url)
        self.parse_As(soup)
        page_text = self.parse_Ps(soup)
        return page_text

    def single_scrape(self):
        """ """
        # Make sure to clear out all queued links
        while len(self.links_searching) > 0:
            self.links_searched.add(self.links_searching.pop())
        # Move all on-deck links to the active queue
        while len(self.links_to_search) > 0:
            self.links_searching.add(self.links_to_search.pop())
        # Process links in the queue
        for link in self.links_searching:
            clean_link = self.process_link(link)
            if clean_link is None:
                self.links_searched.add(link)
                continue
            try:
                page_text = self.parse_page(clean_link)
            except requests.HTTPError:
                print('<HTTPError> Sleeping')
                sleep(10)
            except Exception as e:
                if 'HTTPConnectionPool' in str(e):
                    print('<HTTPConnectionPool Error> Sleeping')
                    sleep(10)
                else:
                    print(e)
                continue
            self.add_data(link, page_text)
        # Finish by moving all queued links to the history
        while len(self.links_searching) > 0:
            self.links_searched.add(self.links_searching.pop())
        return

    def scrape(self, json_filename=None, tsv_filename=None, db_filename=None):
        """ """
        # Parse article
        i = 0
        print('Starting scrape.')
        while i < self.cycle_limit:
            print('%3i | Parsing %4i links.' % (i, len(self.links_to_search)))
            self.single_scrape()
            if len(self.links_to_search) == 0:
                print('Ran out of links to parse at cycle %i' % i)
                break
            i += 1
        print('Ending scrape. Successfully added %i pages of %i.' % (len(self.data), len(self.links_searched)))
        # Check if you need to save out the data
        if [json_filename, tsv_filename, db_filename].count(None) == 3:
            print(self.data)
        else:
            if json_filename is not None:
                self.to_json(json_filename)
            if tsv_filename is not None:
                self.to_tsv(tsv_filename)
            if db_filename is not None:
                self.to_sqlite(db_filename)
        return

    def to_json(self, filename):
        """ """
        assert len(self.data) > 0, "ERROR: Can't save! No data collected!"
        with open(filename, 'x') as f:
            json.dump(self.data, f)
        return

    def to_tsv(self, filename):
        """ """
        assert len(self.data) > 0, "ERROR: Can't save! No data collected!"
        with open(filename, 'x') as f:
            f.write('\t'.join(['timestamp', 'source', 'url', 'text']))
            f.write('\n')
            for row in self.data:
                for col in ['timestamp', 'source', 'url', 'text']:
                    f.write(row[col])
                    if col != 'text':
                        f.write('\t')
                    else:
                        f.write('\n')
        return

    def to_sqlite(self, filename):
        """ """
        assert len(self.data) > 0, "ERROR: Can't save! No data collected!"
        db = sqlite3.connect(filename)
        c = db.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS "SiteScrape" ( "Timestamp" TEXT, "Source" TEXT, "Url" TEXT, "Text" TEXT, PRIMARY KEY( "Source", "Url", "Text" ) )')
        db.commit()
        for row in self.data:
            try:
                c.execute(
                    'INSERT INTO "SiteScrape" ( "Timestamp", "Source", "Url", "Text" ) VALUES (?, ?, ?, ?);',
                    (row['timestamp'], row['source'], row['url'], row['text'])
                )
            except:
                pass
            db.commit()
        return

if __name__ == '__main__' and len(sys.argv) > 1:
    arguments = sys.argv[1:]
    args = []
    kwargs_a = {}
    kwargs_b = {}
    for a in arguments:
        if '=' in a:
            k, v = a.split('=')
            if k == 'cycle_limit': 
                v = int(v)
            if k in ['json_filename', 'tsv_filename', 'db_filename']:
                kwargs_b[k] = v
            else:
                kwargs_a[k] = v
        else:
            args.append(a)

    scraper = SiteScraper(*args, **kwargs_a)
    try:
        scraper.scrape(**kwargs_b)
    except KeyboardInterrupt as e:
        print('Caught error:', e, 'Trying to save before quitting.')
        if 'db_filename' in kwargs_b:
            try:
                scraper.to_sqlite(kwargs_b['db_filename'])
            except Exception as e2:
                raise e2
            raise e
                