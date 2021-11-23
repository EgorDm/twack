import datetime as dt
import json
import logging
import re
import urllib.parse as u

import scrapy

from twack.items import TwackTweet, TwackUser

URL = (
    f'https://api.twitter.com/2/search/adaptive.json?'
    f'include_profile_interstitial_type=1'
    f'&include_blocking=1'
    f'&include_blocked_by=1'
    f'&include_followed_by=1'
    f'&include_want_retweets=1'
    f'&include_mute_edge=1'
    f'&include_can_dm=1'
    f'&include_can_media_tag=1'
    f'&skip_status=1'
    f'&cards_platform=Web-12'
    f'&include_cards=1'
    f'&include_ext_alt_text=true'
    f'&include_quote_count=true'
    f'&include_reply_count=1'
    f'&tweet_mode=extended'
    f'&include_entities=true'
    f'&include_user_entities=true'
    f'&include_ext_media_color=true'
    f'&include_ext_media_availability=true'
    f'&send_error_codes=true'
    f'&simple_quoted_tweet=true'
    f'&query_source=typed_query'
    f'&pc=1'
    f'&spelling_corrections=1'
    f'&ext=mediaStats%2ChighlightedLabel'
    f'&count=100'
    f'&tweet_search_mode=live'
    '&q={query}'
)

CURSOR_RE = re.compile('"(scroll:[^"]*)"')
DT_FMT = '%Y-%m-%d'
RETWEET_FILTER = '-filter:retweets AND -filter:replies'

META_DEPTH = 't_depth'
META_DATE = 't_date'


def build_query(query: str, since: dt.datetime, until: dt.datetime):
    query = query
    if since:
        query += f' since:{since.strftime(DT_FMT)}'
    if until:
        query += f' until:{until.strftime(DT_FMT)}'
    query += ' lang:en'
    return query


def build_url(query: str, cursor=None):
    url = URL.format(query=u.quote(query))
    if cursor:
        url += f'&cursor={cursor}'
    return url


class TweetSpider(scrapy.Spider):
    name = "tweets"
    allowed_domains = ["api.twitter.com"]
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
            'twack.middlewares.TwitterGuestAuthMiddleware': 543,
        }
    }

    # Parameters
    query: str = ''
    since: dt.datetime = dt.datetime.now() - dt.timedelta(days=365)
    until: dt.datetime = dt.datetime.now()
    depth: int = 50
    concurrency: int = 1

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.since = dt.datetime.strptime(self.since, DT_FMT) if isinstance(self.since, str) else self.since
        self.until = dt.datetime.strptime(self.until, DT_FMT) if isinstance(self.until, str) else self.until
        self.depth = int(self.depth)

    def build_request(self, cursor=None, meta=None):
        meta = meta or {}
        depth = meta[META_DEPTH] + 1
        date = meta[META_DATE]

        if depth > self.depth:
            step_size = self.settings.getint('CONCURRENT_REQUESTS')
            date = date - dt.timedelta(days=step_size)
            if date < self.since:
                return None

            logging.log(logging.INFO, f'Reached depth {depth}, resetting to {date}')
            depth = 0

        built_query = build_query(self.query, date, date + dt.timedelta(days=1))
        url = build_url(built_query, cursor=cursor)
        return scrapy.Request(
            url,
            callback=self.parse,
            dont_filter=not cursor,
            meta={META_DEPTH: depth, META_DATE: date}
        )

    def start_requests(self):
        for i in range(self.settings.getint('CONCURRENT_REQUESTS')):
            yield self.build_request(meta={
                META_DEPTH: 0,
                META_DATE: self.until - dt.timedelta(days=i + 1),
            })

    def parse(self, response):
        data = json.loads(response.text)

        yield from map(lambda x: TwackTweet(**x), data['globalObjects']['tweets'].values())
        yield from map(lambda x: TwackUser(**x), data['globalObjects']['users'].values())

        cursor = CURSOR_RE.search(response.text).group(1)
        yield self.build_request(cursor=cursor, meta=response.meta)
