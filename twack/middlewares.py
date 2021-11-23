# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

# useful for handling different item types with a single interface
from scrapy import signals
from scrapy.downloadermiddlewares.cookies import CookiesMiddleware

from twack.twitter import TwitterAuth, TwitterGuestAuth, TwitterAccountAuth
from twack.utils import selenium_to_cookiejar


class TwitterAuthMiddleware(CookiesMiddleware):
    auth: TwitterAuth
    auth_lifetime: int
    request_counter: int = 0
    headers: dict = None

    def __init__(self, crawler, auth, debug=False, auth_lifetime=100):
        super().__init__(debug)
        crawler.signals.connect(self.spider_closed, signals.spider_closed)
        self.auth = auth
        self.auth_lifetime = auth_lifetime

    def invalid_auth(self):
        return self.headers is None or self.request_counter > self.auth_lifetime

    def process_request(self, request, spider):
        cookiejarkey = request.meta.get("cookiejar")
        jar = self.jars[cookiejarkey]

        if self.invalid_auth():
            self.headers, cookies = self.auth.auth()
            selenium_to_cookiejar(cookies, jar)

        self.request_counter += 1
        super().process_request(request, spider)
        for k, v in self.headers.items():
            request.headers[k] = v

    def spider_closed(self, spider):
        self.auth.close()


class TwitterGuestAuthMiddleware(TwitterAuthMiddleware):
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            crawler,
            TwitterGuestAuth(),
            crawler.settings.getbool('COOKIES_DEBUG'),
            crawler.settings.getint('TWITTER_GUEST_AUTH_LIFETIME'),
        )


class TwitterAccountAuthMiddleware(TwitterAuthMiddleware):
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            crawler,
            TwitterAccountAuth(),
            crawler.settings.getbool('COOKIES_DEBUG'),
            crawler.settings.getint('TWITTER_ACCOUNT_AUTH_LIFETIME'),
        )
