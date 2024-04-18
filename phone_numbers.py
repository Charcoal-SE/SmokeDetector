# coding=utf-8
import regex
import number_homoglyphs
from helpers import get_only_digits, remove_end_regex_comments

# The NUMBER_REGEXes are used to obtain strings within a post which are considered to be a single "number". While
#   it would be nice to be able to just use a single regular expression like:
#     r'(?:[(+{[]{1,2}\d|\d(?<=[^\d(+{[]\d|^\d))[\W_]*+(?:\d[\W_]*+){7,18}\d(?=\D|$)'
#   Doing so won't get us all the possible matches of different lengths which start from the same character, even
#   when using the regex package's overlapped=True option. In order to get all different possible lengths,
#   we use multiple regular expressions, with each specifying an explicit length within the range in which we're
#   interested and then combine the results.
#   In order to make it more efficient, we combine those into a single regular expression using lookaheads and
#   capture groups, which will put all of the different possibilities into capture groups, along with empty strings
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
VALID_NON_DIGIT_START_CHARACTERS = r'(+{['
NUMBER_REGEX_START_TEXT = r'(?:[' + VALID_NON_DIGIT_START_CHARACTERS + \
                          r']{1,2}\d|\d(?<=[^\d' + VALID_NON_DIGIT_START_CHARACTERS + \
                          r']\d|^\d))(?:[\W_]*+|\D(?:(?=\d)|(?<=\d\D)))'
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


def matches_regex_ascii_or_unicode(regex_dict, pattern):
    return regex_dict['ascii'].search(pattern) or regex_dict['unicode'].search(pattern)


def matches_number_regex(pattern):
    return matches_regex_ascii_or_unicode(NUMBER_REGEX, pattern)


def matches_number_regex_start(pattern):
    return matches_regex_ascii_or_unicode(NUMBER_REGEX_START, pattern)


def matches_number_regex_end(pattern):
    return matches_regex_ascii_or_unicode(NUMBER_REGEX_END, pattern)


def is_digit_count_in_number_regex_range(digit_count):
    return digit_count > NUMBER_REGEX_MINIMUM_DIGITS and digit_count < NUMBER_REGEX_MAXIMUM_DIGITS


def normalize(number):
    return get_only_digits(number)


def normalize_set(numbers):
    return {normalize(num) for num in numbers}


def normalize_list_only_changed(numbers):
    # We want all which were changed by normalization, even if that results
    #  in re-introducing something that was excluded.
    #  Example: original: ['12a34', '1234']
    #                        ^want    ^don't want
    normalized_list = []
    for num in numbers:
        normalized = normalize(num)
        if normalized != num:
            normalized_list.append(normalized)
    return normalized_list


def normalize_list(numbers):
    return [normalize(num) for num in numbers]


def get_candidate_set_with_start_characters(candidate):
    result = set()
    base = regex.sub(r'^[' + VALID_NON_DIGIT_START_CHARACTERS + r']+', '', candidate)
    result.add(base)
    for first in VALID_NON_DIGIT_START_CHARACTERS:
        result.add(first + base)
        for second in VALID_NON_DIGIT_START_CHARACTERS:
            result.add(first + second + base)
    return result


def get_all_candidates(text):
    """
    Get unprocessed number candidates, normalized entries which are differenet from their unprocessed source,
    and the normalized candidates which are newly generated as a result of deobfuscation.
    """
    unprocessed_list, normalized_list = get_candidates(text, True)
    raw_deobfuscated_list = get_deobfuscated_candidates(text)
    # The raw_deobfuscated list should contain everything that's in the unprocessed list.
    # We don't want to be considering any which are the identical entries as are in the unprocessed
    # list. However, it's possible that an additional identical entry was created through deobfuscation.
    # So, if there are 2 copies of a number on the unprocessed_list and 3 of that number on the
    # raw_deobfuscated_list, then we want to end up with 1 of that number on the deobfuscated_list.
    for unprocessed in unprocessed_list:
        try:
            raw_deobfuscated_list.remove(unprocessed)
        except ValueError:
            pass
    # We only ever deal with the deobfuscated numbers in normalized format. Unlike the normalized list,
    # we want all of them, even if unchanged.
    deobfuscated_list = normalize_list(raw_deobfuscated_list)
    return set(unprocessed_list), set(normalized_list), set(deobfuscated_list)


