# coding=utf-8
import regex
import string

from helpers import regex_compile_no_cache

# In this module our regexes are case-sensitive, and we make use of set subtraction
REGEX_FLAGS = regex.U | regex.S | regex.V1

# An "equivalent" is either a case version of the letter, or a lookalike character.
# Hex numbers are primarily used below, due to the possibility of the characters becoming corrupted when the file
# is edited in editors which don't fully support Unicode, or even just on different operating systems.

EQUIVALENTS_CODEPOINTS: {str: list[int]} = {
    'A': [ord('4'), ord('@')],
    'B': [ord('8')],
    'C': [ord('('), ord('[')],
    'D': [ord(')')],
    'E': [ord('3')],
    'F': [],
    'G': [ord('6'), ord('9')],
    'H': [],
    'I': [ord('1'), ord('l'), ord('|'), ord('!')],
    'J': [],
    'K': [],
    'L': [ord('1'), ord('I'), ord('|'), ord('!')],
    'M': [],
    'N': [],
    'O': [ord('0'), ord('@')],
    'P': [],
    'Q': [ord('9')],
    'R': [],
    'S': [ord('5'), ord('$')],
    'T': [ord('7'), ord('+')],
    'U': [ord('v'), ord('V')],
    'V': [ord('u'), ord('U')],
    'W': [],
    'X': [],
    'Y': [],
    'Z': [ord('2')],

    '.': [ord('*')],

    # used for word breaks in keyphrase definitions
    # note that any non-word character will be accepted as non-obfuscation in matches
    '-': [ord('_')],

    # used for accepting words ending in 's
    "'": [ord('"'), ord("`")],
}

# include the same characters in upper and lower case
for char, codepoints in EQUIVALENTS_CODEPOINTS.items():
    codepoints.append(ord(char.upper()))
    if char.lower() != char.upper():
        codepoints.append(ord(char.lower()))
    codepoints.sort()

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
KEYPHRASE_REGEX_END = "(?!(?!(?:" + build_equivalent_regex("'") + ")?+" + build_equivalent_regex("s") + r"(?!\w))\w)"


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
    for keyphrase, keyphrase_regex, exclude_regex in compiled_keyphrases:
        seen = set()
        for match in filter(lambda m: m not in seen, keyphrase_regex.finditer(text)):
            if not exclude_regex.search(match.group()):
                yield match, keyphrase
            seen.add(match)
