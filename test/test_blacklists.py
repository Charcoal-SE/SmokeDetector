#!/usr/bin/env python3
# coding=utf-8

import yaml
from os import unlink
import regex
from globalvars import GlobalVars

import pytest

from blacklists import Blacklist, YAMLParserCIDR, YAMLParserASN, YAMLParserNS, load_blacklists
from helpers import files_changed, blacklist_integrity_check, not_regex_search_ascii_and_unicode, process_numlist
from findspam import NUMBER_REGEX, NUMBER_REGEX_START, NUMBER_REGEX_END, NUMBER_REGEX_MINIMUM_DIGITS, NUMBER_REGEX_MAXIMUM_DIGITS


def test_number_lists():
    errors = {}
    no_exacts = []
    all_errors = []

    def clear_errors():
        errors['too_many_processed_results'] = []
        errors['fails_number_regex'] = []
        errors['no_unique'] = []
        errors['blacklist_dup_with_no_unique'] = []
        errors['blacklist_dup_with_unique'] = []

    def get_sorted_current_errors_and_clear_errors():
        current_errors = [error for sub in [errors[error_group] for error_group in errors] for error in sub]
        clear_errors()
        return current_errors

    def test_a_number_list(list_type, number_list, blacklist_normalized=None):
        line_number = 0
        all_processed = set()
        all_normalized = set()
        lines_no_unique = []
        lines_duplicate_blacklist_with_no_unique = []
        lines_duplicate_blacklist_with_unique = []
        for pattern in number_list:
            line_number += 1
            entry_description = "{} number ({})::{}:: ".format(list_type, line_number, pattern)
            this_processed_set, all_normalized, unique_normalized, duplicate_normalized = process_numlist([pattern], normalized=all_normalized)
            if len(this_processed_set) != 1:
                errors['too_many_processed_results'].append(entry_description + "too many processed results ({} != 1)".format(len(this_processed_set)))
            processed_pattern = this_processed_set.pop()
            digit_count = len(regex.findall(r'\d', processed_pattern))
            digit_count_text = " ({} digits is OK)".format(digit_count)
            if digit_count < NUMBER_REGEX_MINIMUM_DIGITS or digit_count > NUMBER_REGEX_MAXIMUM_DIGITS:
                digit_count_text = ": {} digits is not >= {} and <= {}".format(digit_count, NUMBER_REGEX_MINIMUM_DIGITS, NUMBER_REGEX_MAXIMUM_DIGITS)
            if not_regex_search_ascii_and_unicode(NUMBER_REGEX, processed_pattern):
                errors['fails_number_regex'].append(entry_description + "fails NUMBER_REGEX{}::{}".format(digit_count_text, processed_pattern))
            else:
                this_no_exacts = []
                if not_regex_search_ascii_and_unicode(NUMBER_REGEX_START, processed_pattern):
                    this_no_exacts.append("Does not match NUMBER_REGEX_START.")
                if not_regex_search_ascii_and_unicode(NUMBER_REGEX_END, processed_pattern):
                    this_no_exacts.append("Does not match NUMBER_REGEX_END.")
                if len(this_no_exacts) > 0:
                    no_exacts.append(entry_description + " ".join(this_no_exacts) + digit_count_text + "::" + pattern)
            if not unique_normalized:
                errors['no_unique'].append(entry_description + "has no unique normalized entries. Duplicate normalized entries: {}".format(duplicate_normalized))
                lines_no_unique.append(str(line_number))
            if blacklist_normalized:
                this_normalized = unique_normalized | duplicate_normalized
                this_normalized_in_blacklist = this_normalized & blacklist_normalized
                this_normalized_not_in_blacklist = this_normalized - blacklist_normalized
                if this_normalized_in_blacklist:
                    not_in_blacklist_text = ":: normalized not in blacklist: {}".format(this_normalized_not_in_blacklist)
                    error_text = entry_description + "has duplicate normalized entries on the blacklist: {}".format(this_normalized_in_blacklist) + not_in_blacklist_text
                    if this_normalized_not_in_blacklist:
                        lines_duplicate_blacklist_with_unique.append(str(line_number))
                        errors['blacklist_dup_with_unique'].append(error_text)
                    else:
                        lines_duplicate_blacklist_with_no_unique.append(str(line_number))
                        errors['blacklist_dup_with_no_unique'].append(error_text)
        lines_no_unique.reverse()
        deletion_list = []
        for error_group in errors:
            if errors[error_group]:
                has_errors = True
                # The following produces a sequence of commands which can be used in vi/vim to delete the entries in the appropriate file which have errors.
                # It's intended use is in the transition from not checking normalizations to applying homoglyphs and checking normalizations.
                line_list = [error.split('(')[1].split(')')[0] for error in errors[error_group]]
                line_list.reverse()
                deletion_list.append('{}: to remove {}: {}'.format(list_type, error_group, 'Gdd'.join(line_list) + 'Gdd'))
        if (deletion_list):
            print('\n')
            print('USE ONLY ONE OF THE FOLLOWING PER RUN OF THESE TESTS. Using more than one will result in the wrong lines being deleted:')
            print('\n'.join(deletion_list))
            print('\n\n')
        return all_processed, all_normalized

    clear_errors()
    load_blacklists()
    blacklist_processed, blacklist_normalized = test_a_number_list("blacklisted", GlobalVars.blacklisted_numbers)
    all_errors.extend(get_sorted_current_errors_and_clear_errors())
    test_a_number_list("watched", GlobalVars.watched_numbers, blacklist_normalized=blacklist_normalized)
    all_errors.extend(get_sorted_current_errors_and_clear_errors())
    no_exacts_count = len(no_exacts)
    if (no_exacts_count > 0):
        pluralize = "" if no_exacts_count == 1 else "s"
        print("\n\t".join(["{} pattern{} can't match exactly:".format(no_exacts_count, pluralize)] + no_exacts))
    error_count = len(all_errors)
    if error_count > 0:
        pluralize = "" if error_count == 1 else "s"
        pytest.fail("\n\t".join(["{} error{} have occurred:".format(error_count, pluralize)] + all_errors))


