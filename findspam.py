# -*- coding: utf-8 -*-
import regex
import phonenumbers


class FindSpam:
    bad_keywords = ["baba ?ji", "fifa.*coins?", "fifabay", "Long Path Tool",
                    "fifaodell", "brianfo", "tosterone", "bajotz",
                    "vashi?k[ae]r[ae]n", "kolcak"
                    "porn", "molvi", "judi bola", "ituBola.com", "lost lover'?s?",
                    "acai", "skin care", "rejuvenated skin",
                    "LifeForce", "swtor2credits", "me2.do", "black magic",
                    "bam2u", "Neuro(3X|flexyn|fuse)", "Nutra", "TesteroneXL",
                    "Bowtrol", "Slim ?Genix", "Cleanse EFX",
                    "Forskolin", "Blackline Elite", "TestCore Pro",
                    "Xtreme Antler", "Maxx Test 3000", "orvigomax",
                    "Cheap Wigs?", "jivam", "(Improve )?Brain Power", "Maximum ?Shred",
                    "aging skin", "acne( prone)? skin", "(skin )?eye serum",
                    "skin (serum|eye)", "bagprada", "6611165613", "Apowersoft",
                    "Service Solahart", "junisse",
                    "(fake|original|uk|novelty) (passports?|driver'?s? licen[cs]e|ID cards?)",
                    "(support|service|helpline)( phone)? number|1[ -]?[ -]?[ -]?866[ -]?978[ -]?(6819|6762)",
                    "(mcafee|hotmail|gmail|outlook|yahoo|lexmark (printer)?) ?(password( recovery)?|tech)? ?((customer|technical) (support|service))? (support|contact|telephone|help(line)?|phone) number",
                    "kitchen for sale", "pdftoexcelconverter", "keepbrowsersafe", "SpyHunter",
                    "pcerror-fix", "filerepairtool", "combatpcviruses", "SkinCentric",
                    "JobsTribune", "join the illuminati", "Brorsoft", "Remo Recover",
                    "kinnaristeel", "clash of (clan|stone)s? (cheats?|tricks?|gems?)",
                    r"(?x:B [\s_]* A [\s_]* M \W{0,5} W [\s_]* A [\s_]* R [\s_]* \.? [\s_]* C [\s_]* O [\s_]* M)",
                    "slumber pm", "1-844-400-7325", "male enhancement", "bestcollegechina",
                    "bbwdesire"]
    bad_keywords_nwb = [u"ಌ", "babyliss", "garcinia", "acai ?berry",  # "nwb" == "no word boundary"
                        "aging ?cream", "b ?a ?m ?((w ?o ?w)|(w ?a ?r))",
                        "abam26"]
    blacklisted_websites = ["online ?kelas", "careyourhealths", "wowtoes",
                            "ipubsoft", "orabank", "powerigfaustralia",
                            "cfpchampionship2015playofflive",
                            "maletestosteronebooster",
                            "tripleeffectseyeserum", "healthcaresup",
                            "filerepairforum",
                            "lxwpro-t", "casque-beatsbydre", "tenderpublish",
                            "elliskinantiaging", "funmac", "lovebiscuits",
                            "Eglobalfitness", "musclezx90site", "fifapal",
                            "hits4slim", "screenshot\\.net", "downloadavideo\\.net",
                            "strongmenmuscle", "sh\\.st/", "musclehealthfitness",
                            "svelmeblog", "preply\\.com", "hellofifa",
                            "fifa15online", "wearepropeople.com", "tagwitty",
                            "axsoccertours", "ragednablog", "ios8easyjailbreak",
                            "totalfitnesspoint", "trustessaywriting",
                            "trustmyessay", "faasoft", "besttvshows", "mytechlabs",
                            "giikers", "pagetube", "myenv\\.org",
                            "pelevoniface",
                            "skinphysiciantips", "fifa2coins", "xtrememusclerecoveryrev",
                            "diabacordoesitwork", "thehealthyadvise",
                            "premiumpureforskolinrev", "hyperglycemiaabout", "dietandhealthguide",
                            "health350", "sourceforge\\.net/projects/freepdftojpgconverter",
                            "pdftoexel\\.wordpress\\.com", "best7th\\.in",
                            "recoverytoolbox\\.com", "mkmk9", "malwaretips", "intellipaat\\.com",
                            "webbuildersguide\\.com", "idealshare.net", "lankabpoacademy\\.com",
                            "evomailserver\\.com", "gameart\\.net",
                            "sofotex\\.com",
                            "mybloggingmoney\\.com", "windows-techsupport\\.com",
                            "supplementsdeal\\.com", "drivethelife\\.com",
                            "lafozi\\.com", "hipslimgarcinia\\.com", "open-swiss-bank\\.com",
                            "healthy-weight-loss-tips\\.com",
                            "tenorshare\\.com", "advancedpdfconverter\\.com",
                            "fix-computer\\.net",
                            "macvideoconverterpro\\.com", "password-master\\.net",
                            "photorecovery-formac\\.com",
                            "rarpasswordunlocker\\.net",
                            "windows7-password-reset\\.net", "windowspasswordcracker\\.com"
                            "windowspasswordreset\\.net",
                            "youtubedownloaderconverter\\.net",
                            "smartpcfixer\\.com", "1fix\\.org",
                            "drivertuner\\.com", "easyfix\\.org", "errorsfixer\\.org",
                            "faq800\\.com", "fix1\\.org", "guru4pc\\.net", "howto4pc\\.org",
                            "official-drivers\\.com", "pceasynow\\.com",
                            "regeasypro\\.com", "registryware\\.org", "smartfixer\\.net",
                            "smartfixer\\.org", "wisefixer\\.com", "wisefixer\\.net",
                            "passwordunlocker\\.com",
                            "password-unlocker\\.com", "passwordtech\\.com", "goshareware\\.com",
                            "nemopdf\\.com", "apowersoft\\.com", "downloaddailymotion\\.com",
                            "free-download-youtube\\.com", "free-music-downloader\\.com",
                            "video-download-capture\\.com", "videograbber\\.net",
                            "password-buster\\.com",
                            "remorecover\\.com", "remosoftware\\.com", "crazybulkreviewsz\\.com",
                            "\\bpatch\\.com\\b", "ajgilworld\\.com", "santomais", "viilms",
                            "clashofclansastucegemmes\\.com", "mothersday-2014\\.org",
                            "bestcelebritiesvideo\\.com", "shopnhlbruins\\.com",
                            "downloadscanpst\\.com",
                            "listoffreeware\\.com", "bigasoft\\.com", "opclub07\\.com",
                            "allavsoft", "vpnranks\\.com", "garciniasecretdietabout\\.com",
                            "musclebuildingproducts\\.info", "magichealthandwellness\\.com",
                            "vanskeys\\.com", "cheapessaywritingservice", "edbtopsts\\.com",
                            "texts\\.io", "writage\\.com", "mobitsolutions\\.com",
                            "askpcexperts\\.com", "anonymousvpnsoftware\\.com",
                            "ecouponcode\\.com", "wasel\\.com", "i-spire\\.com",
                            "internetwasel\\.com", "waselpro\\.com", "iwasl\\.com",
                            "vpnfaqs\\.com", "vpnanswers\\.com", "bestcheapvpnservice\\.com",
                            "unblockingtwitter\\.com", "openingblockedsite\\.com",
                            "arabicdownloads\\.com", "arabicsoftdownload\\.com",
                            "repairtoolbox\\.com", "couchsurfing\\.com",
                            "gta5codes\\.fr", "musclezx90au\\.com",
                            "fallclassicrun\\.com", "forgrams\\.com",
                            "tophealthresource\\.com", "cloudinsights\\.net",
                            "(premium|priceless)-inkjet\\.com", "antivirus\\.comodo\\.com",
                            "clusterlinks\\.com", "connectify\\.me", "liftserump\\.com",
                            "kizi1000\\.in", "weightruinations\\.com",
                            "\\Bfacts\\.(com|net|org)", "products\\.odosta\\.com",
                            "rackons\\.com", "imonitorsoft\\.com",
                            "analec\\.com", "livesportstv\\.us",
                            "dermaessencecreamblog\\.com", "stadtbett\\.com",
                            "healthcaresdiscussion\\.com",
                            "recovery(pro)?\\.(com|net|org)", "password\\.(com|net|org)",
                            "\\.repair\\b", "optimalstackfacts", "x4facts"]
    rules = [
        {'regex': u"(?i)\\b(%s)\\b|%s" % ("|".join(bad_keywords), "|".join(bad_keywords_nwb)), 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)\\b(baba|nike)\\b", 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)\\p{Script=Hangul}", 'all': True,
         'sites': [], 'reason': "Korean character in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)(>>>>|===>|==>>>)(?s).*http", 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"<blockquote>[^\/]*<blockquote>", 'all': True,
         'sites': [], 'reason': "Nested quote blocks in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"(?i)\\b(weight (body ?builder|loo?s[es]|reduction)|muscles?|anti aging|loo?s[es] weight|wrinkles?|diet ?plan)\\b", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com"], 'reason': "Bad keyword in {}", 'title': True, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"(?i)^(?:(?=.*?\\b(?:online|hd)\\b)(?=.*?(?:free|full|unlimited)).*?movies?\\b|(?=.*?\\b(?:acai|kisn)\\b)(?=.*?care).*products?\\b|(?=.*?packer).*mover)", 'all': True,
         'sites': [], 'reason': "Bad keywords in {}", 'title': True, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"\\d(?:_*\\d){9}|\\+?\\d_*\\d[\\s\\-]?(?:_*\\d){8,11}|\\d[ -]?\\d{3}[ -]?\\d{3}[ -]?\\d{4}", 'all': True,
         'sites': ["patents.stackexchange.com"], 'reason': "Phone number detected", 'validation_method': 'check_phone_numbers', 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"(?i)\\b(nigg(a|er)|asshole|fag|fuck(ing?)?|shit|whore|cunt)s?\\b", 'all': True,
         'sites': [], 'reason': "Offensive {} detected", 'insensitive':True, 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)\\b(crap)\\b", 'all': True, 'sites': [], 'reason': "Offensive {} detected", 'insensitive': True, 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"^(?=.*\p{upper})\P{lower}*$", 'all': True, 'sites': [], 'reason': "All-caps title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"^(?=.*[0-9])[^\\pL]*$", 'all': True, 'sites': [], 'reason': "Numbers-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"https?://(?!(www\\.)?example\\.com)[a-zA-Z0-9_.-]+\\.[a-zA-Z]{2,4}(/[a-zA-Z0-9_/?=.-])?", 'all': True,
         'sites': ["stackoverflow.com", "superuser.com", "askubuntu.com"], 'reason': "URL in title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"(?i)(%s)" % "|".join(blacklisted_websites), 'all': True,
         'sites': [], 'reason': "Blacklisted website", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"([^\\s_.?!=0-9-])\\1{10,}", 'all': True, 'sites': [], 'reason': "Repeating characters in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"(?i)(?P<word>[a-zA-Z]+).*((\\b| )+(?P=word)){5,}", 'all': True, 'sites': [], 'reason': "Repeating words in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"^(.)\\1+$", 'all': True, 'sites': [], 'reason': "{} has only one unique char", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"(?<![=#/])\\b[A-z0-9_.%+-]+@(?!example\\.com)[A-z0-9_.%+-]+\\.[A-z]{2,4}\\b", 'all': True,
         'sites': ["stackoverflow.com", "superuser.com", "serverfault.com", "askubuntu.com", "webapps.stackexchange.com", "salesforce.stackexchange.com", "unix.stackexchange.com"], 'reason': "Email in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"(?i)(tejveer ?iq|ser?vice pemanas?)", 'all': True, 'sites': [], 'reason': "Blacklisted username", 'title': False, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u".*<pre>.*", 'all': False, 'sites': ["puzzling.stackexchange.com"], 'reason': 'Code block', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False, 'report_everywhere': False, 'body_summary': False}
    ]

    @staticmethod
    def test_post(title, body, user_name, site, is_answer, body_is_summary):
        result = []
        for rule in FindSpam.rules:
            body_to_check = body
            if rule['stripcodeblocks']:
                body_to_check = regex.sub("<pre>.*?</pre>", "", body, flags=regex.DOTALL)
                body_to_check = regex.sub("<code>.*?</code>", "", body_to_check, flags=regex.DOTALL)
            if rule['all'] != (site in rule['sites']):
                matched_title = regex.compile(rule['regex'], regex.UNICODE).findall(title)
                matched_username = regex.compile(rule['regex'], regex.UNICODE).findall(user_name)
                matched_body = regex.compile(rule['regex'], regex.UNICODE).findall(body_to_check)
                if matched_title and rule['title']:
                    try:
                        if getattr(FindSpam, "%s" % rule['validation_method'])(matched_title):
                            result.append(rule['reason'])
                    except KeyError:  # There is no special logic for this rule
                        result.append(rule['reason'].replace("{}", "title"))
                if matched_username and rule['username']:
                    try:
                        if getattr(FindSpam, "%s" % rule['validation_method'])(matched_username):
                            result.append(rule['reason'])
                    except KeyError:  # There is no special logic for this rule
                        result.append(rule['reason'].replace("{}", "username"))
                if matched_body and rule['body'] and (not body_is_summary or rule['body_summary']):
                    type_of_post = "answer" if is_answer else "body"
                    try:
                        if getattr(FindSpam, "%s" % rule['validation_method'])(matched_body):
                            result.append(rule['reason'].replace("{}", type_of_post))
                    except KeyError:  # There is no special logic for this rule
                        result.append(rule['reason'].replace("{}", type_of_post))
        return result

    @staticmethod
    def check_phone_numbers(matched):
        test_formats = ["IN", "US", None]
        for phone_number in matched:
            for testf in test_formats:
                try:
                    z = phonenumbers.parse(phone_number, testf)
                    if phonenumbers.is_possible_number(z) and phonenumbers.is_valid_number(z):
                        print "Possible %s, Valid %s, Explain: %s" % (phonenumbers.is_possible_number(z), phonenumbers.is_valid_number(z), z)
                        return True
                except phonenumbers.phonenumberutil.NumberParseException:
                    pass
        return False
