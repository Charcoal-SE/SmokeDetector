# -*- coding: utf-8 -*-
import regex
import phonenumbers

# noinspection PyUnusedLocal
def has_repeated_words(s, site):
    words = regex.split(r"[\s.,;!/\()\[\]+_-]", s)
    words = [word for word in words if word != ""]
    streak = 0
    prev = ""
    for word in words:
        if word == prev and word.isalpha() and len(word) > 1:
            streak += 1
        else:
            streak = 0
        prev = word
        if streak >= 5 and streak * len(word) >= 0.2 * len(s):
            return True, u"Repeated word: *{}*".format(word)
    return False, ""


# noinspection PyUnusedLocal
def has_few_characters(s, site):
    s = regex.sub("</?p>", "", s).rstrip()    # remove HTML paragraph tags from posts
    uniques = len(set(list(s)))
    if (len(s) >= 30 and uniques <= 6) or (len(s) >= 100 and uniques <= 15):    # reduce if false reports appear
        return True, u"Contains {} unique characters".format(uniques)
    return False, ""


# noinspection PyUnusedLocal
def has_repeating_characters(s, site):
    s = regex.sub('http[^"]*', "", s)    # remove URLs for this check
    if s is None or len(s) == 0 or len(s) >= 300 or regex.compile("<pre>|<code>").search(s):
        return False, ""
    matches = regex.compile(u"([^\\s_\u200b\u200c.,?!=~*/0-9-])(\\1{10,})", regex.UNICODE).findall(s)
    match = "".join(["".join(match) for match in matches])
    if (100 * len(match) / len(s)) >= 20:  # Repeating characters make up >= 20 percent
        return True, u"Repeated character: *{}*".format(match)
    return False, ""


# noinspection PyUnusedLocal
def link_at_end(s, site):   # link at end of question, on selected sites
    s = regex.sub("</strong>|</em>|</p>", "", s)
    match = regex.compile(ur"(?i)https?://(?:[.A-Za-z0-9-]*/?[.A-Za-z0-9-]*/?|plus\.google\.com/"
                          ur"[\w/]*|www\.pinterest\.com/pin/[\d/]*)</a>\s*$").search(s)
    if match and not regex.compile(r"(?i)upload|\b(imgur|yfrog|gfycat|tinypic|sendvid|ctrlv|prntscr|gyazo|youtu\.?be|"
                                   r"stackexchange|superuser|past[ie].*|dropbox|microsoft|newegg|cnet|"
                                   r"(?<!plus\.)google|localhost|ubuntu)\b").search(match.group(0)):
        return True, u"Link at end: {}".format(match.group(0))
    return False, ""


# noinspection PyUnusedLocal
def non_english_link(s, site):   # non-english link in short answer
    if len(s) < 600:
        links = regex.compile(ur'nofollow(?: noreferrer)?">([^<]*)(?=</a>)', regex.UNICODE).findall(s)
        for link_text in links:
            word_chars = regex.sub(r"(?u)\W", "", link_text)
            non_latin_chars = regex.sub(r"\w", "", word_chars)
            if len(word_chars) >= 1 and ((len(word_chars) <= 20 and len(non_latin_chars) >= 1) or
                                         (len(non_latin_chars) >= 0.05 * len(word_chars))):
                return True, u"Non-English link text: *{}*".format(link_text)
    return False, ""


def mostly_non_latin(s, site):   # majority of post is in non-Latin, non-Cyrillic characters
    if regex.compile("<pre>|<code>").search(s) and site == "stackoverflow.com":  # Avoid false positives on SO
        return False, ""
    word_chars = regex.sub(r'(?u)[\W0-9]|http\S*', "", s)
    non_latin_chars = regex.sub(r"(?u)\p{script=Latin}|\p{script=Cyrillic}", "", word_chars)
    if len(non_latin_chars) > 0.4 * len(word_chars):
        return True, u"Text contains {} non-Latin characters out of {}".format(len(non_latin_chars), len(word_chars))
    return False, ""


