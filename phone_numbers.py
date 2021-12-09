# coding=utf-8
import regex
import number_homoglyphs
from helpers import get_only_digits, remove_end_regex_comment

# The NUMBER_REGEXes are used to obtain strings within a post which are considered to be a single "number". While
#   it would be nice to be able to just use a single regular expression like:
#     r'(?:[(+{[]{1,2}\d|\d(?<=[^\d(+{[]\d|^\d))[\W_]*+(?:\d[\W_]*+){7,18}\d(?=\D|$)'
#   Doing so won't get us all the possible matches of different lengths which start from the same character, even
#   when using the regex package's overlapped=True option. In order to get all different possible lengths,
#   we use multiple regular expressions, with each specifying an explicit length within the range in which we're
#   interested and then combine the results.
#   In order to make it more efficient, we combine those into a single regular expression using lookaheads and
#   capture groups, which will put all of the different possibilites into capture groups, along with empty strings
#   for each length which didn't match.
# The use of separate Unicode and ASCII flagged versions of the regexes is also because they can result in different
#   start and end points for the numbers. We continue to keep that separation for the NUMBER_REGEX,
#   NUMBER_REGEX_START, and NUMBER_REGEX_END in order to not have a separate source for a combined regex. This
#   does result in our CI testing being a bit slower, but is a trade-off for not using two separate regexes, which
#   would reduce maintainability.
# The minimum number of digits to be considered a "number":
NUMBER_REGEX_MINIMUM_DIGITS = 7
# The maximum number of digits to be considered a "number":
NUMBER_REGEX_MAXIMUM_DIGITS = 20
NUMBER_REGEX_RANGE_LOW = NUMBER_REGEX_MINIMUM_DIGITS - 2
NUMBER_REGEX_RANGE_HIGH = NUMBER_REGEX_MAXIMUM_DIGITS - 2
NUMBER_REGEX_START_TEXT = r'(?:[(+{[]{1,2}\d|\d(?<=[^\d(+{[]\d|^\d))(?:[\W_]*+|\D(?:(?=\d)|(?<=\d\D)))'
NUMBER_REGEX_MIDDLE_TEXT = r'(?:\d(?:[\W_]*+|\D(?:(?=\d)|(?<=\d\D)))){{{}}}'
NUMBER_REGEX_END_TEXT = r'\d(?=\D|$)'


def get_number_regex_with_quantfier(quantifier):
    return NUMBER_REGEX_START_TEXT + NUMBER_REGEX_MIDDLE_TEXT.format(quantifier) + NUMBER_REGEX_END_TEXT


NUMBER_REGEX_RANGE_TEXT = "{},{}".format(NUMBER_REGEX_RANGE_LOW, NUMBER_REGEX_RANGE_HIGH)
NUMBER_REGEXTEXT_WITH_RANGE = get_number_regex_with_quantfier(NUMBER_REGEX_RANGE_TEXT)
# Starting the regex with a pattern for the entire range limits the rest of the overall regex to only being tested
# on characters where there's going to be a match.
NUMBER_REGEX_TEXT = r'(?={})'.format(NUMBER_REGEXTEXT_WITH_RANGE)

for number_regex_length in range(NUMBER_REGEX_RANGE_LOW, NUMBER_REGEX_RANGE_HIGH):
    # These lookaheads all have an empty pattern as a second option. This causes all of them to
    # always match, which results in the capture group having the capture and not causing evaluation
    # of the regex to stop.
    NUMBER_REGEX_TEXT += r'(?=({})|)'.format(get_number_regex_with_quantfier(number_regex_length))

