# coding=utf-8
import itertools
import string
import unicodedata
from typing import Iterator, Iterable

import regex

from helpers import regex_compile_no_cache

# In this module our regexes default to case-sensitive
REGEX_FLAGS = regex.U | regex.S

# Forward map from codepoints we encounter to what they might be intended to look like
CODEPOINTS_FOR_LETTER: dict[str, set[int]] = {}

# Backward map from ASCII alphanumerics, etc., to potential homoglyph codepoints
LETTERS_FOR_CODEPOINT: dict[int, set[str]] = {}


def add_equivalent(from_codepoint: int, to_letter: str):
    """Registers from_codepoint as an equivalent of to_letter"""
    return _add_equivalent_codepoints({from_codepoint}, to_letter)


def add_equivalents(from_codepoints: Iterable[int], to_letters: Iterable[str]):
    """Registers all combinations of the given codepoints and letters as equivalents"""
    for letter in to_letters:
        _add_equivalent_codepoints(from_codepoints, letter)


def _add_equivalent_codepoints(from_codepoints: Iterable[int], to_letter: str):
    to_letter = to_letter.upper()
    old_codepoints = CODEPOINTS_FOR_LETTER.get(to_letter)
    if old_codepoints:
        new_codepoints = set(from_codepoints)
        old_codepoints.update(new_codepoints)
    else:
        new_codepoints = {ord(to_letter), ord(to_letter.lower())}
        new_codepoints.update(from_codepoints)
        CODEPOINTS_FOR_LETTER[to_letter] = new_codepoints
    for codepoint in new_codepoints:
        LETTERS_FOR_CODEPOINT.setdefault(codepoint, set()).add(to_letter)


def add_case_insensitive_lookalikes(lookalike_map, case_insensitive_lookalike_map):
    for letter, uncased_names in case_insensitive_lookalike_map.items():
        cased_names = lookalike_map.setdefault(letter, [])
        cased_names.extend(map(str.upper, uncased_names))
        cased_names.extend(map(str.lower, uncased_names))


# NAMED CHARACTERS
# These are defined case-sensitively as either 'UPPER CASE', 'lower case'.
# To make them case-insensitive, use add_case_insensitive_lookalikes().

# Latin letters which look like others (case-sensitive)
LATIN_LOOKALIKE_LETTERS = {
    'A': ['turned alpha', 'inverted alpha'],
    'D': ['delta'],
    'E': ['ESH'],
    'F': ['long s', 'esh with double bar'],
    'I': ['l', 'j', 'J', 'broken l', 'dotless i', 'dotless j'],
    'J': ['dotless j'],
    'L': ['I', 'BROKEN L', 'broken l', 'dotless i', 'dotless j'],
    'S': ['esh'],
    'Q': ['SMALL Q WITH HOOK TAIL']  # sic
}
add_case_insensitive_lookalikes(LATIN_LOOKALIKE_LETTERS, {
    'A': ['ALPHA', 'TURNED V'],
    'B': ['BETA', 'SHARP S', 'CLOSED REVERSED OPEN E'],
    'C': ['STRETCHED C'],
    'D': ['ETH', 'TURNED ALPHA'],
    'E': ['OPEN E'],
    'H': ['HENG', 'HWAIR'],
    'I': ['IOTA'],
    'L': ['IOTA'],
    'N': ['ENG'],
    'O': ['TAILLESS PHI'],
    'P': ['WYNN'],
    'U': ['V', 'UPSILON'],
    'V': ['U', 'UPSILON', 'GAMMA', 'RAMS HORN', 'VEND'],
    'W': ['OMEGA', 'CLOSED OMEGA', 'TURNED M', 'INVERTED M', 'VY'],
    'X': ['CHI'],
    'Y': ['GAMMA', 'VEND'],
})

