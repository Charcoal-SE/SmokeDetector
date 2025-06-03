# coding=utf-8
import itertools
import string
import unicodedata
from typing import Iterator

import regex

from helpers import regex_compile_no_cache

# In this module our regexes default to case-sensitive
REGEX_FLAGS = regex.U | regex.S


def add_case_insensitive_lookalikes(lookalike_map, case_insensitive_lookalike_map):
    for letter, uncased_names in case_insensitive_lookalike_map.items():
        cased_names = lookalike_map.setdefault(letter, [])
        cased_names.extend(map(str.upper, uncased_names))
        cased_names.extend(map(str.lower, uncased_names))


# Latin letters which look like others (case-sensitive)
LATIN_LOOKALIKE_LETTERS = {
    'A': ['turned alpha', 'inverted alpha'],
    'D': ['delta'],
    'F': ['long s'],
    'I': ['l', 'j', 'J', 'broken l', 'dotless i', 'dotless j'],
    'J': ['dotless j'],
    'L': ['I', 'BROKEN L', 'broken l', 'dotless i', 'dotless j'],
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


def get_homoglyphs_by_unicode_names(*name_options):
    for name in itertools.product(*name_options):
        full_name = ' '.join(filter(None, name))
        try:
            yield ord(unicodedata.normalize('NFD', unicodedata.lookup(full_name))[0])
        except KeyError:
            pass


def get_letter_homoglyphs_by_unicode_name(letter_names, alphabet_names):
    for letter_name in letter_names:
        yield from get_homoglyphs_by_unicode_names(
            alphabet_names,
            [None, 'LETTER'],
            [None, 'CAPITAL', 'SMALL CAPITAL'] if letter_name[0].isupper() else [None, 'SMALL'],
            [None, 'LETTER'],
            [letter_name.upper()])


# An "equivalent" is either a case version of the letter, or a lookalike character.
# Hex numbers are primarily used below, due to the possibility of the characters becoming corrupted when the file
# is edited in editors which don't fully support Unicode, or even just on different operating systems.
EQUIVALENT_CODEPOINT_LISTS: {str: list[int]} = {
    'A': [
        ord('@'),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x251, 0x391, 0x3b1, 0x410, 0x430, 0x13aa, 0x15c5, 0x237a, 0xa4ee, 0xff21, 0xff41, 0x102a0, 0x16f40, 0x1d400,
        0x1d41a, 0x1d434, 0x1d44e, 0x1d468, 0x1d482, 0x1d49c, 0x1d4b6, 0x1d4d0, 0x1d4ea, 0x1d504, 0x1d51e, 0x1d538,
        0x1d552, 0x1d56c, 0x1d586, 0x1d5a0, 0x1d5ba, 0x1d5d4, 0x1d5ee, 0x1d608, 0x1d622, 0x1d63c, 0x1d656, 0x1d670,
        0x1d68a, 0x1d6a8, 0x1d6c2, 0x1d6e2, 0x1d6fc, 0x1d71c, 0x1d736, 0x1d756, 0x1d770, 0x1d790, 0x1d7aa,
        # additional ones found
        0x15cb, 0x15e9, 0x2202, 0x2227, 0x22c0,
    ],
    'B': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x184, 0x392, 0x412, 0x42c, 0x13cf, 0x13f4, 0x1472, 0x15af, 0x15f7, 0x212c, 0xa4d0, 0xa7b4, 0xff22, 0x10282,
        0x102a1, 0x10301, 0x1d401, 0x1d41b, 0x1d435, 0x1d44f, 0x1d469, 0x1d483, 0x1d4b7, 0x1d4d1, 0x1d4eb, 0x1d505,
        0x1d51f, 0x1d539, 0x1d553, 0x1d56d, 0x1d587, 0x1d5a1, 0x1d5bb, 0x1d5d5, 0x1d5ef, 0x1d609, 0x1d623, 0x1d63d,
        0x1d657, 0x1d671, 0x1d68b, 0x1d6a9, 0x1d6e3, 0x1d71d, 0x1d757, 0x1d791,
        # additional ones found
        0x10a6, 0x10aa, 0x15b2, 0x15F7, 0x15F8, 0x15F9, 0x15FD, 0x15FE, 0x15FF, 0x1656, 0x1657, 0x1658, 0x165D, 0x165E,
        0x165F, 0x1669, 0x166A, 0x166B, 0x266D,
    ],
    'C': [
        ord('('), ord('['),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x3f2, 0x3f9, 0x421, 0x441, 0x13df, 0x1d04, 0x2102, 0x212d, 0x216d, 0x217d, 0x2ca4, 0x2ca5, 0xa4da, 0xabaf,
        0xff23, 0xff43, 0x102a2, 0x10302, 0x10415, 0x1043d, 0x1051c, 0x118e9, 0x118f2, 0x1d402, 0x1d41c, 0x1d436,
        0x1d450, 0x1d46a, 0x1d484, 0x1d49e, 0x1d4b8, 0x1d4d2, 0x1d4ec, 0x1d520, 0x1d554, 0x1d56e, 0x1d588, 0x1d5a2,
        0x1d5bc, 0x1d5d6, 0x1d5f0, 0x1d60a, 0x1d624, 0x1d63e, 0x1d658, 0x1d672, 0x1d68c, 0x1f74c,
        # additional ones found
        0x1455, 0x1566, 0xa2, 0xa9, 0x20AC, 0x2201, 0x2282, 0x2286, 0x228F, 0x2291, 0x22D0, 0x22E4,
    ],
    'D': [
        ord(')'),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x501, 0x13a0, 0x13e7, 0x146f, 0x15de, 0x15ea, 0x2145, 0x2146, 0x216e, 0x217e, 0xa4d2, 0xa4d3, 0x1d403, 0x1d41d,
        0x1d437, 0x1d451, 0x1d46b, 0x1d485, 0x1d49f, 0x1d4b9, 0x1d4d3, 0x1d4ed, 0x1d507, 0x1d521, 0x1d53b, 0x1d555,
        0x1d56f, 0x1d589, 0x1d5a3, 0x1d5bd, 0x1d5d7, 0x1d5f1, 0x1d60b, 0x1d625, 0x1d63f, 0x1d659, 0x1d673, 0x1d68d,
        # additional ones found
        0x146F, 0x15B1, 0x15DE, 0x15DF, 0x15E0, 0x15EA, 0x15EB, 0x15EC, 0x2202,
    ],
    'E': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x395, 0x415, 0x435, 0x4bd, 0x13ac, 0x212e, 0x212f, 0x2130, 0x2147, 0x22ff, 0x2d39, 0xa4f0, 0xab32, 0xff25,
        0xff45, 0x10286, 0x118a6, 0x118ae, 0x1d404, 0x1d41e, 0x1d438, 0x1d452, 0x1d46c, 0x1d486, 0x1d4d4, 0x1d4ee,
        0x1d508, 0x1d522, 0x1d53c, 0x1d556, 0x1d570, 0x1d58a, 0x1d5a4, 0x1d5be, 0x1d5d8, 0x1d5f2, 0x1d60c, 0x1d626,
        0x1d640, 0x1d65a, 0x1d674, 0x1d68e, 0x1d6ac, 0x1d6e6, 0x1d720, 0x1d75a, 0x1d794,
        # additional ones found
        0x15F4, 0x163F, 0x1653, 0x1666, 0x20AC, 0x2211, 0x2208, 0x220A, 0x22FF, 0x2A0A,
    ],
    'F': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x17f, 0x3dc, 0x584, 0x15b4, 0x1e9d, 0x2131, 0xa4dd, 0xa798, 0xa799, 0xab35, 0x10287, 0x102a5, 0x10525, 0x118a2,
        0x118c2, 0x1d213, 0x1d405, 0x1d41f, 0x1d439, 0x1d453, 0x1d46d, 0x1d487, 0x1d4bb, 0x1d4d5, 0x1d4ef, 0x1d509,
        0x1d523, 0x1d53d, 0x1d557, 0x1d571, 0x1d58b, 0x1d5a5, 0x1d5bf, 0x1d5d9, 0x1d5f3, 0x1d60d, 0x1d627, 0x1d641,
        0x1d65b, 0x1d675, 0x1d68f, 0x1d7ca,
        # additional ones found
        0x2A0D, 0x2A0E, 0x2A0F, 0x2A17,
    ],
    'G': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x18d, 0x261, 0x50c, 0x581, 0x13c0, 0x13f3, 0x1d83, 0x210a, 0xa4d6, 0xff47, 0x1d406, 0x1d420, 0x1d43a, 0x1d454,
        0x1d46e, 0x1d488, 0x1d4a2, 0x1d4d6, 0x1d4f0, 0x1d50a, 0x1d524, 0x1d53e, 0x1d558, 0x1d572, 0x1d58c, 0x1d5a6,
        0x1d5c0, 0x1d5da, 0x1d5f4, 0x1d60e, 0x1d628, 0x1d642, 0x1d65c, 0x1d676, 0x1d690,
        # additional ones found
        0x10BA, 0x13B6,
    ],
    'H': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x397, 0x41d, 0x4bb, 0x570, 0x13bb, 0x13c2, 0x157c, 0x210b, 0x210c, 0x210d, 0x210e, 0x2c8e, 0xa4e7, 0xff28,
        0xff48, 0x102cf, 0x1d407, 0x1d421, 0x1d43b, 0x1d46f, 0x1d489, 0x1d4bd, 0x1d4d7, 0x1d4f1, 0x1d525, 0x1d559,
        0x1d573, 0x1d58d, 0x1d5a7, 0x1d5c1, 0x1d5db, 0x1d5f5, 0x1d60f, 0x1d629, 0x1d643, 0x1d65d, 0x1d677, 0x1d691,
        0x1d6ae, 0x1d6e8, 0x1d722, 0x1d75c, 0x1d796,
        # additional ones found
        0x10AC, 0x10B9,
    ],
    'I': [
        ord('|'), ord('!'),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x31, 0x6c, 0x7c, 0x131, 0x196, 0x1c0, 0x269, 0x26a, 0x2db, 0x37a, 0x399, 0x3b9, 0x406, 0x456, 0x4c0, 0x4cf,
        0x5c0, 0x5d5, 0x5df, 0x627, 0x661, 0x6f1, 0x7ca, 0x13a5, 0x16c1, 0x2110, 0x2111, 0x2113, 0x2139, 0x2148, 0x2160,
        0x2170, 0x217c, 0x2223, 0x2373, 0x23fd, 0x2c92, 0x2d4f, 0xa4f2, 0xa647, 0xab75, 0xfe8d, 0xfe8e, 0xff29, 0xff49,
        0xff4c, 0xffe8, 0x1028a, 0x10309, 0x10320, 0x118c3, 0x16f28, 0x1d408, 0x1d422, 0x1d425, 0x1d43c, 0x1d456,
        0x1d459, 0x1d470, 0x1d48a, 0x1d48d, 0x1d4be, 0x1d4c1, 0x1d4d8, 0x1d4f2, 0x1d4f5, 0x1d526, 0x1d529, 0x1d540,
        0x1d55a, 0x1d55d, 0x1d574, 0x1d58e, 0x1d591, 0x1d5a8, 0x1d5c2, 0x1d5c5, 0x1d5dc, 0x1d5f6, 0x1d5f9, 0x1d610,
        0x1d62a, 0x1d62d, 0x1d644, 0x1d65e, 0x1d661, 0x1d678, 0x1d692, 0x1d695, 0x1d6a4, 0x1d6b0, 0x1d6ca, 0x1d6ea,
        0x1d704, 0x1d724, 0x1d73e, 0x1d75e, 0x1d778, 0x1d798, 0x1d7b2, 0x1d7cf, 0x1d7d9, 0x1d7e3, 0x1d7ed, 0x1d7f7,
        0x1e8c7, 0x1ee00, 0x1ee80, 0x1fbf1,
        # additional ones found
        0x1491, 0xa1,
    ],
    'J': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x37f, 0x3f3, 0x408, 0x458, 0x13ab, 0x148d, 0x2149, 0xa4d9, 0xa7b2, 0xff2a, 0xff4a, 0x1d409, 0x1d423, 0x1d43d,
        0x1d457, 0x1d471, 0x1d48b, 0x1d4a5, 0x1d4bf, 0x1d4d9, 0x1d4f3, 0x1d50d, 0x1d527, 0x1d541, 0x1d55b, 0x1d575,
        0x1d58f, 0x1d5a9, 0x1d5c3, 0x1d5dd, 0x1d5f7, 0x1d611, 0x1d62b, 0x1d645, 0x1d65f, 0x1d679, 0x1d693,
        # additional ones found
        0x148E, 0x148F, 0x14A8, 0x14A9,
    ],
    'K': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x39a, 0x41a, 0x13e6, 0x16d5, 0x2c94, 0xa4d7, 0xff2b, 0x10518, 0x1d40a, 0x1d424, 0x1d43e, 0x1d458, 0x1d472,
        0x1d48c, 0x1d4a6, 0x1d4c0, 0x1d4da, 0x1d4f4, 0x1d50e, 0x1d528, 0x1d542, 0x1d55c, 0x1d576, 0x1d590, 0x1d5aa,
        0x1d5c4, 0x1d5de, 0x1d5f8, 0x1d612, 0x1d62c, 0x1d646, 0x1d660, 0x1d67a, 0x1d694, 0x1d6b1, 0x1d6eb, 0x1d725,
        0x1d75f, 0x1d799,
    ],
    'L': [
        ord('|'), ord('!'),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x31, 0x49, 0x7c, 0x196, 0x1c0, 0x399, 0x406, 0x4c0, 0x5c0, 0x5d5, 0x5df, 0x627, 0x661, 0x6f1, 0x7ca, 0x13de,
        0x14aa, 0x16c1, 0x2110, 0x2111, 0x2112, 0x2113, 0x2160, 0x216c, 0x217c, 0x2223, 0x23fd, 0x2c92, 0x2cd0, 0x2d4f,
        0xa4e1, 0xa4f2, 0xfe8d, 0xfe8e, 0xff29, 0xff4c, 0xffe8, 0x1028a, 0x10309, 0x10320, 0x1041b, 0x10526, 0x118a3,
        0x118b2, 0x16f16, 0x16f28, 0x1d22a, 0x1d408, 0x1d40b, 0x1d425, 0x1d43c, 0x1d43f, 0x1d459, 0x1d470, 0x1d473,
        0x1d48d, 0x1d4c1, 0x1d4d8, 0x1d4db, 0x1d4f5, 0x1d50f, 0x1d529, 0x1d540, 0x1d543, 0x1d55d, 0x1d574, 0x1d577,
        0x1d591, 0x1d5a8, 0x1d5ab, 0x1d5c5, 0x1d5dc, 0x1d5df, 0x1d5f9, 0x1d610, 0x1d613, 0x1d62d, 0x1d644, 0x1d647,
        0x1d661, 0x1d678, 0x1d67b, 0x1d695, 0x1d6b0, 0x1d6ea, 0x1d724, 0x1d75e, 0x1d798, 0x1d7cf, 0x1d7d9, 0x1d7e3,
        0x1d7ed, 0x1d7f7, 0x1e8c7, 0x1ee00, 0x1ee80, 0x1fbf1,
        # additional ones found
        0x221F, 0x2220,
    ],
    'M': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x39c, 0x3fa, 0x41c, 0x13b7, 0x15f0, 0x16d6, 0x2133, 0x216f, 0x217f, 0x2c98, 0xa4df, 0xff2d, 0x102b0, 0x10311,
        0x11700, 0x118e3, 0x1d40c, 0x1d426, 0x1d440, 0x1d45a, 0x1d474, 0x1d48e, 0x1d4c2, 0x1d4dc, 0x1d4f6, 0x1d510,
        0x1d52a, 0x1d544, 0x1d55e, 0x1d578, 0x1d592, 0x1d5ac, 0x1d5c6, 0x1d5e0, 0x1d5fa, 0x1d614, 0x1d62e, 0x1d648,
        0x1d662, 0x1d67c, 0x1d696, 0x1d6b3, 0x1d6ed, 0x1d727, 0x1d761, 0x1d79b,
        # additional ones found
        0x163B, 0x164F, 0x1662, 0x2A07,
    ],
    'N': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x39d, 0x578, 0x57c, 0x2115, 0x2c9a, 0xa4e0, 0xff2e, 0x10513, 0x1d40d, 0x1d427, 0x1d441, 0x1d45b, 0x1d475,
        0x1d48f, 0x1d4a9, 0x1d4c3, 0x1d4dd, 0x1d4f7, 0x1d511, 0x1d52b, 0x1d55f, 0x1d579, 0x1d593, 0x1d5ad, 0x1d5c7,
        0x1d5e1, 0x1d5fb, 0x1d615, 0x1d62f, 0x1d649, 0x1d663, 0x1d67d, 0x1d697, 0x1d6b4, 0x1d6ee, 0x1d728, 0x1d762,
        0x1d79c,
        # additional ones found
        0x10B6, 0x144E, 0x1560, 0x1561, 0x1641, 0x22C2, 0x2229,
    ],
    'O': [
        ord('@'),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x30, 0x39f, 0x3bf, 0x3c3, 0x41e, 0x43e, 0x555, 0x585, 0x5e1, 0x647, 0x665, 0x6be, 0x6c1, 0x6d5, 0x6f5, 0x7c0,
        0x966, 0x9e6, 0xa66, 0xae6, 0xb20, 0xb66, 0xbe6, 0xc02, 0xc66, 0xc82, 0xce6, 0xd02, 0xd20, 0xd66, 0xd82, 0xe50,
        0xed0, 0x101d, 0x1040, 0x10ff, 0x12d0, 0x1d0f, 0x1d11, 0x2134, 0x2c9e, 0x2c9f, 0x2d54, 0x3007, 0xa4f3, 0xab3d,
        0xfba6, 0xfba7, 0xfba8, 0xfba9, 0xfbaa, 0xfbab, 0xfbac, 0xfbad, 0xfee9, 0xfeea, 0xfeeb, 0xfeec, 0xff2f, 0xff4f,
        0x10292, 0x102ab, 0x10404, 0x1042c, 0x104c2, 0x104ea, 0x10516, 0x114d0, 0x118b5, 0x118c8, 0x118d7, 0x118e0,
        0x1d40e, 0x1d428, 0x1d442, 0x1d45c, 0x1d476, 0x1d490, 0x1d4aa, 0x1d4de, 0x1d4f8, 0x1d512, 0x1d52c, 0x1d546,
        0x1d560, 0x1d57a, 0x1d594, 0x1d5ae, 0x1d5c8, 0x1d5e2, 0x1d5fc, 0x1d616, 0x1d630, 0x1d64a, 0x1d664, 0x1d67e,
        0x1d698, 0x1d6b6, 0x1d6d0, 0x1d6d4, 0x1d6f0, 0x1d70a, 0x1d70e, 0x1d72a, 0x1d744, 0x1d748, 0x1d764, 0x1d77e,
        0x1d782, 0x1d79e, 0x1d7b8, 0x1d7bc, 0x1d7ce, 0x1d7d8, 0x1d7e2, 0x1d7ec, 0x1d7f6, 0x1ee24, 0x1ee64, 0x1ee84,
        0x1fbf0,
        # additional ones found
        0x298, 0x2205, 0x2295, 0x2296, 0x2297, 0x2298, 0x2299, 0x229A, 0x229B, 0x229C, 0x229D, 0x2A00, 0x2A01, 0x2A02,
        0x274D,
    ],
    'P': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x3a1, 0x3c1, 0x3f1, 0x420, 0x440, 0x13e2, 0x146d, 0x2119, 0x2374, 0x2ca2, 0x2ca3, 0xa4d1, 0xff30, 0xff50,
        0x10295, 0x1d40f, 0x1d429, 0x1d443, 0x1d45d, 0x1d477, 0x1d491, 0x1d4ab, 0x1d4c5, 0x1d4df, 0x1d4f9, 0x1d513,
        0x1d52d, 0x1d561, 0x1d57b, 0x1d595, 0x1d5af, 0x1d5c9, 0x1d5e3, 0x1d5fd, 0x1d617, 0x1d631, 0x1d64b, 0x1d665,
        0x1d67f, 0x1d699, 0x1d6b8, 0x1d6d2, 0x1d6e0, 0x1d6f2, 0x1d70c, 0x1d71a, 0x1d72c, 0x1d746, 0x1d754, 0x1d766,
        0x1d780, 0x1d78e, 0x1d7a0, 0x1d7ba, 0x1d7c8,
        # additional ones found
        0x10B2, 0x146D, 0x15B0, 0x2117,
    ],
    'Q': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x51b, 0x563, 0x566, 0x211a, 0x2d55, 0x1d410, 0x1d42a, 0x1d444, 0x1d45e, 0x1d478, 0x1d492, 0x1d4ac, 0x1d4c6,
        0x1d4e0, 0x1d4fa, 0x1d514, 0x1d52e, 0x1d562, 0x1d57c, 0x1d596, 0x1d5b0, 0x1d5ca, 0x1d5e4, 0x1d5fe, 0x1d618,
        0x1d632, 0x1d64c, 0x1d666, 0x1d680, 0x1d69a,
        # additional ones found
        0x10AD, 0x146B, 0x15B3
    ],
    'R': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x1a6, 0x433, 0x13a1, 0x13d2, 0x1587, 0x1d26, 0x211b, 0x211c, 0x211d, 0x2c85, 0xa4e3, 0xab47, 0xab48, 0xab81,
        0x104b4, 0x16f35, 0x1d216, 0x1d411, 0x1d42b, 0x1d445, 0x1d45f, 0x1d479, 0x1d493, 0x1d4c7, 0x1d4e1, 0x1d4fb,
        0x1d52f, 0x1d563, 0x1d57d, 0x1d597, 0x1d5b1, 0x1d5cb, 0x1d5e5, 0x1d5ff, 0x1d619, 0x1d633, 0x1d64d, 0x1d667,
        0x1d681, 0x1d69b,
        # additional ones found
        0x10C1, 0x148B, 0x1586, 0x1587, 0x1588, 0x1589, 0xae,
    ],
    'S': [
        ord('$'),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x1bd, 0x405, 0x455, 0x54f, 0x13d5, 0x13da, 0xa4e2, 0xa731, 0xabaa, 0xff33, 0xff53, 0x10296, 0x10420, 0x10448,
        0x118c1, 0x16f3a, 0x1d412, 0x1d42c, 0x1d446, 0x1d460, 0x1d47a, 0x1d494, 0x1d4ae, 0x1d4c8, 0x1d4e2, 0x1d4fc,
        0x1d516, 0x1d530, 0x1d54a, 0x1d564, 0x1d57e, 0x1d598, 0x1d5b2, 0x1d5cc, 0x1d5e6, 0x1d600, 0x1d61a, 0x1d634,
        0x1d64e, 0x1d668, 0x1d682, 0x1d69c,
        # additional ones found
        0x10BD, 0x10C2, 0x10FD, 0x1511, 0x1513, 0x1515, 0x165A, 0x222B, 0x222E, 0x2231, 0x2232, 0x2233,
    ],
    'T': [
        ord('+'),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x3a4, 0x422, 0x13a2, 0x22a4, 0x27d9, 0x2ca6, 0xa4d4, 0xff34, 0x10297, 0x102b1, 0x10315, 0x118bc, 0x16f0a,
        0x1d413, 0x1d42d, 0x1d447, 0x1d461, 0x1d47b, 0x1d495, 0x1d4af, 0x1d4c9, 0x1d4e3, 0x1d4fd, 0x1d517, 0x1d531,
        0x1d54b, 0x1d565, 0x1d57f, 0x1d599, 0x1d5b3, 0x1d5cd, 0x1d5e7, 0x1d601, 0x1d61b, 0x1d635, 0x1d64f, 0x1d669,
        0x1d683, 0x1d69d, 0x1d6bb, 0x1d6f5, 0x1d72f, 0x1d769, 0x1d7a3, 0x1f768,
        # additional ones found
        0x22BA, 0x271D, 0x271E, 0x271F, 0x2020, 0x1F546, 0x1F547,
    ],
    'U': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x28b, 0x3c5, 0x54d, 0x57d, 0x1200, 0x144c, 0x1d1c, 0x222a, 0x22c3, 0xa4f4, 0xa79f, 0xab4e, 0xab52, 0x104ce,
        0x104f6, 0x118b8, 0x118d8, 0x16f42, 0x1d414, 0x1d42e, 0x1d448, 0x1d462, 0x1d47c, 0x1d496, 0x1d4b0, 0x1d4ca,
        0x1d4e4, 0x1d4fe, 0x1d518, 0x1d532, 0x1d54c, 0x1d566, 0x1d580, 0x1d59a, 0x1d5b4, 0x1d5ce, 0x1d5e8, 0x1d602,
        0x1d61c, 0x1d636, 0x1d650, 0x1d66a, 0x1d684, 0x1d69e, 0x1d6d6, 0x1d710, 0x1d74a, 0x1d784, 0x1d7be,
        # additional ones found
        0x10AE, 0x10C0, 0x144C, 0x155E, 0x155F, 0x1640, 0x2210, 0x22C1, 0x22C3, 0x228C, 0x228D, 0x228E, 0x2294,
        0x22D3, 0x222A, 0x2A03, 0x2A04, 0x2A06,
    ],
    'V': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x3bd, 0x474, 0x475, 0x5d8, 0x667, 0x6f7, 0x13d9, 0x142f, 0x1d20, 0x2164, 0x2174, 0x2228, 0x22c1, 0x2d38,
        0xa4e6, 0xa6df, 0xaba9, 0xff56, 0x1051d, 0x11706, 0x118a0, 0x118c0, 0x16f08, 0x1d20d, 0x1d415, 0x1d42f, 0x1d449,
        0x1d463, 0x1d47d, 0x1d497, 0x1d4b1, 0x1d4cb, 0x1d4e5, 0x1d4ff, 0x1d519, 0x1d533, 0x1d54d, 0x1d567, 0x1d581,
        0x1d59b, 0x1d5b5, 0x1d5cf, 0x1d5e9, 0x1d603, 0x1d61d, 0x1d637, 0x1d651, 0x1d66b, 0x1d685, 0x1d69f, 0x1d6ce,
        0x1d708, 0x1d742, 0x1d77c, 0x1d7b6,
        # additional ones found
        0x10AE, 0x10C0, 0x1553, 0x22C3, 0x221A, 0x22CE, 0x2705, 0x2713, 0x2714,
    ],
    'W': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x26f, 0x461, 0x51c, 0x51d, 0x561, 0x13b3, 0x13d4, 0x1d21, 0xa4ea, 0xab83, 0x1170a, 0x1170e, 0x1170f, 0x118e6,
        0x118ef, 0x1d416, 0x1d430, 0x1d44a, 0x1d464, 0x1d47e, 0x1d498, 0x1d4b2, 0x1d4cc, 0x1d4e6, 0x1d500, 0x1d51a,
        0x1d534, 0x1d54e, 0x1d568, 0x1d582, 0x1d59c, 0x1d5b6, 0x1d5d0, 0x1d5ea, 0x1d604, 0x1d61e, 0x1d638, 0x1d652,
        0x1d66c, 0x1d686, 0x1d6a0,
        # additional ones found
        0x15EF, 0x163A, 0x164E, 0x1661, 0x2A08,
    ],
    'X': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0xd7, 0x3a7, 0x425, 0x445, 0x1541, 0x157d, 0x166d, 0x166e, 0x16b7, 0x2169, 0x2179, 0x2573, 0x292b, 0x292c,
        0x2a2f, 0x2cac, 0x2d5d, 0xa4eb, 0xa7b3, 0xff38, 0xff58, 0x10290, 0x102b4, 0x10317, 0x10322, 0x10527, 0x118ec,
        0x1d417, 0x1d431, 0x1d44b, 0x1d465, 0x1d47f, 0x1d499, 0x1d4b3, 0x1d4cd, 0x1d4e7, 0x1d501, 0x1d51b, 0x1d535,
        0x1d54f, 0x1d569, 0x1d583, 0x1d59d, 0x1d5b7, 0x1d5d1, 0x1d5eb, 0x1d605, 0x1d61f, 0x1d639, 0x1d653, 0x1d66d,
        0x1d687, 0x1d6a1, 0x1d6be, 0x1d6f8, 0x1d732, 0x1d76c, 0x1d7a6,
        # additional ones found
        0x166D, 0x2A09, 0x2A2F, 0x2215, 0x2216, 0x2217, 0x2218, 0x274C, 0x274E,
    ],
    'Y': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x263, 0x28f, 0x3a5, 0x3b3, 0x3d2, 0x423, 0x443, 0x4ae, 0x4af, 0x10e7, 0x13a9, 0x13bd, 0x1d8c, 0x1eff, 0x213d,
        0x2ca8, 0xa4ec, 0xab5a, 0xff39, 0xff59, 0x102b2, 0x118a4, 0x118dc, 0x16f43, 0x1d418, 0x1d432, 0x1d44c, 0x1d466,
        0x1d480, 0x1d49a, 0x1d4b4, 0x1d4ce, 0x1d4e8, 0x1d502, 0x1d51c, 0x1d536, 0x1d550, 0x1d56a, 0x1d584, 0x1d59e,
        0x1d5b8, 0x1d5d2, 0x1d5ec, 0x1d606, 0x1d620, 0x1d63a, 0x1d654, 0x1d66e, 0x1d688, 0x1d6a2, 0x1d6bc, 0x1d6c4,
        0x1d6f6, 0x1d6fe, 0x1d730, 0x1d738, 0x1d76a, 0x1d772, 0x1d7a4, 0x1d7ac,
        # additional ones found
        0x10B7, 0x10B8, 0x10BE, 0x10C4, 0xa5,
    ],
    'Z': [
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x396, 0x13c3, 0x1d22, 0x2124, 0x2128, 0xa4dc, 0xab93, 0xff3a, 0x102f5, 0x118a9, 0x118c4, 0x118e5, 0x1d419,
        0x1d433, 0x1d44d, 0x1d467, 0x1d481, 0x1d49b, 0x1d4b5, 0x1d4cf, 0x1d4e9, 0x1d503, 0x1d537, 0x1d56b, 0x1d585,
        0x1d59f, 0x1d5b9, 0x1d5d3, 0x1d5ed, 0x1d607, 0x1d621, 0x1d63b, 0x1d655, 0x1d66f, 0x1d689, 0x1d6a3, 0x1d6ad,
        0x1d6e7, 0x1d721, 0x1d75b, 0x1d795,
    ],

    '.': [
        ord('*'),
        # confusables from https://util.unicode.org/UnicodeJsps/confusables.jsp
        0x660, 0x6f0, 0x701, 0x702, 0x2024, 0xa4f8, 0xa60e, 0x10a50, 0x1d16d,
    ],
}