# noinspection PyUnusedLocal
def has_phone_number(s, site):
    if regex.compile(ur"(?i)\b(address(es)?|run[- ]?time|error|value|server|hostname|timestamp|warning|code|"
                     ur"(sp)?exception|version|chrome|1234567)\b", regex.UNICODE).search(s):
        return False, ""  # not a phone number
    s = regex.sub("[^A-Za-z0-9\\s\"',]", "", s)   # deobfuscate
    s = regex.sub("[Oo]", "0", s)
    s = regex.sub("[Ss]", "5", s)
    s = regex.sub("[Ii]", "1", s)
    matched = regex.compile(ur"(?<!\d)(?:\d{2}\s?\d{8,11}|\d\s{0,2}\d{3}\s{0,2}\d{3}\s{0,2}\d{4}|8\d{2}"
                            ur"\s{0,2}\d{3}\s{0,2}\d{4})(?!\d)", regex.UNICODE).findall(s)
    test_formats = ["IN", "US", "NG", None]      # ^ don't match parts of too long strings of digits
    for phone_number in matched:
        if regex.compile(r"^21474(672[56]|8364)|^192168").search(phone_number):
            return False, ""  # error code or limit of int size, or 192.168 IP
        for testf in test_formats:
            try:
                z = phonenumbers.parse(phone_number, testf)
                if phonenumbers.is_possible_number(z) and phonenumbers.is_valid_number(z):
                    print "Possible {}, Valid {}, Explain: {}".format(phonenumbers.is_possible_number(z),
                                                                      phonenumbers.is_valid_number(z), z)
                    return True, u"Phone number: {}".format(phone_number)
            except phonenumbers.phonenumberutil.NumberParseException:
                pass
    return False, ""


def has_customer_service(s, site):  # flexible detection of customer service in titles
    s = s[0:300].lower()   # if applied to body, the beginning should be enough: otherwise many false positives
    s = regex.sub(r"[^A-Za-z0-9\s]", "", s)   # deobfuscate
    phrase = regex.compile(r"(tech(nical)? support)|((support|service|contact|help(line)?) (telephone|phone|"
                           r"number))").search(s)
    if phrase and site in ["askubuntu.com", "webapps.stackexchange.com", "webmasters.stackexchange.com"]:
        return True, u"Key phrase: *{}*".format(phrase.group(0))
    business = regex.compile(r"(?i)\b(airlines?|AVG|BT|netflix|dell|Delta|epson|facebook|gmail|google|hotmail|hp|"
                             r"lexmark|mcafee|microsoft|norton|out[l1]ook|quickbooks|sage|windows?|yahoo)\b").search(s)
    digits = len(regex.compile(r"\d").findall(s))
    if business and digits >= 5:
        keywords = regex.compile(r"(?i)\b(customer|help|care|helpline|reservation|phone|recovery|service|support|"
                                 r"contact|tech|technical|telephone|number)\b").findall(s)
        if len(set(keywords)) >= 2:
            matches = ", ".join(["".join(match) for match in keywords])
            return True, u"Scam aimed at *{}* customers. Keywords: *{}*".format(business.group(0), matches)
    return False, ""


