# coding=utf-8
from typing import Union

import regex
import yaml
import dns.resolver

from globalvars import GlobalVars
from helpers import log


def load_blacklists():
    GlobalVars.bad_keywords = Blacklist(Blacklist.KEYWORDS).parse()
    GlobalVars.watched_keywords = Blacklist(Blacklist.WATCHED_KEYWORDS).parse()
    GlobalVars.blacklisted_websites = Blacklist(Blacklist.WEBSITES).parse()
    GlobalVars.blacklisted_usernames = Blacklist(Blacklist.USERNAMES).parse()
    GlobalVars.blacklisted_numbers = Blacklist(Blacklist.NUMBERS).parse()
    GlobalVars.watched_numbers = Blacklist(Blacklist.WATCHED_NUMBERS).parse()
    GlobalVars.blacklisted_nses = Blacklist(Blacklist.NSES).parse()
    GlobalVars.watched_nses = Blacklist(Blacklist.WATCHED_NSES).parse()
    GlobalVars.blacklisted_cidrs = Blacklist(Blacklist.CIDRS).parse()
    GlobalVars.watched_cidrs = Blacklist(Blacklist.WATCHED_CIDRS).parse()
    # GlobalVars.blacklisted_asns = Blacklist(Blacklist.ASNS).parse()
    GlobalVars.watched_asns = Blacklist(Blacklist.WATCHED_ASNS).parse()


class BlacklistParser:
    def __init__(self, filename):
        self._filename = filename

    def parse(self):
        return None

    def add(self, item):
        pass

    def remove(self, item):
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

    def remove(self, item: str):
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


class TSVDictParser(BlacklistParser):
    """
    Parser for 3-column TSV file with "when" (Unix timestamp), "who", and
    "what" fields.
    """
    def parse(self):
        dct = {}
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
                    dct[what] = {'when': when, 'by': by_whom}

        return dct

    def add(self, item: Union[str, dict]):
        with open(self._filename, 'a+', encoding='utf-8') as f:
            if isinstance(item, dict):
                item = '{}\t{}\t{}'.format(item[0], item[1], item[2])
            last_char = f.read()[-1:]
            if last_char not in ['', '\n']:
                item = '\n' + item
            f.write(item + '\n')

    def remove(self, item: Union[str, dict]):
        if isinstance(item, dict):
            item = item[2]

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

    def exists(self, item: Union[str, dict]):
        if isinstance(item, dict):
            item = item[2]
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

    def remove(self, item):
        prikey = self.SCHEMA_PRIKEY

        def remove_callback(d):
            for i, compare in enumerate(d['items']):
                if compare[prikey] == item[prikey]:
                    break
            else:
                raise ValueError('No {0} found in list {1}'.format(
                    item[prikey], d['items']))
            del d['items'][i]

        self._write(remove_callback)

    # FIXME: enumerate gets YAML item array index, not line number
    def each(self, with_info=False):
        for i, item in enumerate(self.parse(), start=1):
            if with_info:
                yield item, (i, self._filename)
            else:
                yield item

    def exists(self, item):
        item = item.lower()
        for i, rec in self.each(with_info=True):
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


class Blacklist:
    KEYWORDS = ('bad_keywords.txt', BasicListParser)
    WEBSITES = ('blacklisted_websites.txt', BasicListParser)
    USERNAMES = ('blacklisted_usernames.txt', BasicListParser)
    NUMBERS = ('blacklisted_numbers.txt', BasicListParser)
    WATCHED_KEYWORDS = ('watched_keywords.txt', TSVDictParser)
    WATCHED_NUMBERS = ('watched_numbers.txt', TSVDictParser)
    NSES = ('blacklisted_nses.yml', YAMLParserNS)
    WATCHED_NSES = ('watched_nses.yml', YAMLParserNS)
    CIDRS = ('blacklisted_cidrs.yml', YAMLParserCIDR)
    WATCHED_CIDRS = ('watched_cidrs.yml', YAMLParserCIDR)
    # ASNS = ('blacklisted_asns.yml', YAMLParserASN)
    WATCHED_ASNS = ('watched_asns.yml', YAMLParserASN)

    def __init__(self, type):
        self._filename = type[0]
        self._parser = type[1](self._filename)

    def parse(self):
        return self._parser.parse()

    def add(self, item):
        return self._parser.add(item)

    def remove(self, item):
        return self._parser.remove(item)

    def each(self, with_info=False):
        return self._parser.each(with_info=with_info)

    def exists(self, item):
        return self._parser.exists(item)

    def validate(self):
        return self._parser.validate()