CODEPOINTS_FOR_LETTER: dict[str, set[int]] = {}

LETTERS_FOR_CODEPOINT: dict[int, set[str]] = {}


def add_equivalent(from_codepoint: int, to_letter: str):
    to_letter = to_letter.upper()
    LETTERS_FOR_CODEPOINT.setdefault(from_codepoint, set()).add(to_letter)
    CODEPOINTS_FOR_LETTER.setdefault(to_letter, set()).add(from_codepoint)


for letter, codepoints in EQUIVALENT_CODEPOINT_LISTS.items():
    add_equivalent(ord(letter), letter)
    for codepoint in codepoints:
        add_equivalent(codepoint, letter)

import number_homoglyphs
for digit in string.digits:
    add_equivalent(ord(digit), digit)
    for codepoint, into in number_homoglyphs.translate_dict.items():
        if into == digit:
            add_equivalent(codepoint, digit)

# add Unicode lookups to EQUIVALENTS_CODEPOINTS
for letter in string.ascii_uppercase:
    latin_names = [letter, letter.lower()]
    if letter in LATIN_LOOKALIKE_LETTERS:
        latin_names.extend(LATIN_LOOKALIKE_LETTERS[letter])
    for codepoint in itertools.chain(
        get_letter_homoglyphs_by_unicode_name(latin_names, [None, 'LATIN']),
        get_letter_homoglyphs_by_unicode_name(GREEK_LOOKALIKE_NAMES.get(letter, ()), [None, 'GREEK']),
        get_letter_homoglyphs_by_unicode_name(CYRILLIC_LOOKALIKE_NAMES.get(letter, ()), ['CYRILLIC'])
    ):
        add_equivalent(codepoint, letter)
    add_equivalent(ord(unicodedata.lookup('REGIONAL INDICATOR SYMBOL LETTER ' + letter)), letter)
    if letter in LETTER_LOOKALIKE_DIGITS:
        for digit in LETTER_LOOKALIKE_DIGITS[letter]:
            for codepoint in CODEPOINTS_FOR_LETTER[str(digit)]:
                add_equivalent(codepoint, letter)

