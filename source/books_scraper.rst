Books Scraper
============

This example follows the `DataService` introduction and shows how to scrape a multi-page website.

The website we are going to scrape is `Books to Scrape <https://books.toscrape.com/index.html>`_.
It's been created for this purpose and is a great resource to practice web scraping.

The website has a list of pages with 20 books each. Each book has its own page with detailed information.

We will start by writing the `parse_books_page` function that will extract the book URLs from each page
