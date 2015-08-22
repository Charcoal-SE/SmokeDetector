# -*- coding: utf-8 -*-
import regex
import phonenumbers
from bs4 import BeautifulSoup


def has_repeated_words(s, site):
    words = regex.split(r"[\s.,:;!/\()\[\]+_-]", s)
    words = [w for w in words if w != ""]
    curr = 0
    prev = ""
    for w in words:
        if w == prev and w.isalpha() and len(w) > 1:
            curr += 1
        else:
            curr = 0
        prev = w
        if curr >= 5:
            return True
    return curr >= 5


def has_few_characters(s, site):
    uniques = len(set(list(s))) - 4    # discount < / p > which always appear in post body
    return (len(s) > 36 and uniques < 8) or (len(s) > 100 and uniques < 16)    # reduce if false reports appear


def has_duplicate_links(s, site):
    soup = BeautifulSoup(s)
    links = soup.findAll('a', href=True)
    links = [link['href'] for link in links]
    return len(links) != len(set(links))


def has_repeating_characters(s, site):
    if s is None or len(s) == 0:
        return False
    matches = regex.compile("([^\\s_.,?!=~*/0-9-])(\\1{10,})", regex.UNICODE).findall(s)
    matches = ["".join(match) for match in matches]
    match = "".join(matches)
    return (100 * len(match) / len(s)) >= 20


