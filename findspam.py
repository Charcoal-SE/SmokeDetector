# -*- coding: utf-8 -*-
import regex
import phonenumbers


class FindSpam:
    bad_keywords = ["baba ?ji", "fifa.*coins?", "fifabay", "Long Path Tool",
                    "fifaodell", "brianfo", "nike", "tosterone", "bajotz",
                    "vashi?k[ae]r[ae]n", "sumer", "kolcak"
                    "porn", "molvi", "judi bola", "ituBola.com", "lost lover",
                    "acai", "skin care", "rejuvenated skin",
                    "LifeForce", "swtor2credits", "me2.do", "black magic",
                    "bam2u", "Neuro(3X|flexyn|fuse)", "Nutra", "TesteroneXL",
                    "Bowtrol", "Slim ?Genix", "Cleanse EFX",
                    "Forskolin", "Blackline Elite", "TestCore Pro",
                    "Xtreme Antler", "Maxx Test 3000", "orvigomax",
                    "Cheap Wigs?", "jivam", "(Improve )?Brain Power", "Maximum ?Shred",
                    "aging skin", "acne( prone)? skin", "(skin )?eye serum",
                    "skin (serum|eye)", "bagprada", "6611165613" "Apowersoft",
                    "Service Solahart", "junisse",
                    "(fake|original|uk) (passports?|driver'?s? licen[cs]e|ID cards?)",
                    "(support|service|helpline)( phone)? number|1[ -]?[ -]?[ -]?866[ -]?978[ -]?(6819|6762)",
                    "(hotmail|gmail|outlook|yahoo|lexmark (printer)?) ?(password( recovery)?|tech)? ?((customer|technical) (support|service))? (support|contact|telephone|help(line)?|phone) number",
                    "kitchen for sale", "dolphin porn", "pdftoexcelconverter", "keepbrowsersafe", "SpyHunter",
                    "pcerror-fix", "filerepairtool", "combatpcviruses"]
    bad_keywords_nwb = [u"ಌ", "babyliss", "garcinia"]  # "nwb" == "no word boundary"
    blacklisted_websites = ["online ?kelas", "careyourhealths", "wowtoes",
                            "ipubsoft", "orabank", "powerigfaustralia",
                            "cfpchampionship2015playofflive", "optimalstackfacts",
                            "maletestosteronebooster", "x4facts",
                            "tripleeffectseyeserum", "healthcaresup",
                            "garciniacambogiaprofacts", "filerepairforum",
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
                            "supertestoboostsfacts", "idolizeadvancedeyeserumfacts", "pelevoniface",
                            "skinphysiciantips", "fifa2coins", "xtrememusclerecoveryrev",
                            "diabacordoesitwork", "thehealthyadvise", "supracleanse350facts",
                            "premiumpureforskolinrev", "hyperglycemiaabout", "dietandhealthguide",
                            "health350", "sourceforge.net/projects/freepdftojpgconverter/", "pdftoexel.wordpress.com/"]
    rules = [
        {'regex': u"(?i)\\b(%s)\\b|%s" % ("|".join(bad_keywords), "|".join(bad_keywords_nwb)), 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)\\bbaba\\b", 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)(>>>>|===>|==>>>)(?s).*http", 'all': True,
         'sites': [], 'reason': "Bad keyword in {}", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"(?i)\\b(weight (body ?builder|loo?s[es]|reduction)|muscles? build(ing)?|muscles?( (grow(th)?|diets?))?|anti aging|SkinCentric|loo?s[es] weight|wrinkles?)\\b", 'all': True,
         'sites': ["fitness.stackexchange.com"], 'reason': "Bad keyword in {}", 'title': True, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"(?i)^(?:(?=.*?\\b(?:online|hd)\\b)(?=.*?(?:free|full|unlimited)).*?movies?\\b|(?=.*?\\b(?:acai|kisn)\\b)(?=.*?care).*products?\\b|(?=.*?packer).*mover)", 'all': True,
         'sites': [], 'reason': "Bad keywords in {}", 'title': True, 'body': False, 'username': True, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"\\d(?:_*\\d){9}|\\+?\\d_*\\d[\\s\\-]?(?:_*\\d){8,10}|\\d[ -]?\\d{3}[ -]?\\d{3}[ -]?\\d{4}", 'all': True,
         'sites': ["patents.stackexchange.com"], 'reason': "Phone number detected", 'validation_method': 'check_phone_numbers', 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"(?i)\\b(nigg(a|er)|asshole|fag|fuck(ing?)?|shit|whore|cunt)s?\\b", 'all': True,
         'sites': [], 'reason': "Offensive {} detected", 'insensitive':True, 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"(?i)\\b(crap)\\b", 'all': True, 'sites': [], 'reason': "Offensive {} detected", 'insensitive': True, 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': ur"^(?=.*\p{upper})\P{lower}*$", 'all': True, 'sites': [], 'reason': "All-caps title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"^(?=.*[0-9])[^a-zA-Z]*$", 'all': True, 'sites': [], 'reason': "Numbers-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"https?://[a-zA-Z0-9_.-]+\\.[a-zA-Z]{2,4}(/[a-zA-Z0-9_/?=.-])?", 'all': True,
         'sites': ["stackoverflow.com", "superuser.com", "askubuntu.com"], 'reason': "URL in title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False},
        {'regex': u"(?i)(%s)" % "|".join(blacklisted_websites), 'all': True,
         'sites': [], 'reason': "Blacklisted website", 'title': True, 'body': True, 'username': True, 'stripcodeblocks': False, 'body_summary': True},
        {'regex': u"([^\\s_.?!=0-9-])\\1{10,}", 'all': True, 'sites': [], 'reason': "Repeating characters in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"(?i)(?P<word>[a-zA-Z]+).*((\\b| )+(?P=word)){5,}", 'all': True, 'sites': [], 'reason': "Repeating words in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
        {'regex': u"^(.)\\1+$", 'all': True, 'sites': [], 'reason': "{} has only one unique char", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False},
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