def get_candidates(text, also_normalized=False):
    """
    :param test: Text from which to extract number candidates
    :param also_normalized: Also return the normalized list
    :return: canidate_list or candidate_list, normalized_list
    """
    # The differences between this implementation and the original get_candidates(), which was based on a
    # regex implementation, are:
    #   1. This doesn't have the same potential for catistrophic CPU usage based on input text.
    #   2. When the first character in the candidate is not a digit, this returns only one candidate.
    #      For example "+(123..." will return ["+(123..."]. The regex version returns two candidates, but not
    #      the version without the non-digit start characters (i.e. it returns ["+(123...", "(123..."]).
    #      The characters other than digits which are valid at the start are in VALID_NON_DIGIT_START_CHARACTERS.
    #      The intent at that time was to generate more verbatim matches, but it's better to just have the one
    #      result. In the meantime, normalized matching has been improved and more emphasis placed on it.
    #   3. The regex version routinely returned duplicate entries. This implementation only returns duplicate
    #      entries if there are duplicates in the input text.
    candidates = []
    candidates_normalized = []
    in_process_normalized = []
    in_process = []
    in_process_digit_counts = []
    non_digits = ''
    prev_non_digit = ''
    prev_prev_non_digit = ''
    digits = ''
    # alpha_count is, primarily, the number of alpha characters encountered since the last digit. However, it's
    # also used as a flag, by setting alpha_count = max_alpha + 1, to indicate that some other criteria has
    # been reached which should cause the same behavior.
    # Specifically, it's used for when len_digits > NUMBER_REGEX_MAXIMUM_DIGITS or when
    # len(non_digits) > max_non_digits.
    alpha_count = 0
    max_alpha = 1
    # max_non_digits is moderately high, but is intended to account for potential zalgo text, and/or
    # combining characters, which would leave the number still readable by humans.
    max_non_digits = 50

    def promote_any_in_process_with_appropriate_digit_count():
        for index in range(len(in_process)):
            cur_count = in_process_digit_counts[index]
            if cur_count >= NUMBER_REGEX_MINIMUM_DIGITS and cur_count <= NUMBER_REGEX_MAXIMUM_DIGITS:
                candidates.append(in_process[index])
                if in_process_normalized[index][0] != 'z':
                    # The 'z' at the start is used as a flag that this isn't a valid normalized entry.
                    candidates_normalized.append(in_process_normalized[index])

    def evict_any_in_process_with_too_many_digits():
        for index in reversed(range(len(in_process))):
            if in_process_digit_counts[index] > NUMBER_REGEX_MAXIMUM_DIGITS:
                del in_process[index]
                del in_process_normalized[index]
                del in_process_digit_counts[index]

    def clear_in_process_if_more_than_limit_alpha():
        nonlocal in_process
        nonlocal in_process_normalized
        nonlocal in_process_digit_counts
        if in_process and alpha_count > max_alpha:
            # No sequences continue passed limit alpha characters
            in_process_normalized = []
            in_process = []
            in_process_digit_counts = []

    def if_digits_add_digits_to_all_in_process_and_promote():
        nonlocal in_process
        nonlocal in_process_normalized
        nonlocal in_process_digit_counts
        nonlocal digits
        nonlocal alpha_count
        nonlocal prev_non_digit
        nonlocal prev_prev_non_digit
        if digits:
            len_digits = len(digits)
            if len_digits > NUMBER_REGEX_MAXIMUM_DIGITS:
                # Too many digits. No need to try adding them, nor remembering the next alpha chars
                alpha_count = max_alpha + 1
                clear_in_process_if_more_than_limit_alpha()
            else:
                in_process = [to_add + digits for to_add in in_process]
                in_process_normalized = [to_add + digits for to_add in in_process_normalized]
                in_process_digit_counts = [to_add + len_digits for to_add in in_process_digit_counts]
                # The original regex was written so that if a sequence started with '+(123...', then
                # both '+(123...' and '(123...' ended up as candidates.
                if prev_non_digit in VALID_NON_DIGIT_START_CHARACTERS:
                    if prev_prev_non_digit in VALID_NON_DIGIT_START_CHARACTERS:
                        in_process.append(prev_prev_non_digit + prev_non_digit + digits)
                    else:
                        in_process.append(prev_non_digit + digits)
                else:
                    in_process.append(digits)
                in_process_normalized.append(digits)
                in_process_digit_counts.append(len_digits)
                promote_any_in_process_with_appropriate_digit_count()
                evict_any_in_process_with_too_many_digits()
            digits = ''
            prev_non_digit = ''
            prev_prev_non_digit = ''

    for char in text:
        if char >= '0' and char <= '9':
            # It's a digit
            digits += char
            alpha_count = 0
            if non_digits:
                in_process = [to_add + non_digits for to_add in in_process]
                non_digits = ''
        else:
            # Not a digit
            if_digits_add_digits_to_all_in_process_and_promote()
            prev_prev_non_digit = prev_non_digit
            prev_non_digit = char
            if (char >= 'A' and char <= 'Z') or (char >= 'a' and char <= 'z'):
                alpha_count += 1
                clear_in_process_if_more_than_limit_alpha()
            if alpha_count > max_alpha:
                non_digits = ''
            else:
                non_digits += char
                if len(non_digits) > max_non_digits:
                    alpha_count = max_alpha + 1  # Secondary use is as a flag that all in_process should end.
                    clear_in_process_if_more_than_limit_alpha()
                    non_digits = ''
    if_digits_add_digits_to_all_in_process_and_promote()
    # We can look at returning the normalized in a bit
    if also_normalized:
        return candidates, candidates_normalized
    return candidates


