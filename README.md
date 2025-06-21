# HM Scraper

This project is a Python-based web scraper built with the Scrapy framework and Playwright integration. It is designed to retrieve detailed information about a single product from the H&M website.

## Features

- Loads the product page at:  
  `https://www2.hm.com/bg_bg/productpage.1274171085.html`
- Parses the HTML content and embedded JSON data.
- Extracts the following product details:
  - Product name
  - Selected default color
  - Available colors
  - Price (sale price if available, otherwise regular price)
  - Reviews count
  - Reviews score
- Outputs the extracted data as a JSON file in a structured format.

## Output Format

The scraped data is saved as JSON objects with the following structure:

{
"name": "String",
"price": Double,
"color": "String",
"availableColors": Array,
"reviews_count": Int,
"reviews_score": Double
}


## Usage

1. Install required dependencies, including Scrapy and Scrapy-Playwright.
2. Run the spider using:
```
python3 main.py
```
3. The output JSON file (`product_data.json`) will contain the scraped product information.


### Note:
There are compatibility and performance issues on Windows 11 so if you have docker installed you can use this:
```
docker run m0673n/hm_scraper
```