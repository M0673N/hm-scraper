import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'hm_scraper.settings')

def main():
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl('hm_product')
    process.start()

if __name__ == '__main__':
    main()