def get_normalized_candidates(text):
    return normalize_set(get_candidates(text))


def get_normalized_deobfuscated_candidates(text):
    return normalize_set(get_candidates(number_homoglyphs.normalize(text)))


def get_deobfuscated_candidates(text):
    return get_candidates(number_homoglyphs.normalize(text))


# North American phone numbers with fairly strict formatting
# The goal here is to be sure about identification, even if that leaves ones which are not identified.
# Without a 1. It must have a separator between the 334 groupings, like \d{3}\D\d{3}\D\d{4}, but with more
# than just a single \D permitted. The start can be our normal mix.
NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX = r'(?<=\D)[2-9]\d{2}(?:[\W_]*+|\D(?=\d))(?<=\D)\d{4}$'
NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE = r'[2-9]\d{2}(?:[\W_]*+|\D(?=\d))\d{4}$'
NA_NUMBER_WITHOUT_ONE_REGEX_START = r'^(?:[' + VALID_NON_DIGIT_START_CHARACTERS + \
                                    r']{1,2}[2-9]|[2-9](?<=[^\d' + VALID_NON_DIGIT_START_CHARACTERS + \
                                    r'][2-9]|^[2-9]))\d{2}' + \
                                    r'(?:[\W_]*+|\D(?:(?=\d)|(?<=\d\D)))'
NA_NUMBER_WITHOUT_ONE_REGEX = NA_NUMBER_WITHOUT_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX
NA_NUMBER_WITHOUT_ONE_LOOSE = NA_NUMBER_WITHOUT_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE
# With a 1. It must have a separator between the 334 groupings, like 1\d{3}\D\d{3}\D\d{4}, but with more
# than just a single \D permitted and a separator is permitted after the 1. The start can be our normal mix.
NA_NUMBER_WITH_ONE_REGEX_START = r'^(?:[' + VALID_NON_DIGIT_START_CHARACTERS + \
                                 r']{1,2}1|1(?<=[^\d' + VALID_NON_DIGIT_START_CHARACTERS + \
                                 r']1|^1))(?:[\W_]*+|\D(?=\d))' + \
                                 r'[2-9]\d{2}(?:[\W_]*+|\D(?=\d))'
# There's a trend to using a straight format of "+12345678900", which should be considered a NA number.
NA_NUMBER_WITH_ONE_NO_SEPARATORS_REGEX = r'^\+?1[2-9]\d{2}[2-9]\d{2}\d{4}$'
NA_NUMBER_WITH_ONE_AREA_CODE_SHORT_SEPARATORS_REGEX = r'^\+?1\D{0,2}[2-9]\d{2}\D{0,2}[2-9]\d{2}\d{4}$'
NA_NUMBER_WITH_ONE_REGEX = NA_NUMBER_WITH_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_REGEX
NA_NUMBER_WITH_ONE_LOOSE = NA_NUMBER_WITH_ONE_REGEX_START + NA_NUMBER_CENTRAL_OFFICE_AND_LINE_LOOSE
NA_NUMBER_WITH_ONE_OR_ONE_NO_SEPARATORS_REGEX = '(?:' + NA_NUMBER_WITH_ONE_REGEX + '|' + \
                                                NA_NUMBER_WITH_ONE_AREA_CODE_SHORT_SEPARATORS_REGEX + ')'


def is_north_american_phone_number_with_one(text):
    return regex.match(NA_NUMBER_WITH_ONE_OR_ONE_NO_SEPARATORS_REGEX, text) is not None