# Names of Greek letters which look like Latin letters (case-sensitive)
GREEK_LOOKALIKE_NAMES = {
    'A': ['DELTA', 'LAMBDA', 'lambda'],
    'C': ['final sigma', 'zeta'],
    'D': ['delta'],
    'E': ['EPSILON', 'SIGMA', 'epsilon', 'xi'],
    'H': ['ETA', 'lambda'],
    'K': ['KAI SYMBOL'],
    'M': ['MU', 'SAN', 'san'],
    'N': ['NU', 'lambda', 'eta'],
    'O': ['sigma', 'DELTA', 'phi symbol'],
    'Q': ['phi symbol'],
    'R': ['GAMMA'],
    'U': ['mu', 'nu', 'upsilon'],
    'V': ['mu', 'nu', 'upsilon'],
    'W': ['omega', 'pi symbol'],
    'Y': ['UPSILON', 'gamma'],
    'Z': ['ZETA', 'zeta'],
}
add_case_insensitive_lookalikes(GREEK_LOOKALIKE_NAMES, {
    'A': ['ALPHA'],
    'B': ['BETA'],
    'C': ['LUNATE SIGMA SYMBOL', 'DOTTED LUNATE SIGMA SYMBOL'],
    'F': ['DIGAMMA'],
    'I': ['IOTA'],
    'J': ['YOT'],
    'K': ['KAPPA'],
    'L': ['IOTA'],
    'O': ['OMICRON', 'THETA', 'ARCHAIC KOPPA', 'PHI'],
    'P': ['RHO'],
    'Q': ['ARCHAIC KOPPA', 'PHI'],
    'T': ['TAU', 'ARCHAIC SAMPI'],
    'X': ['CHI'],
})

# Names of Cyrillic letters which look like Latin letters (case-sensitive)
CYRILLIC_LOOKALIKE_NAMES = {
    'H': ['tshe', 'dje'],
    'X': ['HA'],
}
add_case_insensitive_lookalikes(CYRILLIC_LOOKALIKE_NAMES, {
    'A': ['A', 'DE', 'SOFT DE', 'CLOSED LITTLE YUS'],
    'B': ['BE', 'VE', 'HARD SIGN', 'SOFT SIGN'],
    'C': ['ES', 'WIDE ES'],
    'D': ['KOMI DJE'],
    'E': ['IE', 'UKRAINIAN IE', 'ZE', 'E', 'REVERSED ZE'],
    'H': ['EN', 'GHE WITH MIDDLE HOOK'],
    'K': ['KA'],
    'M': ['EM', 'SOFT EM'],
    'N': ['I', 'SHORT I'],
    'O': ['O', 'MONOCULAR O', 'BINOCULAR O', 'MULTIOCULAR O', 'NARROW O', 'FITA'],
    'P': ['ER'],
    'Q': ['EF'],
    'R': ['GHE', 'YA'],
    'T': ['TE'],
    'U': ['TSE', 'CHE', 'REVERSED TSE'],
    'W': ['SHA', 'SHCHA'],
    'X': ['ZHE'],
    'Y': ['U', 'SHORT U', 'STRAIGHT U'],
})

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