# The NUMBER_REGEX is to verify that a pattern with be able to make an exact match to text strings which are
#   selected by the NUMBER_REGEXes. It should be used as a test to verify patterns for number watches and
#   blacklists.
NUMBER_REGEX = {
    'unicode': regex.compile(NUMBER_REGEX_TEXT, flags=regex.UNICODE),
    'ascii': regex.compile(NUMBER_REGEX_TEXT, flags=regex.ASCII)
}
NUMBER_REGEX_START = {
    'unicode': regex.compile(r'^' + NUMBER_REGEX_START_TEXT, flags=regex.UNICODE),
    'ascii': regex.compile(r'^' + NUMBER_REGEX_START_TEXT, flags=regex.ASCII)
}
NUMBER_REGEX_END = {
    'unicode': regex.compile(NUMBER_REGEX_END_TEXT + r'$', flags=regex.UNICODE),
    'ascii': regex.compile(NUMBER_REGEX_END_TEXT + r'$', flags=regex.ASCII)
}


def normalize_number(number):
    return regex.sub(r"(?a)\D", "", number)


def normalize_number_set(numbers):
    return {normalize_number(num) for num in numbers}


def get_all_unique_candidates(text):
    # Get unprocessed, unique normalized, and unique deobfuscated candidates
    unprocessed, normalized, deobfuscated = get_all_candidates(text)
    unique_normalized = normalized - unprocessed
    unique_deobfuscated = deobfuscated - unique_normalized - unprocessed
    return unprocessed, unique_normalized, unique_deobfuscated


def get_all_candidates(text):
    # Get unprocessed, unique normalized, and unique deobfuscated candidates
    unprocessed = get_candidates(text)
    normalized = normalize_number_set(unprocessed)
    deobfuscated = get_normalized_deobfuscated_candidates(text)
    return unprocessed, normalized, deobfuscated


def get_candidates(text):
    # Get all the strings within the text to test which might be considered a single "number".
    # The difficulty here is that we want all the different permutations (restricted to the original order)
    # which can match with any number of digits within our range.
    ascii_findall = NUMBER_REGEX['ascii'].findall(text, overlapped=True)
    numbers = [number for lst in ascii_findall for number in lst if number != '']
    # We only want the ones which consider Unicode digits which are not included with only ASCII digits.
    # Considering the non-ASCII Unicode numbers may result in number candidates which start or end at
    # different points.
    unicode_findall = NUMBER_REGEX['unicode'].findall(text, overlapped=True)
    numbers.extend([number for lst in unicode_findall for number in lst if number != ''])
    numbers = set(numbers)
    return numbers


def get_normalized_candidates(text):
    return normalize_number_set(get_candidates(text))


def get_normalized_deobfuscated_candidates(text):
    return normalize_number_set(get_candidates(number_homoglyphs.normalize(text)))


# North American phone numbers with fairly strict formatting
# The goal here is to be sure about identification, even if that leaves ones which are not identified.
# Without a 1. It must have a separator between the 334 groupings, like \d{3}\D\d{3}\D\d{4}, but with more
# than just a single \D permited. The start can be our normal mix.
NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX = r'(?<=\D)[2-9]\d{2}(?:[\W_]*+|\D(?=\d))(?<=\D)\d{4})$'
NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE = r'[2-9]\d{2}(?:[\W_]*+|\D(?=\d))\d{4})$'
NA_NUMBER_WITHOUT_ONE_REGEX_START = r'^((?:[(+{[]{1,2}[2-9]|[2-9](?<=[^\d(+{[][2-9]|^[2-9]))\d{2}' + \
                                    r'(?:[\W_]*+|\D(?:(?=\d)|(?<=\d\D)))'
NA_NUMBER_WITHOUT_ONE_REGEX = NA_NUMBER_WITHOUT_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX
NA_NUMBER_WITHOUT_ONE_LOOSE = NA_NUMBER_WITHOUT_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE
# With a 1. It must have a separator between the 334 groupings, like 1\d{3}\D\d{3}\D\d{4}, but with more
# than just a single \D permited and a separator is permitted after the 1. The start can be our normal mix.
NA_NUMBER_WITH_ONE_REGEX_START = r'^(?:[(+{[]{1,2}1|1(?<=[^\d(+{[]1|^1))(?:[\W_]*+|\D(?=\d))' + \
                                 r'([2-9]\d{2}(?:[\W_]*+|\D(?=\d))'