# noinspection PyUnusedLocal
def has_health(s, site):   # flexible detection of health spam in titles
    s = s[0:200]   # if applied to body, the beginning should be enough: otherwise many false positives
    capitalized = len(regex.compile(r"\b[A-Z][a-z]").findall(s)) >= 5   # words beginning with uppercase letter
    organ = regex.compile(r"(?i)\b(colon|skin|muscle|bicep|fac(e|ial)|eye|brain|IQ|mind|head|hair|peni(s|le)|"
                          r"breast|body|joint|belly|digest\w*)s?\b").search(s)
    condition = regex.compile(r"(?i)\b(weight|constipat(ed|ion)|dysfunction|swollen|sensitive|wrinkle|aging|"
                              r"suffer|acne|pimple|dry|clog(ged)?|inflam(ed|mation)|fat|age|pound)s?\b").search(s)
    goal = regex.compile(r"(?i)\b(supple|build|los[es]|power|burn|erection|tone(d)|rip(ped)?|bulk|get rid|mood)s?\b|"
                         r"\b(diminish|look|reduc|beaut|renew|young|youth|lift|eliminat|enhance|energ|shred|"
                         r"health(?!kit)|improve|enlarge|remov|vital|slim|lean|boost|str[oe]ng)").search(s)
    remedy = regex.compile(r"(?i)\b(remed(y|ie)|serum|cleans?(e|er|ing)|care|(pro)?biotic|herbal|lotion|cream|"
                           r"gel|cure|drug|formula|recipe|regimen|solution|therapy|hydration|soap|treatment|supplement|"
                           r"diet|moist\w*|injection|potion|ingredient|aid|exercise|eat(ing)?)s?\b").search(s)
    boast = regex.compile(r"(?i)\b(most|best|simple|top|pro|real|mirac(le|ulous)|secrets?|organic|natural|perfect|"
                          r"ideal|fantastic|incredible|ultimate|important|reliable|critical|amazing|fast|good)\b|"
                          r"\b(super|hyper|advantag|benefi|effect|great|valu|eas[iy])").search(s)
    other = regex.compile(r"(?i)\b(product|thing|item|review|advi[cs]e|myth|make use|your?|really|work|tip|shop|"
                          r"store|method|expert|instant|buy|fact|consum(e|ption)|baby|male|female|men|women|grow|"
                          r"idea|suggest\w*|issue)s?\b").search(s)
    score = 4 * bool(organ) + 2 * bool(condition) + 2 * bool(goal) + 2 * bool(remedy) + bool(boast) + \
        bool(other) + capitalized
    if score >= 8:
        match_objects = [organ, condition, goal, remedy, boast, other]
        words = []
        for match in match_objects:
            if match:
                words.append(match.group(0))
        return True, u"Health-themed spam (score {}). Keywords: *{}*".format(score, ", ".join(words).lower())
    return False, ""


def keyword_email(s, site):   # a keyword and an email in the same post
    if regex.compile("<pre>|<code>").search(s) and site == "stackoverflow.com":  # Avoid false positives on SO
        return False, ""
    keyword = regex.compile(ur"(?i)\b(training|we (will )?(offer|develop|provide)|sell|invest(or|ing|ment)|credit|"
                            ur"money|quality|legit|interest(ed)?|guarantee|rent|crack|opportunity|fundraising|campaign|"
                            ur"career|employment|candidate|loan|lover|husband|wife|marriage|illuminati|brotherhood|"
                            ur"(join|contact) (me|us|him)|reach (us|him)|spell(caster)?|doctor|cancer|krebs|"
                            ur"(cheat|hack)(er|ing)?|spying|passport|seaman|scam|pics|vampire|bless(ed)?|atm|miracle|"
                            ur"testimony|kidney|hospital|wetting)s?\b| Dr\.? |\$ ?[0-9,.]{4}|@qq\.com|"
                            ur"\b(герпес|муж|жена|доктор|болезн)").search(s)
    email = regex.compile(ur"(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})"
                          ur"[A-z0-9_.%+-]+\.[A-z]{2,4}\b").search(s)
    if keyword and email:
        return True, u"Keyword *{}* with email {}".format(keyword.group(0), email.group(0))
    obfuscated_email = regex.compile(ur"(?<![=#/])\b[A-z0-9_.%+-]+ *@ *(gmail|yahoo) *\. *com\b").search(s)
    if obfuscated_email and not email:
        return True, u"Obfuscated email {}".format(obfuscated_email.group(0))
    return False, ""


