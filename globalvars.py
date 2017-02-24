# -*- coding: utf-8 -*-

import os
from datetime import datetime
from chatexchange_extension import Client
import HTMLParser
from hashlib import md5
import ConfigParser
from helpers import environ_or_none
import threading


# noinspection PyClassHasNoInit,PyDeprecation
class GlobalVars:
    false_positives = []
    whitelisted_users = []
    blacklisted_users = []
    ignored_posts = []
    auto_ignored_posts = []
    startup_utc = datetime.utcnow().strftime("%H:%M:%S")
    latest_questions = []
    api_backoff_time = 0
    charcoal_room_id = "11540"
    meta_tavern_room_id = "89"
    socvr_room_id = "41570"
    blockedTime = {"all": 0, charcoal_room_id: 0, meta_tavern_room_id: 0, socvr_room_id: 0}
    metasmoke_last_ping_time = datetime.now()

    experimental_reasons = []  # Don't widely report these
    non_socvr_reasons = []    # Don't report to SOCVR
    non_tavern_reasons = [    # Don't report in the Tavern
        "all-caps body",
        "all-caps answer",
        "repeating characters in body",
        "repeating characters in title",
        "repeating characters in answer",
        "few unique characters in body",
        "few unique characters in answer",
        "title has only one unique char",
        "phone number detected in title",
        "offensive body detected",
        "no whitespace in body",
        "no whitespace in answer",
    ]
    non_tavern_sites = ["stackoverflow.com"]

    parser = HTMLParser.HTMLParser()
    wrap = Client("stackexchange.com")
    wrapm = Client("meta.stackexchange.com")
    wrapso = Client("stackoverflow.com")
    privileged_users = {
        charcoal_room_id: [
            "117490",   # Normal Human
            "66258",    # Andy
            "31768",    # ManishEarth
            "103081",   # hichris123
            "73046",    # Undo
            "88521",    # ProgramFOX
            "59776",    # Doorknob
            "31465",    # Seth
            "88577",    # Santa Claus
            "34124",    # Andrew Leach
            "54229",    # apnorton
            "20459",    # S.L. Barth
            "32436",    # tchrist
            "30477",    # Brock Adams
            "58529",    # ferrybig
            "145208",   # Robert Longson
            "178825",   # Ms Yvette
            "171800",   # JAL
            "64978",    # PeterJ
            "125141",   # Jeffrey Bosboom
            "54902",    # bummi
            "135450",   # M.A.R.
            "145604",   # Quill
            "60548",    # rene
            "121401",   # michaelpri
            "116218",   # JamesENL
            "82927",    # Braiam
            "11606",    # bwDraco
            "19761",    # Ilmari Karonen
            "108271",   # Andrew T.
            "171054",   # Magisch
            "190011",   # Petter Friberg
            "165661",   # Tunaki
            "145086",   # Wai Ha Lee
            "137665",   # ByteCommander
            "147884",   # wythagoras
            "186395",   # Åna
            "181293",   # Ashish Ahuja
            "163686",   # Gothdo
            "145827",   # angussidney
            "244748",   # Supreme Leader SnokeDetector (angussidney's sock)
            "121520",   # ArtOfCode
            "244382",   # Lt. A. Code (ArtOfCode's sock to test things with)
            "137388",   # QPaysTaxes
            "212311",   # Ryan Bemrose
            "172397",   # Kyll
            "224538",   # FrankerZ
            "61202",    # OldSkool
            "56166",    # Jan Dvorak
            "133966",   # DavidPostill
            "22839",    # djsmiley2k
            "97389",    # Kaz Wolfe
            "144962",   # DJMcMayhem
            "139423",   # NobodyNada
            "62118",    # tripleee
            "130558",   # Registered User
            "128113",   # arda
            "164318",   # Glorfindel
            "175347",   # Floern
            "180274",   # Alexander O'Mara
            "158742",   # Rob
            "207356",   # 4castle
            "133031",   # Mithrandir
            "169713",   # Mego
            "126657",   # Cerbrus
            "10145",    # Thomas Ward
            "161943",   # J F
            "195967",   # CaffeineAddiction
            "5363"      # Stijn
        ],
        meta_tavern_room_id: [
            "315433",   # Normal Human
            "244519",   # CRABOLO
            "244382",   # TGMCians
            "194047",   # Jan Dvorak
            "158100",   # rene
            "178438",   # Manishearth
            "237685",   # hichris123
            "215468",   # Undo
            "229438",   # ProgramFOX
            "180276",   # Doorknob
            "161974",   # Lynn Crumbling
            "186281",   # Andy
            "266094",   # Unihedro
            "245167",   # Infinite Recursion
            "230261",   # Jason C
            "213575",   # Braiam
            "241919",   # Andrew T.
            "203389",   # backwards-Seth
            "202832",   # Mooseman
            "160017",   # bwDraco
            "201151",   # bummi
            "188558",   # Frank
            "229166",   # Santa Claus
            "159034",   # Kevin Brown
            "203972",   # PeterJ
            "188673",   # Alexis King
            "258672",   # AstroCB
            "227577",   # Sam
            "255735",   # cybermonkey
            "279182",   # Ixrec
            "271104",   # James
            "220428",   # Qantas 94 Heavy
            "153355",   # tchrist
            "238426",   # Ed Cottrell
            "166899",   # Second Rikudo
            "287999",   # ASCIIThenANSI
            "208518",   # JNat
            "284141",   # michaelpri
            "260312",   # vaultah
            "244062",   # SouravGhosh
            "152859",   # Shadow Wizard
            "201314",   # apnorton
            "280934",   # M.A.Ramezani
            "200235",   # durron597
            "148310",   # Awesome Poodles / Brock Adams
            "168333",   # S.L. Barth
            "257207",   # Unikitty
            "244282",   # DroidDev
            "163250",   # Cupcake
            "298265",   # BoomsPlus
            "253560",   # josilber
            "244254",   # misterManSam
            "188189",   # Robert Longson
            "174699",   # Ilmari Karonen
            "202362",   # chmod 666 telkitty
            "289717",   # Quill
            "237813",   # bjb568
            "311345",   # Simon Klaver
            "171881",   # rekire
            "260388",   # Pandya
            "310756",   # Ms Yvette
            "262399",   # Jeffrey Bosboom
            "242209",   # JAL
            "280883",   # ByteCommander
            "302251",   # kos
            "262823",   # ArtOfCode
            "215067",   # Ferrybig
            "308386",   # Magisch
            "285368",   # angussidney
            "158829"    # Thomas Ward
        ],
        socvr_room_id: [
            "1849664",  # Undo
            "2581872",  # hichris123
            "1198729",  # Manishearth
            "3717023",  # Normal Human aka 1999
            "2619912",  # ProgramFOX
            "578411",   # rene
            "1043380",  # gunr2171
            "2246344",  # Sam
            "2756409",  # TylerH
            "1768232",  # durron597
            "359284",   # Kevin Brown
            "258400",   # easwee
            "3622940",  # Unihedron
            "3204551",  # Deduplicator
            "4342498",  # NathanOliver
            "4639281",  # Tiny Giant
            "3093387",  # josilber
            "1652962",  # cimmanon
            "1677912",  # Mogsdad
            "656243",   # Lynn Crumbling
            "3933332",  # Rizier123
            "2422013",  # cybermonkey
            "3478852",  # Nisse Engström
            "2302862",  # Siguza
            "1324",     # Paul Roub
            "1743880",  # Tunaki
            "1663001",  # DavidG
            "2415822",  # JAL
            "4174897",  # Kyll
            "5299236",  # Kevin Guan
            "4050842",  # Thaillie
            "1816093",  # Drew
            "874188",   # Triplee
            "880772",   # approxiblue
            "1835379",  # Cerbrus
            "3956566",  # JamesENL
            "2357233",  # Ms Yvette
            "3155639",  # AlexanderOMara
            "462627",   # Praveen Kumar
            "4490559",  # intboolstring
            "1364007",  # Wai Ha Lee
            "1699210",  # bummi
            "563532",   # Rob
            "5389107",  # Magisch
            "4099593",  # bhargav-rao
            "1542723",  # Ferrybig
            "2025923",  # Tushar
            "5292302",  # Petter Friberg
            "792066",   # Braiam
            "5666987",  # Ian
            "3160466",  # ArtOfCode
            "4688119",  # Ashish Ahuja
            "3476191",  # Nobody Nada
            "2227743",  # Eric D
            "821878",   # Ryan Bemrose
            "1413395",  # Panta Rei
            "4875631",  # FrankerZ
            "2958086",  # Compass
            "499214",   # JanDvorak
            "5647260",  # Andrew L.
            "559745",   # Floern
            "5743988",  # 4castle
            "4622463",  # angussidney
            "603346",   # Thomas Ward
            "3002139",  # Baum mit Augen
            "1863564"   # QPaysTaxes
        ]
    }

    code_privileged_users = None

    smokeDetector_user_id = {charcoal_room_id: "120914", meta_tavern_room_id: "266345",
                             socvr_room_id: "3735529"}

    censored_committer_names = {"3f4ed0f38df010ce300dba362fa63a62": "Undo1"}

    commit = os.popen('git log --pretty=format:"%h" -n 1').read()
    commit_author = os.popen('git log --pretty=format:"%an" -n 1').read()

    if md5(commit_author).hexdigest() in censored_committer_names:
        commit_author = censored_committer_names[md5(commit_author).hexdigest()]

    commit_with_author = os.popen('git log --pretty=format:"%h (' + commit_author + ': *%s*)" -n 1').read()
    on_master = "HEAD detached" not in os.popen("git status").read()
    charcoal_hq = None
    tavern_on_the_meta = None
    socvr = None
    s = ""
    s_reverted = ""
    specialrooms = []
    apiquota = -1
    bodyfetcher = None
    se_sites = []
    users_chatting = {meta_tavern_room_id: [], charcoal_room_id: [], socvr_room_id: []}
    why_data = []
    why_data_allspam = []
    notifications = []
    listen_to_these_if_edited = []
    multiple_reporters = []
    api_calls_per_site = {}

    standby_message = ""
    standby_mode = False

    api_request_lock = threading.Lock()

    num_posts_scanned = 0
    post_scan_time = 0
    posts_scan_stats_lock = threading.Lock()

    config = ConfigParser.RawConfigParser()

    if os.path.isfile('config'):
        config.read('config')
    else:
        config.read('config.ci')

    latest_smokedetector_messages = {meta_tavern_room_id: [], charcoal_room_id: [], socvr_room_id: []}

    # environ_or_none defined in helpers.py
    bot_name = environ_or_none("SMOKEDETECTOR_NAME") or "SmokeDetector"
    bot_repository = environ_or_none("SMOKEDETECTOR_REPO") or "//github.com/Charcoal-SE/SmokeDetector"
    chatmessage_prefix = "[{}]({})".format(bot_name, bot_repository)

    site_id_dict = {}
    post_site_id_to_question = {}

    location = config.get("Config", "location")
    print location

    metasmoke_ws = None

    try:
        metasmoke_host = config.get("Config", "metasmoke_host")
        print metasmoke_host
    except ConfigParser.NoOptionError:
        metasmoke_host = None
        print "metasmoke host not found. Set it as metasmoke_host in the config file." \
              "See https://github.com/Charcoal-SE/metasmoke."

    try:
        metasmoke_key = config.get("Config", "metasmoke_key")
    except ConfigParser.NoOptionError:
        metasmoke_key = ""
        print "No metasmoke key found, which is okay if both are running on the same host"

    try:
        metasmoke_ws_host = config.get("Config", "metasmoke_ws_host")
    except ConfigParser.NoOptionError:
        metasmoke_ws_host = ""
        print "No metasmoke websocket host found, which is okay if you're anti-websocket"

    try:
        github_username = config.get("Config", "github_username")
        github_password = config.get("Config", "github_password")
    except ConfigParser.NoOptionError:
        github_username = None
        github_password = None
