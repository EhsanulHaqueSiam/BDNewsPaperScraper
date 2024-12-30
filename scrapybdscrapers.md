# ittefaq

```py
import scrapy
import json
from scrapy.http import JsonRequest

class IttefaqSpider(scrapy.Spider):
    name = "ittefaq"
    start_urls = [
        'https://en.ittefaq.com.bd/api/theme_engine/get_ajax_contents?widget=28&start=0&count=1000&page_id=1098&subpage_id=0&author=0&tags=&archive_time=&filter='
    ]

    headers = {
        'sec-ch-ua-platform': '"Linux"',
        'Referer': 'https://en.ittefaq.com.bd/bangladesh',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0'
    }

    def start_requests(self):
        for url in self.start_urls:
            yield JsonRequest(url, headers=self.headers)

    def parse(self, response):
        data = json.loads(response.text)
        html_content = data.get("html", "")

        # Use Scrapy's Selector to parse HTML content
        selector = scrapy.Selector(text=html_content)

        # Extract hrefs based on the provided XPath
        links = selector.xpath("//h2[@class='title']//a[@class='link_overlay']/@href").getall()

        # Normalize URLs and yield
        for link in links:
            full_url = response.urljoin(link)
            yield {'url': full_url}
```

`https://en.ittefaq.com.bd/api/theme_engine/get_ajax_contents?widget=28&start={start_at}&count={count}&page_id={catagory_id}&subpage_id=0&author=0&tags=&archive_time=&filter=`

#### catagory_id:
- Politics `page_id=1093 `
- Bangladesh `page_id=1098`
- youth `page_id=1115`
- art-and-culture `page_id=1116`
- climate-change `page_id=1113`
- health `page_id=1114`
- dont-miss `page_id=1119`
- sports `page_id=1095`
- entertainment `page_id=1096`
- lifestyle `page_id=1092`
- business `page_id=1094`
- tech `page_id=1102`
- viral-news `page_id=1104`


posturl: `https://en.ittefaq.com.bd/10197/why-addressing-unemployment-must-be-a-top-priority`
article body `//div[@itemprop='articleBody']//p//text()`
date published `//div[@class='each_row time']//span[@class='tts_time']//@content`

# thebangladeshtoday

`https://thebangladeshtoday.com/?cat={catagory_id}&paged={page_no}`
`https://thebangladeshtoday.com/?cat=93&paged=2`
`//section[@class=' ct-section']//div//div[contains(@class,'oxy-dynamic-list')]//div//a[@class='ct-link']//@href`

#### catagory_id:
- Bangladesh `cat=1`
- Nationwide `cat=93`
- Entertainment `cat=94`
- International `cat=97`
- Sports `cat=95`
- Feature `cat=96`

article url `https://thebangladeshtoday.com/?p=26098`
article body `//div[@class='ct-text-block']//span[contains(@class,'ct-span')]//p//text()`
date is in bangla

# observerbd

`https://www.observerbd.com/archive/2024-12-31`
article url xml path `//div[@class='archive']//a/@href`
article body `//div[@id='toPrint']//div[@id='f']//text()`
