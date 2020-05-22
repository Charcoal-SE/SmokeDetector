# coding=utf-8
from typing import Union

import regex
import yaml
import dns.resolver

from globalvars import GlobalVars
from helpers import log


def load_blacklists():
    bwdict = GlobalVars.git_black_watch_lists

    bwdict['bad_keywords'] = Blacklist(
        'bad_keywords.txt', BasicListParser)
    bwdict['watched_keywords'] = Watchlist(
        'watched_keywords.txt', TSVDictParser)
    bwdict['blacklisted_websites'] = Blacklist(
        'blacklisted_websites.txt', BasicListParser)
    bwdict['blacklisted_usernames'] = UserBlacklist(
        'blacklisted_usernames.txt', BasicListParser)
    bwdict['blacklisted_numbers'] = PhoneBlacklist(
        'blacklisted_numbers.txt', BasicListParser)
    bwdict['watched_numbers'] = PhoneWatchlist(
        'watched_numbers.txt', TSVDictParser)
    bwdict['blacklisted_nses'] = NetBlacklist(
        'blacklisted_nses.yml', YAMLParserNS)
    bwdict['watched_nses'] = NetWatchlist(
        'watched_nses.yml', YAMLParserNS)
    bwdict['blacklisted_cidrs'] = NetBlacklist(
        'blacklisted_cidrs.yml', YAMLParserCIDR)
    bwdict['watched_cidrs'] = NetWatchlist(
        'watched_cidrs.yml', YAMLParserCIDR)
    # bwdict['blacklisted_asns'] = NetBlacklist(
    #    'blacklisted_asns.yml', YAMLParserASN)
    bwdict['watched_asns'] = NetWatchlist(
        'watched_asns.yml', YAMLParserASN)


class BlacklistParser:
    def __init__(self, filename):
        self._filename = filename

    def parse(self):
        return []

    def add(self, item):
        pass

    def delete(self, item):
        pass

    def exists(self, item):
        pass


