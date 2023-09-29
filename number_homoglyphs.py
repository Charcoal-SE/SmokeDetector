# coding=utf-8
import regex

"""
Convert number homoglyphs to ASCII numbers
"""

# The initial values for the number homoglyphs were obtained from
# https://github.com/codebox/homoglyph/blob/master/raw_data/char_codes.txt
# which is Copyright (c) 2015 Rob Dawson under an MIT license:
# https://github.com/codebox/homoglyph/blob/master/LICENSE

# Hex numbers are primarily used below, due to the possibility of the characters becoming corrupted when the file
# is edited in editors which don't fully support Unicode, or even just on different operating systems.
equivalents = {
    # A quick look through Windows 10 Arial indicates this is definitely not all inclusive. I've added
    # a few from that, but a more exhaustive search would be beneficial.
    # The properties are what will be transformed into
    '0': [0x4f, 0x6f, 0xd8, 0x39f, 0x3bf, 0x3c3, 0x41e, 0x43e, 0x555, 0x585, 0x5e1, 0x647, 0x665, 0x6be, 0x6c1, 0x6d5,
          0x6f5, 0x7c0, 0x966, 0x9e6, 0xa66, 0xae6, 0xb20, 0xb66, 0xbe6, 0xc02, 0xc66, 0xc82, 0xce6, 0xd02, 0xd20,
          0xd66, 0xd82, 0xe50, 0xed0, 0x101d, 0x1040, 0x10ff, 0x12d0, 0x1d0f, 0x1d11, 0x2134, 0x2c9e, 0x2c9f,
          0x2d54, 0x3007, 0xa4f3, 0xab3d, 0xfba6, 0xfba7, 0xfba8, 0xfba9, 0xfbaa, 0xfbab, 0xfbac, 0xfbad, 0xfee9,
          0xfeea, 0xfeeb, 0xfeec, 0xff10, 0xff2f, 0xff4f, 0x10292, 0x102ab, 0x10404, 0x1042c, 0x104c2, 0x104ea,
          0x10516, 0x114d0, 0x118b5, 0x118c8, 0x118d7, 0x118e0, 0x1d40e, 0x1d428, 0x1d442, 0x1d45c, 0x1d476,
          0x1d490, 0x1d4aa, 0x1d4de, 0x1d4f8, 0x1d512, 0x1d52c, 0x1d546, 0x1d560, 0x1d57a, 0x1d594, 0x1d5ae,
          0x1d5c8, 0x1d5e2, 0x1d5fc, 0x1d616, 0x1d630, 0x1d64a, 0x1d664, 0x1d67e, 0x1d698, 0x1d6b6, 0x1d6d0,
          0x1d6d4, 0x1d6f0, 0x1d70a, 0x1d70e, 0x1d72a, 0x1d744, 0x1d748, 0x1d764, 0x1d77e, 0x1d782, 0x1d79e,
          0x1d7b8, 0x1d7bc, 0x1d7ce, 0x1d7d8, 0x1d7e2, 0x1d7ec, 0x1d7f6, 0x1ee24, 0x1ee64, 0x1ee84, 0x1fbf0,
          0x24ea, 0x24ff, 0x1f100, 0x1f10b, 0x1f10c, 0x104a0, 0x110f0, 0x11136, 0x1e950, 0x2205],
    '1': [0x49, 0x6c, 0x7c, 0x196, 0x1c0, 0x399, 0x406, 0x4c0, 0x5c0, 0x5d5, 0x5df, 0x627, 0x661, 0x6f1, 0x7ca,
          0x16c1, 0x2110, 0x2111, 0x2113, 0x2160, 0x217c, 0x2223, 0x23fd, 0x2c92, 0x2d4f, 0xa4f2, 0xfe8d, 0xfe8e,
          0xff11, 0xff29, 0xff4c, 0xffe8, 0x1028a, 0x10309, 0x10320, 0x16f28, 0x1d408, 0x1d425, 0x1d43c, 0x1d459,
          0x1d470, 0x1d48d, 0x1d4c1, 0x1d4d8, 0x1d4f5, 0x1d529, 0x1d540, 0x1d55d, 0x1d574, 0x1d591, 0x1d5a8,
          0x1d5c5, 0x1d5dc, 0x1d5f9, 0x1d610, 0x1d62d, 0x1d644, 0x1d661, 0x1d678, 0x1d695, 0x1d6b0, 0x1d6ea,
          0x1d724, 0x1d75e, 0x1d798, 0x1d7cf, 0x1d7d9, 0x1d7e3, 0x1d7ed, 0x1d7f7, 0x1e8c7, 0x1ee00, 0x1ee80,
          0x1fbf1, 0xb9, 0x215f, 0x2160, 0x2170, 0x217c, 0x1e951, 0x1e952],
    '2': [0x1a7, 0x3e8, 0x14bf, 0xa644, 0xa6ef, 0xa75a, 0xff12, 0x1d7d0, 0x1d7da, 0x1d7e4, 0x1d7ee, 0x1d7f8,
          0x1fbf2, 0x577, 0xb2],
    '3': [0x1b7, 0x21c, 0x417, 0x4e0, 0x2ccc, 0xa76a, 0xa7ab, 0xff13, 0x118ca, 0x16f3b, 0x1d206, 0x1d7d1,
          0x1d7db, 0x1d7e5, 0x1d7ef, 0x1d7f9, 0x1fbf3, 0x1d08, 0x1d1f, 0x1d23, 0x1d32, 0x1d94, 0x1d9a, 0x1dbe,
          0x4de, 0x4df, 0x4e0, 0x4e1, 0x4ec, 0x4ed, 0x498, 0x499, 0x417, 0x3f6, 0xb3],
    '4': [0x13ce, 0xff14, 0x118af, 0x1d7d2, 0x1d7dc, 0x1d7e6, 0x1d7f0, 0x1d7fa, 0x1fbf4, 0xa78d, 0x4b6, 0x4b7,
          0x4cb, 0x4cc],
    '5': [0x1bc, 0xff15, 0x118bb, 0x1d7d3, 0x1d7dd, 0x1d7e7, 0x1d7f1, 0x1d7fb, 0x1fbf5, 0x405, 'S'],
    '6': [0x431, 0x13ee, 0x2cd2, 0xff16, 0x118d5, 0x1d7d4, 0x1d7de, 0x1d7e8, 0x1d7f2, 0x1d7fc, 0x1fbf6],
    '7': [0xff17, 0x104d2, 0x118c6, 0x1d212, 0x1d7d5, 0x1d7df, 0x1d7e9, 0x1d7f3, 0x1d7fd, 0x1fbf7],
    '8': [0x222, 0x223, 0x9ea, 0xa6a, 0xb03, 0xff18, 0x1031a, 0x1d7d6, 0x1d7e0, 0x1d7ea, 0x1d7f4, 0x1d7fe,
          0x1e8cb, 0x1fbf8],
    '9': [0x9ed, 0xa67, 0xb68, 0xd6d, 0x2cca, 0xa76e, 0xff19, 0x118ac, 0x118cc, 0x118d6, 0x1d7d7, 0x1d7e1,
          0x1d7eb, 0x1d7f5, 0x1d7ff, 0x1fbf9, 0x1113d],
    '03': [0x2189],
    '11': [0x2161, 0x2171],
    '12': [0xbd],
    '13': [0x2153],
    '14': [0xbc],
    '15': [0x2155],
    '16': [0x2159],
    '17': [0x2150],
    '18': [0x215b],
    '19': [0x2151],
    '23': [0x2154],
    '25': [0x2156],
    '34': [0xbe],
    '35': [0x2157],
    '38': [0x215c],
    '45': [0x2158],
    '56': [0x215a],
    '58': [0x215d],
    '78': [0x215e],
    '110': [0x2152],
    '111': [0x2162, 0x2172],

}

