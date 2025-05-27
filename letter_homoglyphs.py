# coding=utf-8
import itertools

import regex
import string
import unicodedata

from helpers import regex_compile_no_cache

# In this module our regexes are case-sensitive, and we make use of set subtraction
REGEX_FLAGS = regex.U | regex.S | regex.V1

# Latin letters which look like others (case-sensitive)
LATIN_LOOKALIKE_LETTERS = {
    'I': ['l', 'j', 'J'],
    'L': ['I'],
    'U': ['V', 'v'],
    'V': ['U', 'u'],
}

# Letters which exist in "small dotless" versions
LATIN_SMALL_DOTLESS = {
    'I': ['i', 'j'],
    'J': ['j'],
    'L': ['i', 'j'],
}

# Names of letter styles used in Unicode
UNICODE_LETTER_STYLE_NAMES = [
    None,
    'BOLD',
    'ITALIC',
    'BOLD ITALIC',
    'SCRIPT',
    'BOLD SCRIPT',
    'FRAKTUR',
    'BLACK-LETTER',
    'DOUBLE-STRUCK',
    'BOLD FRAKTUR',
    'SANS-SERIF',
    'SANS-SERIF BOLD',
    'SANS-SERIF ITALIC',
    'SANS-SERIF BOLD ITALIC',
    'MONOSPACE',
    # 'COMBINING',
    'PARENTHESIZED',
    'CIRCLED',
    'FULLWIDTH',
    'OUTLINED',
    'TORTOISE SHELL BRACKETED',
    'SQUARED',
    'NEGATIVE CIRCLED',
    'NEGATIVE SQUARED',
    'CROSSED NEGATIVE SQUARED',
]

# Names of Greek letters which look like Latin letters (case-sensitive)
GREEK_LOOKALIKE_NAMES = {
    'A': ['ALPHA', 'DELTA', 'LAMBDA', 'alpha', 'lambda'],
    'B': ['BETA', 'beta', 'beta symbol'],
    'C': ['final sigma', 'zeta', 'LUNATE SIGMA SYMBOL', 'DOTTED LUNATE SIGMA SYMBOL'],
    'D': ['delta'],
    'E': ['EPSILON', 'SIGMA', 'epsilon', 'xi'],
    'F': ['DIGAMMA', 'digamma'],
    'H': ['ETA', 'lambda'],
    'I': ['IOTA', 'iota'],
    'J': ['YOT', 'yot'],
    'K': ['KAPPA', 'kappa', 'KAI SYMBOL'],
    'L': ['IOTA', 'iota'],
    'M': ['MU', 'SAN', 'san'],
    'N': ['NU', 'lambda'],
    'O': ['OMICRON', 'omicron', 'THETA', 'theta', 'sigma', 'DELTA', 'ARCHAIC KOPPA', 'archaic koppa'],
    'P': ['RHO', 'rho'],
    'Q': ['phi', 'ARCHAIC KOPPA', 'archaic koppa'],
    'R': ['GAMMA'],
    'T': ['TAU', 'tau', 'ARCHAIC SAMPI', 'archaic sampi'],
    'U': ['mu', 'nu', 'upsilon'],
    'V': ['mu', 'nu', 'upsilon'],
    'W': ['omega'],
    'X': ['CHI', 'chi'],
    'Y': ['UPSILON', 'gamma'],
    'Z': ['ZETA', 'zeta'],
}

# 1337 (digits which look like Latin letters)
LETTER_LOOKALIKE_DIGITS = {
    'A': [4],
    'B': [8],
    'E': [3],
    'G': [6, 9],
    'I': [1],
    'L': [1],
    'O': [0],
    'Q': [9],
    'S': [5],
    'Z': [2],
}

# Some other names in Unicode which exist in multiple styles
OTHER_LOOKALIKE_NAMES = {
    'A': ['PARTIAL DIFFERENTIAL'],
    'D': ['PARTIAL DIFFERENTIAL'],
    'E': ['EPSILON SYMBOL'],
    'O': ['PHI SYMBOL'],
    'W': ['PI SYMBOL'],
}


def get_homoglyphs_by_unicode_names(*name_options):
    for name in itertools.product(*name_options):
        full_name = ' '.join(filter(None, name))
        try:
            yield ord(unicodedata.normalize('NFD', unicodedata.lookup(full_name))[0])
        except KeyError:
            pass


def get_letter_homoglyphs_by_unicode_name(letter_names, alphabet_name):
    for letter_name in letter_names:
        yield from get_homoglyphs_by_unicode_names(
            [None, 'MATHEMATICAL', 'MODIFIER LETTER'],
            UNICODE_LETTER_STYLE_NAMES,
            unicode_name_alphabet_options(alphabet_name),
            [None, 'CAPITAL' if letter_name[0].isupper() else 'SMALL'],
            [None, 'LETTER'],
            [letter_name.upper()])


