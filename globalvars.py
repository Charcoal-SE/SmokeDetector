# -*- coding: utf-8 -*-

import os
from datetime import datetime
from ChatExchange.chatexchange.client import Client
import HTMLParser
import md5
import ConfigParser


class GlobalVars:
    false_positives = []
    whitelisted_users = []
    blacklisted_users = []
    ignored_posts = []
    auto_ignored_posts = []
    startup_utc = datetime.utcnow().strftime("%H:%M:%S")
    latest_questions = []
    blockedTime = 0
    api_backoff_time = 0
    charcoal_room_id = "11540"
    meta_tavern_room_id = "89"
    socvr_room_id = "41570"
    site_filename = {"electronics.stackexchange.com": "ElectronicsGood.txt",
                     "gaming.stackexchange.com": "GamingGood.txt", "german.stackexchange.com": "GermanGood.txt",
                     "italian.stackexchange.com": "ItalianGood.txt", "math.stackexchange.com": "MathematicsGood.txt",
                     "spanish.stackexchange.com": "SpanishGood.txt", "stats.stackexchange.com": "StatsGood.txt"}

    experimental_reasons = []  # Don't widely report these
    non_tavern_reasons = ["All-caps title",   # Don't report in the Tavern
                          "All-caps body",
                          "All-caps answer",
                          "All-caps body, all-caps title",
                          "Repeating characters in body",
                          "Repeating characters in title",
                          "Repeating characters in answer",
                          "Phone number detected in title",
                          "Offensive body detected",
                          "Email in answer",
                          "Email in title",
                          "Link at end of answer"]
    non_tavern_sites = ["stackoverflow.com"]

    parser = HTMLParser.HTMLParser()
    wrap = Client("stackexchange.com")
    wrapm = Client("meta.stackexchange.com")
    wrapso = Client("stackoverflow.com")
    privileged_users = {charcoal_room_id: ["117490",  # Normal Human
                                           "66258",  # Andy
                                           "31768",  # ManishEarth
                                           "103081",  # hichris123
                                           "73046",  # Undo
                                           "88521",  # ProgramFOX
                                           "59776",  # Doorknob
                                           "31465",  # Seth
                                           "88577",  # Santa Claus
                                           "34124",  # Andrew Leach
                                           "54229",  # apnorton
                                           "20459",  # S.L. Barth
                                           "32436",  # tchrist
                                           "30477",  # Brock Adams
                                           "145208"],  # Robert Longson
                        meta_tavern_room_id: ["259867",  # Normal Human
                                              "244519",  # CRABOLO
                                              "244382",  # TGMCians
                                              "194047",  # Jan Dvorak
                                              "158100",  # rene
                                              "178438",  # Manishearth
                                              "237685",  # hichris123
                                              "215468",  # Undo
                                              "229438",  # ProgramFOX
                                              "180276",  # Doorknob
                                              "161974",  # Lynn Crumbling
                                              "186281",  # Andy
                                              "266094",  # Unihedro
                                              "245167",  # Infinite Recursion
                                              "230261",  # Jason C
                                              "213575",  # Braiam
                                              "241919",  # Andrew T.
                                              "203389",  # backwards-Seth
                                              "202832",  # Mooseman
                                              "160017",  # bwDraco
                                              "201151",  # bummi
                                              "188558",  # Frank
                                              "229166",  # Santa Claus
                                              "159034",  # Kevin Brown
                                              "203972",  # PeterJ
                                              "188673",  # Alexis King
                                              "258672",  # AstroCB
                                              "227577",  # Sam
                                              "255735",  # cybermonkey
                                              "279182",  # Ixrec
                                              "271104",  # James
                                              "220428",  # Qantas 94 Heavy
                                              "153355",  # tchrist
                                              "238426",  # Ed Cottrell
                                              "166899",  # Second Rikudo
                                              "287999",  # ASCIIThenANSI
                                              "208518",  # JNat
                                              "284141",  # michaelpri
                                              "260312",  # vaultah
                                              "244062",  # SouravGhosh
                                              "152859",  # Shadow Wizard
                                              "201314",  # apnorton
                                              "280934",  # M.A.Ramezani
                                              "200235",  # durron597
                                              "148310",  # Awesome Poodles / Brock Adams
                                              "168333",  # S.L. Barth
                                              "257207",  # Unikitty
                                              "244282",  # DroidDev
                                              "163250",  # Cupcake
                                              "298265",  # BoomsPlus
                                              "253560",  # josilber
                                              "244254",  # misterManSam
                                              "188189",  # Robert Longson
                                              "174699",  # Ilmari Karonen
                                              "202362",  # chmod 666 telkitty
                                              "289717",  # Quill
                                              "237813",  # bjb568
                                              "311345",  # Simon Klaver
                                              "171881",  # rekire
                                              "260388"],  # Pandya
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
                            "874188",  # Triplee
                            "880772",  # approxiblue
                            "1835379",  # Cerbrus
                            "1843331",  # Tim Castelijns
                            "3956566",  # JamesENL
                            "2357233",  # Ms Yvette
                            "3155639",  # AlexanderOMara
                            "462627",  # Praveen Kumar
                            "4490559",  # intboolstring
                            "1364007",  # Wai Ha Lee
                            "1699210",  # bummi
                            "563532" ] #Rob
                        }
    smokeDetector_user_id = {charcoal_room_id: "120914", meta_tavern_room_id: "266345",
                             socvr_room_id: "3735529"}

    censored_committer_names = {"3f4ed0f38df010ce300dba362fa63a62": "Undo1"}

    commit = os.popen('git log --pretty=format:"%h" -n 1').read()
    commit_author = os.popen('git log --pretty=format:"%cn" -n 1').read()

    if md5.new(commit_author).hexdigest() in censored_committer_names:
        commit_author = censored_committer_names[md5.new(commit_author).hexdigest()]

    commit_with_author = os.popen('git log --pretty=format:"%h (' + commit_author + ': *%s*)" -n 1').read()
    on_master = os.popen("git rev-parse --abbrev-ref HEAD").read().strip() == "master"
    charcoal_hq = None
    tavern_on_the_meta = None
    socvr = None
    s = ""
    s_reverted = ""
    specialrooms = []
    bayesian_testroom = None
    apiquota = -1
    bodyfetcher = None
    se_sites = []
    users_chatting = {meta_tavern_room_id: [], socvr_room_id: [], charcoal_room_id: []}
    why_data = []
    why_data_allspam = []
    notifications = []
    listen_to_these_if_edited = []
    multiple_reporters = []
    api_calls_per_site = {}

    config = ConfigParser.RawConfigParser()
    config.read('config')

    latest_smokedetector_messages = {meta_tavern_room_id: [], charcoal_room_id: [],
                                     socvr_room_id: []}

    location = config.get("Config", "location")
    print location

    try:
        metasmoke_host = config.get("Config", "metasmoke_host")
        print metasmoke_host
    except ConfigParser.NoOptionError:
        metasmoke_host = None
        print "metasmoke host not found. Set it as metasmoke_host in the config file. See https://github.com/Charcoal-SE/metasmoke."

    try:
        metasmoke_key = config.get("Config", "metasmoke_key")
    except ConfigParser.NoOptionError:
        metasmoke_key = ""
        print "No metasmoke key found, which is okay if both are running on the same host"
