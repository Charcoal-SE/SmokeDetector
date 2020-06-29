import time
import datahandling
import metasmoke
import globalvars
import tasks
from helpers import log


class MetasmokeCache:
    _cache = {}
    _expiries = {}

    @staticmethod
    def get(key):
        """
        Retrieve a cached value. Will not re-generate expired values - if that's the behaviour you need, use
        MetasmokeCache.fetch.

        :param key: the cache key for which to find a value
        :returns: Tuple - [0] the cached value if it's available and in-date, otherwise None;
                          [1] a cache hit status - one of HIT-VALID, HIT-PERSISTENT, MISS-EXPIRED, or MISS-NOITEM
        """
        if key in MetasmokeCache._cache:
            if (key in MetasmokeCache._expiries and MetasmokeCache._expiries[key] >= int(time.time())) or \
               key not in MetasmokeCache._expiries:
                # Expiry was set on cache insert, and the value is still in-date, OR no expiry was set and the item
                # is persistently cached.
                return MetasmokeCache._cache[key],\
                    ('HIT-VALID' if key in MetasmokeCache._expiries else 'HIT-PERSISTENT')
            else:
                # Expiry was set on cache insert, but the value has expired. We're not regenerating values here.
                return None, 'MISS-EXPIRED'
        else:
            # Item never existed in the first place.
            return None, 'MISS-NOITEM'

    @staticmethod
    def fetch(key, generator=None, expiry=None):
        """
        Retrieve a cached value. Will re-generate expired values according to the supplied generator function.

        :param key:       The cache key for which to find a value.
        :param generator: A generator function that returns a fresh value for the supplied key, used if the value
                          has expired. Optional - if absent and the value is expired, a cache status of MISS-NOGEN
                          will be returned.
        :param expiry:    A value in seconds representing the TTL of the cache value. Only used if a fresh value
                          needed to be generated, in which case the fresh value will have this TTL applied. Optional.
        :returns: Tuple - [0] the cached value if it's available or generatable and in-date, otherwise None;
                          [1] a cache hit status - one of HIT-VALID, HIT-PERSISTENT, HIT-GENERATED, or MISS-NOGEN
        """
        value, cache_status = MetasmokeCache.get(key)
        if value is not None:
            # Cache hit. Doesn't matter what kind, because .get ensures it's valid. Return the item and status as-is.
            return value, cache_status
        elif value is None and generator is not None:
            # Cache miss, but we have a generator available so we can gen a value and return that.
            try:
                value = generator()
            except Exception:
                # Already logged in generator() so no need to log again
                return None, 'MISS-NOGEN'
            MetasmokeCache.insert(key, value, expiry)
            tasks.Tasks.do(dump_cache_data)
            return value, 'HIT-GENERATED'
        else:
            # Cache miss, and we can't generate a value - that's a MISS-NOGEN.
            return None, 'MISS-NOGEN'

    @staticmethod
    def fetch_from_api(key, uri, params=None, expiry=None):
        """
        Retrive a cached value. Will regenerate expired values from the metasmoke API.

        :param key:    The cache key for which to find a value.
        :param uri:    The URI for the API route from which to regenerate an expired value.
        :param params: Any parameters to be sent with the API request. The API key will be included automatically.
        :param expiry: A value in seconds representing the TTL of the cache value. Only used if a fresh value
                       needed to be generated, in which case the fresh value will have this TTL applied. Optional.
        :returns: Tuple - [0] the cached value if it's available or generatable and in-date, otherwise None;
                          [1] a cache hit status - one of HIT-VALID, HIT-PERSISTENT, HIT-GENERATED, or MISS-NOGEN
        """
        def generator():
            nonlocal uri, params
            if params is None:
                params = {'page': 1, 'key': globalvars.GlobalVars.metasmoke_key}
            else:
                params = params.update({'page': 1, 'key': globalvars.GlobalVars.metasmoke_key})

            items = []
            while True:
                try:
                    resp = metasmoke.Metasmoke.get(uri, params=params)
                except Exception as e:
                    log('warning', e)
                    raise
                if resp is None or not resp.ok:
                    break
                else:
                    page = resp.json()
                if 'items' in page:
                    items.extend(page['items'])
                if page['has_more'] is False:
                    break
                params['page'] += 1

            return items

        return MetasmokeCache.fetch(key, generator, expiry)

    @staticmethod
    def insert(key, value, expiry=None):
        """
        Insert a new value into the cache. Will overwrite existing value, if there is one.

        :param key:    The cache key under which to insert the value.
        :param value:  The value to insert.
        :param expiry: A value in seconds representing the TTL of the cache value. Optional - if absent, the value
                       will be inserted without a TTL, making it a persistently-cached value.
        :returns: None
        """
        MetasmokeCache._cache[key] = value
        if expiry is not None:
            MetasmokeCache._expiries[key] = int(time.time()) + expiry

        tasks.Tasks.do(dump_cache_data)

    @staticmethod
    def delete(key):
        """
        Delete a cached value.

        :param key: The cache key to delete.
        :returns: None
        """
        del MetasmokeCache._cache[key]
        del MetasmokeCache._expiries[key]
        tasks.Tasks.do(dump_cache_data)


def dump_cache_data():
    """
    Dump all cached data to disk in a pickle file. Not generally intended to be called by client code, but
    dispatched from tasks within this class - but it's there if you need to force a dump for some reason.

    :returns: None
    """
    datahandling._dump_pickle('metasmokeCacheData.p',
                              {'cache': MetasmokeCache._cache, 'expiries': MetasmokeCache._expiries})


def is_website_whitelisted(domain):
    whitelist = MetasmokeCache.fetch_from_api('whitelisted-domains', '/api/v2.0/tags/name/whitelisted/domains',
                                              params={'filter': 'HGGGFLHIHKIHOOH', 'per_page': '100'}, expiry=3600)
    return len(whitelist) > 0 and isinstance(whitelist[0], dict) and domain in map(lambda x: x['domain'], whitelist)