class FindSpam:
    bad_keywords = ["baba ?ji", "fifa.*coins?", "fifabay", "Long Path Tool",
                    "fifaodell", "brianfo", "tosterone", "bajotz",
                    "vashi?k[ae]r[ae]n", "kolcak", "Zapyo", "we (offer|give out) loans",
                    "porn", "molvi", "judi bola", "ituBola.com", "lost lover'?s?",
                    "rejuvenated skin", "ProBrain", "restore[ -]?samsung[ -]?data",
                    "LifeForce", "swtor2credits", "me2.do", "black magic",
                    "bam2u", "Neuro(3X|flexyn|fuse|luma|plex)", "TesteroneXL", "Nitroxin",
                    "Bowtrol", "Slim ?Genix", "Cleanse EFX", "Alpha Rush",
                    "Blackline Elite", "TestCore Pro",
                    "Xtreme Antler", "Maxx Test 3000", "orvigomax",
                    "Cheap Wigs?", "jivam", "Brain (Power|Peak)", "Maximum ?Shred",
                    "aging skin", "acne( prone)? skin", "black[ -]label[ -]no",
                    "skin (serum|eye)", "bagprada", "6611165613", "Apowersoft",
                    "Service Solahart", "junisse", "Profactor[ -]?T"
                    "(fake|original|uk|novelty) (passports?|driver'?s? licen[cs]e|ID cards?)",
                    "(support|service|helpline)( phone)? number|1[ -]?[ -]?[ -]?866[ -]?978[ -]?(6819|6762)",
                    "(mcafee|hotmail|gmail|outlook|yahoo|lexmark (printer)?) ?(password( recovery)?|tech)? ?((customer|technical) (support|service))? (support|contact|telephone|help(line)?|phone) number",
                    "kitchen for sale", "pdftoexcelconverter", "keepbrowsersafe", "SpyHunter",
                    "pcerror-fix", "filerepairtool", "combatpcviruses", "SkinCentric",
                    "JobsTribune", "join the illuminati", "Brorsoft", "Remo Recover",
                    "kinnaristeel", "clash of (clan|stone)s? (cheats?|tricks?|gems?)",
                    r"(?x:B [\s_]* A [\s_]* M \W{0,5} W [\s_]* A [\s_]* R [\s_]* \.? [\s_]* C [\s_]* O [\s_]* M)",
                    "slumber pm", "1-844-400-7325", "(male|penile) enhancement", "bestcollegechina",
                    "bbwdesire", "rsorder", "Shopping ?Cart ?Elite", "Easy ?Data ?Feed",
                    "breasts? enlargement", "best property management", "eduCBA", "Solid[ -]?SEO[ -]?Tools",
                    "maxman ?power", "niagen", "Testo (X|Black)", "day ?trading ?academy", " %uh ",
                    "skinology", "folliplex", "ProDermagenix", "yafei ?cable", "MSP ?Hack ?Tool",
                    "kidney[ -]?bean[ -]?extract", "uggs ?on ?sale", "PhenQ", "Hack ?Tool ?2015",
                    "Vigoraflo", "Fonepaw", "Provasil", "(sas|hadoop|mapreduce|oracle|dba) training",
                    "intellipaat", "Replennage", "Alpha XTRM", "Synagen"]
    bad_keywords_nwb = [u"ಌ", "babyliss", "garcinia", "acai ?berr",  # "nwb" == "no word boundary"
                        "(eye|skin|aging) ?cream", "b ?a ?m ?((w ?o ?w)|(w ?a ?r))", "online ?it ?guru",
                        "abam26", "watch2live", "cogniq", "eye ?(serum|lift)", "tophealth", "poker ?online"
                        "caralluma", "male\\Wperf", "anti[- ]?aging", "lumisse", "ultra[ -]?ketone",
                        "oro[ -]?lift", "skin ?care", "diabazole", "forskolin", "tonaderm", "lumagenex",
                        "nuando[ -]?instant", "\\bnutra", "nitro[ -]?slim", "aimee[ -]?cream"]
    blacklisted_websites = ["online ?kelas", "careyourhealths", "wowtoes",
                            "ipubsoft", "orabank", "powerigfaustralia",
                            "cfpchampionship2015playofflive", "rankassured\\.com",
                            "maletestosteronebooster", "menintalk", "king-steroid"
                            "healthcaresup", "filerepairforum", "beautyskin",
                            "lxwpro-t", "casque-beatsbydre", "tenderpublish",
                            "funmac", "lovebiscuits", "z-data.blogspot.com",
                            "Eglobalfitness", "musclezx90site", "fifapal",
                            "hits4slim", "screenshot\\.net", "downloadavideo\\.net",
                            "strongmenmuscle", "sh\\.st/", "musclehealthfitness",
                            "svelmeblog", "preply\\.com", "hellofifa",
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
                            "pceasynow\\.com", "qobul\\.com",
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
                            "allavsoft", "tryapext\\.com", "essayscouncil\\.com", "caseism\\.com",
                            "vanskeys\\.com", "cheapessaywritingservice", "edbtopsts\\.com",
                            "texts\\.io", "writage\\.com", "mobitsolutions\\.com",
                            "askpcexperts\\.com", "anonymousvpnsoftware\\.com",
                            "ecouponcode\\.com", "wasel(pro)?\\.com", "i-spire\\.(com|net)",
                            "iwasl\\.com", "vpn(faqs|answers|ranks|4games)\\.com",
                            "unblockingtwitter\\.com", "openingblockedsite\\.com",
                            "arabic(soft)?downloads?\\.com",
                            "repairtoolbox\\.com", "couchsurfing\\.com",
                            "gta5codes\\.fr", "musclezx90au\\.com",
                            "fallclassicrun\\.com", "forgrams\\.com",
                            "cloudinsights\\.net", "xtremenitro",
                            "(premium|priceless)-inkjet\\.com", "antivirus\\.comodo\\.com",
                            "clusterlinks\\.com", "connectify\\.me", "liftserump\\.com",
                            "kizi1000\\.in", "weightruinations\\.com",
                            "products\\.odosta\\.com", "naturacelhelp",
                            "rackons\\.com", "imonitorsoft\\.com",
                            "analec\\.com", "livesportstv\\.us",
                            "dermaessencecreamblog\\.com", "stadtbett\\.com",
                            "jetcheats\\.com", "rsgoldmall", "cheatio\\.com",
                            "optimalstackfacts", "x4facts", "endomondo\\.com",
                            "litindia\\.in", "shoppingcartelite\\.com",
                            "customizedwallpaper\\.com", "cracksofts\\.com",
                            "crevalorsite\\.com", "macfixz\\.com", "moviesexplore\\.com",
                            "iphoneunlocking\\.org", "thehealthvictory\\.com",
                            "bloggermaking\\.com", "supportphonenumber\\.com",
                            "slimbodyketone", "prinenidz\\.com", "e-priceinbd",
                            "maddenmobilehack", "supplements4help",
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
                            "appsforpcdownloads", "healthsupplementcare\\.com",
                            "musclebuilding(products|base)", "Blogdolllar\\.net", "bendul\\.com",
                            "megatachoco", "crazybulkstacks", "sqliterecovery\\.com",
                            "creative-proteomics", "biomusclexrrev\\.com",
                            "123trainings\\.com", "(bestof|beta)cheat\\.com", "surejob\\.in",
                            "israelbigmarket"]
    pattern_websites = [r"health\d{3,}", "\\.repair\"", r"filefix(er)?\.com", "\.page\.tl\W",
                        r"\.(com|net)/xtra[\w-]", r"//xtra[\w-]*\.(co|net|org|in\W|info)",
                        r"fifa\d+[\w-]*\.com",
                        r"[\w-](recovery|repair|converter)(pro|kit)?\.(com|net)",
                        r"fix[\w-]*(files?|tool(box)?)\.com",
                        r"(repair|recovery|fix)tool(box)?\.com",
                        r"smart(pc)?fixer\.(com|net|org)",
                        r"password-?(cracker|unlocker|reset|buster|master)\.(com|net|org)",
                        r"(downloader|pdf)converter\.(com|net)",
                        r"//cheat[\w-]{3,}\.(co|net|org|in\W|info)",
                        r"([\w-]password|\Bfacts|\Btoyshop|[\w-]{6,}cheats)\.(co|net|org|in\W|info)",
                        r"(ketones|seotools|crazybulk|onsale|fat(burn|loss)|(\.|//|best)cheap|online(training|solution))[\w-]*\.(co|net|org|in\W|info)",
                        r"(loans|escort|testo|cleanse|supplement|serum|wrinkle|topcare|freetrial)[\w-]*\.(co|net|org|in\W|info)",
                        r"(buy|premium|training|thebest)[\w-]{10,}\.(co|net|org|in\W|info)",
                        r"(natural|pro|magic)[\w-]*health[\w-]*\.(co|net|org|in\W|info)",
                        r"(eye|skin|age|aging)[\w-]*cream[\w-]*\.(co|net|org|in\W|info)",
                        r"(medical|health|beauty|rx)[\w-]*(try|idea|pro|tip|review|blog|guide|advi[sc]|discussion|solution|consult)[\w-]*\.(co|net|org|in\W|info)",
                        r"[\w-]{11,}(ideas?|income|sale|reviews?|advices?|problog|analysis)\.(co|net|org|in\W|info)",
                        "-poker\\.com", "send[\w-]*india\.(co|net|org|in\W|info)",
                        r"(corrupt|repair)[\w-]*.blogspot",
                        r"(file|photo)recovery[\w-]*\.(co|net|org|in\W|info)"]
    rules = [
        {'regex': ur"(?i)\b(%s)\b|%s" % ("|".join(bad_keywords), "|".join(bad_keywords_nwb)), 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)\\b((?<!['\"])baba(?!['\"])|nike)\\b", 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': ur"(?is)^.{0,400}\bgratis\b.{0,400}$", 'all': True,
         'sites': ['softwarerecs.stackexchange.com'], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': ur"(?i)\p{Script=Hangul}", 'all': True,
         'sites': [], 'reason': "Korean character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"(?i)\p{Script=Han}", 'all': True,
         'sites': ["chinese.stackexchange.com", "japanese.stackexchange.com"], 'reason': "Chinese character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"(?i)(>>>|===>|==>>>|Read More\s*>>)(?=(?s).{0,20}http)", 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': ur"<blockquote>\s*(<blockquote>\s*)+\s*<a", 'all': True,
         'sites': [], 'reason': "Nested quote blocks with link", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': ur"(?i)\b(mortgages?|loans)\b", 'all': True,
         'sites': ["money.stackexchange.com", "math.stackexchange.com", "law.stackexchange.com", "economics.stackexchange.com"], 'reason': "Bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"(?i)\b(muscles?|testo ?[sx]\w*|body ?build(er|ing)|wrinkles?|supplements?|probiotics?)\b", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com"], 'reason': "Bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"(?i)diet ?plan|\b(pro)?derma(?!to)|(fat|weight)[ -]?(loo?s[es]|reduction)|loo?s[es] ?weight", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com"], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True},
        {'regex': ur"(?i)(workout|fitness|diet|perfecthealth)[\w-]*\.(com|co\.|net)", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com", "skeptics.stackexchange.com"], 'reason': "Pattern-matching website in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': ur"(?i)^(?:(?=.*?\b(?:online|hd)\b)(?=.*?(?:free|full|unlimited)).*?movies?\b)|(?=.*?\b(?:acai|kisn)\b)(?=.*?care).*products?\b|(?=.*?packer).*mover|online.*training| vs .* live", 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"\d(?:_*\d){9}|\+?\d_*\d[\s-]?(?:_*\d){8,11}|\d[ -]?\d{3}[ -]?\d{3}[ -]?\d{4}", 'all': True,
         'sites': ["patents.stackexchange.com", "math.stackexchange.com"], 'reason': "Phone number detected in {}", 'validation_method': 'check_phone_numbers', 'title': True, 'body': False, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': ur"(?i)\b(nigg(a|er)|asshole|fag|fuck(ing?)?|shit(t?er|hole)|whore|cunt)s?\b", 'all': True,
         'sites': [], 'reason': "Offensive {} detected", 'insensitive':True, 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True},
        {'regex': ur"(?i)\bcrap\b", 'all': True, 'sites': [], 'reason': "Offensive {} detected", 'insensitive': True, 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"^(?=.*\p{upper})\P{lower}*$", 'all': True, 'sites': [], 'reason': "All-caps title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"^(?=.*[0-9])[^\pL]*$", 'all': True, 'sites': [], 'reason': "Numbers-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}", 'all': True,
         'sites': ["stackoverflow.com", "superuser.com", "askubuntu.com"], 'reason': "URL in title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"^https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}(/\S*)?$", 'all': False,
         'sites': ["stackoverflow.com", "superuser.com", "askubuntu.com"], 'reason': "URL-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"(?i)(%s)" % "|".join(blacklisted_websites), 'all': True,
         'sites': [], 'reason': "Blacklisted website in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)(%s)(?![^>]*<)" % "|".join(pattern_websites), 'all': True,
         'sites': [], 'reason': "Pattern-matching website in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True},
        {'method': has_few_characters, 'all': True, 'sites': [], 'reason': "Few unique characters in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'method': has_repeating_characters, 'all': True, 'sites': [], 'reason': "Repeating characters in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'method': has_repeated_words, 'all': True, 'sites': [], 'reason': "Repeating words in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'method': has_duplicate_links, 'all': False, 'sites': ["patents.stackexchange.com"], 'reason': "Duplicate links in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'answers': False},
        {'regex': ur"^(.)\1+$", 'all': True, 'sites': [], 'reason': "{} has only one unique char", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': ur"(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain)\.(com|net|org))[A-z0-9_.%+-]+\.[A-z]{2,4}\b", 'all': True,
         'sites': ["stackoverflow.com", "superuser.com", "serverfault.com", "askubuntu.com", "webapps.stackexchange.com", "salesforce.stackexchange.com", "unix.stackexchange.com", "webmasters.stackexchange.com", "wordpress.stackexchange.com", "magento.stackexchange.com"], 'reason': "Email in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"(?i)(tejveer ?iq|ser?vice pemanas?)", 'all': True, 'sites': [], 'reason': "Blacklisted username", 'title': False, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"(?i)vs", 'all': False, 'sites': ["patents.stackexchange.com"], 'reason': 'Bad keyword in {}', 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"http://[A-Za-z0-9-\.]*/?[A-Za-z0-9-]*/?</a>(?:</strong>)?\s*</p>\s*$", 'all': False, 'sites': ["superuser.com", "drupal.stackexchange.com", "meta.stackexchange.com"], 'reason': 'Link at end of {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'answers': False},
        {'regex': u".*<pre>.*", 'all': False, 'sites': ["puzzling.stackexchange.com"], 'reason': 'Code block', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'report_everywhere': False, 'body_summary': False}
    ]

    @staticmethod
    def test_post(title, body, user_name, site, is_answer, body_is_summary):
        result = []
        why = ""
        for rule in FindSpam.rules:
            body_to_check = body
            try:
                check_if_answer = rule['answers']
            except KeyError:
                check_if_answer = True
            if rule['stripcodeblocks']:
                body_to_check = regex.sub("(?s)<pre>.*?</pre>", "<pre></pre>", body)
                body_to_check = regex.sub("(?s)<code>.*?</code>", "<code></code>", body_to_check)
            if rule['reason'] == 'Phone number detected in {}':
                body_to_check = regex.sub("<img[^>]+>", "", body_to_check)
                body_to_check = regex.sub("<a[^>]+>", "", body_to_check)
            if rule['all'] != (site in rule['sites']):
                matched_body = None
                compiled_regex = None
                if 'regex' in rule:
                    compiled_regex = regex.compile(rule['regex'], regex.UNICODE)
                    matched_title = compiled_regex.findall(title)
                    matched_username = compiled_regex.findall(user_name)
                    if (not body_is_summary or rule['body_summary']) and (not is_answer or check_if_answer):
                        matched_body = compiled_regex.findall(body_to_check)
                else:
                    assert 'method' in rule
                    matched_title = rule['method'](title, site)
                    matched_username = rule['method'](user_name, site)
                    if (not body_is_summary or rule['body_summary']) and (not is_answer or check_if_answer):
                        matched_body = rule['method'](body_to_check, site)
                if matched_title and rule['title']:
                    if 'regex' in rule:
                        search = compiled_regex.search(title)
                        span = search.span()
                        group = search.group()
                        why += "Title - Position %i-%i: %s\n" % (span[0] + 1, span[1] + 1, group)
                    try:
                        if getattr(FindSpam, "%s" % rule['validation_method'])(matched_title):
                            result.append(rule['reason'].replace("{}", "title"))
                    except KeyError:  # There is no special logic for this rule
                        result.append(rule['reason'].replace("{}", "title"))
                if matched_username and rule['username']:
                    if 'regex' in rule:
                        search = compiled_regex.search(user_name)
                        span = search.span()
                        group = search.group()
                        why += "Username - Position %i-%i: %s\n" % (span[0] + 1, span[1] + 1, group)
                    try:
                        if getattr(FindSpam, "%s" % rule['validation_method'])(matched_username):
                            result.append(rule['reason'].replace("{}", "username"))
                    except KeyError:  # There is no special logic for this rule
                        result.append(rule['reason'].replace("{}", "username"))
                if matched_body and rule['body']:
                    if 'regex' in rule:
                        search = compiled_regex.search(body)
                        span = search.span()
                        group = search.group()
                        why += "Body - Position %i-%i: %s\n" % (span[0] + 1, span[1] + 1, group)
                    type_of_post = "answer" if is_answer else "body"
                    try:
                        if getattr(FindSpam, "%s" % rule['validation_method'])(matched_body):
                            result.append(rule['reason'].replace("{}", type_of_post))
                    except KeyError:  # There is no special logic for this rule
                        result.append(rule['reason'].replace("{}", type_of_post))
        result = list(set(result))
        result.sort()
        why = why.strip()
        return result, why

    @staticmethod
    def check_phone_numbers(matched):
        test_formats = ["IN", "US", None]
        for phone_number in matched:
            if regex.compile(r"^21474672[56]\d$").search(phone_number):
                return False
            for testf in test_formats:
                try:
                    z = phonenumbers.parse(phone_number, testf)
                    if phonenumbers.is_possible_number(z) and phonenumbers.is_valid_number(z):
                        print "Possible %s, Valid %s, Explain: %s" % (phonenumbers.is_possible_number(z), phonenumbers.is_valid_number(z), z)
                        return True
                except phonenumbers.phonenumberutil.NumberParseException:
                    pass
        return False
