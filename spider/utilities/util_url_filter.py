# _*_ coding: utf-8 _*_

"""
util_url_filter.py by xianhu
"""

from pybloom_live import ScalableBloomFilter
from .util_config import CONFIG_URL_LEGAL_RE, CONFIG_URL_ILLEGAL_RE


class UrlFilter(object):
    """
    class of UrlFilter, to filter url by regexes and (BloomFilter or set)
    """

    def __init__(self, black_patterns=(CONFIG_URL_ILLEGAL_RE,), white_patterns=(CONFIG_URL_LEGAL_RE,), capacity=None):
        """
        constructor, use the instance of BloomFilter if capacity else the instance of set
        """
        self._re_black_list = [item_re for item_re in black_patterns]
        self._re_white_list = [item_re for item_re in white_patterns]
        self._url_filter = set() if not capacity else ScalableBloomFilter(capacity, error_rate=0.001)
        return

    def update(self, url_list):
        """
        update this url_filter using a url_list
        """
        for url in url_list:
            self._url_filter.add(url)
        return

    def check(self, url):
        """
        check the url based on self._re_black_list and self._re_white_list
        """
        for re_black in self._re_black_list:
            if re_black.search(url):
                return False

        for re_white in self._re_white_list:
            if re_white.search(url):
                return True

        return False if self._re_white_list else True

    def check_and_add(self, url):
        """
        check the url to make sure it hasn't been fetched, and add url to this url_filter
        """
        result = False
        if self.check(url):
            if isinstance(self._url_filter, set):
                result = (url not in self._url_filter)
                self._url_filter.add(url)
            else:
                result = (not self._url_filter.add(url))
        return result
