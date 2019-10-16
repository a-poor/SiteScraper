# SiteScraper

Created by Austin Poor

Simple custom web scraper

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
`> ipython SiteScraper.py source_name start_url allowed_domain base_url cycle_limit json_filename='' tsv_filename='' db_filename=''`

Examples:
`> ipython SiteScraper.py msnbc https://www.msnbc.com/ msnbc.com https://www.msnbc.com db_filename=db/sitescraper.db`
`> ipython SiteScraper.py vox https://www.vox.com/ vox.com https://www.vox.com db_filename=db/sitescraper.db`
`> ipython SiteScraper.py breitbart https://www.breitbart.com/ breitbart.com https://www.breitbart.com db_filename=db/sitescraper.db`
`> ipython SiteScraper.py fox https://www.foxnews.com/ foxnews.com https://www.foxnews.com db_filename=db/sitescraper.db`
