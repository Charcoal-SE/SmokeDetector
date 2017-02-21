# noinspection PyClassHasNoInit
from checks import bad_link_text, has_customer_service, has_eltima, has_few_characters, has_health, has_phone_number,\
    has_repeated_words, has_repeating_characters, is_offensive_post, keyword_email, keyword_link, link_at_end,\
    mostly_non_latin, non_english_link


# noinspection PyClassHasNoInit
class Rules:
    with open("../blacklists/bad_keywords.txt", "r") as f:
        bad_keywords = [line.decode('utf8').rstrip() for line in f if len(line.decode('utf8').rstrip()) > 0]

    with open("../blacklists/blacklisted_websites.txt", "r") as f:
        blacklisted_websites = [line.rstrip() for line in f if len(line.rstrip()) > 0]

    with open("../blacklists/blacklisted_usernames.txt", "Ur") as f:
        blacklisted_usernames = [line.rstrip() for line in f if len(line.rstrip()) > 0]

    bad_keywords_nwb = [  # "nwb" == "no word boundary"
        u"ಌ", "vashi?k[ae]r[ae]n", "babyli(ss|cious)", "garcinia", "cambogia", "acai ?berr",
        "(eye|skin|aging) ?cream", "b ?a ?m ?((w ?o ?w)|(w ?a ?r))", "online ?it ?guru",
        "abam26", "watch2live", "cogniq", "(serum|lift) ?eye", "tophealth", "poker[ -]?online",
        "caralluma", "male\\Wperf", "anti[- ]?aging", "lumisse", "(ultra|berry|body)[ -]?ketone",
        "(cogni|oro)[ -]?(lift|plex)", "diabazole", "forskolin", "tonaderm", "luma(genex|lift)",
        "(skin|face|eye)[- ]?(serum|therapy|hydration|tip|renewal|gel|lotion|cream)",
        "(skin|eye)[- ]?lift", "(skin|herbal) ?care", "nuando[ -]?instant", "\\bnutra", "nitro[ -]?slim",
        "aimee[ -]?cream", "slimatrex", "cosmitone", "smile[ -]?pro[ -]?direct", "bellavei", "opuderm",
        "contact (me|us)\\W*<a ", "follicure", "kidney[ -]?bean[ -]?extract", "ecoflex",
        "\\brsgold", "bellavei", "goji ?xtreme", "lumagenex", "ajkobeshoes", "kreatine",
        "packers.{0,15}(movers|logistic).{0,25}</a>", "guaranteedprofitinvestment",
        "(brain|breast|male|penile|penis)[- ]?(enhance|enlarge|improve|boost|plus|peak)",
        "renuva(cell|derm)", " %uh ", " %ah ", "svelme", "tapsi ?sarkar", "viktminskning",
        "unique(doc)?producers", "green ?tone ?pro", "troxyphen", "seremolyn", "revolyn",
        "(?:networking|cisco|sas|hadoop|mapreduce|oracle|dba|php|sql|javascript|js|java|designing|marketing|"
        "salesforce|joomla)( certification)? (courses?|training).{0,25}</a>",
        "(?:design|development|compan(y|ies)|training|courses?|automation).{0,8}\\L<city>",
        u"Ｃ[Ｏ|0]Ｍ", "ecoflex", "no2factor", "no2blast", "sunergetic", "capilux", "sante ?avis",
        "enduros", "dianabol", "ICQ#?\d{4}-?\d{5}", "3073598075", "lumieres", "viarex", "revimax",
        "celluria", "viatropin", "(meg|test)adrox", "nordic ?loan ?firm", "safflower",
        "(essay|resume|article|dissertation|thesis) ?writing ?service", "satta ?matka", "b.?o.?j.?i.?t.?e.?r"
    ]

    # Patterns: the top three lines are the most straightforward, matching any site with this string in domain name
    pattern_websites = [
        r"(enstella|recoverysoftware|removevirus|support(number|help|quickbooks)|techhelp|calltech|exclusive|"
        r"onlineshop|video(course|classes|tutorial(?!s))|vipmodel|(?<!word)porn|wholesale|inboxmachine|(get|buy)cheap|"
        r"escort|diploma|(govt|government)jobs|extramoney|earnathome|spell(caster|specialist)|profits|"
        r"seo-?(tool|service|trick|market)|onsale|fat(burn|loss)|(\.|//|best)cheap|online-?(training|solution))"
        r"[\w-]*?\.(co|net|org|in\W|info|ir|wordpress|blogspot|tumblr|webs\.)",
        r"(replica(?!t)|rs\d?gold|rssong|runescapegold|maxgain|e-cash|mothers?day|phone-?number|fullmovie|tvstream|"
        r"trainingin|dissertation|(placement|research)-?(paper|statement|essay)|digitalmarketing|infocampus|"
        r"cracked\w{3}|bestmover|relocation|\w{4}mortgage|loans|revenue|testo[-bsx]|cleanse|cleansing|detox|supplement|"
        r"lubricant|serum|wrinkle|topcare|freetrial)[\w-]*?\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(drivingschool|crack-?serial|serial-?(key|crack)|freecrack|appsfor(pc|mac)|probiotic|remedies|heathcare|"
        r"sideeffect|meatspin|packers\S{0,3}movers|(buy|sell)\S{0,12}cvv|goatse|burnfat|gronkaffe|muskel|"
        r"tes(tos)?terone|nitric(storm|oxide)|masculin|menhealth|intohealth|babaji|spellcaster|potentbody|slimbody|"
        r"moist|lefair|derma(?![nt])|xtrm|factorx|(?<!app)nitro(?!us)|endorev|ketone)[\w-]*?\.(co|net|org|in\W|info|"
        r"wordpress|blogspot|tumblr|webs\.)",
        r"(moving|\w{10}spell|[\w-]{3}password|\w{5}deal|\w{5}facts|\w\dfacts|\Btoyshop|[\w-]{5}cheats|[\w-]{6}girls|"
        r"clothing|shoes(inc)?|cheatcode|cracks|credits|-wallet|refunds|truo?ng|viet|trang)\.(co|net|org|in\W|info)",
        r"(health|earn|max|cash|wage|pay|pocket|cent|today)[\w-]{0,6}\d+\.com",
        r"(//|www\.)healthy?\w{5,}\.com",
        r"https?://[\w-.]\.repair\W", r"https?://[\w-.]{10,}\.(top|help)\W", r'https?://[\w-.]*-[\w-.]*\.pro[/"<]',
        r"filefix(er)?\.com", r"\.page\.tl\W", r"infotech\.(com|net|in)",
        r"\.(com|net)/(xtra|muscle)[\w-]", r"http\S*?\Wfor-sale\W",
        r"fifa\d+[\w-]*?\.com", r"[\w-](giveaway|jackets|supplys|male)\.com",
        r"((essay|resume|click2)\w{6,}|(essays|(research|term)paper|examcollection|[\w-]{5}writing|"
        r"writing[\w-]{5})[\w-]*?)\.(co|net|org|in\W|info|us)",
        r"(top|best|expert)\d\w{0,15}\.in\W", r"\dth(\.co)?\.in", r"(jobs|in)\L<city>\.in",
        r"[\w-](recovery|repairs?|rescuer|(?<!epoch|font)converter)(pro|kit)?\.(com|net)",
        r"(corrupt|repair)[\w-]*?\.blogspot", r"http\S*?(yahoo|gmail|hotmail|outlook|office|microsoft)[\w-]{0,10}"
                                              r"(account|tech|customer|support|service|phone|help)[\w-]{0,10}(service|"
                                              r"care|help|recovery|support|phone|number)",
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
        r"(training|institute|marketing)[\w-]{6,}[\w.-]*?\.(co|net|org|in\W|info)",
        r"[\w-](courses?|training)[\w-]*?\.in/", r"\w{9}(buy|roofing)\.(co|net|org|in\W|info)",
        r"(vitamin|dive|hike|love|strong|ideal|natural|pro|magic|beware|top|best|free|cheap|allied|nutrition|"
        r"prostate)[\w-]*?health[\w-]*?\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(eye|skin|age|aging)[\w-]*?cream[\w-]*?\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(acai|advance|aging|alpha|beauty|belle|beta|biotic|body|boost|brain(?!tree)|burn|colon|[^s]cream|creme|"
        r"derma|ecig|eye|face(?!book)|fat|formula|geniu[sx]|grow|hair|health|herbal|ideal|luminous|male|medical|"
        r"medicare|muscle|natura|no2|nutrition|optimal|pearl|perfect|phyto|probio|rejuven|revive|ripped|rx|scam|"
        r"shred|skin|slim|super|testo|[/.]top|trim|[/.]try|ultra|ultra|vapor|vita|weight|wellness|xplode|yoga|"
        r"young|youth)[\w]{0,20}(about|advi[sc]|assess|blog|brazil|canada|care|center|centre|chat|complex(?!ity)|"
        r"congress|consult|critic|critique|cure|denmark|discussion|doctor|dose|essence|essential|extract|fact|formula|"
        r"france|funct?ion|genix|guide|help|idea|info|jacked|l[iy]ft|mag|market|max|mexico|norway|nutrition|order|plus|"
        r"points|policy|potency|power|practice|pro|program|report|review|rewind|site|slim|solution|suppl(y|ier)|sweden|"
        r"tip|trial|try|world|zone)[.\w-]{0,12}\.(co|net|org|in\W|info|wordpress|blogspot|tumblr|webs\.)",
        r"(\w{11}(idea|income|sale)|\w{6}(<?!notebook)(advice|problog|review))s?\.(co|net|in\W|info)",
        r"-(poker|jobs)\.com", r"send[\w-]*?india\.(co|net|org|in\W|info)",
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
        r"youth\Wserum",
    ]
    city_list = [
        "Agra", "Amritsar", "Bangalore", "Bhopal", "Chandigarh", "Chennai", "Coimbatore", "Delhi", "Dubai", "Durgapur",
        "Ghaziabad", "Hyderabad", "Jaipur", "Jalandhar", "Kolkata", "Ludhiana", "Mumbai", "Madurai", "Patna",
        "Portland", "Rajkot", "Surat", "Telangana", "Udaipur", "Uttarakhand", "India", "Pakistan",
        # yes, these aren't cities but...
    ]
    rules = [
        # Sites in sites[] will be excluded if 'all' == True.  Whitelisted if 'all' == False.
        #
        # Category: Bad keywords
        # The big list of bad keywords, for titles and posts
        {'regex': ur"(?is)\b({})\b|{}".format("|".join(bad_keywords), "|".join(bad_keywords_nwb)), 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': True,
         'stripcodeblocks': False, 'body_summary': True, 'max_rep': 4, 'max_score': 1},
        # gratis at the beginning of post, SoftwareRecs is exempt
        {'regex': ur"(?is)^.{0,200}\bgratis\b$", 'all': True,
         'sites': ['softwarerecs.stackexchange.com'], 'reason': "bad keyword in {}", 'title': True, 'body': True,
         'username': False, 'stripcodeblocks': False, 'body_summary': True, 'max_rep': 11, 'max_score': 0},
        # Black magic at the beginning of question, Islam is exempt
        {'regex': ur"^(?is).{0,200}black magic", 'all': True,
         'sites': ["islam.stackexchange.com"], 'reason': "black magic in {}", 'title': True, 'body': True,
         'username': False, 'stripcodeblocks': False, 'body_summary': True, 'answers': False, 'max_rep': 11,
         'max_score': 0},
        # Bad keywords in titles and usernames, all sites
        {'regex': ur"(?i)^(?:(?=.*?\b(?:online|hd)\b)(?=.*?(?:free|full|unlimited)).*?movies?\b)|(?=.*?\b(?:acai|"
                  ur"kisn)\b)(?=.*?care).*products?\b|(?=.*?packer).*mover|(online|certification).*?training|"
                  ur"\bvs\b.*\b(live|vivo)\b|(?<!can |uld )\bwe offer\b|payday loan|смотреть.*онлайн|"
                  ur"watch\b.{0,50}(online|episode|free)|episode.{0,50}\bsub\b", 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': True,
         'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Bad keywords in titles only, all sites
        {'regex': ur"(?i)\b(?!s.m.a.r.t)[a-z]\.+[a-z]\.+[a-z]\.+[a-z]\.+[a-z]\b", 'all': True,
         'sites': [], 'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False,
         'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Eltima: separated into its own method so we can constrain length
        {'method': has_eltima, 'all': True, 'sites': [], 'reason': "bad keyword in {}", 'title': False, 'body': True,
         'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 50, 'max_score': 0},
        # Fake-customer-service in title
        {'method': has_customer_service, 'all': True, 'sites': [], 'reason': "bad keyword in {}", 'title': True,
         'body': True, 'username': False, 'stripcodeblocks': False, 'body_summary': False, 'questions': False,
         'max_rep': 1, 'max_score': 0},
        # Bad health-related keywords in titles, health sites are exempt
        {'regex': ur"(?i)\b((beauty|skin|health|face|eye)[- ]?(serum|therapy|hydration|tip|renewal|shop|store|lyft|"
                  ur"product|strateg(y|ies)|gel|lotion|cream|treatment|method|school|expert)|fat ?burn(er|ing)?|"
                  ur"muscle|testo ?[sx]\w*|body ?build(er|ing)|wrinkle|probiotic|acne|peni(s|le)|erection)s?\b|"
                  ur"(beauty|skin) care\b", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com",
                   "skeptics.stackexchange.com", "robotics.stackexchange.com"], 'reason': "bad keyword in {}",
         'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False,
         'max_rep': 1, 'max_score': 0},
        # Bad health-related keywords in titles, health sites are exempt, flexible method
        {'method': has_health, 'all': False,
         'sites': ["stackoverflow.com", "superuser.com", "askubuntu.com", "drupal.stackexchange.com",
                   "meta.stackexchange.com", "webapps.stackexchange.com", "security.stackexchange.com"],
         'reason': "bad keyword in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False,
         'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Bad health-related keywords in titles and posts, health sites are exempt
        {'regex': ur"(?is)virility|diet ?(plan|pill)|\b(pro)?derma(?=[a-su-z ]\w)|(fat|(?<!dead[ -]?)weight)"
                  ur"[ -]?(loo?s[es]|reduction)|loo?s[es] ?weight|erectile|\bherpes\b|colon ?(detox|clean)|\bpenis\b",
         'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com",
                   "skeptics.stackexchange.com", "bicycles.stackexchange.com", "islam.stackexchange.com"],
         'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True,
         'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # Korean character in title: requires 3
        {'regex': ur"(?i)\p{Script=Hangul}.*\p{Script=Hangul}.*\p{Script=Hangul}", 'all': True,
         'sites': ["korean.stackexchange.com"], 'reason': "Korean character in {}", 'title': True, 'body': False,
         'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Chinese characters in title: requires 3
        {'regex': ur"(?i)\p{Script=Han}.*\p{Script=Han}.*\p{Script=Han}", 'all': True,
         'sites': ["chinese.stackexchange.com", "japanese.stackexchange.com", "ja.stackoverflow.com"],
         'reason': "Chinese character in {}", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False,
         'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Hindi character in title
        {'regex': ur"(?i)\p{Script=Devanagari}", 'all': True,
         'sites': ["hinduism.stackexchange.com"], 'reason': "Hindi character in {}", 'title': True, 'body': False,
         'username': False, 'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # English text on non-English site: rus.SE only
        {'regex': ur"(?i)^[a-z0-9_\W]*[a-z]{3}[a-z0-9_\W]*$", 'all': False,
         'sites': ["rus.stackexchange.com"], 'reason': "English text in {} on a localized site", 'title': True,
         'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Roof repair
        {'regex': u"roof repair", 'all': True,
         'sites': ["diy.stackexchange.com", "outdoors.stackexchange.com", "mechanics.stackexchange.com"],
         'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True,
         'body_summary': True, 'max_rep': 11, 'max_score': 0},
        # Bad keywords (only include link at end sites + SO, the other sites give false positives for these keywords)
        {'regex': ur"(?i)(?<!truth )serum|\b(?<!to )supplements\b", 'all': False,
         'sites': ["stackoverflow.com", "superuser.com", "askubuntu.com", "drupal.stackexchange.com",
                   "meta.stackexchange.com", "security.stackexchange.com", "patents.stackexchange.com",
                   "money.stackexchange.com", "gaming.stackexchange.com", "arduino.stackexchange.com",
                   "workplace.stackexchange.com"],
         'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True,
         'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # Mostly non-Latin alphabet
        {'method': mostly_non_latin, 'all': True,
         'sites': ["stackoverflow.com", "ja.stackoverflow.com", "pt.stackoverflow.com", "es.stackoverflow.com",
                   "islam.stackexchange.com", "japanese.stackexchange.com", "anime.stackexchange.com",
                   "hinduism.stackexchange.com", "judaism.stackexchange.com", "buddhism.stackexchange.com",
                   "chinese.stackexchange.com", "french.stackexchange.com", "spanish.stackexchange.com",
                   "portuguese.stackexchange.com", "codegolf.stackexchange.com", "korean.stackexchange.com"],
         'reason': 'mostly non-Latin {}', 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True,
         'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # Mostly non-Latin alphabet, SO answers only
        {'method': mostly_non_latin, 'all': False,
         'sites': ["stackoverflow.com"],
         'reason': 'mostly non-Latin {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True,
         'body_summary': True, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Jesus Christ, the Son of God, on SciFi.
        {'regex': ur"Son of (David|man)", 'all': False,
         'sites': ["scifi.stackexchange.com"],
         'reason': "bad keyword in {}", 'title': False, 'body': False, 'username': True, 'stripcodeblocks': False,
         'body_summary': False, 'max_rep': 1, 'max_score': 0},
        #
        # Category: Suspicious links
        # Blacklisted sites
        {'regex': u"(?i)({})".format("|".join(blacklisted_websites)), 'all': True,
         'sites': [], 'reason': "blacklisted website in {}", 'title': True, 'body': True, 'username': False,
         'stripcodeblocks': False, 'body_summary': True, 'max_rep': 50, 'max_score': 5},
        # Suspicious sites
        {'regex': ur"(?i)({}|({})[\w-]*?\.(co|net|org|in\W|info|blogspot|wordpress))(?![^>]*<)".format(
            "|".join(pattern_websites), "|".join(bad_keywords_nwb)), 'all': True,
         'sites': [], 'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': False,
            'stripcodeblocks': True, 'body_summary': True, 'max_rep': 1, 'max_score': 1},
        # Bad keyword in link text
        {'method': bad_link_text, 'all': True,
         'sites': [], 'reason': 'bad keyword in link text in {}', 'title': False, 'body': True, 'username': False,
         'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Country-name domains, travel and expats sites are exempt
        {'regex': ur"(?i)([\w-]{6}|shop)(australia|brazil|canada|denmark|france|india|mexico|norway|pakistan|"
                  ur"spain|sweden)\w{0,4}\.(com|net)", 'all': True,
         'sites': ["travel.stackexchange.com", "expatriates.stackexchange.com"],
         'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': True,
         'stripcodeblocks': False, 'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # The TLDs of Iran, Pakistan, and Tokelau in answers
        {'regex': ur'(?i)http\S*\.(ir|pk|tk)[/"<]', 'all': True,
         'sites': [], 'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': True,
         'stripcodeblocks': False, 'body_summary': True, 'max_rep': 1, 'max_score': 0, 'questions': False},
        # Suspicious health-related websites, health sites are exempt
        {'regex': ur"(?i)(bodybuilding|workout|fitness|diet|perfecthealth|muscle|nutrition|"
                  ur"prostate)[\w-]*?\.(com|co\.|net|org|info|in\W)", 'all': True,
         'sites': ["fitness.stackexchange.com", "biology.stackexchange.com", "health.stackexchange.com",
                   "skeptics.stackexchange.com", "bicycles.stackexchange.com"],
         'reason': "pattern-matching website in {}", 'title': True, 'body': True, 'username': True,
         'stripcodeblocks': False, 'body_summary': True, 'max_rep': 4, 'max_score': 2},
        # Links preceded by arrows >>>
        {'regex': ur"(?is)(>>>+|==\s*>>+|====|===>+|==>>+|= = =|(Read More|Click Here) \W{2,20}).{0,20}"
                  ur"http(?!://i.stack.imgur.com).{0,200}$", 'all': True,
         'sites': [], 'reason': "link following arrow in {}", 'title': True, 'body': True, 'username': True,
         'stripcodeblocks': True, 'body_summary': False, 'answers': False, 'max_rep': 11, 'max_score': 0},
        # Link at the end of question, selected sites
        {'method': link_at_end, 'all': False,
         'sites': ["superuser.com", "askubuntu.com", "drupal.stackexchange.com", "meta.stackexchange.com",
                   "security.stackexchange.com", "patents.stackexchange.com", "money.stackexchange.com",
                   "gaming.stackexchange.com", "arduino.stackexchange.com", "workplace.stackexchange.com"],
         'reason': 'link at end of {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False,
         'body_summary': False, 'answers': False, 'max_rep': 1, 'max_score': 0},
        # Link at the end of a short answer
        {'regex': ur'(?is)^.{0,350}<a href="https?://(?:(?:www\.)?[\w-]+\.(?:blogspot\.|wordpress\.|co\.)?\w{2,4}'
                  ur'/?\w{0,2}/?|(?:plus\.google|www\.facebook)\.com/[\w/]+)"[^<]*</a>(?:</strong>)?\W*</p>\s*$'
                  ur'|\[/url\]\W*</p>\s*$', 'all': True,
         'sites': ["raspberrypi.stackexchange.com"], 'reason': 'link at end of {}', 'title': False, 'body': True,
         'username': False, 'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1,
         'max_score': 0},
        # URL repeated at end of post
        {'regex': ur"(?s)<a href=\"(?:http://%20)?(https?://(?:(?:www\.)?"
            ur"[\w-]+\.(?:blogspot\.|wordpress\.|co\.)?\w{2,10}/?"
            ur"[\w-]{0,40}?/?|(?:plus\.google|www\.facebook)\.com/[\w/]+))"
            ur"\" rel=\"nofollow( noreferrer)?\">"
            ur".{300,}<a href=\"(?:http://%20)?\1\" "
            ur"rel=\"nofollow( noreferrer)?\">(?:http://%20)?\1</a>"
            ur"(?:</strong>)?\W*</p>\s*$", 'all': True,
         'sites': [], 'reason': 'repeated URL at end of long post', 'title': False, 'body': True, 'username': False,
         'body_summary': False, 'stripcodeblocks': True, 'max_rep': 1, 'max_score': 0},
        # Link with "thanks for sharing" or a similar phrase in a short answer
        {'method': keyword_link, 'all': True,
         'sites': [], 'reason': 'bad keyword with a link in {}', 'title': False, 'body': True, 'username': False,
         'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # non-linked .tk site at the end of an answer
        {'regex': ur'(?is)\w{3}\.tk(?:</strong>)?\W*</p>\s*$', 'all': True,
         'sites': [], 'reason': 'pattern-matching website in {}', 'title': False, 'body': True, 'username': False,
         'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # non-linked site at the end of a short answer
        {'regex': ur'(?is)^.{0,350}\w{6}\.(com|co\.uk)(?:</strong>)?\W*</p>\s*$', 'all': True,
         'sites': [], 'reason': 'link at end of {}', 'title': False, 'body': True, 'username': False,
         'stripcodeblocks': False, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Shortened URL near the end of question
        {'regex': ur"(?is)://(goo\.gl|bit\.ly|bit\.do|tinyurl\.com|fb\.me|cl\.ly|t\.co|is\.gd|j\.mp|tr\.im|ow\.ly|"
                  ur"wp\.me|alturl\.com|tiny\.cc|9nl\.me|post\.ly|dyo\.gs|bfy\.tw|amzn\.to)/.{0,200}$", 'all': True,
         'sites': ["superuser.com", "askubuntu.com"], 'reason': "shortened URL in {}", 'title': False, 'body': True,
         'username': False, 'stripcodeblocks': True, 'body_summary': False, 'answers': False, 'max_rep': 1,
         'max_score': 0},
        # Shortened URL in an answer
        {'regex': ur"(?is)://(goo\.gl|bit\.ly|bit\.do|tinyurl\.com|fb\.me|cl\.ly|t\.co|is\.gd|j\.mp|tr\.im|ow\.ly|"
                  ur"wp\.me|alturl\.com|tiny\.cc|9nl\.me|post\.ly|dyo\.gs|bfy\.tw|amzn\.to|adf\.ly|adfoc\.us)/",
         'all': True, 'sites': [], 'reason': "shortened URL in {}", 'title': False, 'body': True, 'username': False,
         'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Link text without Latin characters
        {'regex': u">[^0-9A-Za-z<'\"]{3,}</a>", 'all': True,
         'sites': ["ja.stackoverflow.com", "ru.stackoverflow.com", "rus.stackexchange.com", "islam.stackexchange.com",
                   "japanese.stackexchange.com", "hinduism.stackexchange.com", "judaism.stackexchange.com",
                   "buddhism.stackexchange.com", "chinese.stackexchange.com", "russian.stackexchange.com",
                   "codegolf.stackexchange.com", "korean.stackexchange.com"], 'reason': 'non-Latin link in {}',
         'title': False, 'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False,
         'questions': False, 'max_rep': 1, 'max_score': 0},
        # Link text with some non-Latin characters, answers only
        {'method': non_english_link, 'all': True, 'sites': ["pt.stackoverflow.com", "es.stackoverflow.com",
                                                            "ja.stackoverflow.com", "ru.stackoverflow.com",
                                                            "rus.stackexchange.com", "islam.stackexchange.com",
                                                            "japanese.stackexchange.com", "hinduism.stackexchange.com",
                                                            "judaism.stackexchange.com", "buddhism.stackexchange.com",
                                                            "chinese.stackexchange.com", "russian.stackexchange.com",
                                                            "french.stackexchange.com", "portuguese.stackexchange.com",
                                                            "spanish.stackexchange.com", "codegolf.stackexchange.com",
                                                            "korean.stackexchange.com", "esperanto.stackexchange.com"],
         'reason': 'non-English link in {}', 'title': False, 'body': True, 'username': False, 'stripcodeblocks': True,
         'body_summary': False, 'questions': False, 'max_rep': 1, 'max_score': 0},
        # Link text is one character within a word
        {'regex': ur'(?iu)\w<a href="[^"]+" rel="nofollow( noreferrer)?">.</a>\w', 'all': True,
         'sites': [], 'reason': 'one-character link in {}', 'title': False, 'body': True, 'username': False,
         'stripcodeblocks': True, 'body_summary': False, 'max_rep': 11, 'max_score': 1},
        # Link text consists of punctuation, answers only
        {'regex': ur'(?iu)rel="nofollow( noreferrer)?">\W</a>', 'all': True,
         'sites': [], 'reason': 'linked punctuation in {}', 'title': False, 'body': True, 'username': False,
         'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 11, 'max_score': 1},
        # URL in title, some sites are exempt
        {'regex': ur"(?i)https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}|"
                  ur"\w{3,}\.(com|net)\b.*\w{3,}\.(com|net)\b", 'all': True,
         'sites': ["stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com",
                   "ja.stackoverflow.com", "superuser.com", "askubuntu.com", "serverfault.com",
                   "unix.stackexchange.com", "webmasters.stackexchange.com"], 'reason': "URL in title",
         'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False,
         'max_rep': 11, 'max_score': 0},
        # URL-only title, for the exempt sites
        {'regex': ur"(?i)^https?://(?!(www\.)?(example|domain)\.(com|net|org))[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,4}(/\S*)?$",
         'all': False,
         'sites': ["stackoverflow.com", "pt.stackoverflow.com", "ru.stackoverflow.com", "es.stackoverflow.com",
                   "ja.stackoverflow.com", "superuser.com", "askubuntu.com", "serverfault.com",
                   "unix.stackexchange.com", "webmasters.stackexchange.com"], 'reason': "URL-only title",
         'title': True, 'body': False, 'username': False, 'stripcodeblocks': False, 'body_summary': False,
         'max_rep': 11, 'max_score': 0},
        #
        # Category: Suspicious contact information
        # Phone number in title
        {'method': has_phone_number, 'all': True,
         'sites': ["patents.stackexchange.com", "math.stackexchange.com", "mathoverflow.net"],
         'reason': "phone number detected in {}", 'title': True, 'body': False, 'username': False,
         'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Phone number in post
        {'regex': ur"(?s)^.{0,250}\b1 ?[-(. ]8\d{2}[-). ] ?\d{3}[-. ]\d{4}\b", 'all': True,
         'sites': ["math.stackexchange.com"], 'reason': "phone number detected in {}", 'title': False,
         'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True, 'max_rep': 1, 'max_score': 0},
        # Email check for answers on selected sites
        {'regex': ur"(?i)(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})"
                  ur"[A-z0-9_.%+-]+\.[A-z]{2,4}\b", 'all': False,
         'sites': ["biology.stackexchange.com", "bitcoin.stackexchange.com", "ell.stackexchange.com",
                   "english.stackexchange.com", "expatriates.stackexchange.com", "gaming.stackexchange.com",
                   "health.stackexchange.com", "money.stackexchange.com", "parenting.stackexchange.com",
                   "rpg.stackexchange.com", "scifi.stackexchange.com", "travel.stackexchange.com",
                   "worldbuilding.stackexchange.com"], 'reason': "email in {}", 'title': True, 'body': True,
         'username': False, 'stripcodeblocks': True, 'body_summary': False, 'questions': False, 'max_rep': 1,
         'max_score': 0},
        # Email check for questions: check only at the end, and on selected sites
        {'regex': ur"(?i)(?<![=#/])\b[A-z0-9_.%+-]+@(?!(example|domain|site|foo|\dx)\.[A-z]{2,4})"
                  ur"[A-z0-9_.%+-]+\.[A-z]{2,4}\b(?s).{0,100}$", 'all': False,
         'sites': ["money.stackexchange.com", "travel.stackexchange.com", "gamedev.stackexchange.com",
                   "gaming.stackexchange.com"], 'reason': "email in {}", 'title': True, 'body': True,
         'username': False, 'stripcodeblocks': True, 'body_summary': False, 'answers': False, 'max_rep': 1,
         'max_score': 0},
        # Combination of keyword and email in questions and answers, for all sites
        {'method': keyword_email, 'all': True, 'sites': [], 'reason': "bad keyword with email in {}", 'title': True,
         'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # QQ/ICQ/Whatsapp... numbers, for all sites
        {'regex': ur'(?i)(?<![a-z0-9])Q{1,2}(?:(?:[vw]|[^a-z0-9])\D{0,8})?\d{5}[.-]?\d{4,5}(?!["\d])|'
                  ur'\bICQ[ :]{0,5}\d{9}\b|\bwh?atsapp?[ :]{0,5}\d{10}', 'all': True, 'sites': [],
         'reason': "messaging number in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': True,
         'body_summary': False, 'max_rep': 1, 'max_score': 0},
        #
        # Category: Trolling
        # Offensive content in titles and posts
        {'method': is_offensive_post, 'all': True, 'sites': [], 'reason': "offensive {} detected", 'title': True,
         'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': True,
         'max_rep': 101, 'max_score': 2},
        # Offensive title: titles are more sensitive
        {'regex': ur"(?i)\bfuck|(?<!brain)fuck(ers?|ing)?\b", 'all': True, 'sites': [],
         'reason': "offensive {} detected", 'title': True, 'body': False, 'username': False,
         'stripcodeblocks': True, 'body_summary': False,
         'max_rep': 101, 'max_score': 5},
        # No whitespace, punctuation, or formatting in a post
        {'regex': ur"(?i)^<p>[a-z]+</p>\s*$", 'all': True, 'sites': ["codegolf.stackexchange.com",
                                                                     "puzzling.stackexchange.com"],
         'reason': "no whitespace in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False,
         'body_summary': False, 'max_rep': 1, 'max_score': 0},
        # Numbers-only title
        {'regex': ur"^(?=.*[0-9])[^\pL]*$", 'all': True, 'sites': ["math.stackexchange.com"],
         'reason': "numbers-only title", 'title': True, 'body': False, 'username': False, 'stripcodeblocks': False,
         'body_summary': False, 'max_rep': 50, 'max_score': 0},
        # Few unique characters
        {'method': has_few_characters, 'all': True, 'sites': ["pt.stackoverflow.com", "ru.stackoverflow.com",
                                                              "es.stackoverflow.com", "rus.stackexchange.com"],
         'reason': "few unique characters in {}", 'title': False, 'body': True, 'username': False,
         'stripcodeblocks': False, 'body_summary': False, 'max_rep': 10000, 'max_score': 1000000},
        # Repeating characters
        {'method': has_repeating_characters, 'all': True, 'sites': ["pt.stackoverflow.com", "ru.stackoverflow.com",
                                                                    "es.stackoverflow.com", "rus.stackexchange.com",
                                                                    "chinese.stackexchange.com"],
         'reason': "repeating characters in {}", 'title': True, 'body': True, 'username': False,
         'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1000000, 'max_score': 1000000},
        # Repeating words
        {'method': has_repeated_words, 'all': True, 'sites': [], 'reason': "repeating words in {}", 'title': True,
         'body': True, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 11,
         'max_score': 0},
        # One unique character in title
        {'regex': ur"^(.)\1+$", 'all': True, 'sites': [], 'reason': "{} has only one unique char", 'title': True,
         'body': False, 'username': False, 'stripcodeblocks': True, 'body_summary': False, 'max_rep': 1000000,
         'max_score': 1000000},
        # Parenting troll
        {'regex': ur"(?i)\b(erica|jeff|er1ca|spam|moderator)\b", 'all': False, 'sites': ["parenting.stackexchange.com"],
         'reason': "bad keyword in {}", 'title': False, 'body': True, 'username': False, 'stripcodeblocks': False,
         'body_summary': True, 'max_rep': 50, 'max_score': 0},
        # Academia kangaroos
        {'regex': ur"(?i)kangaroos", 'all': False, 'sites': ["academia.stackexchange.com"],
         'reason': "bad keyword in {}", 'title': True, 'body': True, 'username': False, 'stripcodeblocks': False,
         'body_summary': False, 'max_rep': 1, 'max_score': 0},
        {'regex': ur"(?i)\b\<a href=\".{0,25}\.xyz\"( rel=\"nofollow( noreferrer)?\")?\>.{0,15}google.{0,15}\<\/a\>\b",
         'all': True, 'sites': [], 'reason': 'non-Google "google search" link in {}', 'title': False, 'body': True,
         'username': False, 'body_summary': False, 'stripcodeblocks': True, 'max_rep': 1, 'max_score': 0},
        # Academia image by low-rep user
        {'regex': ur'\<img src="[^"]+"(?: alt="[^"]+")?>', 'all': False, 'sites': ['academia.stackexchange.com'],
         'reason': 'image by low-rep user', 'title': False, 'body': True, 'username': False, 'body_summary': False,
         'stripcodeblocks': True, 'max_rep': 1, 'max_score': 0},
        # Link inside nested blockquotes
        {'regex': ur'(?:<blockquote>\s*){6}<p><a href="([^<>]+)"[^<>]*>\1</a>\s*</p>\s*</blockquote>', 'all': True,
         'sites': [], 'reason': 'link inside deeply nested blockquotes', 'title': False, 'body': True,
         'username': False, 'body_summary': False, 'stripcodeblocks': True, 'max_rep': 1, 'max_score': 0},

        #
        # Category: other
        # Blacklisted usernames
        {'regex': ur"(?i)({})".format("|".join(blacklisted_usernames)), 'all': True, 'sites': [],
         'reason': "blacklisted username", 'title': False, 'body': False, 'username': True, 'stripcodeblocks': False,
         'body_summary': False, 'max_rep': 1, 'max_score': 0},
        {'regex': u"(?i)^jeff$", 'all': False, 'sites': ["parenting.stackexchange.com"],
         'reason': "blacklisted username", 'title': False, 'body': False, 'username': True,
         'stripcodeblocks': False, 'body_summary': False, 'max_rep': 1, 'max_score': 0}
    ]