def unicode_name_alphabet_options(alphabet_name):
    return [None] if alphabet_name is None else [
        None, alphabet_name,
        'SUBSCRIPT ' + alphabet_name, alphabet_name + ' SUBSCRIPT',
        'SUPERSCRIPT ' + alphabet_name, alphabet_name + ' SUPERSCRIPT']


def get_digit_homoglyphs_by_unicode_name(digits):
    for digit in digits:
        digit_name = unicodedata.name(str(digit)).split()[-1]
        yield from get_homoglyphs_by_unicode_names(
            [None, 'MATHEMATICAL'],
            UNICODE_LETTER_STYLE_NAMES,
            [None, 'SUPERSCRIPT', 'SUBSCRIPT'],
            [None, 'DIGIT'],
            [digit_name])


def get_other_homoglyphs_by_unicode_name(names):
    for name in names:
        yield from get_homoglyphs_by_unicode_names(
            [None, 'MATHEMATICAL'],
            UNICODE_LETTER_STYLE_NAMES,
            [None, 'SUPERSCRIPT', 'SUBSCRIPT'],
            [name])


# An "equivalent" is either a case version of the letter, or a lookalike character.
# Hex numbers are primarily used below, due to the possibility of the characters becoming corrupted when the file
# is edited in editors which don't fully support Unicode, or even just on different operating systems.
EQUIVALENTS_CODEPOINTS: {str: list[int]} = {
    'A': [ord('@')],
    'B': [],
    'C': [ord('('), ord('[')],
    'D': [ord(')')],
    'E': [],
    'F': [],
    'G': [],
    'H': [],
    'I': [ord('|'), ord('!')],
    'J': [],
    'K': [],
    'L': [ord('|'), ord('!')],
    'M': [],
    'N': [],
    'O': [ord('@')],
    'P': [],
    'Q': [],
    'R': [],
    'S': [ord('$')],
    'T': [ord('+')],
    'U': [],
    'V': [],
    'W': [],
    'X': [],
    'Y': [],
    'Z': [],

    '.': [ord('*')],

    # used for word breaks in keyphrase definitions
    # note that any non-word character will be accepted as non-obfuscation in matches
    '-': [ord('_')],
}

# add Unicode lookups to EQUIVALENTS_CODEPOINTS
for letter in string.ascii_uppercase:
    latin_names = [letter, letter.lower()]
    if letter in LATIN_LOOKALIKE_LETTERS:
        latin_names.extend(LATIN_LOOKALIKE_LETTERS[letter])
    if letter in LATIN_SMALL_DOTLESS:
        latin_names.extend('dotless ' + c for c in LATIN_SMALL_DOTLESS[letter])
    EQUIVALENTS_CODEPOINTS[letter].extend(itertools.chain(
        get_letter_homoglyphs_by_unicode_name(latin_names, 'LATIN'),
        get_letter_homoglyphs_by_unicode_name(GREEK_LOOKALIKE_NAMES.get(letter, ()), 'GREEK'),
        get_other_homoglyphs_by_unicode_name(OTHER_LOOKALIKE_NAMES.get(letter, ())),
        get_digit_homoglyphs_by_unicode_name(LETTER_LOOKALIKE_DIGITS.get(letter, ()))
    ))


# include the same characters in upper and lower case
for char, codepoints in EQUIVALENTS_CODEPOINTS.items():
    codepoints.append(ord(char.upper()))
    if char.lower() != char.upper():
        codepoints.append(ord(char.lower()))
    EQUIVALENTS_CODEPOINTS[char] = list(sorted(set(codepoints)))

import number_homoglyphs
for digit in string.digits:
    EQUIVALENTS_CODEPOINTS[digit] = [ord(digit)] + number_homoglyphs.equivalents[digit]
    EQUIVALENTS_CODEPOINTS[digit].sort()


# Codepoints that could stand for either letters, or as punctuation/separators
POSSIBLE_SEPARATOR_CODEPOINTS: list[int] = []

for char, codepoints in EQUIVALENTS_CODEPOINTS.items():
    for codepoint in codepoints:
        if regex.match(r'\W', chr(codepoint), flags=REGEX_FLAGS) and codepoint not in POSSIBLE_SEPARATOR_CODEPOINTS:
            POSSIBLE_SEPARATOR_CODEPOINTS.append(codepoint)


# These are diacritical marks that are expressed as separate codepoints, but don't take extra space on the screen.
COMBINING_MARK_REGEX = r"\p{Mn}"


