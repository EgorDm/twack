# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import pymongo
from scrapy.utils.project import get_project_settings

from twack.items import TwackTweet, TwackUser, TwackFollow
from twack.utils import get_mongo

MAPPING = {
    'tweets': TwackTweet,
    'users': TwackUser,
}


class TwackPipeline:
    def __init__(self) -> None:
        super().__init__()
        settings = get_project_settings()
        self.db = get_mongo(settings)
        self.collection_tweets = self.db['tweets']
        self.collection_users = self.db['users']

    def process_item(self, item, spider):
        if isinstance(item, TwackTweet):
            self.collection_tweets.update_one({'_id': str(item['id'])}, {'$set': {
                '_id': str(item['id']),
                **item
            }}, upsert=True)
        elif isinstance(item, TwackUser):
            self.collection_users.update_one({'_id': str(item['id'])}, {'$set': {
                '_id': str(item['id']),
                **item
            }}, upsert=True)
        elif isinstance(item, TwackFollow):
            super_following = item['super_following']
            self.collection_users.update_one(
                {'_id': str(item['user_id'])},
                {'$set': {
                    f't_following.{str(item["following_id"])}': super_following
                }},
            )
        else:
            raise TypeError(f'Unknown item type: {type(item)}')

        return item
