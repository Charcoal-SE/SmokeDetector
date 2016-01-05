# -*- coding: utf-8 -*-
import regex
import phonenumbers


def all_caps_text(s, site):
    s = regex.sub("<[^>]*>", "", s)   # remove HTML tags
    s = regex.sub("&\w+;", "", s)     # remove HTML entities
    if len(s) <= 150 and regex.compile(ur"SQL|\b(ERROR|PHP|QUERY|ANDROID|CASE|SELECT|HAVING|COUNT|GROUP|ORDER BY|INNER|OUTER)\b").search(s):
        return False, ""   # common words in non-spam all-caps titles
    if len(s) >= 25 and regex.compile(ur"^(?=.*\p{upper})\P{lower}*$", regex.UNICODE).search(s):
        return True, "All in caps"
    return False, ""


def has_repeated_words(s, site):
    words = regex.split(r"[\s.,;!/\()\[\]+_-]", s)
    words = [w for w in words if w != ""]
    curr = 0
    prev = ""
    for w in words:
        if w == prev and w.isalpha() and len(w) > 1:
            curr += 1
        else:
            curr = 0
        prev = w
        if curr >= 5 and curr * len(w) >= 0.2 * len(s):
            return True, u"Repeated word {}".format(w)
    return False, ""


def has_few_characters(s, site):
    s = regex.sub("</?p>", "", s)    # remove HTML paragraph tags from posts
    uniques = len(set(list(s)))
    if (len(s) >= 30 and uniques <= 6) or (len(s) >= 100 and uniques <= 15):    # reduce if false reports appear
        return True, u"Contains {} unique characters".format(uniques)
    return False, ""


def has_repeating_characters(s, site):
    s = regex.sub('http[^"]*', "", s)    # remove URLs for this check
    if s is None or len(s) == 0:
        return False, ""
    matches = regex.compile("([^\\s_.,?!=~*/0-9-])(\\1{10,})", regex.UNICODE).findall(s)
    matches = ["".join(match) for match in matches]
    match = "".join(matches)
    if (100 * len(match) / len(s)) >= 20:
        return True, u"Repeated character: {}".format(match)
    return False, ""


def link_at_end(s, site):
    s = regex.sub("</strong>|</em>|</p>", "", s)
    match = regex.compile(ur"http://[A-Za-z0-9-.]*/?[A-Za-z0-9-]*/?</a>\s*$", regex.UNICODE).findall(s)
    if len(match) > 0 and not regex.compile(r"\b(imgur|stackexchange|superuser|past[ie].*|dropbox|microsoft|newegg|cnet|google|localhost|ubuntu)\b", regex.UNICODE).search(match[0]):
        return True, u"Link at end: {}".format(match[0])
    return False, ""


def non_english_link(s, site):   # non-english link in short answer
    if len(s) < 400:
        links = regex.compile(ur"(?<=>)[^<]*(?=</a>)", regex.UNICODE).findall(s)
        for link_text in links:
            word_chars = regex.sub(r"(?u)\W", "", link_text)
            non_latin_chars = regex.sub(r"\w", "", word_chars)
            if len(non_latin_chars) > 0.2 * len(word_chars) and len(non_latin_chars) >= 2:
                return True, u"Non-English link text {}".format(link_text)
    return False, ""


def has_phone_number(s, site):
    if regex.compile(ur"(?i)\b(run[- ]?time|error|(sp)?exception|1234567)\b", regex.UNICODE).search(s):
        return False, ""  # not a phone number
    s = regex.sub("(?i)O", "0", s)
    s = regex.sub("(?i)S", "5", s)
    s = regex.sub("(?i)[I]", "1", s)
    matched = regex.compile(ur"(?<!\d)(?:\d(?:_*\d){9}|\+?\d_*\d[\s-]?(?:_*\d){8,11}|\d[ -.(]{0,2}\d{3}[ -.)]{0,2}\d{3}[ -.]{0,2}\d{4})(?!\d)", regex.UNICODE).findall(s)
    test_formats = ["IN", "US", None]      # ^ don't match parts of too long strings of digits
    for phone_number in matched:
        if regex.compile(r"^21474(672[56]|8364)\d$").search(phone_number):
            return False, ""  # error code or limit of int size
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
    s = s[0:200].lower()   # if applied to body, the beginning should be enough: otherwise many false positives
    business = regex.compile(r"(?i)\b(dell|epson|facebook|gmail|google|hotmail|hp|lexmark|mcafee|microsoft|out[l1]ook|quickbooks|yahoo|Delta|airlines?)\b").findall(s)
    digits = len(regex.compile(r"\d").findall(s))
    if (business and digits >= 5):
        keywords = regex.compile(r"(?i)\b(customer|help|helpline|reservation|phone|recovery|service|support|tech|technical|telephone|number)\b").findall(s)
        if len(set(keywords)) >= 2:
            matches = ["".join(match) for match in keywords]
            match = ", ".join(matches)
            return True, "Scam aimed at {} customers. Keywords: {}".format(business[0], match)
    return False, ""