sequences = [
    # (number_start, number_end, number_increment, code_point_start, code_point_increment)
    # circled numbers:
    # zero = 0x24ea is handled in the zero number equivalent
    # circled 1 through 20 with code points starting at 0x2460 through 0x2473
    # '⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
    (1, 20, 1, 0x2460, 1),
    # circled: 21 -> 35, start 0x3251
    # '㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟'
    (21, 35, 1, 0x3251, 1),
    # circled: 36 -> 50, start 0x32B1
    # '㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿'
    (36, 50, 1, 0x32B1, 1),
    # DINGBAT CIRCLED SANS-SERIF: 1 -> 10, start 0x2780
    # 0 = 0x1F10B is handled in the zero number equivalent
    # '➀➁➂➃➄➅➆➇➈➉'
    (1, 10, 1, 0x2780, 1),
    # parenthesized: 1 -> 20, start 0x2474
    # '⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿⒀⒁⒂⒃⒄⒅⒆⒇'
    (1, 20, 1, 0x2474, 1),
    # dot following: 1 -> 20, start 0x2488
    # 0 = 0x1F100 is handled in the zero number equivalent
    # '⒈⒉⒊⒋⒌⒍⒎⒏⒐⒑⒒⒓⒔⒕⒖⒗⒘⒙⒚⒛'
    (1, 20, 1, 0x2488, 1),
    # negative circled: 11 -> 20, start 0x24EB
    # 0 = 0x24FF is handled in the zero number equivalent
    # ''
    (11, 20, 1, 0x24EB, 1),
    # double circled: 1 -> 10, start 0x24F5
    # '⓵⓶⓷⓸⓹⓺⓻⓼⓽⓾'
    (1, 10, 1, 0x24F5, 1),
    # on black square, 10's: 10 -> 80, start 0x3248
    # '㉈㉉㉊㉋㉌㉍㉎㉏'
    (10, 80, 10, 0x3248, 1),
    # CIRCLED IDEOGRAPH: 1 -> 10, start 0x3280
    # '㊀㊁㊂㊃㊄㊅㊆㊇㊈㊉'
    (1, 10, 1, 0x3280, 1),
    # Superscript: 0 -> 9, start 0x2070
    # '⁰¹²³⁴⁵⁶⁷⁸⁹',
    # 1, 2, & 3 are not necessarily available. They can be found at 0xb9, 0xb2, 0xb3, which are handled within
    # number_equivalents.
    (0, 9, 1, 0x2070, 1),
    # Subscript: 0 -> 9, start 0x2080
    # '₀₁₂₃₄₅₆₇₈₉',
    (0, 9, 1, 0x2080, 1),
    # DINGBAT NEGATIVE CIRCLED: 1 -> 10, start 0x2776
    # The 0 is 0x24ff, which is individually included above
    (1, 10, 1, 0x2776, 1),
    # DINGBAT NEGATIVE CIRCLED SANS-SERIF: 1 -> 10, start 0x278A
    (1, 10, 1, 0x278A, 1),
    # DIGIT ZERO COMMA: 0 -> 9, start 0x1F101
    (0, 9, 1, 0x1F101, 1),
]