# Manual definitions of equivalent codepoints for characters
# Hex numbers are primarily used below, due to the possibility of the characters becoming corrupted when the file
# is edited in editors which don't fully support Unicode, or even just on different operating systems.
add_equivalents([
    ord('@'),
    0x15cb, 0x15e9, 0x2202, 0x2227,
], "A")
add_equivalents([
    0x10a6, 0x10aa, 0x15b2, 0x15F8, 0x15F9, 0x15FD, 0x15FE, 0x15FF, 0x1656, 0x1657, 0x1658, 0x165D, 0x165E, 0x165F,
    0x1669, 0x166A, 0x166B, 0x266D,
], "B")
add_equivalents([
    ord('('), ord('['),
    0x1455, 0x1566, 0xa9, 0x20AC, 0x2201, 0x2286, 0x228F, 0x2291, 0x22D0, 0x22E4,
], "C")
add_equivalents([
    ord(')'),
    0x15B1, 0x15DF, 0x15E0, 0x15EB, 0x15EC, 0x2202,
], "D")
add_equivalents([
    0x15F4, 0x163F, 0x1653, 0x1666, 0x20AC, 0x2211, 0x2208, 0x220A, 0x2A0A,
], "E")
add_equivalents([
    0x2A0D, 0x2A0E, 0x2A0F, 0x2A17,
], "F")
add_equivalents([
    0x10BA, 0x13B6,
], "G")
add_equivalents([
    0x10AC, 0x10B9,
], "H")
add_equivalents([
    0x1491, 0xa1,
], "I")
add_equivalents([
    ord('|'), ord('!'),
], "IL")
add_equivalents([
    0x148E, 0x148F, 0x14A8, 0x14A9,
], "J")
add_equivalents([
    0x221F, 0x2220,
], "L")
add_equivalents([
    0x163B, 0x164F, 0x1662, 0x2A07,
], "M")
add_equivalents([
    0x548, 0x10B6, 0x1560, 0x1561, 0x1641,
], "N")
add_equivalents([
    ord('@'),
    0x298, 0x2205, 0x2297, 0x2298, 0x229A, 0x229B, 0x229C, 0x274D, 0x102A8,
], "O")
add_equivalents([
    0xb0, 0x16dc,
], "O.")
add_equivalents([
    0x10B2, 0x15B0, 0x2117,
], "P")
add_equivalents([
    0x10AD, 0x146B, 0x15B3,
], "Q")
add_equivalents([
    0x10C1, 0x148B, 0x1586, 0x1588, 0x1589, 0xae,
], "R")
add_equivalents([
    ord('$'),
    0x283, 0x10BD, 0x10C2, 0x10FD, 0x1511, 0x1513, 0x1515, 0x165A, 0x222E, 0x2231, 0x2232, 0x2233,
], "S")
add_equivalents([
    ord('+'),
    0x22BA, 0x271D, 0x271E, 0x271F, 0x2020, 0x1F546, 0x1F547,
], "T")
add_equivalents([
    0x155E, 0x155F, 0x1640, 0x2210, 0x228C, 0x228D, 0x228E, 0x2294, 0x22D3,
], "U")
add_equivalents([
    0x10AE, 0x10C0,
], "UV")
add_equivalents([
    0x1553, 0x221A, 0x22CE, 0x2705, 0x2713, 0x2714,
], "V")
add_equivalents([
    0x460, 0x163A, 0x164E, 0x1661, 0x2A08,
], "W")
add_equivalents([
    0x2A09, 0x274C, 0x274E,
], "X")
add_equivalents([
    0x10B7, 0x10B8, 0x10BE, 0x10C4,
], "Y")
add_equivalents([
    ord('*'),
    0xb7, 0x22C6, 0x220E,
], ".")


# support all homoglyphs that we support for phone numbers
import number_homoglyphs
for digit in string.digits:
    add_equivalents((codepoint
                     for codepoint, into in number_homoglyphs.translate_dict.items()
                     if into == digit),
                    [digit])


def get_homoglyphs_by_unicode_names(*name_options):
    """
    Yields codepoints by creating possible Unicode names out of combinations of the input lists.

    None can be added to an input list to allow it to be optionally skipped.
    """
    for name in itertools.product(*name_options):
        full_name = ' '.join(filter(None, name))
        try:
            yield ord(unicodedata.normalize('NFD', unicodedata.lookup(full_name))[0])
        except KeyError:
            pass


def get_letter_homoglyphs_by_unicode_name(letter_names, alphabet_names):
    """
    Yields codepoints for a given set of letter names and alphabet names.

    None can be added to alphabet_names allow it to be optionally skipped.
    """
    for letter_name in letter_names:
        yield from get_homoglyphs_by_unicode_names(
            alphabet_names,
            [None, 'LETTER'],
            [None, 'CAPITAL', 'SMALL CAPITAL'] if letter_name[0].isupper() else [None, 'SMALL'],
            [None, 'LETTER'],
            [letter_name.upper()])


# Look up Unicode characters by alphabet names and similar
for letter in string.ascii_uppercase:
    latin_names = [letter, letter.lower()]
    if letter in LATIN_LOOKALIKE_LETTERS:
        latin_names.extend(LATIN_LOOKALIKE_LETTERS[letter])
    add_equivalents(itertools.chain(
        get_letter_homoglyphs_by_unicode_name(latin_names, [None, 'LATIN']),
        get_letter_homoglyphs_by_unicode_name(GREEK_LOOKALIKE_NAMES.get(letter, ()), [None, 'GREEK']),
        get_letter_homoglyphs_by_unicode_name(CYRILLIC_LOOKALIKE_NAMES.get(letter, ()), ['CYRILLIC'])
    ), letter)
    add_equivalent(ord(unicodedata.lookup('REGIONAL INDICATOR SYMBOL LETTER ' + letter)), letter)
    if letter in LETTER_LOOKALIKE_DIGITS:
        for digit in LETTER_LOOKALIKE_DIGITS[letter]:
            add_equivalents(CODEPOINTS_FOR_LETTER[str(digit)], letter)


