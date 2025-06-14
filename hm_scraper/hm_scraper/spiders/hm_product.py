import scrapy
import json
import re
from scrapy import Selector
from scrapy_playwright.page import PageMethod

class HMProductSpider(scrapy.Spider):
    name = "hm_product"
    allowed_domains = ["www2.hm.com"]
    start_urls = ["https://www2.hm.com/bg_bg/productpage.1274171085.html"]

    custom_settings = {
        # Output the scraped items in JSON Lines format (one JSON object per line)
        'FEED_FORMAT': 'jsonlines',
        'FEED_URI': 'product_data.json',
    }

    def start_requests(self):
        """
        Initiates requests to start URLs with Playwright enabled.
        Uses Playwright to render JavaScript-heavy pages by waiting for network idle state.
        Sets custom headers including User-Agent and Accept-Language for better mimicry of real browsers.
        """
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,  # Enable Playwright for this request
                    "playwright_include_page": True,  # Include Playwright page object in response.meta
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),  # Wait until network is idle before processing
                    ],
                },
                headers={
                    # Spoof a realistic User-Agent to avoid bot detection
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/115.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                    "Referer": "https://www2.hm.com/bg_bg/index.html",
                    "Connection": "keep-alive",
                }
            )

    async def parse(self, response):
        """
        Parses the product page response.
        Extracts product details from embedded JSON data.
        Uses Playwright to interact with page elements to reveal reviews info.
        Yields a dictionary with product info.
        """
        # Extract JSON data embedded in the __NEXT_DATA__ script tag for structured product info
        script = response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
        if not script:
            self.logger.error("Could not find __NEXT_DATA__ script tag")
            return

        data = json.loads(script)

        # Navigate through nested JSON keys to reach product details
        product_data = data.get('props', {}).get('pageProps', {}).get('productPageProps', {}).get('aemData', {}).get('productArticleDetails', {})
        if not product_data:
            self.logger.error("Product data not found in JSON")
            return
        
        # Extract product name
        product_name = product_data.get("productName", "")

        # Extract product variations (e.g., colors)
        variations = product_data.get('variations', {})
        if not variations:
            self.logger.error("No variations found")
            return

        # Initialize list for available color names
        available_colors = []

        # Extract default color
        default_color = response.css(
            '#__next > main > div.rOGz > div > div > div:nth-child(2) > div > div > div.f27895 > section > p::text'
        ).get()

        selected_variant = None  # Will hold the variant matching the default color

        # Iterate over variations to collect all color names and find the selected variant
        for variant in variations.values():
            color_name = variant.get("name", "")
            if color_name == default_color:
                selected_variant = variant  # Found the variant matching the default color
            if color_name not in available_colors:
                available_colors.append(color_name)

        # Safeguard: if no matching variant found, pick the first one as fallback
        if not selected_variant:
            first_key = list(variations.keys())[0]
            selected_variant = variations[first_key]

        # Extract price, prioritizing sale price ("redPriceValue") if available
        red_price_val = selected_variant.get("redPriceValue", "").strip()
        white_price_val = selected_variant.get("whitePriceValue", "").strip()
        try:
            price = float(red_price_val) if red_price_val else float(white_price_val)
        except Exception:
            price = 0.0  # Default price if parsing fails

        # Use Playwright page object to interact with the page for reviews info
        page = response.meta["playwright_page"]

        # Click on the element to reveal reviews count and score
        await page.click(
            "#__next > main > div.rOGz > div > div > div:nth-child(2) > div > div > div.f27895 > section > div.ff18ac.ab7eab > div > a:nth-child(2)"
        )

        # Wait explicitly for the reviews count button to appear after click
        await page.wait_for_selector('button.abb0ad.dfc6c7.a61a60.ed39fb', timeout=5000)

        # Get updated HTML content after interaction
        content = await page.content()
        new_selector = Selector(text=content)

        # Extract reviews count element HTML
        count_el = new_selector.css('button.abb0ad.dfc6c7.a61a60.ed39fb').get()
        # Use regex to find number inside square brackets, e.g., "[60]"
        match = re.search(r'\[(\d+)\]', count_el)
        count = int(match.group(1)) if match else 0

        # Extract reviews score text and convert to float
        score_text = new_selector.css(
            'button.d1a171.f14b25 > div > span.ed5fe2.ca866b::text'
        ).get()
        reviews_score = float(score_text.strip()) if score_text else 0.0

        # Yield the scraped product data as a dictionary
        yield {
            "name": product_name,
            "price": price,
            "color": default_color,
            "availableColors": available_colors,
            "reviews_count": count,
            "reviews_score": reviews_score,
        }

# To run this spider, use:
# scrapy crawl hm_product