def build_regex_charset(codepoints, prefix='[', suffix=']'):
    return prefix + regex.escape(''.join(map(chr, codepoints))) + suffix


def get_equivalent_codepoints(c: str) -> list[int]:
    codepoints = EQUIVALENTS_CODEPOINTS.get(c.upper())
    return codepoints if codepoints is not None else [ord(c)]


def build_equivalent_charset_regex(c: str, **kwargs) -> str:
    """
    Returns a regex string, for a single character only, which is equivalent of the given character.
    Does not match extra combining modifiers.
    """
    return build_regex_charset(get_equivalent_codepoints(c), **kwargs)


def build_equivalent_regex(c: str) -> str:
    """Returns a regex string for any equivalent of the given character."""
    return build_equivalent_charset_regex(c) + COMBINING_MARK_REGEX + "*+"


# These are treated as potential word separators in keyphrases and exclude checks
KEYPHRASE_SPACE_REGEX = build_equivalent_charset_regex("-", prefix=r'[\s')


def is_keyphrase_space(c: str) -> bool:
    return bool(regex.match(KEYPHRASE_SPACE_REGEX, c, flags=REGEX_FLAGS))


# The end of a keyphrase: optional plural or possessive s, then no immediate letter or number.
# We don't use \b because it's possible the last "letter" was a lookalike that is technically non-word.
KEYPHRASE_REGEX_END = "(?!(?!" + build_equivalent_regex("s") + r"(?!\w))\w)"


def build_possible_separator_regex_charset(c: str) -> str | None:
    codepoints = list(filter(POSSIBLE_SEPARATOR_CODEPOINTS.__contains__, get_equivalent_codepoints(c)))
    if codepoints:
        return build_regex_charset(codepoints)
    else:
        return None


SEPARATOR_REGEX = r"[\W_\s{}]".format(COMBINING_MARK_REGEX)


def build_separator_regex(char_before: str, char_after: str) -> str:
    """
    Builds a regular expression string for the space between two keyword characters.
    This space is made up of whitespace, other non-word characters, and optional combining marks.
    """
    if is_keyphrase_space(char_after):
        return ""  # we will create the word separator when the space is char_before

    # To avoid needing any backtracking, any non-letter characters that could possibly be obfuscated letters
    # FOR THE NEXT EXPECTED LETTER ONLY are not counted as punctuation.
    ambiguous_charset = build_possible_separator_regex_charset(char_after)
    if ambiguous_charset:
        return r"(?:[{}--{}])*+".format(SEPARATOR_REGEX, ambiguous_charset)
    else:
        return SEPARATOR_REGEX + "*+"


def build_keyphrase_regex(keyphrase: str) -> str:
    # We don't use \b, because it's possible the first "letter" will be a lookalike that is technically non-word.
    # Instead, we do a lookbehind after we've matched the first letter.
    r = build_equivalent_charset_regex(keyphrase[0]) + r"(?<!\w.){}*+".format(COMBINING_MARK_REGEX)
    for next_idx in range(1, len(keyphrase)):
        r += build_separator_regex(keyphrase[next_idx - 1], keyphrase[next_idx])
        if not is_keyphrase_space(keyphrase[next_idx]):
            r += build_equivalent_regex(keyphrase[next_idx])
    return r + KEYPHRASE_REGEX_END


def build_exclude_regex(keyphrase: str, exclude: str | None) -> str:
    # Always exclude the keyphrase, regardless of changes in word breaks
    r = "^" + regex.sub(pattern=KEYPHRASE_SPACE_REGEX + "++",
                        repl=SEPARATOR_REGEX.replace('\\', '\\\\') + "*+",  # sub() processes backslashes
                        string=keyphrase,
                        flags=REGEX_FLAGS) + "$"
    if exclude:
        r += r"|\b(?:" + exclude + r")\b"
    return "(?i:" + r + ")"


def compile_keyphrases(*keyphrases: (str, str | None)):
    compiled = []
    for keyphrase, exclude in keyphrases:
        compiled.append((
            keyphrase.replace('_', ''),
            regex_compile_no_cache(build_keyphrase_regex(keyphrase), REGEX_FLAGS),
            regex_compile_no_cache(build_exclude_regex(keyphrase, exclude), REGEX_FLAGS)))
    return compiled


def find_matches(compiled_keyphrases, text: str):
    text = unicodedata.normalize('NFD', text)
    for keyphrase, keyphrase_regex, exclude_regex in compiled_keyphrases:
        seen = set()
        for match in filter(lambda m: m not in seen, keyphrase_regex.finditer(text)):
            if not exclude_regex.search(match.group()):
                yield match, keyphrase
            seen.add(match)