def has_health(s, site):   # flexible detection of health spam in titles
    s = s[0:200].lower()   # if applied to body, the beginning should be enough: otherwise many false positives
    organ = regex.compile(r"(?i)\b(colon|skin|muscle|fac(e|ial)|eye|brain|mind|head|peni(s|le)|breast|body|belly|digest\w*)s?\b").search(s)
    condition = regex.compile(r"(?i)\b(weight|constipat(ed|ion)|swollen|sensitive|wrinkle|aging|suffer|acne|pimple|dry|clog(ged)?|inflam(ed|mation)|fat|age|pound)s?\b").search(s)
    goal = regex.compile(r"(?i)\b(supple|healthy?|build|los[es]|power|young(er)?|youth(ful)?|burn|erection|IQ|energy|tone(d)|shred(ed)?|rip(ped)?|bulk up|get rid|mood)s?\b|\b(diminish|look|reduc|beaut|renew|lift|eliminat|enhance|improve|enlarge|remov|vital|slim|lean|boost|str[oe]ng)s?").search(s)
    remedy = regex.compile(r"(?i)\b(remed(y|ie)|serum|cleans?(e|er|ing)|care|(pro)?biotic|herbal|lotion|cream|gel|cure|drug|formula|recipe|solution|therapy|hydration|soap|treatment|supplement|diet|moist\w*|injection|potion|ingredient|aid|exercise|eat(ing)?)s?\b").search(s)
    boast = regex.compile(r"(?i)\b(most|best|easy|simple|top|pro|real|mirac(le|ulous)|organic|natural|perfect|fantastic|incredible|important|critical|amazing|fast|good)\b|\b(super|hyper|advantag|benefi|effect|great|valu)").search(s)
    other = regex.compile(r"(?i)\b(product|thing|item|review|advi[cs]e|make use|your?|really|work|tip|shop|store|method|expert|instant|buy|fact|consum(e|ption)|baby|male|female|men|women|grow|idea|suggest\w*|issue)s?\b").search(s)
    score = 4 * bool(organ) + 2 * bool(condition) + 2 * bool(goal) + 2 * bool(remedy) + bool(boast) + bool(other)
    if score >= 7:
        match_objects = [organ, condition, goal, remedy, boast, other]
        words = []
        for match in match_objects:
            if match:
                words.append(match.group(0))
        return True, "Health-themed spam (score {}). Keywords: {}".format(score, ", ".join(words))
    return False, ""