translate_dict = {}

# equivalences
for into in equivalents:
    for codePoint in equivalents[into]:
        translate_dict[codePoint] = into

# sequences
for sequence in sequences:
    codePoint = sequence[3]
    for into in range(sequence[0], sequence[1] + 1, sequence[2]):
        translate_dict[codePoint] = str(into)
        codePoint += sequence[4]

translate_table = str.maketrans(translate_dict)


def normalize(text):
    return text.translate(translate_table)


def table_as_regex(table=None, hex_prefix='', hex_sufix='', separator='', range_separator='-', prefix='[', sufix=']',
                   as_characters=False, max_value=None, included_obfuscations=None, zero_padding=None,
                   uppercase_hex=None):
    """
    Returns a regular expression character class of all the characters in the provided translation table.
    :param table:            The table to operate upon. Defaults to translate_table.
    :param hex_prefix:       Characters to include before a hex character code
    :param hex_sufix:        Characters to include after a hex character code
    :param separator:        Character to separate separate hex entries/characters
    :param range_separator:  Character indicating two hex codes or characters are a range
    :param prefix:           Characters to include at the begining of the character class
    :param sufix:            Characters to include at the end of the character class
    :param as_characters:    True indicates characters should be used instead of hex character codepoints
    :param max_value:        Maximum value to include (e.g. limit to 4 hex digits by specifying 0xffff)
    :param included_obfuscations: List of str/characters the translations for which will be included
    :param zero_padding:     Number of zero-padded chracters for the hex values
    :param upercase_hex:     Use upercase [A-F] letters for hex codes
    :return: A string
    """
    table = table if table else translate_table
    escapes = []
    zero_padding_format = '%0{}x'.format(zero_padding)

    def get_single_value_as_hex_escape(value):
        if as_characters:
            return chr(value)
        if zero_padding is None:
            value = hex(value)[2:]
        else:
            value = zero_padding_format % value
        if uppercase_hex:
            value = value.upper()
        return '{}{}{}'.format(hex_prefix, value, hex_sufix)

    def append_previous(first, prev):
        if max_value is not None:
            if first > max_value:
                return
            if prev > max_value:
                prev = max_value
        prev_text = get_single_value_as_hex_escape(prev)
        if first == prev:
            escapes.append(prev_text)
        else:
            escapes.append('{}{}{}'.format(get_single_value_as_hex_escape(first), range_separator, prev_text))

    keys = [int(key) for key in table.keys()]
    keys.sort(key=int)
    start = None
    previous = None
    for key in keys:
        if included_obfuscations is not None and table[key] not in included_obfuscations:
            continue
        if start is None:
            # Handle the first key we're going to output.
            start = key
            previous = key
            continue
        if not range_separator or previous + 1 != key:
            append_previous(start, previous)
            start = key
        previous = key
    append_previous(start, previous)
    return '{}{}{}'.format(prefix, separator.join(escapes), sufix)