def find_equivalents(char: str) -> set[str]:
    """Search for equivalents that we haven't manually defined"""
    already_defined = LETTERS_FOR_CODEPOINT.get(ord(char))
    if already_defined:
        return already_defined

    # Look for new equivalents in both official confusables and decomposed forms
    found = set()
    for confusable in UNICODE_CONFUSABLES.get(char, ()):
        found |= find_equivalents(confusable)  # recurse to apply other techniques and look up
    stripped = strip_decomposed_diacritics(char)
    if stripped != char:
        found |= find_equivalents(stripped)  # recurse to apply other techniques and look up
    if found:
        return found

    # If we've found nothing yet, maybe we have a character with a "flourish".
    # Try stripping it
    stripped = strip_flourishes(char)
    if stripped != char:
        return find_equivalents(stripped)  # recurse to apply other techniques and look up
    else:
        return found  # empty set, nothing found


NONMARK_CHAR_REGEX = regex.compile(r'[^\p{M}]', flags=REGEX_FLAGS)


def strip_decomposed_diacritics(char):
    """Removes diacritics from character by Unicode decomposition, if possible."""
    normalized = unicodedata.normalize('NFKD', char)
    if NONMARK_CHAR_REGEX.search(normalized, pos=1):
        return char
    else:
        return normalized[0]


FLOURISH_REGEX = regex.compile(r' (?:WITH .*+|BARRED|CROSSED|LONG-LEGGED)', flags=REGEX_FLAGS)


def strip_flourishes(char):
    """Tries to remove things like tails or bars from characters that aren't removed by decomposition."""
    try:
        name = unicodedata.name(char)
    except ValueError:
        return char
    normalized_name = FLOURISH_REGEX.sub('', name)
    try:
        return char if normalized_name == name else unicodedata.lookup(normalized_name)
    except KeyError:
        return char


def load_confusables() -> dict[str, set[str]]:
    """Loads the Unicode confusables.txt file as a mapping from -> set(to, ...)"""
    with open("unicode/confusables.txt", "r") as f:
        confusable_map: dict[str, set[str]] = {}
        for line in f:
            line = line.split('#', maxsplit=1)[0].strip()
            if line:
                hex_from, hex_to = map(str.split, line.split(';')[:2])
                if len(hex_from) == 1:
                    chars_to = ''.join(chr(int(h, 16)) for h in hex_to)
                    if not NONMARK_CHAR_REGEX.search(chars_to, pos=1):
                        char_from = chr(int(hex_from[0], 16))
                        confusable_map.setdefault(char_from, set()).add(chars_to[0])
        return confusable_map


UNICODE_CONFUSABLES = load_confusables()


# Fill out the remaining equivalents that we can find automatically
for codepoint in range(0x7f, 0x110000):
    if codepoint not in LETTERS_FOR_CODEPOINT:
        add_equivalents([codepoint], find_equivalents(chr(codepoint)))


# Codepoints that could stand for punctuation/separators
POSSIBLE_SEPARATOR_CODEPOINTS: set[int] = set(map(ord, string.punctuation + string.whitespace)).union([
    0x1FBF1,
])

for codepoints in CODEPOINTS_FOR_LETTER.values():
    for codepoint in codepoints:
        if regex.match(r'\W', chr(codepoint), flags=REGEX_FLAGS):
            POSSIBLE_SEPARATOR_CODEPOINTS.add(codepoint)


# Potential word separators in keyphrase and exclude check definitions
KEYPHRASE_SPACE_REGEX = r'[\s\-_]++'

# Potential word separators in exclude check regexes
SEPARATOR_REGEX = r"(?:[\W_\s]\p{M}*+)*"


# Exclusions are case-insensitive, and should match at any word-ish boundary
EXCLUDE_BOOKENDING_START = r"(?i:(?:\b|_|^)(?:"
EXCLUDE_BOOKENDING_END = r")(?:\b|_|$))"

# The default exclusion is to exclude the keyphrase itself, case-insensitively.
EXCLUDE_BOOKENDING_DEFAULT_START = r"(?i:^"
# If we've seen the entire phrase, we don't need to worry about anything on the end but combining marks
EXCLUDE_BOOKENDING_DEFAULT_END = r"(?!\p{M}))"


