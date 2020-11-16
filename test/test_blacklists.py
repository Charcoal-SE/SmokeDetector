#!/usr/bin/env python3
# coding=utf-8

import yaml
from os import unlink

import pytest

from blacklists import *
from helpers import files_changed, blacklist_integrity_check


def test_blacklist_integrity():
    errors = blacklist_integrity_check()

    if len(errors) == 1:
        pytest.fail(errors[0])
    elif len(errors) > 1:
        pytest.fail("\n\t".join(["{} errors has occurred:".format(len(errors))] + errors))


def test_remote_diff():
    file_set = set("abcdefg")
    true_diff = "a c k p"
    false_diff = "h j q t"
    assert files_changed(true_diff, file_set)
    assert not files_changed(false_diff, file_set)


def yaml_validate_existing(cls, filename, parser):
    return cls(filename, parser).validate()


def test_yaml_blacklist():
    with open('test_ip.yml', 'w') as y:
        yaml.dump({
            'Schema': 'yaml_cidr',
            'Schema_version': '2019120601',
            'items': [
                {'ip': '1.2.3.4'},
                {'ip': '2.3.4.5', 'disable': True},
                {'ip': '3.4.5.6', 'comment': 'comment'},
            ]}, y)
    blacklist = NetWatchlist('test_ip.yml', YAMLParserCIDR)
    with pytest.raises(ValueError) as e:
        blacklist.add('1.3.34')
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '1.3.4'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '1.2.3.4'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '2.3.4.5'})
    with pytest.raises(ValueError) as e:
        blacklist.delete({'ip': '34.45.56.67'})
    blacklist.add({'ip': '1.3.4.5'})
    assert '1.2.3.4' in blacklist.parse()
    assert '2.3.4.5' not in blacklist.parse()
    assert '3.4.5.6' in blacklist.parse()
    blacklist.delete({'ip': '3.4.5.6'})
    assert '3.4.5.6' not in blacklist.parse()
    unlink('test_ip.yml')

    yaml_validate_existing(NetBlacklist, 'blacklisted_cidrs.yml', YAMLParserCIDR)
    yaml_validate_existing(NetWatchlist, 'watched_cidrs.yml', YAMLParserCIDR)


def test_yaml_asn():
    with open('test_asn.yml', 'w') as y:
        yaml.dump({
            'Schema': 'yaml_asn',
            'Schema_version': '2019120601',
            'items': [
                {'asn': '123'},
                {'asn': '234', 'disable': True},
                {'asn': '345', 'comment': 'comment'},
            ]}, y)
    blacklist = NetBlacklist('test_asn.yml', YAMLParserASN)
    with pytest.raises(ValueError) as e:
        blacklist.add('123')
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': 'invalid'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': '123'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': '234'})
    with pytest.raises(ValueError) as e:
        blacklist.delete({'asn': '9897'})
    assert '123' in blacklist.parse()
    assert '234' not in blacklist.parse()
    assert '345' in blacklist.parse()
    blacklist.delete({'asn': '345'})
    assert '345' not in blacklist.parse()
    unlink('test_asn.yml')

    yaml_validate_existing(NetWatchlist, 'watched_asns.yml', YAMLParserASN)


def test_yaml_nses():
    with open('test_nses.yml', 'w') as y:
        yaml.dump({
            'Schema': 'yaml_ns',
            'Schema_version': '2019120601',
            'items': [
                {'ns': 'example.com.'},
                {'ns': 'example.net.', 'disable': True},
                {'ns': 'example.org.', 'comment': 'comment'},
            ]}, y)
    blacklist = NetBlacklist('test_nses.yml', YAMLParserNS)
    assert 'example.com.' in blacklist.parse()
    assert 'EXAMPLE.COM.' not in blacklist.parse()
    with pytest.raises(ValueError) as e:
        blacklist.add({'ns': 'example.com.'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ns': 'EXAMPLE.COM.'})
    assert 'example.net.' not in blacklist.parse()
    assert 'example.org.' in blacklist.parse()
    blacklist.delete({'ns': 'example.org.'})
    assert 'example.org.' not in blacklist.parse()
    unlink('test_nses.yml')

    yaml_validate_existing(NetBlacklist, 'blacklisted_nses.yml', YAMLParserNS)
    yaml_validate_existing(NetWatchlist, 'watched_nses.yml', YAMLParserNS)
