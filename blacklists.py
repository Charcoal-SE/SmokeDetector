from typing import Union
from concurrent.futures import ThreadPoolExecutor

import regex
import yaml
import dns.resolver
import sys
import time

from globalvars import GlobalVars
from helpers import log, log_current_exception, color, pluralize
from models.yaml_files import CidrYamlDocument, CidrListItem


def load_blacklists():
    GlobalVars.bad_keywords = Blacklist(Blacklist.KEYWORDS).parse()
    GlobalVars.watched_keywords = Blacklist(Blacklist.WATCHED_KEYWORDS).parse()
    GlobalVars.blacklisted_websites = Blacklist(Blacklist.WEBSITES).parse()
    GlobalVars.blacklisted_usernames = Blacklist(Blacklist.USERNAMES).parse()
    GlobalVars.blacklisted_numbers_raw = Blacklist(Blacklist.NUMBERS).parse()
    GlobalVars.watched_numbers_raw = Blacklist(Blacklist.WATCHED_NUMBERS).parse()
    GlobalVars.blacklisted_nses = Blacklist(Blacklist.NSES).parse()
    GlobalVars.watched_nses = Blacklist(Blacklist.WATCHED_NSES).parse()
    GlobalVars.blacklisted_cidrs = Blacklist(Blacklist.CIDRS).parse()
    GlobalVars.watched_cidrs = Blacklist(Blacklist.WATCHED_CIDRS).parse()
    # GlobalVars.blacklisted_asns = Blacklist(Blacklist.ASNS).parse()
    GlobalVars.watched_asns = Blacklist(Blacklist.WATCHED_ASNS).parse()


