import os.path
import pickle
from typing import Tuple, List

from scrapy.utils.project import get_project_settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class TwitterAuth:
    def auth(self) -> Tuple[dict, List[dict]]:
        pass

    def close(self):
        pass


class TwitterGuestAuth(TwitterAuth):
    driver: webdriver.Firefox

    def __init__(self):
        driver_options = webdriver.FirefoxOptions()
        driver_options.headless = True
        self.driver = webdriver.Firefox(options=driver_options)

    def auth(self):
        self.driver.delete_all_cookies()
        self.driver.get('https://twitter.com/explore')

        # Update cookies
        cookies = self.driver.get_cookies()

        # Update headers
        guest_token = self.driver.get_cookie('gt')['value']
        # csrf_token = self.driver.get_cookie('ct0')['value']
        headers = {
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'x-guest-token': guest_token,
            # 'x-csrf-token': csrf_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'en',
        }
        return headers, cookies

    def close(self):
        self.driver.quit()


COOKIES_SAFEFILE = "auth_twitter_cookies.pkl"


class TwitterAccountAuth(TwitterAuth):
    driver_options: webdriver.FirefoxOptions
    driver: webdriver.Firefox

    def __init__(self):
        driver_options = webdriver.FirefoxOptions()
        driver_options.headless = True
        self.driver = webdriver.Firefox(options=driver_options)

    def auth(self):
        # Load cookies
        self.driver.get('https://twitter.com/')
        if os.path.exists(COOKIES_SAFEFILE):
            with open(COOKIES_SAFEFILE, 'rb') as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                self.driver.add_cookie(cookie)

        # Login to twitter and refresh cookies
        self.driver.get('https://twitter.com/')
        element = WebDriverWait(self.driver, 5) \
            .until(EC.presence_of_element_located((By.XPATH, "//*[text()='Tweet']|//*[text()='Sign in']")))

        if element.text == 'Sign in':
            self.login()
            cookies = self.driver.get_cookies()
            self.driver.close()
        else:
            cookies = self.driver.get_cookies()

        # Update cookies
        pickle.dump(cookies, open(COOKIES_SAFEFILE, "wb"))

        # Return cookies
        csrf_token = self.driver.get_cookie('ct0')['value']
        guest_token = self.driver.get_cookie('gt')['value']
        headers = {
            'x-twitter-auth-type': ' OAuth2Session',
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'x-guest-token': guest_token,
            'x-csrf-token': csrf_token,
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'en',
        }
        return headers, cookies

    def login(self):
        settings = get_project_settings()
        self.driver.execute_script("window.open()")

        self.driver.get('https://twitter.com/i/flow/login')
        if settings.getbool('TWITTER_AUTOLOGIN'):
            WebDriverWait(self.driver, 20) \
                .until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))) \
                .send_keys(settings.get('TWITTER_USER'))
            self.driver.find_element_by_xpath("//*[text()='Next']") \
                .click()

            element = WebDriverWait(self.driver, 10) \
                .until(EC.presence_of_element_located((By.XPATH, "//*[text()='Log in']|//*[text()='Next']")))

            if element.text == 'Next':
                self.driver.find_element_by_css_selector("input[name='text']") \
                    .send_keys(settings.get('TWITTER_USERNAME'))
                element.click()

            WebDriverWait(self.driver, 10) \
                .until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))) \
                .send_keys(settings.get('TWITTER_PASS'))
            self.driver.find_element_by_xpath("//*[text()='Log in']") \
                .click()

        WebDriverWait(self.driver, 3600) \
            .until(EC.presence_of_element_located((By.XPATH, "//*[text()='Tweet']")))

    def close(self):
        self.driver.quit()