for codepoint in range(0x7f, 0x110000):
    if codepoint in LETTERS_FOR_CODEPOINT:
        continue
    char = chr(codepoint)
    normalized = unicodedata.normalize('NFKD', char)
    if normalized == char:
        if unicodedata.category(char)[0] == 'C':
            continue
        try:
            name = unicodedata.name(char)
        except ValueError:
            continue
        normalized_name = regex.sub(r' (?:BARRED|CROSSED|LONG-LEGGED|WITH .*)', '', name, flags=REGEX_FLAGS)
        if normalized_name == name:
            continue
        try:
            normalized = unicodedata.lookup(normalized_name)
        except KeyError:
            continue
    if len(normalized) > 1:
        if any(unicodedata.category(c)[0] != 'M' for c in normalized[1:]):
            continue
    for letter in LETTERS_FOR_CODEPOINT.get(ord(normalized[0]), ()):
        add_equivalent(codepoint, letter)


# Codepoints that could stand for either letters, or as punctuation/separators
POSSIBLE_SEPARATOR_CODEPOINTS: set[int] = set()

for letter, codepoints in CODEPOINTS_FOR_LETTER.items():
    for codepoint in codepoints:
        if regex.match(r'\W', chr(codepoint), flags=REGEX_FLAGS) and codepoint not in POSSIBLE_SEPARATOR_CODEPOINTS:
            POSSIBLE_SEPARATOR_CODEPOINTS.add(codepoint)


