# -*- coding: utf-8 -*-
import regex
import phonenumbers


def all_caps_text(s, site):
    s = regex.sub("<[^>]*>", "", s)   # remove HTML tags
    s = regex.sub("&\w+;", "", s)     # remove HTML entities
    if len(s) <= 150 and regex.compile(ur"SQL|\b(ERROR|PHP|QUERY|ANDROID|CASE|SELECT|HAVING|COUNT|GROUP|ORDER BY|INNER|OUTER)\b").search(s):
        return False, ""   # common words in non-spam all-caps titles
    if len(s) >= 15 and regex.compile(ur"^(?=.*\p{upper})\P{lower}*$", regex.UNICODE).search(s):
        return True, "All in caps"
    return False, ""


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


def has_few_characters(s, site):
    s = regex.sub("</?p>", "", s).rstrip()    # remove HTML paragraph tags from posts
    uniques = len(set(list(s)))
    if (len(s) >= 30 and uniques <= 6) or (len(s) >= 100 and uniques <= 15):    # reduce if false reports appear
        return True, u"Contains {} unique characters".format(uniques)
    return False, ""


def has_repeating_characters(s, site):
    s = regex.sub('http[^"]*', "", s)    # remove URLs for this check
    if s is None or len(s) == 0 or len(s) >= 300 or regex.compile("<pre>|<code>").search(s):
        return False, ""
    matches = regex.compile(u"([^\\s_\u200b\u200c.,?!=~*/0-9-])(\\1{10,})", regex.UNICODE).findall(s)
    match = "".join(["".join(match) for match in matches])
    if (100 * len(match) / len(s)) >= 20:
        return True, u"Repeated character: *{}*".format(match)
    return False, ""


def link_at_end(s, site):   # link at end of question, on selected sites
    s = regex.sub("</strong>|</em>|</p>", "", s)
    match = regex.compile(ur"(?i)https?://(?:[.A-Za-z0-9-]*/?[.A-Za-z0-9-]*/?|plus\.google\.com/[\w/]*|www\.pinterest\.com/pin/[\d/]*)</a>\s*$").search(s)
    if match and not regex.compile(r"(?i)upload|\b(imgur|yfrog|gfycat|tinypic|sendvid|ctrlv|prntscr|gyazo|youtu\.?be|stackexchange|superuser|past[ie].*|dropbox|microsoft|newegg|cnet|(?<!plus\.)google|localhost|ubuntu)\b").search(match.group(0)):
        return True, u"Link at end: {}".format(match.group(0))
    return False, ""


def non_english_link(s, site):   # non-english link in short answer
    if len(s) < 600:
        links = regex.compile(ur'(?<=nofollow">)[^<]*(?=</a>)', regex.UNICODE).findall(s)
        for link_text in links:
            word_chars = regex.sub(r"(?u)\W", "", link_text)
            non_latin_chars = regex.sub(r"\w", "", word_chars)
            if (len(word_chars) <= 20 and len(non_latin_chars) >= 1) or (len(non_latin_chars) >= 0.05 * len(word_chars)):
                return True, u"Non-English link text: *{}*".format(link_text)
    return False, ""


def mostly_non_latin(s, site):   # majority of post is in non-Latin, non-Cyrillic characters
    if regex.compile("<pre>|<code>").search(s) and site == "stackoverflow.com":  # Avoid false positives on SO
        return False, ""
    word_chars = regex.sub(r'(?u)[\W0-9]|http\S*', "", s)
    non_latin_chars = regex.sub(r"(?u)\p{script=Latin}|\p{script=Cyrillic}", "", word_chars)
    if (len(non_latin_chars) > 0.4 * len(word_chars)):
        return True, u"Text contains {} non-Latin characters out of {}".format(len(non_latin_chars), len(word_chars))
    return False, ""


def has_phone_number(s, site):
    if regex.compile(ur"(?i)\b(address(es)?|run[- ]?time|error|value|server|hostname|timestamp|warning|code|(sp)?exception|version|chrome|1234567)\b", regex.UNICODE).search(s):
        return False, ""  # not a phone number
    s = regex.sub("[^A-Za-z0-9\\s\"',]", "", s)   # deobfuscate
    if site != 'math.stackexchange.com':
        s = regex.sub(",", "", s)                 # keep commas for Math titles
    s = regex.sub("[Oo]", "0", s)
    s = regex.sub("[Ss]", "5", s)
    s = regex.sub("[Ii]", "1", s)
    matched = regex.compile(ur"(?<!\d)(?:\d{2}\s?\d{8,11}|\d\s{0,2}\d{3}\s{0,2}\d{3}\s{0,2}\d{4}|8\d{2}\s{0,2}\d{3}\s{0,2}\d{4})(?!\d)", regex.UNICODE).findall(s)
    test_formats = ["IN", "US", "NG", None]      # ^ don't match parts of too long strings of digits
    for phone_number in matched:
        if regex.compile(r"^21474(672[56]|8364)|^192168").search(phone_number):
            return False, ""  # error code or limit of int size, or 192.168 IP
        for testf in test_formats:
            try:
                z = phonenumbers.parse(phone_number, testf)
                if phonenumbers.is_possible_number(z) and phonenumbers.is_valid_number(z):
                    print "Possible {}, Valid {}, Explain: {}".format(phonenumbers.is_possible_number(z), phonenumbers.is_valid_number(z), z)
                    return True, u"Phone number: {}".format(phone_number)
            except phonenumbers.phonenumberutil.NumberParseException:
                pass
    return False, ""


def has_customer_service(s, site):  # flexible detection of customer service in titles
    s = s[0:300].lower()   # if applied to body, the beginning should be enough: otherwise many false positives
    s = regex.sub(r"[^A-Za-z0-9\s]", "", s)   # deobfuscate
    phrase = regex.compile(r"(tech(nical)? support)|((support|service|contact|help(line)?) (telephone|phone|number))").search(s)
    if phrase and site in ["askubuntu.com", "webapps.stackexchange.com", "webmasters.stackexchange.com"]:
        return True, u"Key phrase: *{}*".format(phrase.group(0))
    business = regex.compile(r"(?i)\b(airlines?|AVG|BT|netflix|dell|Delta|epson|facebook|gmail|google|hotmail|hp|lexmark|mcafee|microsoft|norton|out[l1]ook|quickbooks|sage|windows?|yahoo)\b").search(s)
    digits = len(regex.compile(r"\d").findall(s))
    if (business and digits >= 5):
        keywords = regex.compile(r"(?i)\b(customer|help|care|helpline|reservation|phone|recovery|service|support|contact|tech|technical|telephone|number)\b").findall(s)
        if len(set(keywords)) >= 2:
            matches = ", ".join(["".join(match) for match in keywords])
            return True, u"Scam aimed at *{}* customers. Keywords: *{}*".format(business.group(0), matches)
    return False, ""


def has_health(s, site):   # flexible detection of health spam in titles
    s = s[0:200]   # if applied to body, the beginning should be enough: otherwise many false positives
    capitalized = len(regex.compile(r"\b[A-Z][a-z]").findall(s)) >= 5   # words beginning with uppercase letter
    organ = regex.compile(r"(?i)\b(colon|skin|muscle|bicep|fac(e|ial)|eye|brain|IQ|mind|head|hair|peni(s|le)|breast|body|joint|belly|digest\w*)s?\b").search(s)
    condition = regex.compile(r"(?i)\b(weight|constipat(ed|ion)|dysfunction|swollen|sensitive|wrinkle|aging|suffer|acne|pimple|dry|clog(ged)?|inflam(ed|mation)|fat|age|pound)s?\b").search(s)
    goal = regex.compile(r"(?i)\b(supple|build|los[es]|power|burn|erection|tone(d)|rip(ped)?|bulk|get rid|mood)s?\b|\b(diminish|look|reduc|beaut|renew|young|youth|lift|eliminat|enhance|energ|shred|health|improve|enlarge|remov|vital|slim|lean|boost|str[oe]ng)").search(s)
    remedy = regex.compile(r"(?i)\b(remed(y|ie)|serum|cleans?(e|er|ing)|care|(pro)?biotic|herbal|lotion|cream|gel|cure|drug|formula|recipe|regimen|solution|therapy|hydration|soap|treatment|supplement|diet|moist\w*|injection|potion|ingredient|aid|exercise|eat(ing)?)s?\b").search(s)
    boast = regex.compile(r"(?i)\b(most|best|simple|top|pro|real|mirac(le|ulous)|secrets?|organic|natural|perfect|ideal|fantastic|incredible|ultimate|important|reliable|critical|amazing|fast|good)\b|\b(super|hyper|advantag|benefi|effect|great|valu|eas[iy])").search(s)
    other = regex.compile(r"(?i)\b(product|thing|item|review|advi[cs]e|myth|make use|your?|really|work|tip|shop|store|method|expert|instant|buy|fact|consum(e|ption)|baby|male|female|men|women|grow|idea|suggest\w*|issue)s?\b").search(s)
    score = 4 * bool(organ) + 2 * bool(condition) + 2 * bool(goal) + 2 * bool(remedy) + bool(boast) + bool(other) + capitalized
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
    keyword = regex.compile(ur"(?i)\b(training|we (will )?(offer|develop|provide)|sell|invest(or|ing|ment)|credit|money|quality|legit|interest(ed)?|guarantee|rent|crack|opportunity|fundraising|campaign|career|employment|candidate|loan|lover|husband|wife|marriage|illuminati|brotherhood|(join|contact) (me|us|him)|reach (us|him)|spell(caster)?|doctor|cancer|krebs|(cheat|hack)(er|ing)?|spying|passport|seaman|scam|pics|vampire|bless(ed)?|atm|miracle|testimony|kidney|hospital|wetting)s?\b| Dr\.? |\$ ?[0-9,.]{4}|@qq\.com|\b(герпес|муж|жена|доктор|болезн)").search(s)
    email = regex.compile(ur"(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})[A-z0-9_.%+-]+\.[A-z]{2,4}\b").search(s)
    if keyword and email:
        return True, u"Keyword *{}* with email {}".format(keyword.group(0), email.group(0))
    obfuscated_email = regex.compile(ur"(?<![=#/])\b[A-z0-9_.%+-]+ *@ *gmail *\. *com\b").search(s)
    if obfuscated_email and not email:
        return True, u"Obfuscated email {}".format(obfuscated_email.group(0))
    return False, ""