def is_north_american_phone_number_without_one(text):
    return regex.match(NA_NUMBER_WITHOUT_ONE_REGEX, text) is not None


def is_north_american_phone_number_with_one_loose(text):
    return regex.match(NA_NUMBER_WITH_ONE_LOOSE, text) is not None


def is_north_american_phone_number_without_one_loose(text):
    return regex.match(NA_NUMBER_WITHOUT_ONE_LOOSE, text) is not None


def deobfuscate(text):
    return number_homoglyphs.normalize(text)


def get_north_american_with_separators_from_normalized(normalized):
    base = normalized[-10:-7] + '-' + normalized[-7:-4] + '-' + normalized[-4:]
    country_code = '1-' if len(normalized) > 10 else ''
    return country_code + base


def get_maybe_north_american_not_in_normalized_but_in_all(pattern, normalized, all_normalized=None):
    without_comments, comments = split_processed_and_comments(pattern)
    north_american_extra, north_american_add_type, maybe_north_american_extra = \
        get_north_american_alternate_normalized(normalize(deobfuscate(without_comments)), force=True)
    if maybe_north_american_extra not in normalized and \
            (all_normalized is None or maybe_north_american_extra in all_normalized):
        return maybe_north_american_extra
    return ''


def get_north_american_alternate_normalized(non_normalized, normalized=None, force=False):
    normalized = normalized if normalized else normalize(non_normalized)
    north_american_extra = ''
    north_american_add_type = ''
    maybe_north_american_extra = ''
    non_normalized = normalized if force else non_normalized
    if is_north_american_phone_number_with_one(non_normalized):
        # Add a version without a one
        north_american_extra = normalized[1:]
        north_american_add_type = 'non-1'
    elif is_north_american_phone_number_without_one(non_normalized):
        # Add a version with a one
        north_american_extra = '1' + normalized
        north_american_add_type = 'add-1'
    elif is_north_american_phone_number_with_one_loose(non_normalized):
        # Add a version without a one
        maybe_north_american_extra = normalized[1:]
        north_american_add_type = 'non-1'
    elif is_north_american_phone_number_without_one_loose(non_normalized):
        # Add a version with a one
        maybe_north_american_extra = '1' + normalized
        north_american_add_type = 'add-1'
    return north_american_extra, north_american_add_type, maybe_north_american_extra


def split_processed_and_comments(pattern):
    without_comments = remove_end_regex_comments(pattern)
    comment = pattern.replace(without_comments, '')
    return without_comments, comment


def check_comments_for_north_american_directive(comments):
    force_is_north_american = 'is noram' in comments.lower() or 'IS NA' in comments
    force_no_north_american = 'no noram' in comments.lower() or 'NO NA' in comments
    return force_is_north_american, force_no_north_american


def get_north_american_forced_or_no_from_pattern(pattern):
    without_comments, comments = split_processed_and_comments(pattern)
    return check_comments_for_north_american_directive(comments)


def process_numlist(numlist, processed=None, normalized=None):
    # The normalized list does contain any processed item which is also normalized.
    processed = processed if processed is not None else set()
    normalized = normalized if normalized is not None else set()
    unique_normalized = set()
    duplicate_normalized = set()
    full_list = dict()
    index = 0
    for entry in numlist:
        index += 1
        this_entry_normalized = set()
        without_comments, comments = split_processed_and_comments(entry)
        processed.add(without_comments)
        comment = entry.replace(without_comments, '')
        force_is_north_american, force_no_north_american = check_comments_for_north_american_directive(comments)
        # normalized to only digits
        this_entry_normalized.add(normalize(without_comments))
        deobfuscated = deobfuscate(without_comments)
        # deobfuscated and normalized: We don't look for the non-normalized deobfuscated
        normalized_deobfuscated = normalize(deobfuscated)
        this_entry_normalized.add(normalized_deobfuscated)
        if not force_no_north_american:
            north_american_extra, north_american_add_type, maybe_north_american_extra = \
                get_north_american_alternate_normalized(deobfuscated, normalized_deobfuscated, force_is_north_american)
            if maybe_north_american_extra and force_is_north_american:
                north_american_extra = maybe_north_american_extra
                maybe_north_american_extra = ''
            if north_american_extra:
                this_entry_normalized.add(north_american_extra)
        # The normalized list *does* contain the processed string, if it's also normalized, as we need it to test
        #   against obfuscated
        normalized |= this_entry_normalized
        full_entry = (without_comments, this_entry_normalized)
        full_list[entry] = full_entry
    return full_list, processed, normalized