def table_as_ms_search_regex(table=None, max_value=0xffff, included_obfuscations=None, as_characters=False,
                             with_digits=False, extra_escape=None):
    r"""
    For MS search: Returns a regular expression character class of all the characters in the provided translation table.
    :param table:            The table to operate upon. Defaults to translate_table.
    :param max_value:        Maximum value to include (e.g. limit to 4 hex digits by specifying 0xffff)
    :param included_obfuscations: List of str/characters the translations for which will be included
    :param as_characters:    True indicates characters should be used instead of hex character codepoints
    :param with_digits:      Include \d in the character class
    :param extra_escape:     Add an additional '\' to the '\x{x}' and '\d' escapes, so '\\x{x}' and '\\d' are used.
    :return: A string
    """
    hex_prefix = r'\\x{' if extra_escape else r'\x{'
    prefix = get_prefix_with_digit_and_extra_escape(with_digits, extra_escape)
    return table_as_regex(table=table, prefix=prefix, hex_prefix=hex_prefix, hex_sufix='}', max_value=max_value,
                          included_obfuscations=included_obfuscations, as_characters=as_characters)


def table_as_ms_regexp_regex(table=None, max_value=0xffff, included_obfuscations=None, as_characters=False,
                             with_digits=False, extra_escape=None):
    r"""
    For MS Regexp: Returns a regular expression character set of all the characters in the provided translation table.
    :param table:            The table to operate upon. Defaults to translate_table.
    :param max_value:        Maximum value to include (e.g. limit to 4 hex digits by specifying 0xffff)
    :param included_obfuscations: List of str/characters the translations for which will be included
    :param as_characters:    True indicates characters should be used instead of hex character codepoints
    :param with_digits:      Include \d in the character class
    :param extra_escape:     Add an additional '\' to the '\uxxxx' and '\d' escapes, so '\\uxxxx' and '\\d' are used.
    :return: A string
    """
    hex_prefix = r'\\u' if extra_escape else r'\u'
    prefix = get_prefix_with_digit_and_extra_escape(with_digits, extra_escape)
    return table_as_regex(table=table, prefix=prefix, hex_prefix=hex_prefix, hex_sufix='', max_value=max_value,
                          included_obfuscations=included_obfuscations, zero_padding=4, as_characters=as_characters)


def table_as_sd_regex(table=None, max_value=0xffffffff, included_obfuscations=None, as_characters=False,
                      with_digits=False, extra_escape=None):
    r"""
    For SD regex: Returns a regular expression character set of all the characters in the provided translation table.
    :param table:            The table to operate upon. Defaults to translate_table.
    :param max_value:        Maximum value to include (e.g. limit to 4 hex digits by specifying 0xffff)
    :param included_obfuscations: List of str/characters the translations for which will be included
    :param as_characters:    True indicates characters should be used instead of hex character codepoints
    :param with_digits:      Include \d in the character class
    :param extra_escape:     Add a '\' to the '\U', '\u', and '\d' escapes, so '\\U', '\\u', and '\\d' are used.
    :return: A string
    """
    hex_prefix = r'\\U' if extra_escape else r'\U'
    prefix = get_prefix_with_digit_and_extra_escape(with_digits, extra_escape)
    long_u_escape = table_as_regex(table=table, prefix=prefix, hex_prefix=hex_prefix, hex_sufix='', max_value=max_value,
                                   included_obfuscations=included_obfuscations, zero_padding=8,
                                   as_characters=as_characters)
    # The regex package does its own parsing of escapes, even on the replace-with string. So, the extra escape on
    # the '\\u' is needed, just like it is on the '\\U' in the regex pattern.
    return regex.sub(r'\\U0000(?=[\dA-Fa-f]{4})', r'\\u', long_u_escape)


def get_prefix_with_digit_and_extra_escape(with_digits, extra_escape):
    prefix = r'[\d' if with_digits else '['
    return prefix.replace('\\', '\\\\') if extra_escape else prefix
