import scrapy
import json
from scrapy_playwright.page import PageMethod

class HMProductSpider(scrapy.Spider):
    name = "hm_product"
    allowed_domains = ["www2.hm.com"]
    start_urls = ["https://www2.hm.com/bg_bg/productpage.1274171085.html"]

    custom_settings = {
        'FEED_FORMAT': 'json',
        'FEED_URI': 'product_data.json',
        # 'LOG_LEVEL': 'INFO',
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={"playwright": True},
                headers={
                    'Accept-Language': 'bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Referer': 'https://www2.hm.com/bg_bg/index.html',
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36',
                }
            )


    def parse(self, response):
        # Extract JSON data embedded in the __NEXT_DATA__ script tag
        script = response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
        if not script:
            self.logger.error("Could not find __NEXT_DATA__ script tag")
            return

        data = json.loads(script)

        # Dump the data into a file to explore the structure
        # with open("data_dump.txt", "w", encoding="utf-8") as f:
        #     json.dump(data, f, ensure_ascii=False, indent=4)

        # Navigate JSON to product details
        product_data = data.get('props', {}).get('pageProps', {}).get('productPageProps', {}).get('aemData', {}).get('productArticleDetails', {})
        if not product_data:
            self.logger.error("Product data not found in JSON")
            return
        
        product_name = product_data.get("productName", "")

        variations = product_data.get('variations', {})
        if not variations:
            self.logger.error("No variations found")
            return

        # Build a list of available color names from each variation
        available_colors = []
        for variant in variations.values():
            color_name = variant.get("name", "")
            if color_name and color_name not in available_colors:
                available_colors.append(color_name)

        # Select the first variation as the default selected variant
        first_variant_key = list(variations.keys())[0]
        selected_variant = variations[first_variant_key]
        default_color = selected_variant.get("name", "")

        # For price, use the "redPriceValue" (e.g., sale price) if available, otherwise "whitePriceValue"
        red_price_val = selected_variant.get("redPriceValue", "").strip()
        white_price_val = selected_variant.get("whitePriceValue", "").strip()
        try:
            # Give priority to the red (sales) price if present
            price = float(red_price_val) if red_price_val else float(white_price_val)
        except Exception:
            price = 0.0        


        # Reviews info
        # TODO

        yield {
            "name": product_name,
            "price": price,
            "color": default_color,
            "availableColors": available_colors,
            # "reviews_count": count,
            # "reviews_score": reviews_score,
        }

# scrapy crawl hm_product