class FindSpam:
    bad_keywords = ["baba ?ji", "fifa.*coins?", "fifabay", "Long Path Tool",
                    "fifaodell", "brianfo", "tosterone", "bajotz",
                    "kolcak", "Zapyo", "we (offer|give out) (loans|funds|funding)",
                    "[- ]porn[. ]", "molvi", "judi bola", "ituBola.com", "lost lover'?s?",
                    "rejuvenated skin", "ProBrain", "restore[ -]?samsung[ -]?data",
                    "LifeForce", "swtor2credits", "me2.do",
                    "bam2u", "Neuro(3X|flexyn|fuse|luma|plex)", "TesteroneXL", "Nitroxin",
                    "Bowtrol", "Slim ?Genix", "Cleanse EFX", "Alpha Rush",
                    "Blackline Elite", "TestCore Pro", "blank(ed)? ?ATM(card)?", "ATM Machine Vault",
                    "Xtreme Antler", "Maxx Test 3000", "orvigomax",
                    "Cheap Wigs?", "jivam", "^(?s).{0,200}brain[- ]?power", "Maximum ?Shred",
                    "aging skin", "acne( prone)? skin", "black[ -]label[ -]no",
                    "bagprada", "6611165613", "Apowersoft",
                    "Service Solahart", "junisse", "Profactor[ -]?T",
                    "(fake|original|novelty|quality).{0,5}(passports?|driver'?s? licen[cs]e|ID cards?)",
                    "^.{0,200}(support|service|helpline)( phone)? number|1[ -]?[ -]?[ -]?866[ -]?978[ -]?(6819|6762)",
                    "(mcafee|hotmail|gmail|outlook|yahoo|lexmark (printer)?) ?(password( recovery)?|tech)? ?((customer|technical) (support|service))? (support|contact|telephone|help(line)?|phone) number",
                    "kitchen for sale", "pdftoexcelconverter", "keepbrowsersafe", "SpyHunter",
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
                    "(networking|cisco|sas|hadoop|mapreduce|oracle|dba|php|sql|javascript|js|java|designing|salesforce)( certification)? training.{0,25}</a>",
                    "intellipaat", "Replennage", "Alpha XTRM", "Synagen", "Nufinity",
                    "V[ -]?Stamina", "Gynectrol", "Adderin", "Whizz Systems?", "intellux", "viooz",
                    "smartican", "essay writing service", "T-complex", "retrodynamic formula",
                    "eltima", "raging lion", "love.*spell ?caster", "08151871776",
                    "^.{0,199}(contact|offer|join).{0,99}\d{9}.{0,99}$", "KrojamSoft", "FilesSearch ?Tool"]
    bad_keywords_nwb = [u"ಌ", "vashi?k[ae]r[ae]n", "babyli(ss|cious)", "garcinia", "cambogia", "acai ?berr",  # "nwb" == "no word boundary"
                        "(eye|skin|aging) ?cream", "b ?a ?m ?((w ?o ?w)|(w ?a ?r))", "online ?it ?guru",
                        "abam26", "watch2live", "cogniq", "(skin|face|eye) ?(serum|lift)", "(serum|lift) ?eye", "tophealth", "poker ?online",
                        "caralluma", "male\\Wperf", "anti[- ]?aging", "lumisse", "(ultra|berry|body)[ -]?ketone",
                        "(cogni|oro)[ -]?(lift|plex)", "skin ?care", "diabazole", "forskolin", "tonaderm", "luma(genex|lift)",
                        "nuando[ -]?instant", "\\bnutra", "nitro[ -]?slim", "aimee[ -]?cream",
                        "slimatrex", "cosmitone", "smile[ -]?pro[ -]?direct", "bellavei", "opuderm",
                        "contact (me|us)\\W*<a ", "follicure", "kidney[ -]?bean[ -]?extract", "ecoflex",
                        "\\brs(gold|song)", "bellavei", "goji ?xtreme", "lumagenex", "packers.{0,15}movers.{0,25}</a>",
                        "(brain|breast|male|penile|penis)[- ]?(enhance|enlarge|improve|boost|plus|peak)",
                        "renuva(cell|derm)", " %uh ", " %ah ", "svelme", "tapsi ?sarkar", "viktminskning",
                        "unique(doc)?producers", "green ?tone ?pro", "troxyphen", "seremolyn", "revolyn",
                        "training.{0,4}chennai"]
    blacklisted_websites = ["online ?kelas", "careyourhealths", "wowtoes",
                            "ipubsoft", "orabank", "powerigfaustralia",
                            "cfpchampionship2015playofflive", "rankassured\\.com",
                            "maletestosteronebooster", "menintalk", "king-steroid",
                            "healthcaresup", "filerepairforum", "beautyskin",
                            "lxwpro-t", "casque-beatsbydre", "tenderpublish",
                            "funmac", "lovebiscuits", "z-data.blogspot.com",
                            "Eglobalfitness", "musclezx90site", "fifapal",
                            "hits4slim", "screenshot\\.net", "downloadavideo\\.net",
                            "strongmenmuscle", "sh\\.st/", "adf\\.ly/", "//j\\.gs/", "musclehealthfitness",
                            "preply\\.com", "hellofifa", "chinadivision",
                            "fifa\\d*online", "wearepropeople.com", "tagwitty",
                            "axsoccertours", "ragednablog", "ios8easyjailbreak",
                            "totalfitnesspoint", "trustessaywriting", "thesispaperwriters",
                            "trustmyessay", "faasoft", "besttvshows", "mytechlabs",
                            "giikers", "pagetube", "myenv\\.org", "testkiz\\.com",
                            "pelevoniface", "herintalk", "menshealth", "examguidez",
                            "skinphysiciantips", "fifa2coins", "xtrememusclerecoveryrev",
                            "diabacordoesitwork", "thehealthyadvise", "mixresult\\.com",
                            "premiumpureforskolinrev", "hyperglycemiaabout", "dietandhealthguide",
                            "sourceforge\\.net/projects/freepdftojpgconverter",
                            "pdftoexel\\.wordpress\\.com", "best7th\\.in",
                            "recoverytoolbox\\.com", "mkmk9", "malwaretips", "intellipaat\\.com",
                            "webbuildersguide\\.com", "idealshare.net", "lankabpoacademy\\.com",
                            "evomailserver\\.com", "gameart\\.net",
                            "sofotex\\.com", "erecteentry", "fairharvardfund",
                            "mybloggingmoney\\.com", "windows-techsupport\\.com",
                            "drivethelife\\.com", "singlerank\\.com", "sayeureqa\\.com",
                            "lafozi\\.com", "open-swiss-bank\\.com", "kalimadedot\\.blogspot",
                            "tenorshare\\.com", "advancedpdfconverter\\.com",
                            "fix-computer\\.net", "drillpressselect", "chinatour\\.com",
                            "macvideoconverterpro\\.com", "password-master\\.net",
                            "photorecovery-formac\\.com", "thecasesolutions\\.com",
                            "rarpasswordunlocker\\.net", "hackerscontent\\.com",
                            "windows7-password-reset\\.net", "windowspasswordcracker\\.com"
                            "windowspasswordreset\\.net", "official-?driver",
                            "youtubedownloaderconverter\\.net", "santerevue", "cheatsumo\\.com",
                            "smartpcfixer", "1fix\\.org", "code4email\\.com",
                            "drivertuner\\.com", "easyfix\\.org", "errorsfixer\\.org",
                            "faq800\\.com", "fix1\\.org", "guru4pc\\.net", "howto4pc\\.org",
                            "pceasynow\\.com", "qobul\\.com", "onlinegiftdeal\\.com",
                            "regeasypro\\.com", "registryware\\.org", "smartfixer\\.(net|org)",
                            "dlllibrary\\.net", "wisefixer\\.(com|net|org)",
                            "password-?unlocker\\.com", "dropbox18gb\\.com",
                            "passwordtech\\.com", "goshareware\\.com",
                            "nemopdf\\.com", "apowersoft\\.com", "downloaddailymotion\\.com",
                            "free-download-youtube\\.com", "free-music-downloader\\.com",
                            "video-download-capture\\.com", "videograbber\\.net",
                            "password-buster\\.com", "globalvision\\.com\\.vn",
                            "remorecover\\.com", "remosoftware\\.com",
                            "\\bpatch\\.com\\b", "ajgilworld\\.com", "santomais", "viilms",
                            "clashofclansastucegemmes\\.com", "mothersday-2014\\.org",
                            "bestcelebritiesvideo\\.com", "shopnhlbruins\\.com",
                            "downloadscanpst\\.com", "downloadgames", "gameshop4u\\.com",
                            "listoffreeware\\.com", "bigasoft\\.com", "opclub07\\.com",
                            "allavsoft", "tryapext\\.com", "essays(origin|council)\\.com", "caseism\\.com",
                            "vanskeys\\.com", "cheapessaywritingservice", "edbtopsts\\.com",
                            "texts\\.io", "writage\\.com", "mobitsolutions\\.com",
                            "askpcexperts\\.com", "anonymousvpnsoftware\\.com",
                            "ecouponcode\\.com", "wasel(pro)?\\.com", "i-spire\\.(com|net)",
                            "iwasl\\.com", "vpn(faqs|answers|ranks|4games)\\.com",
                            "unblockingtwitter\\.com", "openingblockedsite\\.com",
                            "arabic(soft)?downloads?\\.com", "braindumpsvalid",
                            "repairtoolbox\\.com", "couchsurfing\\.com",
                            "gta5codes\\.fr", "musclezx90au\\.com", "pcsoftpro\\.com",
                            "fallclassicrun\\.com", "forgrams\\.com",
                            "cloudinsights\\.net", "xtremenitro", "surfmegeek",
                            "(premium|priceless)-inkjet\\.com", "antivirus\\.comodo\\.com",
                            "clusterlinks\\.com", "connectify\\.me",
                            "kizi1000\\.in", "weightruinations\\.com",
                            "products\\.odosta\\.com", "naturacelhelp",
                            "rackons\\.com", "imonitorsoft\\.com", "biginfosys\\.com",
                            "analec\\.com", "livesportstv\\.us", "batteriedepcportable",
                            "stadtbett\\.com", "tokoterbaik\\.com",
                            "jetcheats\\.com", "cheatio\\.com", "empiremountainbikes",
                            "optimalstack(facts|products)", "x4facts", "endomondo\\.com",
                            "litindia\\.in", "shoppingcartelite\\.com",
                            "customizedwallpaper\\.com", "cracksofts\\.com",
                            "crevalorsite\\.com", "macfixz\\.com", "moviesexplore\\.com",
                            "iphoneunlocking\\.org", "thehealthvictory\\.com",
                            "bloggermaking\\.com", "supportphonenumber\\.com",
                            "slimbodyketone", "prinenidz\\.com", "e-priceinbd",
                            "maddenmobilehack", "supplements4help", "watchtheboxing",
                            "cacherealestate\\.com", "Matrixhackka007", "aoatech\\.com",
                            "pharaohtools", "msoutlooktools\\.com", "softwarezee",
                            "i-hire\\.pro", "pandamw\\.com", "hariraya2015\\.net",
                            "scampunch\\.com", "multipelife\\.com", "seasoncars\\.com",
                            "eltima\\.com", "flexihub\\.com", "\\.debt\\.com",
                            "hotfrog\\.ca", "snorg(content|tees)\\.com", "webtechcoupons",
                            "architecturedesign\\.tk", "playerhot\\.com",
                            "xinyanlaw", "ultrafinessesite", "sunitlabs\\.com", "puravol\\.net",
                            "statesmovie", "cleanlean", "iFoneMate", "babygames5\\.com",
                            "replacementlaptopkeys\\.com", "safewiper\\.com",
                            "appsforpcdownloads", "academicservices\\.us",
                            "musclebuilding(products|base)", "Blogdolllar\\.net", "bendul\\.com",
                            "megatachoco", "sqliterecovery\\.com", "shtylm\\.com",
                            "creative-proteomics", "biomusclexrrev\\.com", "revommerce.com",
                            "123trainings", "(bestof|beta)cheat\\.com", "surejob\\.in",
                            "israelbigmarket", "hdmoviesfair\\.com", "chinatour\\.com", "celebsclothing\\.com",
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
                            "shacamerica\\.net", "nillowpages\\.com", "letsnurture\\.com", "healthpeters\\.com",
                            "rozapk\\.com", "jihosoft\\.com", "mahnazmezon\\.com", "technical-care\\.com",
                            "skyformation\\.com", "shiftingsolutions\\.in", "bandsawjudge\\.com",
                            "liveestorebuilder\\.com", "exampracticequestions\\.com", "createspace\\.com",
                            "healthpeters\\.com", "fun-flicks\\.com", "smarketingclub\\.com", "cbitss\\.in",
                            "o-lovius\\.com", "crackedapkfull\\.com", "aldovmcgregor\\.co", "priredeream\\.com",
                            "adonads\\.com", "uufix\\.com", "slimrootz\\.com", "robomart\\.com", "fedotov\\.co",
                            "resumewritingservicecleveland\\.us", "uflysoft\\.net", "simicart\\.com",
                            "thereferraltask\\.net", "ajax2014\\.ir", "voxforem\\.com", "writeversity\\.com",
                            "labstech\\.org", "rikshairuym", "zicamagsopt", "how2world\\.com", "splendyrsite\\.net",
                            "3gwith4g\\.com", "xride-hd\\.com", "sincycle\\.com", "wcwnetworking\\.com",
                            "vivaspanish\\.org", "wanglu123\\.com", "z0download\\.com", "citehr\\.com",
                            "thecreatingexperts\\.com", "masterm\\.com", "ablockplus\\.org", "iseenlab\\.com",
                            "whatech\\.com", "crunchbase\\.com", "fileniaz\\.com", "icoolsoft\\.com",
                            "replicabreitlingwatches\\.co", "wonderful-watch\\.co", "plagiarism-checker\\.me",
                            "khannaescorts\\.com", "windowslivemailconverter\\.com", "mboxconverter\\.com",
                            "sapboonline\\.com", "thinkittraining\\.in", "salesforcetrainingexpert\\.in",
                            "weblogic-trainingchennai\\.in", "indiaflower"]
    pattern_websites = [r"health\d{3,}", r"http\S*?\.repair\W", r"filefix(er)?\.com", "\.page\.tl\W",
                        r"\.(com|net)/(xtra|muscle)[\w-]",
                        r"fifa\d+[\w-]*?\.com", r"[\w-](giveaway|jackets|supplys)\.com",
                        r"(essay|resume)\w{6,}\.(co|net|org|in\W|info|us)",
                        r"(top|best)\d\w{2,15}\.in\W",
                        r"[\w-](recovery|repair|(?<!epoch|font)converter)(pro|kit)?\.(com|net)",
                        r"http\S*?(yahoo|gmail|hotmail|outlook|office|microsoft)[\w-]*?(tech|customer|support|service|phone|help|\d+)[\w-]*?(support|phone|number)",
                        r"sourceforge\.net[\w/]*convert",
                        r"fix[\w-]*?(files?|tool(box)?)\.com",
                        r"(repair|recovery|fix)tool(box)?\.com",
                        r"smart(pc)?fixer\.(com|net|org)",
                        r"password-?(cracker|unlocker|reset|buster|master)\.(com|net|org)",
                        r"(downloader|pdf)converter\.(com|net)",
                        r"(livestreaming|watch[\w-]*?(live|online))\.(com|net|tv)",
                        r"//(cheat[\w-.]{3,}|xtreme[\w-]{5,})\.(co|net|org|in\W|info)",
                        r"([\w-]password|[\w]{5,}facts|\Btoyshop|[\w-]{6,}cheats|credits)\.(co|net|org|in\W|info)",
                        r"(escort|diploma|extramoney|earnathome|spell(caster|specialist)|profits|seo(tool|service|trick)|onsale|fat(burn|loss)|(\.|//|best)cheap|online(training|solution))[\w-]*?\.(co|net|org|in\W|info)",
                        r"(trainingin|cracked\w{3}|bestmover|\w{4}mortgage|loans|revenue|testo[-bsx]|cleanse|detox|supplement|lubricant|serum|wrinkle|topcare|freetrial)[\w-]*?\.(co|net|org|in\W|info)",
                        r"(nitro(?!us)|crazybulk|nauseam|endorev|ketone|//xtra)[\w-]*?\.(co|net|org|in\W|info)",
                        r"(acai|buy|premium|thebest|[/.]try)[\w-]{10,}\.(co|net|org|in\W|info)",
                        r"training[\w.-]{6,}\.(co|net|org|in\W|info)",
                        r"\w{9}buy\.(co|net|org|in\W|info)",
                        r"(love|strong|natural|pro|magic|beware|top|best|free|cheap|allied|nutrition)[\w-]*?health[\w-]*?\.(co|net|org|in\W|info)",
                        r"(eye|skin|age|aging)[\w-]*?cream[\w-]*?\.(co|net|org|in\W|info)",
                        r"(grow|rejuven|revive|burn|vapor|ecig|formula|biotic|male|derma|medical|medicare|health|beauty|youth|young|rx|skin|trim|slim|weight|fat|nutrition|shred|advance|perfect|top|alpha|beta|colon|brain(?!tree))[\w]{0,20}(about|market|max|help|info|policy|program|try|slim|idea|pro|tip|review|assess|report|critique|blog|site|guide|advi[sc]|discussion|solution|consult|source|sups|vms|cream|grow|enhance)[\w-]{0,10}\.(co|net|org|in\W|info)",
                        r"\w{11}(ideas?|income|sale|reviews?|advices?|problog)\.(co|net|org|in\W|info)",
                        "-poker\\.com", "send[\w-]*?india\.(co|net|org|in\W|info)",
                        r"(corrupt|repair)[\w-]*?\.blogspot", r"[\w-]courses.in/",
                        r"(file|photo|android|iphone)recovery[\w-]*?\.(co|net|org|in\W|info)",
                        r"(videos?|movies?|watch)online[\w-]*?\.", r"hd(video|movie)[\w-]*?\.",
                        r"backlink(?!(o\.|watch))[\w-]*?\.(co|net|org|in\W|info)",
                        r"(replica[^nt]\w{5,}|\wrolex)\.(co|net|org|in\W|info)",
                        r"customer(service|support)[\w-]*?\.(co|net|info)"]
    rules = [
        # Sites in sites[] will be excluded if 'all' == True.  Whitelisted if 'all' == False.
        #
        # Category: Bad keywords
        # The big list of bad keywords, for titles and posts
        {'regex': ur"(?is)\b({})\b|{}".format("|".join(bad_keywords), "|".join(bad_keywords_nwb)), 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 50},
        # baba and nike are restricted to the beginning of posts: many false positives otherwise
        {'regex': ur"(?is)^.{0,200}\b(baba|nike) ", 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 11},
        # gratis at the beginning of post, SoftwareRecs is exempt
        {'regex': ur"(?is)^.{0,200}\bgratis\b$", 'all': True,
         'sites': ['softwarerecs.stackexchange.com'], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 11},
        # Black magic at the beginning of post, Islam is exempt
        {'regex': ur"^(?is).{0,200}black magic", 'all': True,
         'sites': ["islam.stackexchange.com"], 'reason': "black magic in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 11},
        # Bad keywords in titles only, all sites
        {'regex': ur"(?i)^(?:(?=.*?\b(?:online|hd)\b)(?=.*?(?:free|full|unlimited)).*?movies?\b)|(?=.*?\b(?:acai|kisn)\b)(?=.*?care).*products?\b|(?=.*?packer).*mover|(online|certification).*?training| vs .* (live|vivo)|\bxtra\b|\bwe offer\b|payday loan", 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 11},
        # Fake-customer-service in title
        {'method': has_customer_service, 'all': True, 'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1},
        # Bad health-related keywords in titles, health sites are exempt
        {'regex': ur"(?i)\b((beauty|skin|face|health|eye)[- ]?(care|serum|therapy|hydration|tip|renewal|shop|store|lift|product|strateg(y|ies)|gel|lotion|cream|treatment|method|school|expert)|fat ?burn(er|ing)?|muscle|testo ?[sx]\w*|body ?build(er|ing)|wrinkle|(?<!to )supplement|probiotic|acne|peni(s|le)|erection)s?\b", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 11},
        # Bad health-related keywords in titles, health sites are exempt, flexible method
        {'method': has_health, 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1},
        # Bad health-related keywords in titles and posts, health sites are exempt
        {'regex': ur"(?is)virility|diet ?(plan|pill)|\b(pro)?derma(?=[a-su-z ]\w)|(fat|(?<!dead[ -]?)weight)[ -]?(loo?s[es]|reduction)|loo?s[es] ?weight|\bherpes\b|(?<!truth )serum|colon (detox|clean)", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com", "bicycles.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 11},
        # "vs" in titles, for sports events, Patents only
        {'regex': u"(?i)vs", 'all': False, 'sites': ["patents.stackexchange.com"], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 11},
        # Korean character in title
        {'regex': ur"(?i)\p{Script=Hangul}.*\p{Script=Hangul}.*\p{Script=Hangul}", 'all': True,
         'sites': [], 'reason': "Korean character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 11},
        # Chinese characters in title: requires two groups of 3
        {'regex': ur"(?i)\p{Script=Han}{3}.*\p{Script=Han}{3}", 'all': True,
         'sites': ["chinese.stackexchange.com", "japanese.stackexchange.com"], 'reason': "Chinese character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 11},
        # Hindi character in title
        {'regex': ur"(?i)\p{Script=Devanagari}", 'all': True,
         'sites': ["hinduism.stackexchange.com"], 'reason': "Hindi character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 11},
        #
        # Category: Suspicious links
        # Blacklisted sites
        {'regex': u"(?i)({})".format("|".join(blacklisted_websites)), 'all': True,
         'sites': [], 'reason': "blacklisted website in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 50},
        # Suspicious sites
        {'regex': u"(?i)({})(?![^>]*<)".format("|".join(pattern_websites)), 'all': True,
         'sites': [], 'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 11},
        # Suspicious health-related websites, health sites are exempt
        {'regex': ur"(?i)(workout|fitness\w{2,}|diet|perfecthealth|muscle)[\w-]*?\.(com|co\.|net|org|info)", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com", "bicycles.stackexchange.com"], 'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 11},
        # Links preceded by arrows >>>
        {'regex': ur"(?is)(>>>|===>|==>>>|(Read|Visit) More\s*[=>]{2,})(?=.{0,20}http.{0,200}$)", 'all': True,
         'sites': [], 'reason': "link following arrow in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 11},
        # Link at the end of question, selected sites
        {'method': link_at_end, 'all': False,
         'sites': ["superuser.com", "askubuntu.com", "drupal.stackexchange.com", "meta.stackexchange.com", "security.stackexchange.com", "patents.stackexchange.com"], 'reason': 'link at end of {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'answers': False, 'max_rep': 1},
        # Link at the end of a short answer, set as a separate paragraph
        {'regex': ur'(?s)^.{0,200}<p>\s*<a href="http://[\w.-]+\.(com|net|in|co.uk)/?"[^<]*</a>\s*</p>\s*$', 'all': True,
         'sites': [], 'reason': 'link at end of {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1},
        # Shortened URL in a short answer
        {'regex': ur"(?s)^.{0,200}://(goo\.gl|bit\.ly|tinyurl\.com|fb\.me|cl\.ly|t\.co|is\.gd|j\.mp|tr\.im|ow\.ly|wp\.me|alturl\.com|tiny\.cc)/.{0,150}$", 'all': True, 'sites': [], 'reason': "shortened URL in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1},
        # Link text without Latin characters
        {'regex': u">[^0-9A-Za-z<'\"]{3,}</a>", 'all': True,
         'sites': ["jp.stackoverflow.com", "ru.stackoverflow.com", "rus.stackexchange.com", "islam.stackexchange.com", "japanese.stackexchange.com", "hinduism.stackexchange.com", "judaism.stackexchange.com", "buddhism.stackexchange.com", "chinese.stackexchange.com", "russian.stackexchange.com", "codegolf.stackexchange.com"], 'reason': 'non-Latin link in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 11},
        # Link text with many non-Latin characters
        {'method': non_english_link, 'all': True, 'sites': ["pt.stackoverflow.com", "es.stackoverflow.com", "jp.stackoverflow.com", "ru.stackoverflow.com", "rus.stackexchange.com", "islam.stackexchange.com", "japanese.stackexchange.com", "hinduism.stackexchange.com", "judaism.stackexchange.com", "buddhism.stackexchange.com", "chinese.stackexchange.com", "russian.stackexchange.com", "french.stackexchange.com", "portuguese.stackexchange.com", "spanish.stackexchange.com", "codegolf.stackexchange.com"],
         'reason': 'non-English link in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1},
        # URL in title, some sites are exempt
        {'regex': ur"https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}", 'all': True,
         'sites': ["stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com", "superuser.com", "askubuntu.com"], 'reason': "URL in title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 50},
        # URL-only title, for the exempt sites
        {'regex': ur"^https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}(/\S*)?$", 'all': False,
         'sites': ["stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com", "superuser.com", "askubuntu.com"], 'reason': "URL-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 50},
        #
        # Category: Suspicious contact information
        # Phone number in title
        {'method': has_phone_number, 'all': True, 'sites': ["patents.stackexchange.com", "math.stackexchange.com"], 'reason': "phone number detected in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 11},
        # Email check for answers, some sites exempt
        {'regex': ur"(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})[A-z0-9_.%+-]+\.[A-z]{2,4}\b", 'all': True,
         'sites': ["stackoverflow.com", "es.stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "superuser.com", "serverfault.com", "askubuntu.com", "webapps.stackexchange.com", "salesforce.stackexchange.com", "unix.stackexchange.com", "webmasters.stackexchange.com", "wordpress.stackexchange.com", "magento.stackexchange.com", "elementaryos.stackexchange.com", "tex.stackexchange.com", "civicrm.stackexchange.com"], 'reason': "email in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 11},
        # Combination of keyword and email in answer, for the exempt sites
        {'regex': ur"(?is)\b(loans?|illuminati|brotherhood|(join|reach) us|spell(caster)?|passports?|visas?|bless)\b.*?(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})[A-z0-9_.%+-]+\.[A-z]{2,4}\b", 'all': False,
         'sites': ["stackoverflow.com", "es.stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "superuser.com", "serverfault.com", "askubuntu.com", "webapps.stackexchange.com", "salesforce.stackexchange.com", "unix.stackexchange.com", "webmasters.stackexchange.com", "wordpress.stackexchange.com", "magento.stackexchange.com", "elementaryos.stackexchange.com", "tex.stackexchange.com", "civicrm.stackexchange.com"], 'reason': "email in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 11},
        # Email check for questions: check only at the end
        {'regex': ur"(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})[A-z0-9_.%+-]+\.[A-z]{2,4}\b(?s).{0,300}$", 'all': True,
         'sites': ["stackoverflow.com", "es.stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "superuser.com", "serverfault.com", "askubuntu.com", "webapps.stackexchange.com", "salesforce.stackexchange.com", "unix.stackexchange.com", "webmasters.stackexchange.com", "wordpress.stackexchange.com", "magento.stackexchange.com", "elementaryos.stackexchange.com", "tex.stackexchange.com", "civicrm.stackexchange.com"], 'reason': "email in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'answers': False, 'max_rep': 11},
        #
        # Category: Trolling
        # Offensive content in titles and posts
        {'regex': ur"(?i)\b(nigg(a|er)|asshole|fag(got)?|daf[au][qk]|(mother)?fuc?k+(ing?|e?r)?|shit(t?er|hole|head)?|dickhead|whore|cunt|dee[sz]e? nut[sz])s?\b", 'all': True,
         'sites': [], 'reason': "offensive {} detected", 'insensitive':True, 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 101},
        # Offensive content in titles only
        {'regex': ur"(?i)\bcrap\b", 'all': True, 'sites': [], 'reason': "offensive {} detected", 'insensitive': True, 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 101},
        # All-caps text
        {'method': all_caps_text, 'all': True, 'sites': ["pt.stackoverflow.com", "ru.stackoverflow.com"], 'reason': "all-caps {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1000000},
        # Numbers-only title
        {'regex': ur"^(?=.*[0-9])[^\pL]*$", 'all': True, 'sites': [], 'reason': "numbers-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 50},
        # Few unique characters
        {'method': has_few_characters, 'all': True, 'sites': [], 'reason': "few unique characters in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1000000},
        # Repeating characters
        {'method': has_repeating_characters, 'all': True, 'sites': [], 'reason': "repeating characters in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1000000},
        # Repeating words
        {'method': has_repeated_words, 'all': True, 'sites': [], 'reason': "repeating words in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 11},
        # One unique character in title
        {'regex': ur"^(.)\1+$", 'all': True, 'sites': [], 'reason': "{} has only one unique char", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 11},
        # Parenting troll
        {'regex': ur"(?i)\b(erica|jeff|er1ca|spam|moderator)\b", 'all': False, 'sites': ["parenting.stackexchange.com"], 'reason': "bad keyword in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 50},
        #
        # Category: other
        # Blacklisted usernames
        {'regex': u"(?i)(tejveer ?iq|ser?vice pemanas?)", 'all': True, 'sites': [], 'reason': "blacklisted username", 'title': False, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 50}
    ]

    @staticmethod
    def test_post(title, body, user_name, site, is_answer, body_is_summary, user_rep):
        result = []
        why = ""
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
            if rule['stripcodeblocks']:    # use a placeholder to avoid triggering "few unique characters" when most of post is code
                body_to_check = regex.sub("(?s)<pre>.*?</pre>", "placeholder for omitted code block", body)
                body_to_check = regex.sub("(?s)<code>.*?</code>", "placeholder for omitted code block", body_to_check)
            if rule['reason'] == 'Phone number detected in {}':
                body_to_check = regex.sub("<img[^>]+>", "", body_to_check)
                body_to_check = regex.sub("<a[^>]+>", "", body_to_check)
            if rule['all'] != (site in rule['sites']) and user_rep <= rule['max_rep']:
                matched_body = None
                compiled_regex = None
                if is_regex_check:
                    compiled_regex = regex.compile(rule['regex'], regex.UNICODE)
                    matched_title = compiled_regex.findall(title)
                    matched_username = compiled_regex.findall(user_name)
                    if (not body_is_summary or rule['body_summary']) and (not is_answer or check_if_answer) and (is_answer or check_if_question):
                        matched_body = compiled_regex.findall(body_to_check)
                else:
                    assert 'method' in rule
                    matched_title, why_title = rule['method'](title, site)
                    if (matched_title) and rule['title']:
                        why += "Title - " + why_title + "\n"
                    matched_username, why_username = rule['method'](user_name, site)
                    if (matched_username) and rule['username']:
                        why += "Username - " + why_username + "\n"
                    if (not body_is_summary or rule['body_summary']) and (not is_answer or check_if_answer) and (is_answer or check_if_question):
                        matched_body, why_body = rule['method'](body_to_check, site)
                        if (matched_body) and rule['body']:
                            why += "Post - " + why_body + "\n"
                if matched_title and rule['title']:
                    why += FindSpam.generate_why(compiled_regex, title, u"Title", is_regex_check)
                    result.append(rule['reason'].replace("{}", "title"))
                if matched_username and rule['username']:
                    why += FindSpam.generate_why(compiled_regex, user_name, u"Username", is_regex_check)
                    result.append(rule['reason'].replace("{}", "username"))
                if matched_body and rule['body']:
                    why += FindSpam.generate_why(compiled_regex, body, u"Body", is_regex_check)
                    type_of_post = "answer" if is_answer else "body"
                    result.append(rule['reason'].replace("{}", type_of_post))
        result = list(set(result))
        result.sort()
        why = why.strip()
        return result, why

    @staticmethod
    def generate_why(compiled_regex, matched_text, type_of_text, is_regex_check):
        if is_regex_check:
            search = compiled_regex.search(matched_text)
            span = search.span()
            group = search.group()
            return type_of_text + u" - Position {}-{}: {}\n".format(span[0] + 1, span[1] + 1, group)
        return ""