# Potential word separators in keyphrase and exclude check definitions
KEYPHRASE_SPACE_REGEX = r'[\s\-_]++'

# Potential word separators in exclude check regexes
SEPARATOR_REGEX = r"(?:[\W_\s][\W_\s\p{Mn}]*+)?+"


def build_exclude_regex(keyphrase: str, exclude: str | None) -> str:
    # Always exclude the keyphrase, regardless of changes in word breaks
    r = SEPARATOR_REGEX.join(map(regex.escape, regex.split(KEYPHRASE_SPACE_REGEX, keyphrase, flags=REGEX_FLAGS)))
    if exclude:
        r += r"|" + exclude
    return r"(?i:\b(?:" + r + r")s?\b)"


class ObfuscationFinder:
    def __init__(self, *keyphrases: (str, str | None)):
        self.match_trie = {}
        for keyphrase, exclude in keyphrases:
            self.add_keyphrase(keyphrase, exclude)

    def add_keyphrase(self, keyphrase, exclude='', keyphrase_name=None):
        """Adds one keyphrase to be searched for."""
        if keyphrase_name is None:
            keyphrase_name = keyphrase.replace('_', '')
        letters = regex.sub(KEYPHRASE_SPACE_REGEX, '', keyphrase.upper(), flags=REGEX_FLAGS)
        current_trie = self.match_trie
        for letter in letters:
            current_trie = current_trie.setdefault(letter, {})
        current_trie.setdefault('', {})[keyphrase_name] = regex_compile_no_cache(build_exclude_regex(keyphrase, exclude),
                                                                                 REGEX_FLAGS)
        if keyphrase[-1].upper() != 'S':
            self.add_keyphrase(keyphrase + '_S', exclude, keyphrase_name=keyphrase_name)

    def find_matches(self, text: str) -> Iterator[tuple[str, str, tuple[int, int]]]:
        """Searches the given text for obfuscated keyphrases.

        Yields resulting tuples of (keyphrase_name, obfuscated_text, (start_pos, end_pos))
        """
        match_trie = self.match_trie
        old_candidates: list[tuple[dict, str, int]] = []
        new_candidates: list[tuple[dict, str, int]] = []
        already_found: set[tuple[int, str]] = set()
        previous_char = ''
        for text_pos, char in enumerate(itertools.chain(*text, ('',))):
            if is_possible_word_end(previous_char, char):
                # yield all finished current candidates
                for candidate_trie, candidate_text, start_pos in old_candidates:
                    keyphrases = candidate_trie.get('')
                    if keyphrases is not None:
                        for keyphrase_name, exclude_regex in keyphrases.items():
                            if ((start_pos, keyphrase_name) not in already_found
                                    and not exclude_regex.search(candidate_text)):
                                yield (keyphrase_name,
                                       candidate_text,
                                       (start_pos, text_pos - 1))
                                already_found.add((start_pos, keyphrase_name))

            if is_possible_separator(previous_char, char):
                # optionally skip over the word separator
                for candidate_trie, candidate_text, start_pos in old_candidates:
                    new_candidates.append((candidate_trie, candidate_text + char, start_pos))

            if is_possible_word_start(previous_char, char):
                old_candidates.append((match_trie, '', text_pos))

            if char:
                for letter in get_possible_letters(char):
                    for candidate_trie, candidate_text, start_pos in old_candidates:
                        candidate_trie = candidate_trie.get(letter)
                        if candidate_trie is not None:
                            new_candidate = (candidate_trie, candidate_text + char, start_pos)
                            if new_candidate not in new_candidates:
                                new_candidates.append(new_candidate)

            previous_char = char
            new_candidates, old_candidates = old_candidates, new_candidates
            new_candidates.clear()