def build_exclude_regex(keyphrase: str, exclude: str | None) -> str:
    # Always exclude the keyphrase, regardless of changes in word breaks
    r = (EXCLUDE_BOOKENDING_DEFAULT_START
         + SEPARATOR_REGEX.join(regex.escape(w)
                                for w in split_at_possible_word_breaks(keyphrase)
                                if not regex.fullmatch(KEYPHRASE_SPACE_REGEX, w, flags=REGEX_FLAGS))
         + EXCLUDE_BOOKENDING_DEFAULT_END)
    if exclude:
        r += r"|" + EXCLUDE_BOOKENDING_START + exclude + EXCLUDE_BOOKENDING_END
    return r


def fullchars(text: str) -> Iterator[tuple[str, int]]:
    """Yields all the "full characters" of the string, plus an empty string at the end.

    A "full character" takes up one character space when rendered, thus it includes the initial character and the
    following combining characters.
    """
    fullchar = ''
    fullchar_pos = 0
    for text_pos, char in enumerate(text):
        if not unicodedata.combining(char):
            if fullchar:
                yield fullchar, fullchar_pos
            fullchar = char
            fullchar_pos = text_pos
        else:
            fullchar += char
    if fullchar:
        yield fullchar, fullchar_pos
    yield '', len(text)


class ObfuscationFinder:
    def __init__(self, *keyphrases: tuple[str, str | None]):
        self.match_trie = {}
        for keyphrase, exclude in keyphrases:
            self.add_keyphrase(keyphrase, exclude)

    def add_keyphrase(self, keyphrase, exclude='', keyphrase_name=None, letters=None):
        """Adds one keyphrase to be searched for."""
        if keyphrase_name is None:
            keyphrase_name = keyphrase.replace('_', '')
        if letters is None:
            letters = regex.sub(KEYPHRASE_SPACE_REGEX, '', keyphrase.upper(), flags=REGEX_FLAGS)
        current_trie = self.match_trie
        for letter in letters:
            current_trie = current_trie.setdefault(letter, {})
        # Store leaf nodes at '', and allow multiple keyphrases by storing them as a dict by keyphrase name
        current_trie.setdefault('', {})[keyphrase_name] = regex_compile_no_cache(
            build_exclude_regex(keyphrase, exclude), REGEX_FLAGS)
        # Catch the word even if it has an "S" after it
        if letters[-1] != 'S':
            self.add_keyphrase(keyphrase, exclude, keyphrase_name=keyphrase_name, letters=letters + 'S')

    def find_matches(self, text: str) -> Iterator[tuple[str, str, tuple[int, int]]]:
        """Searches the given text for obfuscated keyphrases.

        Yields resulting tuples of (keyphrase_name, obfuscated_text, (start_pos, end_pos))
        """
        match_trie = self.match_trie
        old_candidates: list[tuple[dict, int]] = []
        new_candidates: list[tuple[dict, int]] = []
        already_found: set[tuple[int, str]] = set()
        previous_fullchar = ''
        for fullchar, text_pos in fullchars(text):
            if is_possible_separator(fullchar):
                # optionally skip over the word separator
                new_candidates.extend(old_candidates)

            if is_possible_word_break(previous_fullchar, fullchar):
                # yield all finished current candidates
                for candidate_trie, start_pos in old_candidates:
                    keyphrases = candidate_trie.get('')
                    if keyphrases is not None:
                        candidate_text = text[start_pos:text_pos]  # up to but not including fullchar
                        for keyphrase_name, exclude_regex in keyphrases.items():
                            found_key = (start_pos, keyphrase_name)
                            if (found_key not in already_found
                                    and not exclude_regex.search(candidate_text)):
                                yield (keyphrase_name,
                                       candidate_text,
                                       (start_pos, text_pos - 1))
                                already_found.add(found_key)
                # candidate for a new word starting here
                old_candidates.append((match_trie, text_pos))

            if fullchar:
                for letter in get_possible_letters(fullchar):
                    for candidate_trie, start_pos in old_candidates:
                        candidate_trie = candidate_trie.get(letter)
                        if candidate_trie is not None:
                            new_candidate = (candidate_trie, start_pos)
                            if new_candidate not in new_candidates:
                                new_candidates.append(new_candidate)

            previous_fullchar = fullchar
            new_candidates, old_candidates = old_candidates, new_candidates
            new_candidates.clear()