def keyword_link(s, site):   # thanking keyword and a link in the same short answer
    if len(s) > 400:
        return False, ""
    link = regex.compile(ur'(?i)<a href="https?://\S+').search(s)
    if not link or regex.compile(r"(?i)upload|\b(imgur|yfrog|gfycat|tinypic|sendvid|ctrlv|prntscr|gyazo|youtu\.?be|stackexchange|superuser|past[ie].*|dropbox|microsoft|newegg|cnet|(?<!plus\.)google|localhost|ubuntu)\b").search(link.group(0)):
        return False, ""
    praise = regex.compile(ur"(?i)\b(nice|good|interesting|helpful|great) (article|blog|post)\b").search(s)
    thanks = regex.compile(ur"(?i)\b(appreciate|than(k|ks|x))\b").search(s)
    keyword = regex.compile(ur"(?i)\b(I really appreciate|many thanks|thanks a lot|thank you (very|for)|than(ks|x) for (sharing|this|your)|dear forum members|(very informative|stumbled upon (your|this)) (blog|site|website))\b").search(s)
    if link and keyword:
        return True, u"Keyword *{}* with link {}".format(keyword.group(0), link.group(0))
    if link and thanks and praise:
        return True, u"Keywords *{}*, *{}* with link {}".format(thanks.group(0), praise.group(0), link.group(0))
    return False, ""


def bad_link_text(s, site):   # suspicious text of a hyperlink
    s = regex.sub("</?strong>|</?em>", "", s)  # remove font tags
    keywords = regex.compile(ur"(?isu)^(buy|cheap) |live[ -]?stream|(^| )make (money|\$)(^| )(porno?|(whole)?sale|coins|replica|luxury|essays?|in \L<city>)($| )|(^| )\L<city>.*(service|escort|call girl)|(best|make|full|hd|software|cell|data)[\w ]{1,20}(online|service|company|repair|recovery)|\b(writing service|essay (writing|tips))", city=FindSpam.city_list)
    links = regex.compile(ur'(?<=nofollow">)[^<]*(?=</a>)', regex.UNICODE).findall(s)
    business = regex.compile(r"(?i)(^| )(airlines?|AVG|BT|netflix|dell|Delta|epson|facebook|gmail|google|hotmail|hp|lexmark|mcafee|microsoft|norton|out[l1]ook|quickbooks|sage|windows?|yahoo)($| )")
    support = regex.compile(r"(?i)(^| )(customer|care|helpline|reservation|phone|recovery|service|support|contact|tech|technical|telephone|number)($| )")
    for link_text in links:
        keywords_match = keywords.search(link_text)
        if keywords_match:
            return True, u"Bad keyword *{}* in link text".format(keywords_match.group(0).strip())
        business_match = business.search(link_text)
        support_match = support.search(link_text)
        if business_match and support_match:
            return True, u"Bad keywords *{}*, *{}* in link text".format(business_match.group(0).strip(), support_match.group(0).strip())
    return False, ""


def is_offensive_post(s, site):
    if s is None or len(s) == 0:
        return False, ""

    offensive = regex.compile(ur"(?is)\b(ur mom|(yo)?u suck|8={3,}D|nigg[aeu][rh]?|ass ?hole|fag(got)?|daf[au][qk]|(?<!brain)(mother|mutha)?fuc?k+(a|ing?|e?(r|d)| off+| y(ou|e)(rself)?| u+|tard)?|shit(t?er|head)|you scum|dickhead|pedo|whore|cunt|cocksucker|ejaculated?|cummies|butthurt|(private|pussy) show|lesbo|bitches|(eat|suck)\b.{0,20}\bdick|dee[sz]e? nut[sz])s?\b")
    matches = offensive.finditer(s)
    len_of_match = 0
    text_matched = []
    for match in matches:
        len_of_match += match.end() - match.start()
        text_matched.append(match.group(0))

    if (1000 * len_of_match / len(s)) >= 15:  # currently at 1.5%, this can change if it needs to
        return True, u"Offensive keyword{}: *{}*".format("s" if len(text_matched) > 1 else "", ", ".join(text_matched))
    return False, ""


def has_eltima(s, site):
    reg = regex.compile(ur"(?is)\beltima")
    if reg.search(s) and len(s) <= 750:
        return True, u"Bad keyword *eltima* and body length under 750 chars"
    return False, ""


