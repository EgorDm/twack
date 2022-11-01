# twack
Tweet scraping tool.

Features:
* Scrape tweets given hashtag or a filter
* Scrape users follower network
* All the data is stored into mongodb

## Usage
Scraping tweets containing foo and #bar after 1st of januari 2022
```
scrapy crawl Footer -a query="foo,#bar" -a since="2022-01-01T00:00:00"
```

Scrape followers for a certain user
```
scrapy crawl FollowerSpider -a users="elonmusk"
```