NA_NUMBER_WITH_ONE_REGEX = NA_NUMBER_WITH_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX
NA_NUMBER_WITH_ONE_LOOSE = NA_NUMBER_WITH_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE


def is_north_american_phone_number_with_one(text):
    return regex.match(NA_NUMBER_WITH_ONE_REGEX, text) is not None


def is_north_american_phone_number_without_one(text):
    return regex.match(NA_NUMBER_WITHOUT_ONE_REGEX, text) is not None


def is_north_american_phone_number_with_one_loose(text):
    return regex.match(NA_NUMBER_WITH_ONE_LOOSE, text) is not None


def is_north_american_phone_number_without_one_loose(text):
    return regex.match(NA_NUMBER_WITHOUT_ONE_LOOSE, text) is not None


def process_numlist(numlist, processed=None, normalized=None):
    processed = processed if processed is not None else set()
    normalized = normalized if normalized is not None else set()
    unique_normalized = set()
    duplicate_normalized = set()
    full_list = dict()
    index = 0
    for entry in numlist:
        index += 1
        this_entry_normalized = set()
        without_comment = remove_end_regex_comment(entry)
        processed.add(without_comment)
        comment = entry.replace(without_comment, '')
        force_no_north_american = 'no noram' in comment.lower() or 'NO NA' in comment
        force_is_north_american = 'is noram' in comment.lower() or 'IS NA' in comment
        # normalized to only digits
        this_entry_normalized.add(get_only_digits(without_comment))
        deobfuscated = number_homoglyphs.normalize(without_comment)
        # deobfuscated and normalized: We don't look for the non-normalized deobfuscated
        normalized_deobfuscated = get_only_digits(deobfuscated)
        this_entry_normalized.add(normalized_deobfuscated)
        report_text = '({}) Number entry: {}'.format(index, entry)
        north_american_extra = ''
        north_american_add_type = ''
        maybe_north_american_extra = ''
        maybe_north_american_add_type = ''
        if not force_no_north_american:
            if is_north_american_phone_number_with_one(deobfuscated):
                # Add a version without a one
                north_american_extra = normalized_deobfuscated[1:]
                north_american_add_type = 'non-1'
            elif is_north_american_phone_number_without_one(deobfuscated):
                # Add a version with a one
                north_american_extra = '1' + normalized_deobfuscated
                north_american_add_type = 'add-1'
            elif is_north_american_phone_number_with_one_loose(deobfuscated):
                # Add a version without a one
                maybe_north_american_extra = normalized_deobfuscated[1:]
                maybe_north_american_add_type = 'non-1'
            elif is_north_american_phone_number_without_one_loose(deobfuscated):
                # Add a version with a one
                maybe_north_american_extra = '1' + normalized_deobfuscated
                maybe_north_american_add_type = 'add-1'
        if maybe_north_american_extra and force_is_north_american:
            north_american_extra = maybe_north_american_extra
            north_american_add_type = maybe_north_american_add_type
            maybe_north_american_extra = ''
            maybe_north_american_add_type = ''
        if north_american_extra:
            this_entry_normalized.add(north_american_extra)
            report_text += ': NorAm {} normalized: {}'.format(north_american_add_type, north_american_extra)
        if maybe_north_american_extra:
            report_text += ': MAYBE NorAm {} normalized: {} (NOT ADDED)'.format(maybe_north_american_add_type,
                                                                                maybe_north_american_extra)
        normalized |= this_entry_normalized
        full_entry = (without_comment, this_entry_normalized)
        full_list[entry] = full_entry
        report_text += ':: adding normalized: {}'.format(this_entry_normalized)
        report_text += ':: full_entry: {}'.format(full_entry)
        print(report_text)
    return full_list, processed, normalized