def get_possible_letters(fullchar: str):
    char = fullchar[0]
    equivalents = LETTERS_FOR_CODEPOINT.get(ord(char))
    if equivalents is not None:
        yield from equivalents
        if char.upper() in equivalents:
            return
    yield char


def is_possible_word_break(previous_fullchar: str, fullchar: str) -> bool:
    if not previous_fullchar or not fullchar:
        return True
    previous_category = unicodedata.category(previous_fullchar[0])
    next_category = unicodedata.category(fullchar[0])
    if next_category == 'Ll':
        return previous_category not in ('Ll', 'Lu', 'Lt')
    elif next_category in ('Lu', 'Lt'):
        return previous_category != 'Lu'
    elif previous_category in ('Nd', 'Nl'):
        return next_category != previous_category
    else:
        return True


def is_possible_separator(fullchar: str) -> bool:
    return (bool(fullchar)
            and (ord(fullchar[0]) in POSSIBLE_SEPARATOR_CODEPOINTS
                 or not fullchar[0].isalnum()))


def split_at_possible_word_breaks(text: str) -> Iterator[str]:
    """Splits text using is_possible_word_break()"""
    previous_fullchar = ''
    word = ''
    for fullchar, _text_pos in fullchars(text):
        if word and is_possible_word_break(previous_fullchar, fullchar):
            yield word
            word = ''
        word += fullchar
        previous_fullchar = fullchar


if __name__ == '__main__':
    import sys
    import random

    def print_help():
        print("Commands:", file=sys.stderr)
        print("\tdecode TEXT\tFinds all possible decodings of TEXT", file=sys.stderr)
        print("\tunknown TEXT\tFinds all unknown characters in TEXT", file=sys.stderr)
        print("\tglyphs LETTER\tPrints all homoglyphs of LETTER", file=sys.stderr)
        print("\transom TEXT\tConverts TEXT into random homoglyphs", file=sys.stderr)
        print("\tdump\tPrints all homoglyphs in a form for diffing", file=sys.stderr)

    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print_help()
        exit(2)

    def analyze_text(text):
        letter_options = []
        unknown = set()
        for char in text:
            could_be = list(LETTERS_FOR_CODEPOINT.get(ord(char), ()))
            if char.upper() not in could_be and (char.isspace() or char in string.printable):
                could_be.append(char)
            elif not could_be and not regex.match(r'\p{M}', char, flags=REGEX_FLAGS):
                could_be.append('?')
                unknown.add(char)
            letter_options.append(could_be)
        return letter_options, unknown

    def find_possible_words(text):
        print("Analyzing %r for obfuscation" % text)
        letter_options, unknown = analyze_text(text)
        for letters in itertools.product(*letter_options):
            print("Could be " + ''.join(letters))
        print("Unknown chars: %r" % ''.join(sorted(unknown)))

    def find_unknown_chars(text):
        print("Analyzing %r for obfuscation" % text)
        letter_options, unknown = analyze_text(text)
        print("Unknown chars: %r" % ''.join(sorted(unknown)))

    cmd = sys.argv[1]
    arg = ' '.join(sys.argv[2:])
    if cmd == 'decode':
        find_possible_words(arg)
    elif cmd == 'unknown':
        find_unknown_chars(arg)
    elif cmd == 'glyphs':
        print(''.join(map(chr, CODEPOINTS_FOR_LETTER[arg.upper()])))
    elif cmd == 'ransom':
        result = ''
        for c in regex.sub(r'\p{M}++', '', unicodedata.normalize('NFD', arg), flags=REGEX_FLAGS):
            if c.upper() in CODEPOINTS_FOR_LETTER:
                result += chr(random.choice(list(CODEPOINTS_FOR_LETTER[c.upper()])))
            else:
                result += c
        print(result)
    elif cmd == 'dump':
        for letter in sorted(CODEPOINTS_FOR_LETTER.keys()):
            for codepoint in sorted(CODEPOINTS_FOR_LETTER[letter]):
                print("{} = {} ({})".format(letter, chr(codepoint), hex(codepoint)))
    else:
        print('Unknown command %r' % cmd, file=sys.stderr)
        print_help()
        exit(2)
