import datetime as dt
import json
import logging
import urllib.parse as u
from typing import List

import scrapy

from twack.items import TwackUser, TwackFollow
from twack.utils import get_mongo

URL = (
    'https://twitter.com/i/api/graphql/pHK32L4uCgGxnMCfPoNIAw/Following?variables={query}'
)

META_USER_ID = 't_user_id'
META_RESULT_COUNT = 't_result_count'


def url_params(userId, cursor=None):
    cursor = dict(cursor=cursor) if cursor else {}

    return {
        "userId": userId,
        "count": 100,
        **cursor,
        "withTweetQuoteCount": False,
        "includePromotedContent": False,
        "withSuperFollowsUserFields": True,
        "withUserResults": True,
        "withBirdwatchPivots": False,
        "withReactionsMetadata": False,
        "withReactionsPerspective": False,
        "withSuperFollowsTweetFields": True
    }


def build_url(userId, cursor=None):
    params = url_params(userId, cursor)
    query = u.quote(json.dumps(params))
    return URL.format(query=query)


def build_users_query(userIds: List[str] = None):
    user_filter = {'user_id': {'$in': userIds}} if userIds else {}

    return [
        {
            '$group': {
                '_id': "$user_id_str",
                'tweet_count': {'$sum': 1}
            }
        },
        {
            '$sort': {'tweet_count': -1}
        },
        {
            '$lookup': {
                'from': "users",
                'localField': "_id",
                'foreignField': "id_str",
                'as': "user",
            }
        },
        {
            '$unwind': {
                'path': "$user",
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$project': {
                '_id': 0,
                'user_id': "$_id",
                'tweet_count': 1,
                'following_count': {'$cond': {
                    'if': {'$eq': [{'$type': "$user.t_following"}, "object"]},
                    'then': {'$size': {'$objectToArray': "$user.t_following"}},
                    'else': 0
                }}
            }
        },
        {
            '$match': {
                'following_count': {'$eq': 0},
                **user_filter,
            }
        }
    ]


class FollowerSpider(scrapy.Spider):
    name = "follows"
    allowed_domains = ["api.twitter.com"]
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
            'twack.middlewares.TwitterAccountAuthMiddleware': 543,
        }
    }

    # Parameters
    users: List[str] = None

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.users = self.users.split(',') if self.users else None

    def users_iterator(self):
        db = get_mongo(self.settings)
        results = db['tweets'].aggregate(build_users_query(self.users))
        for result in results:
            yield result['user_id']

    def build_request(self, cursor=None, meta=None):
        user_id = meta[META_USER_ID]
        result_count = meta[META_RESULT_COUNT]

        if result_count == 0:
            return None

        if cursor is None:
            logging.info(f'Starting crawl for user {user_id}')

        return scrapy.Request(
            url=build_url(user_id, cursor),
            meta={META_USER_ID: user_id},
            callback=self.parse,
            dont_filter=True
        )

    def start_requests(self):
        for user_id in self.users_iterator():
            yield self.build_request(meta={
                META_USER_ID: user_id,
                META_RESULT_COUNT: None
            })

    def parse(self, response):
        data = json.loads(response.text)
        meta = response.meta

        instructions = data['data']['user']['result']['timeline']['timeline']['instructions']
        instruction = next(filter(lambda x: x['type'] == 'TimelineAddEntries', instructions), None)
        entries = list(filter(lambda x: x['entryId'].startswith('user'), instruction['entries'])) if instruction else []
        cursor_entry = next(filter(lambda x: x['entryId'].startswith('cursor-bottom'), instruction['entries']),
                            None) if instruction else None
        cursor = cursor_entry['content']['value'] if cursor_entry else None

        follow_entries = [x['content']['itemContent'] for x in entries]
        for entry in follow_entries:
            user = entry['user_results']['result']
            if 'rest_id' not in user:
                continue

            yield TwackUser({
                'id': user['rest_id'],
                'id_str': str(user['rest_id']),
                **user['legacy'],
            })

            yield TwackFollow(
                scrape_date=dt.datetime.now(),
                user_id=meta[META_USER_ID],
                following_id=user['rest_id'],
                super_following=user['super_following']
            )

        meta[META_RESULT_COUNT] = len(follow_entries)
        yield self.build_request(cursor=cursor, meta=meta)