# noinspection PyUnusedLocal
def keyword_link(s, site):   # thanking keyword and a link in the same short answer
    if len(s) > 400:
        return False, ""
    link = regex.compile(ur'(?i)<a href="https?://\S+').search(s)
    if not link or regex.compile(r"(?i)upload|\b(imgur|yfrog|gfycat|tinypic|sendvid|ctrlv|prntscr|gyazo|youtu\.?be|"
                                 r"stackexchange|superuser|past[ie].*|dropbox|microsoft|newegg|cnet|(?<!plus\.)google|"
                                 r"localhost|ubuntu)\b").search(link.group(0)):
        return False, ""
    praise = regex.compile(ur"(?i)\b(nice|good|interesting|helpful|great) (article|blog|post)\b").search(s)
    thanks = regex.compile(ur"(?i)\b(appreciate|than(k|ks|x))\b").search(s)
    keyword = regex.compile(ur"(?i)\b(I really appreciate|many thanks|thanks a lot|thank you (very|for)|"
                            ur"than(ks|x) for (sharing|this|your)|dear forum members|(very informative|"
                            ur"stumbled upon (your|this)) (blog|site|website))\b").search(s)
    if link and keyword:
        return True, u"Keyword *{}* with link {}".format(keyword.group(0), link.group(0))
    if link and thanks and praise:
        return True, u"Keywords *{}*, *{}* with link {}".format(thanks.group(0), praise.group(0), link.group(0))
    return False, ""


# noinspection PyUnusedLocal
def bad_link_text(s, site):   # suspicious text of a hyperlink
    s = regex.sub("</?strong>|</?em>", "", s)  # remove font tags
    keywords = regex.compile(ur"(?isu)^(buy|cheap) |live[ -]?stream|(^| )make (money|\$)|(^| )(porno?|(whole)?sale|"
                             ur"coins|replica|luxury|essays?|in \L<city>)($| )|(^| )\L<city>.*(service|escort|"
                             ur"call girl)|(best|make|full|hd|software|cell|data)[\w ]{1,20}(online|service|company|"
                             ur"repair|recovery)|\b(writing service|essay (writing|tips))", city=FindSpam.city_list)
    links = regex.compile(ur'nofollow(?: noreferrer)?">([^<]*)(?=</a>)', regex.UNICODE).findall(s)
    business = regex.compile(r"(?i)(^| )(airlines?|AVG|BT|netflix|dell|Delta|epson|facebook|gmail|google|hotmail|hp|"
                             r"lexmark|mcafee|microsoft|norton|out[l1]ook|quickbooks|sage|windows?|yahoo)($| )")
    support = regex.compile(r"(?i)(^| )(customer|care|helpline|reservation|phone|recovery|service|support|contact|"
                            r"tech|technical|telephone|number)($| )")
    for link_text in links:
        keywords_match = keywords.search(link_text)
        if keywords_match:
            return True, u"Bad keyword *{}* in link text".format(keywords_match.group(0).strip())
        business_match = business.search(link_text)
        support_match = support.search(link_text)
        if business_match and support_match:
            return True, u"Bad keywords *{}*, *{}* in link text".format(business_match.group(0).strip(),
                                                                        support_match.group(0).strip())
    return False, ""


# noinspection PyUnusedLocal
def is_offensive_post(s, site):
    if s is None or len(s) == 0:
        return False, ""

    offensive = regex.compile(ur"(?is)\b(ur mom|(yo)?u suck|8={3,}D|nigg[aeu][rh]?|(ass ?|a|a-)hole|fag(got)?|"
                              ur"daf[au][qk]|(?<!brain)(mother|mutha)?fuc?k+(a|ing?|e?(r|d)| off+| y(ou|e)(rself)?|"
                              ur" u+|tard)?|shit(t?er|head)|you scum|dickhead|pedo|whore|cunt|cocksucker|ejaculated?|"
                              ur"jerk off|cummies|butthurt|(private|pussy) show|lesbo|bitches|(eat|suck)\b.{0,20}\b"
                              ur"dick|dee[sz]e? nut[sz])s?\b")
    matches = offensive.finditer(s)
    len_of_match = 0
    text_matched = []
    for match in matches:
        len_of_match += match.end() - match.start()
        text_matched.append(match.group(0))

    if (1000 * len_of_match / len(s)) >= 15:  # currently at 1.5%, this can change if it needs to
        return True, u"Offensive keyword{}: *{}*".format("s" if len(text_matched) > 1 else "", ", ".join(text_matched))
    return False, ""


# noinspection PyUnusedLocal
def has_eltima(s, site):
    reg = regex.compile(ur"(?is)\beltima")
    if reg.search(s) and len(s) <= 750:
        return True, u"Bad keyword *eltima* and body length under 750 chars"
    return False, ""