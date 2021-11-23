import time
from dataclasses import dataclass
from http.cookiejar import Cookie, CookieJar
from typing import List

import pymongo
from selenium import webdriver

driver_options = webdriver.FirefoxOptions()
driver_options.headless = True
driver = webdriver.Firefox(options=driver_options)


def twitter_login(headers, cookies):
    pass


def update_cookies():
    driver.delete_all_cookies()
    driver.get('https://twitter.com/explore')

    # Update cookies
    cookies = driver.get_cookies()

    # Update headers
    guest_token = driver.get_cookie('gt')['value']
    csrf_token = driver.get_cookie('ct0')['value']
    headers = {
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'x-guest-token': guest_token,
        'x-csrf-token': csrf_token,
        'x-twitter-active-user': 'yes',
        'x-twitter-client-language': 'en',
    }
    return headers, cookies


def retry(fn, count=5, delay=1, cb=None):
    ex = None
    for i in range(count):
        try:
            return fn()
        except Exception as e:
            time.sleep(delay)
            if cb: cb()
            ex = e
    raise ex


def selenium_to_cookiejar(cookies: List[dict], jar: CookieJar) -> None:
    for cookie in cookies:
        jar.set_cookie(selenium_cookie_to_cookiejar(cookie))


def selenium_cookie_to_cookiejar(cookie: dict) -> Cookie:
    return Cookie(
        version=-1, port=None, port_specified=False,
        name=cookie['name'], value=cookie['value'],
        domain=cookie['domain'],
        domain_specified=bool(cookie['domain']),
        domain_initial_dot=cookie['domain'].startswith('.'),
        path=cookie['path'],
        path_specified=bool(cookie['path']),
        expires=cookie['expiry'] if 'expiry' in cookie else None, secure=cookie['secure'],
        discard=True,
        comment=None, comment_url=None,
        rfc2109=False,
        rest={'HttpOnly': cookie['httpOnly']},
    )


def get_mongo(settings):
    connection = pymongo.MongoClient(
        host=settings.get("MONGO_HOST"),
        port=settings.get("MONGO_PORT"),
        username=settings.get("MONGO_USER"),
        password=settings.get("MONGO_PASS"),
    )
    return connection[settings.get("MONGO_DB")]
