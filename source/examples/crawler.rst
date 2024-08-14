Books Crawler
============

In this example we will build a Crawler that follows all the page links on `Books to Scrape <https://books.toscrape.com/index.html>`_.

Building a crawler in DataService is fairly trivial.
We just need to define a function that finds all links on the page, yields them and then calls itself recursively.
DataService already implements a deduplication mechanism so you don't need to worry about making unnecessary requests.