class FindSpam:
    bad_keywords = [
        "baba ji", "fifa.{0,20}coins?", "fifabay", "Long ?Path ?Tool", "writing service",
        "fifaodell", "brianfo", "tosterone", "bajotz",
        "kolcak", "Zapyo", "we (offer|give out) (loans|funds|funding)",
        "molvi", "judi bola", "ituBola.com", "lost lover'?s?",
        "rejuvenated skin", "ProBrain", "restore[ -]?samsung[ -]?data",
        "swtor2credits", "me2.do", "death reckoning calculate",
        "bam2u", "Neuro(3X|flexyn|fuse|luma|plex)", "TesteroneXL", "Nitroxin",
        "Bowtrol", "Slim ?Genix", "Cleanse EFX", "Alpha ?(Rush|Fuel)", "exoslim",
        "Blackline Elite", "TestCore Pro", "blank(ed)? ?ATM\\b( card)?", "ATM Machine Vault",
        "Xtreme Antler", "Maxx Test 3000", "orvigomax",
        "Cheap Wigs?", "jivam", "^(?s).{0,200}brain[- ]?power", "Maximum ?Shred",
        "aging skin", "acne( prone)? skin", "black[ -]label[ -]no",
        "bagprada", "6611165613", "Apowersoft", "ChatSim",
        "Service Solahart", "junisse", "Profactor[ -]?T",
        "(fake|novelty|quality|buy(ing)?|sell(ing)?|offer).{0,20}(passport|driver'?s? licen[cs]e|ID card|green card|residence permit|toefl|Ielts)s?",
        "^.{0,200}(support|service|helpline)( phone)? number|1[ -]?[ -]?[ -]?866[ -]?978[ -]?(6819|6762)",
        "(mcafee|hotmail|gmail|outlook|yahoo|lexmark (printer)?) ?(password( recovery)?|tech)? ?((customer|technical) (support|service))? (support|contact|telephone|help(line)?|phone) number",
        "kitchen for sale", "pdftoexcelconverter", "keepbrowsersafe",
        "pcerror-fix", "filerepairtool", "combatpcviruses", "SkinCentric",
        "JobsTribune", "join the (great )?illuminati", "Brorsoft", "Remo Recover",
        "kinnaristeel", "clash of (clan|stone)s? (cheats?|tricks?|gems?)",
        r"(?x:B [\s_]* A [\s_]* M \W{0,5} W [\s_]* A [\s_]* R [\s_]* \.? [\s_]* C [\s_]* O [\s_]* M)",
        "slumber pm", "1-844-400-7325", "bestcollegechina",
        "bbwdesire", "rsorder", "Shopping ?Cart ?Elite", "Easy ?Data ?Feed",
        "breasts? enlargement", "best (hotel|property) management", "eduCBA", "Solid[ -]?SEO[ -]?Tools",
        "maxman ?power", "niagen", "Testo (X|Black)", "day ?trading ?academy",
        "skinology", "folliplex", "yafei ?cable", "MSP ?Hack ?Tool",
        "uggs ?on ?sale", "PhenQ", "Hack ?Tool ?2015", "ATM hackers?",
        "Vigoraflo", "Fonepaw", "Provasil", "Slimera", "Cerebria", "Xanogen",
        "intellipaat", "Replennage", "Alpha XTRM", "Synagen", "Nufinity",
        "V[ -]?Stamina", "Gynectrol", "Adderin", "Whizz Systems?", "intellux", "viooz",
        "smartican", "T-complex", u"фальшивы(е|х) (деньги|денег|купюры?)",
        "raging lion", "(love|miracle).*spell ?casters?", "08151871776", "retrodynamic formula",
        "^.{0,199}(contact|offer|join).{0,99}\d{9}.{0,99}$", "Krojam(Soft|Cleaner)?", "FilesSearch ?Tool",
        "teksonit", "Re@d More", "Live Streaming</a", "Blackcore ?Edge", "Copy Buffett", "Push Money App",
        "Volive( Solutions)?", "Herbalife", "Accumass", "purple rhino male enhancement", "Dating Coaching",
        "male enhancement supplements", "alpha levo", "digital marketing course", "stark trading system",
        "bring back lost lover", "service proposal essay", "enetdocumentation", "okaygoods",
        "dr ?eziza", "(spell(home)?|temple|classes)@gmail\\.com", "viagra", "cialis", "slotobit",
        "putlocker", "vimax", "(contact|call) us today", "call \\d{3}-\\d{4}-\\d{4}",
        "I knew I wanted to get him alone, but I couldn.t be obvious about it. So, I came up with a plan. I waited",
        "Yeah! I had some liquid courage. I figured I would give it a shot. The worst he could say was no! Plus the semester",
        "friends that I came to UCU  a virgin and the first day I lost my virginity in a shower with two girls",
        "As I am carrying my personal effects to my room, I spot this girl, probably another fresher, sex hungry as I am",
    ]
    bad_keywords_nwb = [
        u"ಌ", "vashi?k[ae]r[ae]n", "babyli(ss|cious)", "garcinia", "cambogia", "acai ?berr",  # "nwb" == "no word boundary"
        "(eye|skin|aging) ?cream", "b ?a ?m ?((w ?o ?w)|(w ?a ?r))", "online ?it ?guru",
        "abam26", "watch2live", "cogniq", "(serum|lift) ?eye", "tophealth", "poker[ -]?online",
        "caralluma", "male\\Wperf", "anti[- ]?aging", "lumisse", "(ultra|berry|body)[ -]?ketone",
        "(cogni|oro)[ -]?(lift|plex)", "diabazole", "forskolin", "tonaderm", "luma(genex|lift)",
        "(skin|face|eye)[- ]?(serum|therapy|hydration|tip|renewal|gel|lotion|cream)",
        "(skin|eye)[- ]?lift", "(skin|herbal) ?care", "nuando[ -]?instant", "\\bnutra", "nitro[ -]?slim", "aimee[ -]?cream",
        "slimatrex", "cosmitone", "smile[ -]?pro[ -]?direct", "bellavei", "opuderm",
        "contact (me|us)\\W*<a ", "follicure", "kidney[ -]?bean[ -]?extract", "ecoflex",
        "\\brsgold", "bellavei", "goji ?xtreme", "lumagenex", "ajkobeshoes", "kreatine",
        "packers.{0,15}(movers|logistic).{0,25}</a>", "guaranteedprofitinvestment",
        "(brain|breast|male|penile|penis)[- ]?(enhance|enlarge|improve|boost|plus|peak)",
        "renuva(cell|derm)", " %uh ", " %ah ", "svelme", "tapsi ?sarkar", "viktminskning",
        "unique(doc)?producers", "green ?tone ?pro", "troxyphen", "seremolyn", "revolyn",
        "(?:networking|cisco|sas|hadoop|mapreduce|oracle|dba|php|sql|javascript|js|java|designing|marketing|salesforce|joomla)( certification)? (courses?|training).{0,25}</a>",
        "(?:design|development|compan(y|ies)|training|courses?|automation).{0,8}\\L<city>",
        u"Ｃ[Ｏ|0]Ｍ", "ecoflex", "no2factor", "no2blast", "sunergetic", "capilux", "sante ?avis",
        "enduros", "dianabol", "ICQ#?\d{4}-?\d{5}", "3073598075", "lumieres", "viarex", "revimax",
        "celluria", "viatropin", "(meg|test)adrox", "nordic ?loan ?firm", "safflower",
        "(essay|resume|article|dissertation|thesis) ?writing ?service", "satta ?matka", "bojiter"
    ]
    blacklisted_websites = [
        "online ?kelas", "careyourhealths", "wowtoes", "(naga|dewa)poker", "reshapeready\\.com",
        "ipubsoft", "orabank", "powerigfaustralia", "rankassured\\.com", "ewebtonic\\.in",
        "maletestosteronebooster", "menintalk", "king-steroid", "dragonblazewiki\\.com",
        "healthcaresup", "filerepairforum", "beautyskin", "innovativehostingcorp",
        "lxwpro-t", "casque-beatsbydre", "tenderpublish", "predictway\\.com", "up24\\.pro",
        "funmac", "lovebiscuits", "z-data.blogspot.com", "pub4sure\\.com", "freeprnow\\.com",
        "Eglobalfitness", "musclezx90site", "fifapal", "mentorshouse\\.com", "jobshelp\\.in",
        "hits4slim", "screenshot\\.net", "downloadavideo\\.net", "nutirions\\.com",
        "sh\\.st/", "//adf\\.ly/", "//j\\.gs/", "centerweb10", "okaygoods\\.com",
        "preply\\.com", "hellofifa", "chinadivision", "driverdr\\.com", "rsgp4u\\.com",
        "fifa\\d*online", "wearepropeople.com", "tagwitty", "codetoils\\.com", "htstore\\.info",
        "axsoccertours", "ragednablog", "ios8easyjailbreak", "webforpc\\.com", "vbuycars\\.com",
        "totalfitnesspoint", "trustessaywriting", "thesispaperwriters", "homeworkhelponline",
        "trustmyessay", "faasoft", "besttvshows", "mytechlabs", "Housecarbike\\.com",
        "giikers", "pagetube", "myenv\\.org", "testkiz\\.com", "nebusconitirk", "boxasian\\.com",
        "pelevoniface", "herintalk", "menshealth", "examguidez", "kynix\\.com",
        "skinphysiciantips", "xtrememusclerecoveryrev", "xtgenixau\\.com", "orignalsoft\\.com",
        "diabacordoesitwork", "mixresult\\.com", "win-ipad\\.", "mecharithm\\.com",
        "healthy?(advise|finder|booklet|order|rewind|flyup|buzzer|victory|peters|guide)",
        "hyperglycemiaabout", "waffor\\.com", "feedcabal\\.com", "koohenoorgroup\\.com",
        "sourceforge\\.net/projects/freepdftojpgconverter", "latestdatabase\\.com",
        "pdftoexel\\.wordpress\\.com", "best7th\\.in", "resolit\\.us", "techinpost\\.com",
        "malwaretips", "hackerscontent\\.com", "hrsoftwaresolution\\.com", "qboffers\\.com",
        "webbuildersguide\\.com", "idealshare\\.net", "lankabpoacademy\\.com", "\\Wfita\\.in\\W",
        "evomailserver\\.com", "gameart\\.net", "voonik\\.com", "pulsenight\\.com",
        "sofotex\\.com", "erecteentry", "fairharvardfund", "newfundingpoint\\.com",
        "mybloggingmoney\\.com", "windows-techsupport\\.com", "visaadvicecentre\\.com",
        "drivethelife\\.com", "singlerank\\.com", "sayeureqa\\.com", "callpcexpert\\.com",
        "lafozi\\.com", "open-swiss-bank\\.com", "kalimadedot\\.blogspot", "cadsoftusa\\.com",
        "tenorshare\\.com", "thecasesolutions\\.com", "3dollarlogos\\.com", "inboxsdk\\.com",
        "fix-computer\\.net", "drillpressselect", "chinatour\\.com", "official-?driver",
        "santerevue", "cheatsumo\\.com", "videostir\\.com", "focusitlabs\\.com",
        "smartpcfixer", "1fix\\.org", "code4email\\.com", "nwgolds\\.com", "resumeplus\\.us",
        "drivertuner\\.com", "easyfix\\.org", "errorsfixer\\.org", "diligentwriters\\.com",
        "faq800\\.com", "fix1\\.org", "guru4pc\\.net", "howto4pc\\.org", "isaura\\.info",
        "pceasynow\\.com", "qobul\\.com", "onlinegiftdeal\\.com", "articlebullet\\.com",
        "regeasypro\\.com", "registryware\\.org", "smartfixer\\.(net|org)", "chirbit\\.com",
        "dlllibrary\\.net", "wisefixer\\.(com|net|org)", "dojobsonline\\.com", "/mu6\\.me/",
        "password-?unlocker\\.com", "dropbox18gb\\.com", "mysocialpromos\\.com",
        "passwordtech\\.com", "goshareware\\.com", "digitalacads\\.in", "crichdlive\\.com",
        "nemopdf\\.com", "downloaddailymotion\\.com", "bharatplaza\\.com", "boostmmr\\.com",
        "free-download-youtube\\.com", "free-music-downloader\\.com", "responsivesites\\.net",
        "video-download-capture\\.com", "videograbber\\.net", "gangboard.com", "freelank\\.com",
        "globalvision\\.com\\.vn", "csoftglobal\\.com", "bsscommerce\\.com", "nmeasoft\\.com",
        "remorecover\\.com", "remosoftware\\.com", "freethemes\\.co", "kliring\\.co\\.id",
        "\\bpatch\\.com\\b", "ajgilworld\\.com", "santomais", "viilms", "fashionient\\.com",
        "clashofclansastucegemmes\\.com", "american-writers\\.org", "comaarp.org",
        "bestcelebritiesvideo\\.com", "shopnhlbruins\\.com", "mon-rasage.fr", "systweak\\.com",
        "downloadscanpst\\.com", "downloadgames", "gameshop4u\\.com", "laustan\\.com",
        "listoffreeware\\.com", "bigasoft\\.com", "opclub07\\.com", "tekpirates\\.com",
        "allavsoft", "tryapext\\.com", "essays(origin|council)\\.com", "caseism\\.com",
        "vanskeys\\.com", "cheapessaywritingservice", "edbtopsts\\.com", "appkodes.\\com",
        "texts\\.io", "writage\\.com", "mobitsolutions\\.com", "pokemongodownload\\.co",
        "askpcexperts\\.com", "anonymousvpnsoftware\\.com", "mmfsolutions\\.sg", "ungeekit\\.com",
        "ecouponcode\\.com", "wasel(pro)?\\.com", "i-spire\\.(com|net)", "sandangku\\.com",
        "iwasl\\.com", "vpn(faqs|answers|ranks|4games)\\.com", "airmore\\.com", "showmore\\.com",
        "unblockingtwitter\\.com", "openingblockedsite\\.com", "credenceresearch\\.com",
        "arabic(soft)?downloads?\\.com", "braindumpsvalid", "cardsbymellc\\.com", "codek\\.tv",
        "couchsurfing\\.com", "sukere\\.com", "elsner\\.com", "latestphonespec\\.com",
        "gta5codes\\.fr", "pcsoftpro\\.com", "addium\\.info", "graspui\\.com", "fifaeasy\\.com",
        "fallclassicrun\\.com", "forgrams\\.com", "windowiso\\.com", "grantelevators\\.com",
        "cloudinsights\\.net", "xtremenitro", "surfmegeek", "techittricks\\.com", "din571\\.com",
        "(premium|priceless)-inkjet\\.com", "meatspin", "techappzone\\.com", "wdtel\\.com",
        "clusterlinks\\.com", "kizi1000\\.in", "weightruinations\\.com", "etrove\\.com\\.sg",
        "products\\.odosta\\.com", "naturacelhelp", "guidemesupss\\.com", "neistersen\\.com",
        "rackons\\.com", "imonitorsoft\\.com", "biginfosys\\.com", "worldofpower\\.co\\.uk",
        "analec\\.com", "livesportstv\\.us", "batteriedepcportable", "heflo\\.com",
        "stadtbett\\.com", "tokoterbaik\\.com", "\\Welance\\.com", "create-new-account\\.com",
        "jetcheats\\.com", "cheatio\\.com", "empiremountainbikes", "assignmentcamp\\.co",
        "optimalstack(facts|products)", "x4facts", "endomondo\\.com", "sulekha\\.com",
        "litindia\\.in", "egovtjobs\\.in", "tipsntrick\\.in", "techstack\\.in", "yatko\\.com",
        "customizedwallpaper\\.com", "oathtohealth\\.com", "appsforwin10\\.com",
        "crevalorsite\\.com", "macfixz\\.com", "moviesexplore\\.com", "computouchinc\\.com",
        "iphoneunlocking\\.org", "driverbasket\\.com", "erasephone\\.com", "femalevenue\\.com",
        "bloggermaking\\.com", "supportphonenumber\\.com", "digitalmantra\\.co", "fcvpn\\.me",
        "prinenidz\\.com", "e-priceinbd", "ecigpre\\.com", "movingexpert\\.in", "1stquest\\.com",
        "maddenmobilehack", "supplements4help", "watchtheboxing", "scriptbaran\\.com",
        "cacherealestate\\.com", "Matrixhackka007", "aoatech\\.com", "leonardhysaj\\.com",
        "pharaohtools", "msoutlooktools\\.com", "softwarezee", "imobie\\.com", "primosync\\.com",
        "i-hire\\.pro", "pandamw\\.com", "hariraya2015\\.net", "devpost\\.com", "genglobal\\.org",
        "multipelife\\.com", "seasoncars\\.com", "evolvedlifevisions\\.com", "leptigentry\\.com",
        "flexihub\\.com", "\\.debt\\.com", "websiteseochecker\\.com", "fullsoftversion\\.com",
        "hotfrog\\.ca", "snorg(content|tees)\\.com", "webtechcoupons", "diwaliimages\\d+\\.in",
        "architecturedesign\\.tk", "playerhot\\.com", "fitwaypoint\\.com", "usefulpcguide\\.com",
        "xinyanlaw", "ultrafinessesite", "sunitlabs\\.com", "puravol\\.net", "2captcha\\.com",
        "statesmovie", "cleanlean", "iFoneMate", "babygames5\\.com",
        "replacementlaptopkeys\\.com", "safewiper\\.com", "ostoto\\.com",
        "academicservices\\.us", "writerspk\\.com",
        "musclebuilding(products|base)", "Blogdolllar\\.net", "bendul\\.com",
        "megatachoco", "shtylm\\.com", "drilluobetemple\\.webs",
        "creative-proteomics", "revommerce.com", "opendatascience\\.com",
        "123trainings", "(bestof|beta)cheat\\.com", "surejob\\.in",
        "israelbigmarket", "chinatour\\.com", "savemantra\\.com",
        "imeshlab\\.com", "sagacademy\\.com", "moderncar\\.com", "[/.]iwacy\\.com",
        "topbartercard\\.com", "couponconnexion\\.com", "npmedicalhome\\.com",
        "ironbe\\.com", "sedancoupeseriesspecs\\.com", "techvaid\\.com", "pirachaexports\\.com",
        "fastunsecured\\.com", "fullchatroom\\.com", "ecartbasiccartlead",
        "edigitalplace\\.com", "plagiarismchecker\\.(us|com)", "excelanto\\.com",
        "trylxwprot", "geniusbrain", "clazwork", "doorgrow\\.com", "ibworldacademy",
        "pdfask\\.com", "bookbrokerz\\.com", "solarismovies", "giftsinmind\\.co",
        "eximiussoftsolutions\\.com", "droid4apk\\.", "canwestcellular",
        "pages\\.rediff\\.com", "limitlesspill", "eltib2\\.wordpress\\.com",
        "access-electronic\\.co", "guyideas\\.esy\\.es", "alconelectronics\\.com",
        "quicksolutionspell", "metaboostsite", "digicheat\\.com", "socialviralize\\.com",
        "[./]occn\\.org", "illusiongroups\\.com", "varite\\.com", "hooraysoft\\.com",
        "gcbxnow\\.com", "godowell\\.net", "place4papers", "tradingqna\\.com",
        "shacamerica\\.net", "nillowpages\\.com", "letsnurture\\.com",
        "rozapk\\.com", "jihosoft\\.com", "mahnazmezon\\.com", "technical-care\\.com",
        "skyformation\\.com", "shifting(expert|solutions)\\.in", "bandsawjudge\\.com",
        "liveestorebuilder\\.com", "exampracticequestions\\.com", "createspace\\.com",
        "fun-flicks\\.com", "smarketingclub\\.com", "cbitss\\.in",
        "o-lovius\\.com", "aldovmcgregor\\.co", "priredeream\\.com", "quicksearch\\.in",
        "adonads\\.com", "uufix\\.com", "slimrootz\\.com", "robomart\\.com", "fedotov\\.co",
        "uflysoft\\.net", "simicart\\.com", "sellcvv\\.co", "oprfid\\.com",
        "thereferraltask\\.net", "voxforem\\.com", "writeversity\\.com",
        "labstech\\.org", "rikshairuym", "zicamagsopt", "how2world\\.com", "splendyrsite\\.net",
        "3gwith4g\\.com", "xride-hd\\.com", "sincycle\\.com", "wcwnetworking\\.com",
        "vivaspanish\\.org", "wanglu123\\.com", "z0download\\.com", "citehr\\.com",
        "thecreatingexperts\\.com", "masterm\\.com", "ablockplus\\.org", "iseenlab\\.com",
        "whatech\\.com", "fileniaz\\.com", "icoolsoft\\.com", "agriya\\.com",
        "wonderful-watch\\.co", "plagiarism-checker\\.me", "asodoneright",
        "sapboonline\\.com", "thinkittraining\\.in", "salesforcetrainingexpert\\.in",
        "indiaflower", "achatlaser\\.com", "desimahol\\.com", "independentracingwheel",
        "latestone\\.com", "iwebsoul\\.com", "uttarakhandshadi", "kaintek\\.com", "giftcodes\\.net",
        "josmprtion\\.com", "pc-helpp\\.com", "tufflo\\.com", "MobiKin\\.com", "manualbirds\\.com",
        "assignmentbay\\.co", "nora777\\.com", "nutpile\\.com", "traffic-bots\\.com",
        "chatsim\\.com", "mlkblasters\\.org", "champcash\\.com", "bisbury\\.com",
        "rankyouup\\.com", "reviewanalysis\\.co", "apponfly\\.com", "gogames\\.me",
        "trutech\\.co", "askmespam\\.com", "imdresses\\.com", "doesitscam\\.com",
        "jobsopening\\.co\\.in", "retersweld\\.com", "mindextra\\.com", "upcoming-trend\\.com",
        "psychicfuguestudio", "softserialhq\\.com", "unstopableshrine\\.webs\\.com",
        "softaken\\.com", "lyonstechnologies", "serialkeygeneratorfree\\.com", "routeperfect\\.com",
        "tupely\\.com", "apk(heart|safe)\\.com", "uflysoft\\.net", "nimblemessaging\\.com",
        "oleville\\.net", "nutribulletrecipes\\.org", "wirexapp\\.com", "x4up\\.org",
        "decalontop\\.com", "urlopener\\.com", "mobile57\\.com", "learn(spicy|perfact)",
        "getfitness\\.in", "trustwiko\\.com", "attendasoft", "selfybuzz\\.com", "meritcampus\\.com",
        "fastindiaservice\\.com", "shharshsajv", "fizyetimusing", "fornatgaex", "shwesanenid",
        "accountingassignments\\.help", "phphelponline\\.com", "eremaxfuncionabr", "zu-rich\\.li",
        "appsapkfile\\.com", "bandarterbaikterpercaya\\.net", "yourdailymovie\\.com",
        "ipinteria\\.com", "blogines\\.com", "stepupheights\\.com", "gfix\\.in",
        "aminoprimexl\\.com", "csharpstar\\.com", "vbscore\\.com", "blueeagleindia\\.com",
        "vizayn\\.com", "androidpureapk\\.com", "hzxiaoya\\.com",
        "upsafe\\.com", "spiritsofts\\.com", "rcptec\\.com", "gmax-brasil\\.com", "icognix\\.net",
        "\\Wpysoft\\.com", "zescode\\.com", "eserviceshelp\\.in", "captainform\\.com",
        "techiphone\\.com", "kmminoaq4yci5woj\\.onion", "BlackListHackers\\.com",
        "transferphone\\.com", "hindipathshala\\.com", "applify\\.co", "armmlm\\.com",
        "snipercrack\\.tk", "averagemaleheight\\.tk", "educba\\.com", "neosurftobitcoin\\.net",
        "silver-card\\.net", "cards101\\.net", "hakerstars\\.com", "king-dumps\\.us",
        "cuidados-saude", "klereumcol\\.com", "gupshupchatroom\\.com", "petsworld\\.in",
        "godiabetesrevenge", "reflectivevestsindia", "anyframe\\.net", "canadianprofits\\.tv",
        "dcweddingandevents\\.com", "slimdreneavis", "wefix365\\.us", "esofttools\\.com",
        "wondershare\\.com", "pulsionerotica\\.com", "worldtraveltime\\.net", "antivirus\\.comodo\\.com",
        "cardvdonline\\.com", "icasnetwork\\.org", "epicresearch\\.co", "\\.soup\\.io", "pccdkeys\\.com",
        "hotxt\\.co\\.uk", "rcframecontractors", "bsgolds\\.com", "thedropnet\\.com",
        "science\\.misis\\.ru", "pdf\\.ac/", "slotobit\\.com", "thaykinhmanhinhcamung\\.com",
        "sfdcbot\\.herokuapp\\.com", "technosanatgroup\\.com", "csgostrong\\.com",
        "emget\\.net", "gevezemirc\\.com", "divinenutrions\\.com", "ace23\\.tk", "fbsparta\\.com",
        "delhigurgaon\\.in", "gurgaonsex\\.com", "mehedi399blog", "myfundbucket\\.com",
        "zaputra\\.com", "ok8uk\\.org\\.uk", "visitdevonandcornwall\\.co\\.uk",
        "discussfact\\.com", "sirabhinavjain\\.com", "moneytransfercomparison\\.co", "rospher\\.com",
        "exchangeratetoday\\.co", "currencysolutions\\.co", "accudb\\.com", "iqdermaessentials\\.com",
        "grey-areaweed\\.com", "360musicng\\.co", "oyetrade\\.com", "softwarednl.com", "800support\\.net",
        "trickspaid\\.com", "bulksmsclub\\.com", "redbubble\\.com", "joomag\\.com", "bigclasses\\.com",
        "ladybirdco\\.com", "magehit\\.com", "colors34.com", "ultimatewowguide\\.com", "fiverr\\.com/\\w+",
        "shaperich\\.com", "ugccoaching\\.com", "androidpluspc\\.com", "learnit\\.technology", "mastersite\\.com\\.ua",
        "jobstelangana\\.in", "readyscript\\.ru", "unlock-bootloaderb\\.xyz", "romrootandroid\\.xyz", "drozforskolin\\.org",
        "supplementsadvisor\\.org", "pokercheatcenter\\.com", "intelligentadvices\\.com", "yoursbetterhealthsolutions\\.com",
        "makehimmine\\.com\\.au", "shopicheck\\.com", "hivimoore\\.com", "blogmium\\.com", "soundmagic\\.us",
        "onlinecorrection\\.com", "dragracerv3game\\.com", "bananakong\\.net", "himzakaz\\.net", "dropcrack\\.com",
        "raybiztech\\.com", "cegonsoft\\.com", "technomaniya\\.com", "instantassignmenthelp\\.com\\.au", "huintech\\.com",
        "dramaonline\\.pk", "gamingustaad\\.com", "carding-wutransfer\\.com", "nulife\\.co\\.in", "fixmyprinter\\.com",
        "iseepassword\\.com", "samedaypros\\.com", "zen-promo\\.com", "seyf-educ\\.com", "moneybanker\\.no",
        "webhax\\.xyz",
    ]
    # Patterns: the top three lines are the most straightforward, matching any site with this string in domain name
    pattern_websites = [
        r"(enstella|recoverysoftware|removevirus|support(number|help|quickbooks)|techhelp|calltech|exclusive|onlineshop|video(course|classes|tutorial(?!s))|vipmodel|(?<!word)porn|wholesale|inboxmachine|(get|buy)cheap|escort|diploma|(govt|government)jobs|extramoney|earnathome|spell(caster|specialist)|profits|seo-?(tool|service|trick|market)|onsale|fat(burn|loss)|(\.|//|best)cheap|online-?(training|solution))[\w-]*?\.(co|net|org|in\W|info|ir|wordpress|blogspot|tumblr|webs\.)",
        r"(replica(?!t)|rs\d?gold|rssong|runescapegold|maxgain|e-cash|mothers?day|phone-?number|fullmovie|tvstream|trainingin|dissertation|(placement|research)-?(paper|statement|essay)|digitalmarketing|infocampus|cracked\w{3}|bestmover|relocation|\w{4}mortgage|loans|revenue|testo[-bsx]|cleanse|cleansing|detox|supplement|lubricant|serum|wrinkle|topcare|freetrial)[\w-]*?\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(drivingschool|crack-?serial|serial-?(key|crack)|freecrack|appsfor(pc|mac)|probiotic|remedies|heathcare|sideeffect|meatspin|packers\S{0,3}movers|(buy|sell)\S{0,12}cvv|goatse|burnfat|gronkaffe|muskel|tes(tos)?terone|nitric(storm|oxide)|masculin|menhealth|intohealth|babaji|spellcaster|potentbody|slimbody|moist|lefair|derma(?![nt])|xtrm|factorx|(?<!app)nitro(?!us)|endorev|ketone)[\w-]*?\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(moving|\w{10}spell|[\w-]{3}password|\w{5}deal|\w{5}facts|\w\dfacts|\Btoyshop|[\w-]{5}cheats|[\w-]{6}girls|clothing|shoes(inc)?|cheatcode|cracks|credits|-wallet|refunds|truo?ng|viet|trang)\.(co|net|org|in\W|info)",
        r"(health|earn|max|cash|wage|pay|pocket|cent|today)[\w-]{0,6}\d+\.com",
        r"(//|www\.)healthy?\w{5,}\.com",
        r"https?://[\w-.]\.repair\W", r"https?://[\w-.]{10,}\.(top|help)\W", r'https?://[\w-.]*-[\w-.]*\.pro[/"<]',
        r"filefix(er)?\.com", r"\.page\.tl\W", r"infotech\.(com|net|in)",
        r"\.(com|net)/(xtra|muscle)[\w-]", r"http\S*?\Wfor-sale\W",
        r"fifa\d+[\w-]*?\.com", r"[\w-](giveaway|jackets|supplys|male)\.com",
        r"((essay|resume|click2)\w{6,}|(essays|(research|term)paper|examcollection|[\w-]{5}writing|writing[\w-]{5})[\w-]*?)\.(co|net|org|in\W|info|us)",
        r"(top|best|expert)\d\w{0,15}\.in\W", r"\dth(\.co)?\.in", r"(jobs|in)\L<city>\.in",
        r"[\w-](recovery|repairs?|rescuer|(?<!epoch|font)converter)(pro|kit)?\.(com|net)", r"(corrupt|repair)[\w-]*?\.blogspot",
        r"http\S*?(yahoo|gmail|hotmail|outlook|office|microsoft)[\w-]{0,10}(account|tech|customer|support|service|phone|help)[\w-]{0,10}(service|care|help|recovery|support|phone|number)",
        r"http\S*?(essay|resume|thesis|dissertation|paper)-?writing",
        r"fix[\w-]*?(files?|tool(box)?)\.com", r"(repair|recovery|fix)tool(box)?\.(co|net|org)",
        r"smart(pc)?fixer\.(co|net|org)",
        r"password[\w-]*?(cracker|unlocker|reset|buster|master|remover)\.(co|net)",
        r"crack[\w-]*?(serial|soft|password)[\w-]*?\.(co|net)",
        r"(downloader|pdf)converter\.(com|net)", r"sourceforge\.net[\w/]*convert",
        r"ware[\w-]*?download\.(com|net|info|in\W)",
        r"((\d|\w{3})livestream|livestream(ing|s))[\w]*?\.(com|net|tv)", r"\w+vs\w+live\.(com|net|tv)",
        r"(play|watch|cup|20)[\w-]*?(live|online)\.(com|net|tv)", r"worldcup\d[\w-]*?\.(com|net|tv|blogspot)",
        r"https?://(\w{5,}tutoring\w*|cheat[\w-.]{3,}|xtreme[\w-]{5,})\.",
        r"(platinum|paying|acai|buy|premium|premier|ultra|thebest|best|[/.]try)[\w]{10,}\.(co|net|org|in\W|info)",
        r"(training|institute|marketing)[\w-]{6,}[\w.-]*?\.(co|net|org|in\W|info)", r"[\w-](courses?|training)[\w-]*?\.in/",
        r"\w{9}(buy|roofing)\.(co|net|org|in\W|info)",
        r"(vitamin|dive|hike|love|strong|ideal|natural|pro|magic|beware|top|best|free|cheap|allied|nutrition|prostate)[\w-]*?health[\w-]*?\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(eye|skin|age|aging)[\w-]*?cream[\w-]*?\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(acai|advance|aging|alpha|beauty|belle|beta|biotic|body|boost|brain(?!tree)|burn|colon|[^s]cream|creme|derma|ecig|eye|face(?!book)|fat|formula|geniu[sx]|grow|hair|health|herbal|ideal|luminous|male|medical|medicare|muscle|natura|no2|nutrition|optimal|pearl|perfect|phyto|probio|rejuven|revive|ripped|rx|scam|shred|skin|slim|super|testo|[/.]top|trim|[/.]try|ultra|ultra|vapor|vita|weight|wellness|xplode|yoga|young|youth)[\w]{0,20}(about|advi[sc]|assess|blog|brazil|canada|care|center|centre|chat|complex(?!ity)|congress|consult|critic|critique|cure|denmark|discussion|doctor|dose|essence|essential|extract|fact|formula|france|funct?ion|genix|guide|help|idea|info|jacked|l[iy]ft|mag|market|max|mexico|norway|nutrition|order|plus|points|policy|potency|power|practice|pro|program|report|review|rewind|site|slim|solution|suppl(y|ier)|sweden|tip|trial|try|world|zone)[.\w-]{0,12}\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(\w{11}(idea|income|sale)|\w{6}(advice|problog|review))s?\.(co|net|in\W|info)",
        r"-(poker|jobs)\.com",
        r"send[\w-]*?india\.(co|net|org|in\W|info)",
        r"(file|photo|android|iphone)recovery[\w-]*?\.(co|net|org|in\W|info)",
        r"(videos?|movies?|watch)online[\w-]*?\.", r"hd(video|movie)[\w-]*?\.",
        r"backlink(?!(o\.|watch))[\w-]*?\.(co|net|org|in\W|info)",
        r"(replica[^nt]\w{5,}|\wrolex)\.(co|net|org|in\W|info)",
        r"customer(service|support)[\w-]*?\.(co|net|org|in\W|info)",
        r"conferences?alert[\w-]*?\.(co|net|org|in\W|info)",
        r"seo\.com(?!/\w)", r"\Wseo[\w-]{10,}\.(com|net|in\W)",
        r"(?<!site)24x7[\w-]*?\.(co|net|org|in\W|info)",
        r"backlink[\w-]*?\.(com|net|de|blogspot)",
        r"(software|developers|packers|movers|logistic|service)[\w-]*?india\.(com|in\W)",
        r"scam[\w-]*?(book|alert|register|punch)[\w-]*?\.(co|net|org|in\W|info)",
        r"http\S*?crazy(mass|bulk)", r'http\S*\.com\.com[/"<]',
        r"https?://[^/\s]{8,}healer",
        r"\w{9}rev\.com", r'reddit\.com/\w{6}/"',
        r"world[\w-]*?cricket[\w-]*?\.(co|net|org|in\W|info)",
        r"(credit|online)[\w-]*?loan[\w-]*?\.(co|net|org|in\W|info)",
        r"worldcup\d+live\.(com?|net|org|in\W|info)",
        r"((concrete|beton)-?mixer|crusher)[\w-]*?\.(co|net)",
        r"\w{7}formac\.(com|net|org)",
        r"sex\.(com|net|info)", r"https?://(www\.)?sex",
        r"[\w-]{12}\.(webs|66ghz)\.com", r'online\.us[/"<]',
        r"ptvsports\d+.com",
    ]
    city_list = [
        "Agra", "Amritsar", "Bangalore", "Bhopal", "Chandigarh", "Chennai", "Coimbatore", "Delhi", "Dubai", "Durgapur",
        "Ghaziabad", "Hyderabad", "Jaipur", "Jalandhar", "Kolkata", "Ludhiana", "Mumbai", "Madurai", "Patna", "Portland",
        "Rajkot", "Surat", "Telangana", "Udaipur", "Uttarakhand", "India", "Pakistan",  # yes, these aren't cities but...
    ]
    rules = [
        # Sites in sites[] will be excluded if 'all' == True.  Whitelisted if 'all' == False.
        #
        # Category: Bad keywords
        # The big list of bad keywords, for titles and posts
        {'regex': ur"(?is)\b({})\b|{}".format("|".join(bad_keywords), "|".join(bad_keywords_nwb)), 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 4, 'max_score': 1},
        # baba and nike are restricted to the beginning of posts: many false positives otherwise
        {'regex': ur"(?is)^.{0,200}\bnike ", 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 11, 'max_score': 0},
        # gratis at the beginning of post, SoftwareRecs is exempt
        {'regex': ur"(?is)^.{0,200}\bgratis\b$", 'all': True,
         'sites': ['softwarerecs.stackexchange.com'], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 11, 'max_score': 0},
        # Black magic at the beginning of question, Islam is exempt
        {'regex': ur"^(?is).{0,200}black magic", 'all': True,
         'sites': ["islam.stackexchange.com"], 'reason': "black magic in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'answers': False, 'max_rep': 11, 'max_score': 0},
        # Bad keywords in titles and usernames, all sites
        {'regex': ur"(?i)^(?:(?=.*?\b(?:online|hd)\b)(?=.*?(?:free|full|unlimited)).*?movies?\b)|(?=.*?\b(?:acai|kisn)\b)(?=.*?care).*products?\b|(?=.*?packer).*mover|(online|certification).*?training|\bvs\b.*\b(live|vivo)\b|(?<!can |uld )\bwe offer\b|payday loan|смотреть.*онлайн|watch\b.{0,50}(online|episode|free)|episode.{0,50}\bsub\b", 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Bad keywords in titles only, all sites
        {'regex': ur"(?i)\b(?!s.m.a.r.t)[a-z]\.+[a-z]\.+[a-z]\.+[a-z]\.+[a-z]\b", 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Eltima: separated into its own method so we can constrain length
        {'method': has_eltima, 'all': True, 'sites': [], 'reason': "bad keyword in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 50, 'max_score': 0},
        # Fake-customer-service in title
        {'method': has_customer_service, 'all': True, 'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Bad health-related keywords in titles, health sites are exempt
        {'regex': ur"(?i)\b((beauty|skin|health|face|eye)[- ]?(serum|therapy|hydration|tip|renewal|shop|store|lyft|product|strateg(y|ies)|gel|lotion|cream|treatment|method|school|expert)|fat ?burn(er|ing)?|muscle|testo ?[sx]\w*|body ?build(er|ing)|wrinkle|probiotic|acne|peni(s|le)|erection)s?\b|(beauty|skin) care\b", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com", "robotics.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Bad health-related keywords in titles, health sites are exempt, flexible method
        {'method': has_health, 'all': False,
         'sites': ["stackoverflow.com", "superuser.com", "askubuntu.com", "drupal.stackexchange.com", "meta.stackexchange.com", "webapps.stackexchange.com", "security.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Bad health-related keywords in titles and posts, health sites are exempt
        {'regex': ur"(?is)virility|diet ?(plan|pill)|\b(pro)?derma(?=[a-su-z ]\w)|(fat|(?<!dead[ -]?)weight)[ -]?(loo?s[es]|reduction)|loo?s[es] ?weight|erectile|\bherpes\b|colon ?(detox|clean)|\bpenis\b", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com", "bicycles.stackexchange.com", "islam.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # Korean character in title: requires 3
        {'regex': ur"(?i)\p{Script=Hangul}.*\p{Script=Hangul}.*\p{Script=Hangul}", 'all': True,
         'sites': ["korean.stackexchange.com"], 'reason': "Korean character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Chinese characters in title: requires 3
        {'regex': ur"(?i)\p{Script=Han}.*\p{Script=Han}.*\p{Script=Han}", 'all': True,
         'sites': ["chinese.stackexchange.com", "japanese.stackexchange.com", "ja.stackoverflow.com"], 'reason': "Chinese character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Hindi character in title
        {'regex': ur"(?i)\p{Script=Devanagari}", 'all': True,
         'sites': ["hinduism.stackexchange.com"], 'reason': "Hindi character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Other suspicious characters in title
        {'regex': ur"(?i)\p{Block=EnclosedAlphanumerics}|\p{Block=Cherokee}|\p{Block=Georgian}|\p{Block=MiscellaneousSymbols}|\p{Block=MiscellaneousSymbolsAndPictographs}", 'all': True,
         'sites': ["stackoverflow.com", "chinese.stackexchange.com", "japanese.stackexchange.com", "ja.stackoverflow.com", "korean.stackexchange.com"], 'reason': "Bad character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # English text on non-English site: rus.SE only
        {'regex': ur"(?i)^[a-z0-9_\W]*[a-z]{3}[a-z0-9_\W]*$", 'all': False,
         'sites': ["rus.stackexchange.com"], 'reason': "English text in {} on a localized site", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Roof repair
        {'regex': u"roof repair", 'all': True,
         'sites': ["diy.stackexchange.com", "outdoors.stackexchange.com", "mechanics.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 11, 'max_score': 0},
        # Bad keywords (only include link at end sites + SO, the other sites give false positives for these keywords)
        {'regex': ur"(?i)(?<!truth )serum|\b(?<!to )supplements\b", 'all': False, 'sites': ["stackoverflow.com", "superuser.com", "askubuntu.com", "drupal.stackexchange.com", "meta.stackexchange.com", "security.stackexchange.com", "patents.stackexchange.com", "money.stackexchange.com", "gaming.stackexchange.com", "arduino.stackexchange.com", "workplace.stackexchange.com"],
         'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # Mostly non-Latin alphabet
        {'method': mostly_non_latin, 'all': True,
         'sites': ["stackoverflow.com", "ja.stackoverflow.com", "pt.stackoverflow.com", "es.stackoverflow.com", "islam.stackexchange.com", "japanese.stackexchange.com", "anime.stackexchange.com", "hinduism.stackexchange.com", "judaism.stackexchange.com", "buddhism.stackexchange.com", "chinese.stackexchange.com", "french.stackexchange.com", "spanish.stackexchange.com", "portuguese.stackexchange.com", "codegolf.stackexchange.com", "korean.stackexchange.com"],
         'reason': 'mostly non-Latin {}', 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # Mostly non-Latin alphabet, SO answers only
        {'method': mostly_non_latin, 'all': False,
         'sites': ["stackoverflow.com"],
         'reason': 'mostly non-Latin {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'questions': False, 'max_rep': 1, 'max_score': 0},
        #
        # Category: Suspicious links
        # Blacklisted sites
        {'regex': u"(?i)({})".format("|".join(blacklisted_websites)), 'all': True,
         'sites': [], 'reason': "blacklisted website in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 50, 'max_score': 5},
        # Suspicious sites
        {'regex': ur"(?i)({}|({})[\w-]*?\.(co|net|org|in\W|info|blogspot|wordpress))(?![^>]*<)".format("|".join(pattern_websites), "|".join(bad_keywords_nwb)), 'all': True,
         'sites': [], 'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 1, 'max_score': 1},
        # Bad keyword in link text
        {'method': bad_link_text, 'all': True,
         'sites': [], 'reason': 'bad keyword in link text in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Country-name domains, travel and expats sites are exempt
        {'regex': ur"(?i)([\w-]{6}|shop)(australia|brazil|canada|denmark|france|india|mexico|norway|pakistan|spain|sweden)\w{0,4}\.(com|net)", 'all': True,
         'sites': ["travel.stackexchange.com", "expatriates.stackexchange.com"], 'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # The TLDs of Iran, Pakistan, and Tokelau in answers
        {'regex': ur'(?i)http\S*\.(ir|pk|tk)[/"<]', 'all': True,
         'sites': [], 'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 1, 'max_score': 0, 'questions': False},
        # Suspicious health-related websites, health sites are exempt
        {'regex': ur"(?i)(bodybuilding|workout|fitness|diet|perfecthealth|muscle|nutrition|prostate)[\w-]*?\.(com|co\.|net|org|info|in\W)", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com", "bicycles.stackexchange.com"], 'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 4, 'max_score': 2},
        # Links preceded by arrows >>>
        {'regex': ur"(?is)(>>>|==\s*>>|====|===>|==>>|= = =|(Read More|Click Here) \W{2,20}).{0,20}http(?!://i.stack.imgur.com).{0,200}$", 'all': True,
         'sites': [], 'reason': "link following arrow in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': True, 'body_summary': False, 'answers': False, 'max_rep': 11, 'max_score': 0},
        # Link at the end of question, selected sites
        {'method': link_at_end, 'all': False,
         'sites': ["superuser.com", "askubuntu.com", "drupal.stackexchange.com", "meta.stackexchange.com", "security.stackexchange.com", "patents.stackexchange.com", "money.stackexchange.com", "gaming.stackexchange.com", "arduino.stackexchange.com", "workplace.stackexchange.com"], 'reason': 'link at end of {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'answers': False, 'max_rep': 1, 'max_score': 0},
        # Link at the end of a short answer
        {'regex': ur'(?is)^.{0,350}<a href="https?://(?:(?:www\.)?[\w-]+\.(?:blogspot\.|wordpress\.|co\.)?\w{2,4}/?\w{0,2}/?|(?:plus\.google|www\.facebook)\.com/[\w/]+)"[^<]*</a>(?:</strong>)?\W*</p>\s*$|\[/url\]\W*</p>\s*$', 'all': True,
         'sites': [], 'reason': 'link at end of {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Link with "thanks for sharing" or a similar phrase in a short answer
        {'method': keyword_link, 'all': True,
         'sites': [], 'reason': 'bad keyword with a link in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # non-linked .tk site at the end of an answer
        {'regex': ur'(?is)\w{3}\.tk(?:</strong>)?\W*</p>\s*$', 'all': True,
         'sites': [], 'reason': 'pattern-matching website in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # non-linked site at the end of a short answer
        {'regex': ur'(?is)^.{0,350}\w{6}\.(com|co\.uk)(?:</strong>)?\W*</p>\s*$', 'all': True,
         'sites': [], 'reason': 'link at end of {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Shortened URL near the end of question
        {'regex': ur"(?is)://(goo\.gl|bit\.ly|bit\.do|tinyurl\.com|fb\.me|cl\.ly|t\.co|is\.gd|j\.mp|tr\.im|ow\.ly|wp\.me|alturl\.com|tiny\.cc|9nl\.me|post\.ly|dyo\.gs|bfy\.tw|amzn\.to)/.{0,200}$", 'all': True, 'sites': ["superuser.com", "askubuntu.com"], 'reason': "shortened URL in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'answers': False, 'max_rep': 1, 'max_score': 0},
        # Shortened URL in an answer
        {'regex': ur"(?is)://(goo\.gl|bit\.ly|bit\.do|tinyurl\.com|fb\.me|cl\.ly|t\.co|is\.gd|j\.mp|tr\.im|ow\.ly|wp\.me|alturl\.com|tiny\.cc|9nl\.me|post\.ly|dyo\.gs|bfy\.tw|amzn\.to)/", 'all': True, 'sites': [], 'reason': "shortened URL in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Link text without Latin characters
        {'regex': u">[^0-9A-Za-z<'\"]{3,}</a>", 'all': True,
         'sites': ["ja.stackoverflow.com", "ru.stackoverflow.com", "rus.stackexchange.com", "islam.stackexchange.com", "japanese.stackexchange.com", "hinduism.stackexchange.com", "judaism.stackexchange.com", "buddhism.stackexchange.com", "chinese.stackexchange.com", "russian.stackexchange.com", "codegolf.stackexchange.com", "korean.stackexchange.com"], 'reason': 'non-Latin link in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Link text with some non-Latin characters, answers only
        {'method': non_english_link, 'all': True, 'sites': ["pt.stackoverflow.com", "es.stackoverflow.com", "ja.stackoverflow.com", "ru.stackoverflow.com", "rus.stackexchange.com", "islam.stackexchange.com", "japanese.stackexchange.com", "hinduism.stackexchange.com", "judaism.stackexchange.com", "buddhism.stackexchange.com", "chinese.stackexchange.com", "russian.stackexchange.com", "french.stackexchange.com", "portuguese.stackexchange.com", "spanish.stackexchange.com", "codegolf.stackexchange.com", "korean.stackexchange.com"],
         'reason': 'non-English link in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Link text is one character within a word
        {'regex': ur'(?iu)\w<a href="[^"]+" rel="nofollow">.</a>\w', 'all': True,
         'sites': [], 'reason': 'one-character link in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 11, 'max_score': 1},
        # Link text consists of punctuation, answers only
        {'regex': ur'(?iu)rel="nofollow">\W</a>', 'all': True,
         'sites': [], 'reason': 'linked punctuation in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 11, 'max_score': 1},
        # URL in title, some sites are exempt
        {'regex': ur"(?i)https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}|\w{3,}\.(com|net)\b.*\w{3,}\.(com|net)\b", 'all': True,
         'sites': ["stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com", "ja.stackoverflow.com", "superuser.com", "askubuntu.com", "serverfault.com", "unix.stackexchange.com", "webmasters.stackexchange.com"], 'reason': "URL in title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 11, 'max_score': 0},
        # URL-only title, for the exempt sites
        {'regex': ur"(?i)^https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}(/\S*)?$", 'all': False,
         'sites': ["stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com", "ja.stackoverflow.com", "superuser.com", "askubuntu.com", "serverfault.com", "unix.stackexchange.com", "webmasters.stackexchange.com"], 'reason': "URL-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 11, 'max_score': 0},
        #
        # Category: Suspicious contact information
        # Phone number in title
        {'method': has_phone_number, 'all': True, 'sites': ["patents.stackexchange.com", "math.stackexchange.com", "mathoverflow.net"], 'reason': "phone number detected in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Phone number in post
        {'regex': ur"(?s)^.{0,250}\b1 ?[-(. ]8\d{2}[-). ] ?\d{3}[-. ]\d{4}\b", 'all': True, 'sites': ["math.stackexchange.com"], 'reason': "phone number detected in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # Email check for answers on selected sites
        {'regex': ur"(?i)(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})[A-z0-9_.%+-]+\.[A-z]{2,4}\b", 'all': False,
         'sites': ["biology.stackexchange.com", "bitcoin.stackexchange.com", "ell.stackexchange.com", "english.stackexchange.com", "expatriates.stackexchange.com", "gaming.stackexchange.com", "health.stackexchange.com", "money.stackexchange.com", "parenting.stackexchange.com", "rpg.stackexchange.com", "scifi.stackexchange.com", "travel.stackexchange.com", "worldbuilding.stackexchange.com"], 'reason': "email in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Email check for questions: check only at the end, and on selected sites
        {'regex': ur"(?i)(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})[A-z0-9_.%+-]+\.[A-z]{2,4}\b(?s).{0,100}$", 'all': False,
         'sites': ["money.stackexchange.com", "travel.stackexchange.com", "gamedev.stackexchange.com", "gaming.stackexchange.com", "patents.stackexchange.com"], 'reason': "email in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'answers': False, 'max_rep': 1, 'max_score': 0},
        # Combination of keyword and email in questions and answers, for all sites
        {'method': keyword_email, 'all': True, 'sites': [], 'reason': "bad keyword with email in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # QQ/ICQ/Whatsapp... numbers, for all sites
        {'regex': ur'(?i)(?<![a-z0-9])Q{1,2}(?:(?:[vw]|[^a-z0-9])\D{0,8})?\d{5}[.-]?\d{4,5}(?!["\d])|\bICQ[ :]{0,5}\d{9}\b|\bwh?atsapp?[ :]{0,5}\d{10}', 'all': True, 'sites': [], 'reason': "messaging number in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        #
        # Category: Trolling
        # Offensive content in titles and posts
        {'method': is_offensive_post, 'all': True, 'sites': [], 'reason': "offensive {} detected", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True,
         'max_rep': 101, 'max_score': 2},
        # Offensive title: titles are more sensitive
        {'regex': ur"(?i)\bfuck|(?<!brain)fuck(ers?|ing)?\b", 'all': True, 'sites': [], 'reason': "offensive {} detected", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': True, 'body_summary': False,
         'max_rep': 101, 'max_score': 5},
        # All-caps text
        {'method': all_caps_text, 'all': True, 'sites': ["pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com", "ja.stackoverflow.com", "rus.stackexchange.com"],
         'reason': "all-caps {}", 'title': False, 'body': True, 'questions': False, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # No whitespace, punctuation, or formatting in a post
        {'regex': ur"(?i)^<p>[a-z]+</p>\s*$", 'all': True, 'sites': ["codegolf.stackexchange.com", "puzzling.stackexchange.com"],
         'reason': "no whitespace in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Numbers-only title
        {'regex': ur"^(?=.*[0-9])[^\pL]*$", 'all': True, 'sites': ["math.stackexchange.com"], 'reason': "numbers-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 50, 'max_score': 0},
        # Few unique characters
        {'method': has_few_characters, 'all': True, 'sites': ["pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com", "rus.stackexchange.com"],
         'reason': "few unique characters in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 10000, 'max_score': 1000000},
        # Repeating characters
        {'method': has_repeating_characters, 'all': True, 'sites': ["pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com", "rus.stackexchange.com", "chinese.stackexchange.com"],
         'reason': "repeating characters in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1000000, 'max_score': 1000000},
        # Repeating words
        {'method': has_repeated_words, 'all': True, 'sites': [], 'reason': "repeating words in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 11, 'max_score': 0},
        # One unique character in title
        {'regex': ur"^(.)\1+$", 'all': True, 'sites': [], 'reason': "{} has only one unique char", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1000000, 'max_score': 1000000},
        # Parenting troll
        {'regex': ur"(?i)\b(erica|jeff|er1ca|spam|moderator)\b", 'all': False, 'sites': ["parenting.stackexchange.com"], 'reason': "bad keyword in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 50, 'max_score': 0},
        # Academia kangaroos
        {'regex': ur"(?i)kangaroos", 'all': False, 'sites': ["academia.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        {'regex': ur"(?i)\b\<a href=\".{0,25}\.xyz\"( rel=\"nofollow\")?\>.{0,15}google.{0,15}\<\/a\>\b", 'all': True, 'sites': [], 'reason': 'non-Google "google search" link in {}', 'title': False, 'body': True, 'username': False, 'body_summary': False, 'stripcodeblocks': True, 'max_rep': 1, 'max_score': 0},
        #
        # Category: other
        # Blacklisted usernames
        {'regex': ur"(?i)(^l(?:ol){2,}$|^troll$|tejveer ?iq|ser?vice pemanas?|\bnigg[aeu][rh]?|\b(fuck(er|ing)?|penis)\b|^wingding$|dlqudals|^[a-z ]+juri(?:n|na|ns|sa|ya|yam|ym)$|^[a-z]+jiibond$)", 'all': True, 'sites': [], 'reason': "blacklisted username", 'title': False, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        {'regex': u"(?i)^jeff$", 'all': False, 'sites': ["parenting.stackexchange.com"], 'reason': "blacklisted username", 'title': False, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0}
    ]

    @staticmethod
    def test_post(title, body, user_name, site, is_answer, body_is_summary, user_rep, post_score):
        result = []
        why = {'title': [], 'body': [], 'username': []}
        for rule in FindSpam.rules:
            body_to_check = body
            is_regex_check = 'regex' in rule
            try:
                check_if_answer = rule['answers']
            except KeyError:
                check_if_answer = True
            try:
                check_if_question = rule['questions']
            except KeyError:
                check_if_question = True
            body_to_check = regex.sub("[\xad\u200b\u200c]", "", body_to_check)
            if rule['stripcodeblocks']:    # use a placeholder to avoid triggering "few unique characters" when most of post is code
                body_to_check = regex.sub("(?s)<pre>.*?</pre>", u"<pre><code>placeholder for omitted code/код block</pre></code>", body_to_check)
                body_to_check = regex.sub("(?s)<code>.*?</code>", u"<pre><code>placeholder for omitted code/код block</pre></code>", body_to_check)
            if rule['reason'] == 'Phone number detected in {}':
                body_to_check = regex.sub("<img[^>]+>", "", body_to_check)
                body_to_check = regex.sub("<a[^>]+>", "", body_to_check)
            if rule['all'] != (site in rule['sites']) and user_rep <= rule['max_rep'] and post_score <= rule['max_score']:
                matched_body = None
                compiled_regex = None
                if is_regex_check:
                    compiled_regex = regex.compile(rule['regex'], regex.UNICODE, city=FindSpam.city_list)  # using a named list \L in some regexes
                    matched_title = compiled_regex.findall(title)
                    matched_username = compiled_regex.findall(user_name)
                    if (not body_is_summary or rule['body_summary']) and (not is_answer or check_if_answer) and (is_answer or check_if_question):
                        matched_body = compiled_regex.findall(body_to_check)
                else:
                    assert 'method' in rule
                    matched_title, why_title = rule['method'](title, site)
                    if matched_title and rule['title']:
                        why["title"].append(u"Title - {}".format(why_title))
                    matched_username, why_username = rule['method'](user_name, site)
                    if matched_username and rule['username']:
                        why["username"].append(u"Username - {}".format(why_username))
                    if (not body_is_summary or rule['body_summary']) and (not is_answer or check_if_answer) and (is_answer or check_if_question):
                        matched_body, why_body = rule['method'](body_to_check, site)
                        if matched_body and rule['body']:
                            why["body"].append(u"Post - {}".format(why_body))
                if matched_title and rule['title']:
                    why["title"].append(FindSpam.generate_why(compiled_regex, title, u"Title", is_regex_check))
                    result.append(rule['reason'].replace("{}", "title"))
                if matched_username and rule['username']:
                    why["username"].append(FindSpam.generate_why(compiled_regex, user_name, u"Username", is_regex_check))
                    result.append(rule['reason'].replace("{}", "username"))
                if matched_body and rule['body']:
                    why["body"].append(FindSpam.generate_why(compiled_regex, body_to_check, u"Body", is_regex_check))
                    type_of_post = "answer" if is_answer else "body"
                    result.append(rule['reason'].replace("{}", type_of_post))
        result = list(set(result))
        result.sort()
        why = "\n".join(filter(None, why["title"]) + filter(None, why["body"]) + filter(None, why["username"])).strip()
        return result, why

    @staticmethod
    def generate_why(compiled_regex, matched_text, type_of_text, is_regex_check):
        if is_regex_check:
            matches = compiled_regex.finditer(matched_text)
            why_for_matches = []
            for match in matches:
                span = match.span()
                group = match.group()
                why_for_matches.append(u"Position {}-{}: {}".format(span[0] + 1, span[1] + 1, group))
            return type_of_text + u" - " + ", ".join(why_for_matches)
        return ""
