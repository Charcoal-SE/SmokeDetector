# coding=utf-8
import regex
import unicodedata
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
    ("word", "", "l0ts 0f w0rds", ["w0rds"]),
    ("word", "", "l0ts 0f w0rd's", ["w0rd"]),
    ("word", "", "l0ts 0f w'0'r'd's", ["w'0'r'd"]),
    ("thing word", "", "th1ng.word", ["th1ng.word"]),
    ("thing word", "", "thing | w.o.r.d", ["thing | w.o.r.d"]),
    ("very airy", "", "v e r y a  i   r     y!", ["v e r y a  i   r     y"]),
    ("cash$money", "", "c4sh$money", ["c4sh$money"]),
    ("cash$money", "", "   c a s h $ m o n e y  ", ["c a s h $ m o n e y"]),
    ("cash$money", "", "cash5money", []),
    ("caller", "", "ca||er.ca| |er,call|er", ["ca||er", "ca| |er", "call|er"]),
    ("caller", "", "ca|ller*ca||ller!cal||ler", ["ca|ller", "ca||ller", "cal||ler"]),
    ("caller", "all", "c a l l e r c all e r ca ll er", ["c a l l e r", "ca ll er"]),
    ("test", "", "t e s ts and t_3_s_t's", ["t e s ts", "t_3_s_t"]),
    ("test", "est|te", "t-ests or +.est's, or te sts", []),
    ("start", "", "$tart $ t a r t  ...$t ar t!", ["$tart", "$ t a r t", "$t ar t"]),
    ("abcde", "", 'abcd3"s a b c d e`s a.b.c.d.e5', ["abcd3", "a b c d e", "a.b.c.d.e5"]),
    ("bad", "", "bád", ["bád"]),
    ("the word", "", "dots in \u1e97\u0324he word", ["\u1e97\u0324he word"]),
    ("Ice", "", "iCe, iÇe", ["iÇe"]),
    ("luck", "", "lvck", ["lvck"]),
    ("Tricky", "", "(tr\U0001D6A4cky)", ["tr\U0001D6A4cky"]),
    ("airlines", "", "𝘼𝙞𝙧𝙡𝙞𝙣𝙚𝙨", ["𝘼𝙞𝙧𝙡𝙞𝙣𝙚𝙨"]),
    ("loan", "", "𝐋𝐨𝐚𝐧 𝐋oan L𝐨AN", ["𝐋𝐨𝐚𝐧", "𝐋oan", "L𝐨AN"]),
    ("bad", "", "b\U0001D74Fd", ["b\U0001D74Fd"]),
    ("best", "", "B𝟛st", ["B𝟛st"]),
    ("A", "", "𝞐-𝜶-𝛢-α", ["𝞐", "𝜶", "𝛢", "α"]),
    ("devious", "", "δΕνΙΘυs", ["δΕνΙΘυs"]),
    ("abc", "", "ABC \u13aaBC A\u0184C AB\U00010302", ["\u13aaBC", "A\u0184C", "AB\U00010302"]),
    ("def", "", "DEF \u15deEF D\u212eF DE\U0001D213", ["\u15deEF", "D\u212eF", "DE\U0001D213"]),
    ("ghi", "", "GHI \u13F3HI G\U000102cfI GH\u06F1", ["\u13F3HI", "G\U000102cfI", "GH\u06F1"]),
    ("jkl", "", "JKL \u0458KL J\u16D5L JK\U000118A3", ["\u0458KL", "J\u16D5L", "JK\U000118A3"]),
    ("mno", "", "MNO \u16D6NO M\uA4E0O MN\U000118D7", ["\u16D6NO", "M\uA4E0O", "MN\U000118D7"]),
    ("pqr", "", "PQR \U00010295QR P\u2D55R PQ\uAB48", ["\U00010295QR", "P\u2D55R", "PQ\uAB48"]),
    ("stu", "", "STU \U00010420TU S\u22A4U ST\u028B", ["\U00010420TU", "S\u22A4U", "ST\u028B"]),
    ("vwx", "", "VWX \u2164WX V\U000118EFX VW\uA7B3", ["\u2164WX", "V\U000118EFX", "VW\uA7B3"]),
    ("yz", "", "YZ \U00016F43Z Y\uAB93", ["\U00016F43Z", "Y\uAB93"]),
    ("z.com", "", "z*com z.com z\uA60Ecom z*c0m", ["z*com", "z\uA60Ecom", "z*c0m"]),
    ("looking", "", "are you lookiɴg for this", ["lookiɴg"]),
    ("aha", "", "a\U00010796a", ["a\U00010796a"]),
    ("spam r us", "", "spam-Я-us!", ["spam-Я-us"]),
    ("customer service", "", "ᏟႮՏͲϴᎷᎬᎡ service", ["ᏟႮՏͲϴᎷᎬᎡ service"]),
    ("price", "", "🇵🇷🇮🇨🇪", ["🇵🇷🇮🇨🇪"]),
    ("ucsaw", "", "Ⴎᑕᔕᗩᗯ", ["Ⴎᑕᔕᗩᗯ"]),
    ("he he", "", "HE he, yes ℏℇ ℎ€; and furthermore ℋ℮ ℌℯ!", ["ℏℇ ℎ€", "ℋ℮ ℌℯ"]),
    ("pkaicrucabdxdie", "", "℗KÅℹ©️®️µ¢ªßð×Ð¡⅀", ["℗KÅℹ©️®️µ¢ªßð×Ð¡⅀"]),
    ("easy", "", "③⁴₅y", ["③⁴₅y"]),
    ("0123456789", "", "\U0001D7F6¹\U0001D7EE\U0001D7DB\U0001D7D2\u2464\u2479\u248E\u24FC\u277E", ["\U0001D7F6¹\U0001D7EE\U0001D7DB\U0001D7D2\u2464\u2479\u248E\u24FC\u277E"]),
    ("one", "", "ϴηϵ øᑎє", ["ϴηϵ", "øᑎє"]),
    ("q", "", "Q \u024a \u024b", ["\u024a", "\u024b"]),
    ("a b", "", "a\u0301b a \u0301b", ["a\u0301b"]),
    ("voila", "", "voi" + "|" * 10_000 + "a", ["voi" + "|" * 10_000 + "a"]),
    ("caller", "", "ca" + "|" * 10_000 + "er", ["ca" + "|" * 10_000 + "er"]),
])
def test_find_matches(keyphrase, exclude, text, expected_matches):
    compiled = letter_homoglyphs.compile_keyphrases((keyphrase, exclude))
    matches = [(unicodedata.normalize('NFC', m), k)
               for k, m, p in letter_homoglyphs.find_matches(compiled, text)]
    assert matches == [(unicodedata.normalize('NFC', m), keyphrase.replace('_', ''))
                       for m in expected_matches]


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
    ("regex.dots", "", "regexNdots", False),
])
def test_build_exclude_regex(keyphrase, exclude, text, match_expected):
    result = regex.search(letter_homoglyphs.build_exclude_regex(keyphrase, exclude), text, letter_homoglyphs.REGEX_FLAGS)
    if match_expected:
        assert result
    else:
        assert not result