def test_blacklist_integrity():
    errors = blacklist_integrity_check()

    if len(errors) == 1:
        pytest.fail(errors[0])
    elif len(errors) > 1:
        pytest.fail("\n\t".join(["{} errors have occurred:".format(len(errors))] + errors))


def test_remote_diff():
    file_set = set("abcdefg")
    true_diff = "a c k p"
    false_diff = "h j q t"
    assert files_changed(true_diff, file_set)
    assert not files_changed(false_diff, file_set)


def yaml_validate_existing(filename, cls):
    return Blacklist((filename, cls)).validate()


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
    blacklist = Blacklist(('test_ip.yml', YAMLParserCIDR))
    with pytest.raises(ValueError) as e:
        blacklist.add('1.3.34')
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '1.3.4'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '1.2.3.4'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '2.3.4.5'})
    with pytest.raises(ValueError) as e:
        blacklist.remove({'ip': '34.45.56.67'})
    blacklist.add({'ip': '1.3.4.5'})
    assert '1.2.3.4' in blacklist.parse()
    assert '2.3.4.5' not in blacklist.parse()
    assert '3.4.5.6' in blacklist.parse()
    blacklist.remove({'ip': '3.4.5.6'})
    assert '3.4.5.6' not in blacklist.parse()
    unlink('test_ip.yml')

    yaml_validate_existing('blacklisted_cidrs.yml', YAMLParserCIDR)
    yaml_validate_existing('watched_cidrs.yml', YAMLParserCIDR)


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
    blacklist = Blacklist(('test_asn.yml', YAMLParserASN))
    with pytest.raises(ValueError) as e:
        blacklist.add('123')
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': 'invalid'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': '123'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': '234'})
    with pytest.raises(ValueError) as e:
        blacklist.remove({'asn': '9897'})
    assert '123' in blacklist.parse()
    assert '234' not in blacklist.parse()
    assert '345' in blacklist.parse()
    blacklist.remove({'asn': '345'})
    assert '345' not in blacklist.parse()
    unlink('test_asn.yml')

    yaml_validate_existing('watched_asns.yml', YAMLParserASN)


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
    blacklist = Blacklist(('test_nses.yml', YAMLParserNS))
    assert 'example.com.' in blacklist.parse()
    assert 'EXAMPLE.COM.' not in blacklist.parse()
    with pytest.raises(ValueError) as e:
        blacklist.add({'ns': 'example.com.'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ns': 'EXAMPLE.COM.'})
    assert 'example.net.' not in blacklist.parse()
    assert 'example.org.' in blacklist.parse()
    blacklist.remove({'ns': 'example.org.'})
    assert 'example.org.' not in blacklist.parse()
    unlink('test_nses.yml')

    yaml_validate_existing('blacklisted_nses.yml', YAMLParserNS)
    yaml_validate_existing('watched_nses.yml', YAMLParserNS)
