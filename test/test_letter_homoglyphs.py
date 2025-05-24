# coding=utf-8
import regex
import letter_homoglyphs
import pytest


@pytest.mark.parametrize("keyphrase, exclude, text, expected_matches", [
    ("a", "", "b 4 d", ["4"]),
    ("hello there", "", "hello th3re", ["hello th3re"]),
    ("hello there", "", " he11othere.", ["he11othere"]),
    ("hello", "", "h3llo there", ["h3llo"]),
    ("hello", "", "hell0there", []),
    ("there", "", "hello th3re", ["th3re"]),
    ("there", "", "hellothere", []),
    ("hello", "", "h3ll0 there", ["h3ll0"]),
    ("test", "", "te$+", ["te$+"]),
    ("one two", "", "(on3\t tw0)", ["on3\t tw0"]),
    ("word", "", "l0ts 0f w0rds", ["w0rd"]),
    ("word", "", "l0ts 0f w0rd's", ["w0rd"]),
    ("word", "", "l0ts 0f w'0'r'd's", ["w'0'r'd"]),
    ("thing word", "", "th1ng.word", ["th1ng.word"]),
    ("thing word", "", "thing | w.o.r.d", ["thing | w.o.r.d"]),
    ("very airy", "", "v e r y a  i   r     y!", ["v e r y a  i   r     y"]),
    ("cash$money", "", "c4sh$money", ["c4sh$money"]),
    ("cash$money", "", "   c a s h $ m o n e y  ", ["c a s h $ m o n e y"]),
    ("cash$money", "", "cash5money", []),
    ("caller", "", "ca||er.ca| |er,call|er", ["ca||er", "ca| |er", "call|er"]),
    ("caller", "all", "c a l l e r c all e r ca ll er", ["c a l l e r", "ca ll er"]),
    ("test", "", "t e s ts and t_3_s_t's", ["t e s t", "t_3_s_t"]),
    ("test", "est|te", "t-ests or +.est's, or te sts", []),
    ("start", "", "$tart $ t a r t  ...$t ar t!", ["$tart", "$ t a r t", "$t ar t"]),
    ("abcde", "", 'abcd3"s a b c d e`s a.b.c.d.e5', ["abcd3", "a b c d e", "a.b.c.d.e"]),
])
def test_find_matches(keyphrase, exclude, text, expected_matches):
    compiled = letter_homoglyphs.compile_keyphrases((keyphrase, exclude))
    matches = [(m.group(), k) for m, k in letter_homoglyphs.find_matches(compiled, text)]
    assert matches == [(m, keyphrase.replace('_', '')) for m in expected_matches]


@pytest.mark.parametrize("keyphrase", [
    "a",
    "bc",
    "d e",
])
def test_build_keyphrase_regex_matches_keyphrase(keyphrase):
    r = letter_homoglyphs.build_keyphrase_regex(keyphrase)
    assert regex.search(r, keyphrase, letter_homoglyphs.REGEX_FLAGS)


@pytest.mark.parametrize("keyphrase, exclude", [
    ("test", ""),
    ("test", "t"),
    ("test test test", ""),
    ("test test test", "blah|bleh"),
])
def test_build_exclude_regex_matches_keyphrase(keyphrase, exclude):
    r = letter_homoglyphs.build_exclude_regex(keyphrase, exclude)
    assert regex.search(r, keyphrase, letter_homoglyphs.REGEX_FLAGS)


@pytest.mark.parametrize("keyphrase, exclude, text, match_expected", [
    ("test", "t", "this", False),
    ("test", "t", "t his", True),
    ("test", "", "t3st", False),
    ("some thing", "thing", "s0mething", False),
    ("some thing", "thing", "s0me-thing", True),
    ("some thing", "", "some  .  thing", True),
    ("some thing", "thing|abc", "some  .  thing", True),
    ("some thing", "thing|abc", "notsome  .  thing", True),
    ("some thing", "", "notsome  .  thing", False),
])
def test_build_exclude_regex(keyphrase, exclude, text, match_expected):
    result = regex.search(letter_homoglyphs.build_exclude_regex(keyphrase, exclude), text, letter_homoglyphs.REGEX_FLAGS)
    if match_expected:
        assert result
    else:
        assert not result


@pytest.mark.parametrize("chars, non", [
    ("a", "X"),
    ("ABCDEFG", "123"),
    ("ñó", "ẽºä"),
])
def test_build_regex_charset(chars, non):
    regex_charset = letter_homoglyphs.build_regex_charset(map(ord, chars))
    for char in chars:
        assert regex.fullmatch(regex_charset, char, letter_homoglyphs.REGEX_FLAGS)
    for char in non:
        assert not regex.fullmatch(regex_charset, char, letter_homoglyphs.REGEX_FLAGS)


@pytest.mark.parametrize("char", list("abCD90'.#"))
def test_build_equivalent_regex_same(char):
    assert regex.fullmatch(letter_homoglyphs.build_equivalent_regex(char), char, letter_homoglyphs.REGEX_FLAGS)


@pytest.mark.parametrize("char", list("abyz"))
def test_build_equivalent_regex_case_insensitive(char):
    assert regex.fullmatch(letter_homoglyphs.build_equivalent_regex(char.lower()), char.upper(), letter_homoglyphs.REGEX_FLAGS)
    assert regex.fullmatch(letter_homoglyphs.build_equivalent_regex(char.upper()), char.lower(), letter_homoglyphs.REGEX_FLAGS)


def test_build_equivalent_regex_combining_modifiers():
    assert regex.fullmatch(letter_homoglyphs.build_equivalent_regex('e'), "e\u0301", letter_homoglyphs.REGEX_FLAGS)