class BasicListParser(BlacklistParser):
    def _normalize(self, input):
        """
        Wrapper to normalize a value. Default method just calls .rstrip()
        """
        return input.rstrip()

    def parse(self):
        with open(self._filename, 'r', encoding='utf-8') as f:
            return [self._normalize(line)
                    for line in f if len(line.rstrip()) > 0 and line[0] != '#']

    def add(self, item: str):
        with open(self._filename, 'a+', encoding='utf-8') as f:
            last_char = f.read()[-1:]
            if last_char not in ['', '\n']:
                item = '\n' + item
            f.write(item + '\n')

    def delete(self, item: str):
        with open(self._filename, 'r+', encoding='utf-8') as f:
            items = f.readlines()
            items = [x for x in items if item not in x]
            f.seek(0)
            f.truncate()
            f.writelines(items)

    def each(self, with_info=False):
        # info = (filename, lineno)
        with open(self._filename, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, start=1):
                if with_info:
                    yield line.rstrip("\n"), (i, self._filename)
                else:
                    yield line.rstrip("\n")

    def exists(self, item: str):
        item = item.lower()

        with open(self._filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, x in enumerate(lines, start=1):
                if item == x.lower().rstrip('\n'):
                    return True, i

        return False, -1


class WhoWhatWhenString(str):
    """
    str wrapper with additional attributes for TSVDictParser to generate
    """
    def __new__(cls, seq, who, when, filename, lineno, *args, **kwargs):
        self = super().__new__(cls, seq, *args, **kwargs)
        self._who = who
        self._when = when
        self._filename = filename
        self._lineno = lineno
        return self

    def when(self):
        return self._when

    def who(self):
        return self._who


class TSVDictParser(BlacklistParser):
    """
    Parser for 3-column TSV file with "when" (Unix timestamp), "who", and
    "what" fields.
    """
    def parse(self):
        with open(self._filename, 'r', encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                if regex.compile(r'^\s*(?:#|$)').match(line):
                    continue
                try:
                    when, by_whom, what = line.rstrip().split('\t')
                except ValueError as err:
                    log('error', '{0}:{1}:{2}'.format(
                        self._filename, lineno, err))
                    continue
                if what[0] != "#":
                    """
                    yield WhoWhatWhenString(
                        who=by_whom, when=when,
                        filename=self._filename, lineno=lineno, what)
                    """
                    yield WhoWhatWhenString(seq=what, who=by_whom, when=when, filename=self._filename, lineno=lineno)

    def add(self, item: Union[str, WhoWhatWhenString]):
        with open(self._filename, 'a+', encoding='utf-8') as f:
            if isinstance(item, WhoWhatWhenString):
                item = '{}\t{}\t{}'.format(item.when(), item.who(), item)
            last_char = f.read()[-1:]
            if last_char not in ['', '\n']:
                item = '\n' + item
            f.write(item + '\n')

    def delete(self, item: Union[str, WhoWhatWhenString]):
        with open(self._filename, 'r+', encoding='utf-8') as f:
            items = f.readlines()
            items = [
                x for x in items if ('\t' not in x) or
                (len(x.split('\t')) == 3 and x.split('\t')[2].strip() != item)]
            f.seek(0)
            f.truncate()
            f.writelines(items)

    def each(self, with_info=False):
        # info = (filename, lineno)
        with open(self._filename, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, start=1):
                if line.count('\t') == 2:
                    if with_info:
                        yield line.rstrip("\n").split('\t')[2], (
                            i, self._filename)
                    else:
                        yield line.rstrip("\n").split('\t')[2]

    def exists(self, item: Union[str, WhoWhatWhenString]):
        if not isinstance(item, WhoWhatWhenString):
            item = item.split('\t')[-1]

        with open(self._filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, x in enumerate(lines, start=1):
                if '\t' not in x:
                    continue

                splat = x.split('\t')
                if len(splat) == 3 and splat[2].strip() == item:
                    return True, i
        return False, -1


class YAMLParserCIDR(BlacklistParser):
    """
    YAML parser for IP blacklist (name suggests we should move to proper
    CIDR eventually).

    Base class for parsers for YAML files with simple schema validation.
    """
    # Remember to update the schema version if any of this needs to be changed
    SCHEMA_VERSION = '2019120601'  # yyyy mm dd id
    SCHEMA_VARIANT = 'yaml_cidr'
    SCHEMA_PRIKEY = 'ip'

    def __init__(self, filename):
        super().__init__(filename)

    def _parse(self, keep_disabled=False):
        with open(self._filename, 'r', encoding='utf-8') as f:
            y = yaml.safe_load(f)
        if y['Schema'] != self.SCHEMA_VARIANT:
            raise ValueError(
                'Schema variant: got {0}, but expected {1}'.format(
                    y['Schema'], self.SCHEMA_VARIANT))
        if y['Schema_version'] > self.SCHEMA_VERSION:
            raise ValueError(
                'Schema version {0} is bigger than supported {1}'.format(
                    y['Schema_version'], self.SCHEMA_VERSION))
        for item in y['items']:
            if not keep_disabled and item.get('disable'):
                continue
            yield item

    def parse(self):
        return [item[self.SCHEMA_PRIKEY] for item in self._parse()]

    def _write(self, callback):
        d = {
            'Schema': self.SCHEMA_VARIANT,
            'Schema_version': self.SCHEMA_VERSION,
            'items': sorted(
                self._parse(keep_disabled=True),
                key=lambda x: x[self.SCHEMA_PRIKEY])
        }
        callback(d)
        with open(self._filename, 'w', encoding='utf-8') as f:
            yaml.dump(d, f)

    def _validate(self, item):
        ip_regex = regex.compile(r'''
            (?(DEFINE)(?P<octet>
              0|1[0-9]{0,2}|2(?:[0-4][0-9]?)?|25[0-5]?|2[6-9]|[3-9][0-9]?))
            ^(?!0)(?&octet)(?:\.(?&octet)){3}$''', regex.X)

        if 'ip' in item:
            if not ip_regex.match(item['ip']):
                raise ValueError(
                    'Field "ip" is not a valid IP address: {0}'.format(
                        item['ip']))
            '''
            if 'cidr' in item:
                raise ValueError(
                    'Cannot have both "ip" and "cidr" members: {0!r}'.format(
                        item))
        elif 'cidr' in item:
            if not 'base' in item['cidr'] or not 'mask' in item['cidr']:
                raise ValueError(
                    'Field "cidr" must have members "base" and "mask"')
            if not ip_regex.match(item['cidr']['base']):
                raise ValueError(
                    'Field "base" is not a valid IP address: {0}'.format(
                        item['cidr']['base']))
            mask = int(item['cidr']['mask'])
            if mask < 0 or mask > 32:
                raise ValueError(
                    'Field "mask" must be between 0 and 32: {0}'.format(
                        item['cidr']['mask']))
            '''
        else:
            raise ValueError(
                'Item needs to have an "ip" member field: {0!r}'.format(item))

    def validate(self):
        for item in self._parse():
            self._validate(item)

    def add(self, item):
        self._validate(item)
        prikey = self.SCHEMA_PRIKEY

        def add_callback(d):
            for compare in d['items']:
                if compare[prikey] == item[prikey]:
                    raise ValueError('{0} already in list {1}'.format(
                        item[prikey], d['items']))
            d['items'].append(item)

        self._write(add_callback)

    def delete(self, item):
        prikey = self.SCHEMA_PRIKEY

        def delete_callback(d):
            for i, compare in enumerate(d['items']):
                if compare[prikey] == item[prikey]:
                    break
            else:
                raise ValueError('No {0} found in list {1}'.format(
                    item[prikey], d['items']))
            del d['items'][i]

        self._write(delete_callback)

    # FIXME: enumerate gets YAML item array index, not line number
    def each(self, with_info=False):
        for i, item in enumerate(self.parse(), start=1):
            if with_info:
                yield item, (i, self._filename)
            else:
                yield item

    def exists(self, item):
        item = item.lower()
        for rec, i in self.each(with_info=True):
            if item == rec:
                return True, i
        return False, -1


class YAMLParserNS(YAMLParserCIDR):
    """
    YAML parser for name server blacklists.
    """
    SCHEMA_VARIANT = 'yaml_ns'
    SCHEMA_PRIKEY = 'ns'

    def _normalize(self, item):
        """
        Normalize to lower case
        """
        return item.rstrip().lower()

    def _validate(self, item):
        def item_check(ns):
            if not host_regex.match(ns):
                raise ValueError(
                    '{0} does not look like a valid host name'.format(
                        item['ns']))
            if item.get('disable', None):
                return False
            try:
                addr = dns.resolver.query(ns, 'a')
                log('debug', '{0} resolved to {1}'.format(
                    ns, ','.join(x.to_text() for x in addr)))
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                if not item.get('pass', None):
                    soa = dns.resolver.query(ns, 'soa')
                    log('debug', '{0} has no A record; SOA is {1}'.format(
                        ns, ';'.join(s.to_text() for s in soa)))
            except dns.resolver.NoNameservers:
                if not item.get('pass', None):
                    log('warn', '{0} has no available servers to service DNS '
                                'request.'.format(ns))
            except dns.resolver.Timeout:
                log('warn', '{0}: DNS lookup timed out.'.format(ns))
            return True

        host_regex = regex.compile(r'^([a-z0-9][-a-z0-9]*\.){2,}$')
        if 'ns' not in item:
            raise ValueError(
                'Item must have member field "ns": {0!r}'.format(item))
        if isinstance(item['ns'], str):
            return item_check(item['ns'])
        elif isinstance(item['ns'], list):
            accept = True
            for ns in item['ns']:
                if not item_check(ns):
                    accept = False
            return accept
        else:
            raise ValueError(
                'Member "ns" must be either string or list of strings: '
                '{0!r}'.format(item['ns']))


class YAMLParserASN(YAMLParserCIDR):
    """
    YAML parser for ASN blacklists.
    """
    SCHEMA_VARIANT = 'yaml_asn'
    SCHEMA_PRIKEY = 'asn'

    def _validate(self, item):
        if 'asn' not in item:
            raise ValueError(
                'Item must have member field "asn": {0!r}'.format(item))
        asn = int(item['asn'])
        if asn <= 0 or asn >= 4200000000 or \
                64496 <= asn <= 131071 or asn == 23456:
            raise ValueError('Not a valid public AS number: {0}'.format(asn))


class Blacklist(list):
    def __init__(self, filename, cls):
        self._filename = filename
        self._cls = cls
        self._parser = cls(filename)
        super().__init__(self._parser.parse())

    @staticmethod
    def resolve(identifier):
        """
        Map identifier to the corresponding key in GlobalVars.git_black_watch_lists
        """
        mapping = {
            'keyword': 'keywords',
            'number': 'numbers',
            'phone': 'numbers',
            'asn': 'asns',
            'ip': 'cidrs',
            'ns': 'nses',
        }
        if 'watch' in identifier:
            prefix = 'watched'
        elif 'keyword' in identifier:
            prefix = 'bad'
        else:
            prefix = 'blacklisted'
        for term, suffix in mapping.items():
            if term in identifier:
                return '%s_%s' % (prefix, suffix)
        raise KeyError('Blacklists.resolve(): Could not resolve %s' % identifier)

    def parse(self):
        return self._parser.parse()

    def add(self, item):
        return self._parser.add(item)

    def delete(self, item):
        return self._parser.delete(item)

    def each(self, with_info=False):
        return self._parser.each(with_info=with_info)

    def exists(self, item):
        return self._parser.exists(item)

    def validate(self):
        return self._parser.validate()

    #

    def parserclass(self):
        return self._cls

    def filename(self):
        return self._filename

    def already_caught(self, string_to_test):
        """
        Test a candidate string; return a list of reasons if it is already
        caught.

        The method not_reject_reasons returns a list of reasons which do not
        cause a rejection to be returned; in other words, they are removed
        from the reasons.
        """
        ownerdict = {'display_name': 'Valid username',
                     'reputation': 1, 'link': ''}
        querydict = {'title': 'Valid title', 'body': 'Valid body',
                     'owner': None, 'site': "", 'IsAnswer': None, 'score': 0}
        reasons = set()
        for answerp in False, True:
            for userp in False, True:
                owner = ownerdict.copy()
                question = querydict.copy()
                if userp:
                    owner['display_name'] = string_to_test
                else:
                    question['body'] = string_to_test
                question['owner'] = owner
                question['IsAnswer'] = answerp
                verdicts, _ = findspam.FindSpam.test_post(question)
                reasons.update(set(verdicts))

        filter_out = self.not_reject_reasons()
        return [reason for reason in reasons
                if all([x not in reason.lower() for x in filter_out])]

    def not_reject_reasons(self):
        """
        Which reasons should be filtered out when deciding whether something
        is not acceptable to add to a blacklist?

        Called by the already_caught method; provides hooks for the
        WatchMixin and PhoneMixin classes.
        """
        filter_out = [
            "potentially bad ns",
            "potentially bad asn",
            "potentially problematic",
            "potentially bad ip"]
        filter_out.append(self._watch_not_reject_reasons())
        filter_out.append(self._phone_not_reject_reasons())
        return filter_out

    def _watch_not_reject_reasons(self):
        """
        Return extended reasons to reject a blacklist addition for watch
        lists.

        No-op in the base class; populated in WatchMixin.
        """
        return []

    def _phone_not_reject_reasons(self):
        """
        Return additional reasons to reject a blacklist addition for phone
        lists.

        No-op in the base class; populated in PhoneMixin.
        """
        return []

    def regextype(self):
        """
        Whether to perform regex validation etc on candidate patterns.

        True in the base class; overridden by NetMixin and PhoneMixin.
        """
        return True

    def numbertype(self):
        """
        Whether to perform phone number normalizations.

        False in the base class; overridden by PhoneMixin.
        """
        return False

    def watchtype(self):
        """
        Whether this is a watchlist instead of a blacklist.

        False in the base class; overridden by WatchMixin.
        """
        return False

    def _ms_search_url_tail(self):
        """
        Class-specific URL tail for ms_search_url() method.
        """
        return "body_is_regex=1&body="

    def ms_search_url(self):
        """
        Return URL to use for Metasmoke search.

        Subclasses will want to override the _ms_search_url_tail method.
        """
        return 'https://metasmoke.erwaysoftware.com/search?utf8=%E2%9C%93{0}'.format(
            self._ms_search_url_tail())


class WatchMixin:
    """
    Mixin to create watch behavior from a base class
    """
    def _watch_not_reject_reasons(self):
        return ["potentially bad keyword"]

    def watchtype(self):
        return True


class UserMixin:
    """
    Mixin to create username class behavior from a base class
    """
    def _ms_search_url_tail(self):
        return "username_is_regex=1&username="


class NetMixin:
    """
    Mixin for net resources (hostname labels, IP addresses, etc)
    """
    def regextype(self):
        return False


class PhoneMixin(NetMixin):
    """
    Mixin to create phone number class behavior from a base class
    """
    def additional_filtered_out_reasons(self):
        return ["mostly non-latin", "phone number detected",
                "messaging number detected"]

    def numbertype(self):
        return True

    def _ms_search_url_tail(self):
        return "body="


class Watchlist(WatchMixin, Blacklist):
    pass


class UserBlacklist(UserMixin, Blacklist):
    pass


class UserWatchlist(UserMixin, WatchMixin, Blacklist):
    pass


class NetBlacklist(NetMixin, Blacklist):
    pass


class NetWatchlist(NetMixin, WatchMixin, Blacklist):
    pass


class PhoneBlacklist(PhoneMixin, Blacklist):
    pass


class PhoneWatchlist(PhoneMixin, WatchMixin, Blacklist):
    pass


'''
if __name__ == '__main__':
    load_blacklists()
    blacklist_id = Blacklist.resolve('watch-ip')
    print(blacklist_id)
    blacklister = GlobalVars.git_black_watch_lists[blacklist_id]
    exists, line = blacklister.exists('103.10.200.62')
    print(exists, line)
    print('****')
# """
    for name, bwlist in GlobalVars.git_black_watch_lists.items():
        print('{0} type: {1}'.format(name, type(bwlist)))
        for method in ('regextype', 'numbertype', 'watchtype', 'not_reject_reasons'):
            print('{0}.{1}() = {2}'.format(bwlist.filename(), method, getattr(bwlist, method)()))
        for item in bwlist.each():
            print('each[0]: %r' % item)
            break
'''
