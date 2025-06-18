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

        try:
            data = json.loads(script)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decoding error: {e}")
            return

        # Navigate through nested JSON keys to reach product details
        product_data = data.get('props', {}).get('pageProps', {}).get('productPageProps', {}).get('aemData', {}).get('productArticleDetails', {})
        if not product_data:
            self.logger.error("Product data not found in JSON")
            return
        
        # Extract product name and variations
        product_name = product_data.get("productName", "").strip()
        variations = product_data.get("variations", {})

        if not variations:
            self.logger.error("No variations found")
            return

        # Initialize list for available color names
        available_colors = []

        # Get the default color shown on the page and normalize it
        default_color = response.xpath('string(//h2[contains(normalize-space(.),"Цвят")]/following-sibling::p[1])').get()
        if default_color:
            default_color = default_color.strip()

        # Initialize available colors and find the matching variant, using case-insensitive comparison
        available_colors = []
        selected_variant = None
        for variant in variations.values():
            color_name = variant.get("name", "").strip()
            if color_name:
                if color_name not in available_colors:
                    available_colors.append(color_name)
                if default_color and color_name.lower() == default_color.lower():
                    selected_variant = variant

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

        # Use Playwright page object to reveal reviews info
        page = response.meta.get("playwright_page")
        if not page:
            self.logger.error("Playwright page object missing")
            return

        try:
            # Click element to open reviews details
            await page.click(
                "//main//section//a[2]/div[1]/text()",
                timeout=5000,
            )
            await page.wait_for_selector("//button[contains(normalize-space(.), 'Коментари')]/text()", timeout=5000)
            content = await page.content()
        except Exception as e:
            self.logger.error(f"Error during Playwright interaction: {e}")
            # as a fallback, try to get the current content anyway
            content = await page.content()
        finally:
            # Always close the Playwright page to free resources
            await page.close()

        # Get updated HTML content after interaction
        new_selector = Selector(text=content)

        # Extract reviews count using regex on text within the button
        reviews_count = 0
        count_text = new_selector.xpath("//button[contains(normalize-space(.), 'Коментари')]/text()").get()
        if count_text:
            match = re.search(r"\[(\d+)\]", count_text)
            if match:
                reviews_count = int(match.group(1))

        # Extract reviews score and safely convert it to a float
        reviews_score = 0.0
        score_text = new_selector.xpath(
            '//button[contains(normalize-space(.),"Коментари")]/following-sibling::button//span[2]/text()'
            ).get()
        if score_text:
            try:
                reviews_score = float(score_text.strip())
            except ValueError:
                self.logger.error("Unable to parse reviews score")

        # Yield the scraped product data as a dictionary
        yield {
            "name": product_name,
            "price": price,
            "color": default_color,
            "availableColors": available_colors,
            "reviews_count": reviews_count,
            "reviews_score": reviews_score,
        }