def get_possible_letters(char: str):
    equivalents = LETTERS_FOR_CODEPOINT.get(ord(char))
    if equivalents is not None:
        yield from equivalents
        if char.upper() in equivalents:
            return
    yield char


def is_possible_word_start(previous_char: str, char: str) -> bool:
    return not regex.match(r'\w', previous_char, flags=REGEX_FLAGS)


def is_possible_word_end(previous_char: str, char: str) -> bool:
    return not regex.match(r'\w', char, flags=REGEX_FLAGS)


def is_possible_separator(previous_char: str, char: str) -> bool:
    return char and (ord(char) in POSSIBLE_SEPARATOR_CODEPOINTS or not char.isalnum())


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


if __name__ == '__main__':
    import sys
    import random

    def print_help():
        print("Commands:", file=sys.stderr)
        print("\tdecode TEXT\tFinds all possible decodings of TEXT", file=sys.stderr)
        print("\tunknown TEXT\tFinds all unknown characters in TEXT", file=sys.stderr)
        print("\tglyphs LETTER\tPrints all homoglyphs of LETTER", file=sys.stderr)
        print("\transom TEXT\tConverts TEXT into random homoglyphs", file=sys.stderr)

    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print_help()
        exit(2)

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
    else:
        print('Unknown command %r' % cmd, file=sys.stderr)
        print_help()
        exit(2)