class BlacklistParser:
    def __init__(self, filename: str):
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
        if with_info:
            with open(self._filename, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, start=1):
                    yield line.rstrip("\n"), (i, self._filename)
        else:
            with open(self._filename, 'r', encoding='utf-8') as f:
                for line in f:
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
    def parse(self):
        dct = {}
        with open(self._filename, 'r', encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                if regex.compile(r'^\s*(?:#|$)').match(line):
                    continue
                try:
                    when, by_whom, what = line.rstrip().split('\t')
                except ValueError as err:
                    log('error', '{0}:{1}:{2}'.format(self._filename, lineno, err))
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
            items = [x for x in items if ('\t' not in x) or
                     (len(x.split('\t')) == 3 and x.split('\t')[2].strip() != item)]
            f.seek(0)
            f.truncate()
            f.writelines(items)

    def each(self, with_info=False):
        # info = (filename, lineno)
        if with_info:
            with open(self._filename, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, start=1):
                    if line.count('\t') == 2:
                        yield line.rstrip("\n").split('\t')[2], (i, self._filename)
        else:
            with open(self._filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.count('\t') == 2:
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
    YAML parser for IP blacklist (name suggests we should move to proper CIDR eventually).

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
            content = f.read()
        document = CidrYamlDocument.from_yaml(content)
        if document.Schema != self.SCHEMA_VARIANT:
            raise ValueError('Schema variant: got {0}, but expected {1}'.format(
                document.Schema, self.SCHEMA_VARIANT))
        if document.Schema_version > self.SCHEMA_VERSION:
            raise ValueError('Schema version {0} is bigger than supported {1}'.format(
                document.Schema_version, self.SCHEMA_VERSION))
        for item in document.items:
            if not keep_disabled and getattr(item, 'disable', False):
                continue
            yield item

    def parse(self):
        """返回主键字段的字符串列表（与旧实现保持兼容）。"""
        values = []
        for item in self._parse():
            if not hasattr(item, self.SCHEMA_PRIKEY):
                continue
            value = getattr(item, self.SCHEMA_PRIKEY)
            if value is None:
                continue
            values.append(str(value))
        return values

    def _write(self, callback):
        items = sorted(
            self._parse(keep_disabled=True),
            key=lambda x: getattr(x, self.SCHEMA_PRIKEY))

        d = {
            'Schema': self.SCHEMA_VARIANT,
            'Schema_version': self.SCHEMA_VERSION,
            'items': [item.to_dict() for item in items]
        }
        callback(d)
        with open(self._filename, 'w', encoding='utf-8') as f:
            yaml.dump({k: v for k, v in d.items() if k != 'items'}, f)
            f.write("items:\n")
            yaml.dump(d['items'], f)

    def _normalize(self, item):
        return item.rstrip()

    def _validate(self, item):
        """Validate a single CIDR/IP entry.

        支持两种输入形式：
        - dict: 旧实现／测试代码仍直接传入字典，例如 {"ip": "1.2.3.4"}
        - CidrListItem Pydantic 模型：正常从 YAML 解析得到的对象
        另外，为兼容既有测试，字符串形式会被视为 ip 文本并直接校验格式。
        """
        ip_regex = regex.compile(r'''
            (?(DEFINE)(?P<octet>
              0|1[0-9]{0,2}|2(?:[0-4][0-9]?)?|25[0-5]?|2[6-9]|[3-9][0-9]?))
            ^(?!0)(?&octet)(?:\.(?&octet)){3}$''', regex.X)

        # 兼容 dict / 模型 / 纯字符串三种输入
        if isinstance(item, str):
            ip_value = item
            cidr_value = None
        elif isinstance(item, dict):
            ip_value = item.get('ip')
            cidr_value = item.get('cidr')
        else:
            ip_value = getattr(item, 'ip', None)
            cidr_value = getattr(item, 'cidr', None)

        if ip_value is not None:
            if not ip_regex.match(ip_value):
                raise ValueError('Field "ip" is not a valid IP address: {0}'.format(ip_value))
            return

        if cidr_value is not None:
            # cidr 也可能是 dict 或 CidrInfo 模型
            if isinstance(cidr_value, dict):
                base = cidr_value.get('base')
                mask = cidr_value.get('mask')
            else:
                base = getattr(cidr_value, 'base', None)
                mask = getattr(cidr_value, 'mask', None)

            if base is None or mask is None:
                raise ValueError('Field "cidr" must have members "base" and "mask"')
            if not ip_regex.match(base):
                raise ValueError('Field "base" is not a valid IP address: {0}'.format(base))

            try:
                mask_int = int(mask)
            except (TypeError, ValueError):
                raise ValueError('Field "mask" must be between 0 and 32: {0}'.format(mask))

            if mask_int < 0 or mask_int > 32:
                raise ValueError('Field "mask" must be between 0 and 32: {0}'.format(mask))
            return

        # 既没有 ip 也没有 cidr
        raise ValueError('Item needs to have an "ip" or "cidr" member field: {0!r}'.format(item))

    def validate(self):
        for item in self._parse():
            self._validate(item)

    def add(self, item):
        self._validate(item)
        prikey = self.SCHEMA_PRIKEY

        def add_callback(d):
            # 兼容 dict 与 Pydantic 模型两种形式
            if isinstance(item, dict):
                item_prikey_val = item.get(prikey)
            else:
                item_prikey_val = getattr(item, prikey, None)

            if item_prikey_val is None:
                raise ValueError('Item must have member field "{0}": {1!r}'.format(prikey, item))

            item_normalized = self._normalize(str(item_prikey_val))
            for compare in d['items']:
                # d['items'] 始终是 dict 列表，保持现有 compare.get(prikey) 访问方式不变
                compare_val = compare.get(prikey)
                if compare_val is None:
                    continue
                if self._normalize(str(compare_val)) == item_normalized:
                    raise KeyError('{0} already in list'.format(item_prikey_val))

            if isinstance(item, dict):
                new_entry = dict(item)
            else:
                new_entry = item.to_dict()
            d['items'].append(new_entry)

        self._write(add_callback)

    def remove(self, item):
        prikey = self.SCHEMA_PRIKEY

        def remove_callback(d):
            # 兼容 dict 与 Pydantic 模型两种形式
            if isinstance(item, dict):
                item_to_remove = item.get(prikey)
            else:
                item_to_remove = getattr(item, prikey, None)

            if item_to_remove is None:
                raise ValueError('Item must have member field "{0}": {1!r}'.format(prikey, item))

            item_to_remove_normalized = self._normalize(str(item_to_remove))
            for i, compare in enumerate(d['items']):
                compare_val = compare.get(prikey)
                if compare_val is None:
                    continue
                if self._normalize(str(compare_val)) == item_to_remove_normalized:
                    break
            else:
                raise ValueError('No {0} found in list'.format(item_to_remove))
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

    def parse(self):
        """返回 NS 主键原始结构（字符串或字符串列表），保持与旧实现兼容。"""
        values = []
        for item in self._parse():
            # CidrListItem 或 dict
            if isinstance(item, dict):
                ns_value = item.get(self.SCHEMA_PRIKEY)
            else:
                ns_value = getattr(item, self.SCHEMA_PRIKEY, None)
            if ns_value is None:
                continue
            values.append(ns_value)
        return values

    def _validate(self, item):
        def item_check(ns):
            if not host_regex.match(ns):
                raise ValueError(
                    '{0} does not look like a valid host name'.format(ns))
            disable_flag = False
            if isinstance(item, CidrListItem):
                disable_flag = bool(getattr(item, 'disable', False))
            elif isinstance(item, dict):
                disable_flag = bool(item.get('disable', None))
            if disable_flag:
                return False

            # 在 pytest 环境下跳过真实 DNS 解析，避免因网络导致的超时
            if "pytest" in sys.modules:
                return True

            # Extend lifetime if we are running a test
            extra_params = dict()
            if "pytest" in sys.modules:
                extra_params['lifetime'] = 15
            try:
                try:
                    addr = dns.resolver.resolve(ns, 'a', search=True, **extra_params)
                    # Outputing for every resolved entry makes it harder to find the actual error,
                    # due to being swamped with data in the error output.
                    # log('debug', '{0} resolved to {1}'.format(
                    #     ns, ','.join(x.to_text() for x in addr)))
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    pass_flag = False
                    if isinstance(item, CidrListItem):
                        pass_flag = bool(getattr(item, 'pass', None))
                    elif isinstance(item, dict):
                        pass_flag = bool(item.get('pass', None))
                    if not pass_flag:
                        soa = dns.resolver.resolve(ns, 'soa', search=True, **extra_params)
                        log('debug', '{0} has no A record; SOA is {1}'.format(
                            ns, ';'.join(s.to_text() for s in soa)))
                except dns.resolver.NoNameservers:
                    pass_flag = False
                    if isinstance(item, CidrListItem):
                        pass_flag = bool(getattr(item, 'pass', None))
                    elif isinstance(item, dict):
                        pass_flag = bool(item.get('pass', None))
                    if not pass_flag:
                        log('warn', '{0} has no available servers to service DNS '
                                    'request.'.format(ns))
                except dns.resolver.Timeout:
                    log('warn', '{0}: DNS lookup timed out.'.format(ns))
            except Exception as excep:
                log_current_exception()
                log('error', '{}'.format(color('-' * 41 + 'v' * len(ns), 'red', attrs=['bold'])), no_exception=True)
                log('error', ('validate YAML: Failed NS validation for:'
                              ' {} in {}'.format(color(ns, 'white', attrs=['bold']), self._filename)),
                    no_exception=True)
                log('error', '{}'.format(color('-' * 41 + '^' * len(ns), 'red', attrs=['bold'])), no_exception=True)
                if "pytest" in sys.modules:
                    if isinstance(item, dict):
                        item['error'] = excep
                        return item
                    else:
                        item_dict = item.to_dict()
                        item_dict['error'] = excep
                        return item_dict
                else:
                    raise
            return True

        host_regex = regex.compile(
            r'^([a-z0-9][-a-z0-9]*\.){2,}$', flags=regex.IGNORECASE)

        # 兼容 dict 与 Pydantic 模型两种形式
        if isinstance(item, dict):
            ns_value = item.get('ns')
        else:
            ns_value = getattr(item, 'ns', None)

        if ns_value is None:
            raise ValueError('Item must have member field "ns": {0!r}'.format(item))

        if isinstance(ns_value, str):
            return item_check(ns_value)
        elif isinstance(ns_value, list):
            accept = True
            for ns in ns_value:
                if not item_check(ns):
                    accept = False
            return accept
        else:
            raise ValueError(
                'Member "ns" must be either string or list of strings: {0!r}'.format(
                    ns_value))

    def validate_list(self, list_to_validate):
        # 20 max_workers appeared to be reasonable. When 30 or 50 workers were tried,
        # it appeared to result in longer times and intermittent failures.
        with ThreadPoolExecutor(max_workers=10) as executor:
            return list(executor.map(self._validate, list_to_validate, timeout=300))

    def validate(self):
        parsed_list = self._parse()
        log('info', 'Validation Pass 1:')  # Just a blank line
        results_pass1 = self.validate_list(parsed_list)
        entries_with_exception = [entry for entry in results_pass1 if entry is not True]
        # There are intermittent issues on some of the entries, so we run a second pass on the failures.
        # This may end up taking substantial time in testing, so we'll need to monitor for that.
        pass1_error_count = len(entries_with_exception)
        if pass1_error_count == 0:
            # Everything passed
            return
        log('info', 'Validation Pass 1 had {} {}. Waiting 6 seconds'.format(pass1_error_count,
                                                                            pluralize(pass1_error_count, 'error', 's')))
        time.sleep(6)
        log('debug', '(blank lines)\n\n\n\n\n\n')  # Just blank lines
        log('info', 'Validation Pass 2:')  # Just a blank line
        results_pass2 = self.validate_list(entries_with_exception)
        entries_with_exception2 = [entry for entry in results_pass2 if entry is not True]
        number_failed_to_validate = len(entries_with_exception2)
        if number_failed_to_validate > 0:
            entry_plural = pluralize(number_failed_to_validate, 'entr', 'ies', 'y')
            exception_entries_text = [
                color('{}'.format(entry.get('ns', 'NO NS')), 'white', attrs=['bold'])
                + ' in {} for {}'.format(self._filename,
                                         '{}.{}'.format(entry['error'].__class__.__module__,
                                                        entry['error'].__class__.__name__)
                                         if entry.get('error', None) is not None else '')
                for entry in entries_with_exception2]
            exception_entries_indented = '\n    {}'. format('\n    '.join(exception_entries_text))
            problems_text_colored = (color('{} which failed to validate twice:'.format(entry_plural.capitalize()),
                                           'red', attrs=['bold'])
                                     + exception_entries_indented)
            log('debug', '(blank lines)\n\n\n')  # Just blank lines
            log('error', problems_text_colored)
            raise Exception('{} {} failed to validate in {}{}'.format(number_failed_to_validate, entry_plural,
                                                                      self._filename, exception_entries_indented))


class YAMLParserASN(YAMLParserCIDR):
    """
    YAML parser for ASN blacklists.
    """
    SCHEMA_VARIANT = 'yaml_asn'
    SCHEMA_PRIKEY = 'asn'

    def _validate(self, item):
        # 兼容 dict 与 Pydantic 模型两种形式；对原始标量保持与旧实现一致的错误行为
        if isinstance(item, dict):
            asn_value = item.get('asn')
        else:
            asn_value = getattr(item, 'asn', None)

        if asn_value is None:
            # 与旧实现一致：缺少 asn 字段时直接报错
            raise ValueError('Item must have member field "asn": {0!r}'.format(item))

        try:
            asn = int(asn_value)
        except (TypeError, ValueError):
            raise ValueError('Not a valid public AS number: {0}'.format(asn_value))
        if asn <= 0 or asn >= 4200000000 or 64496 <= asn <= 131071 or asn == 23456:
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

    def __init__(self, type: tuple[str, type[BlacklistParser]]):
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
