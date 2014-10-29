#requires https://pypi.python.org/pypi/websocket-client/
import websocket
import sys
import threading
import json,os,getpass,time
from findspam import FindSpam
from ChatExchange.chatexchange.client import *
import HTMLParser
import random
from bayesian.classify import Classify
from bayesian.learn import Learn
import re
import pickle
import os.path
from datetime import datetime

false_positives = []
whitelisted_users = []
blacklisted_users = []
startup_utc = datetime.utcnow().strftime("%H:%M:%S")

def load_false_positives():
    if(os.path.isfile("falsePositives.txt")):
        with open("falsePositives.txt", "r") as f:
            false_positives = pickle.load(f)

def load_whitelisted_users():
    if(os.path.isfile("whitelistedUsers.txt")):
        with open("whitelistedUsers.txt", "r") as f:
            whitelisted_users = pickle.load(f)

def load_blacklisted_users():
    if(os.path.isfile("blacklistedUsers.txt")):
        with open("blacklistedUsers.txt", "r") as f:
            blacklisted_users = pickle.load(f)

parser=HTMLParser.HTMLParser()

if("ChatExchangeU" in os.environ):
    username=os.environ["ChatExchangeU"]
else:
    print "Username: "
    username=raw_input()
if("ChatExchangeP" in os.environ):
    password=os.environ["ChatExchangeP"]
else:
    password=getpass.getpass("Password: ")

load_false_positives()
load_whitelisted_users()
load_blacklisted_users()

latest_questions = []
blockedTime = 0
charcoal_room_id = "11540"
meta_tavern_room_id = "89"
privileged_users = { charcoal_room_id: ["66258", "31768","103081","73046","88521","59776"], meta_tavern_room_id: ["244519","244382","194047","158100","178438","237685","215468","229438","180276", "161974", "244382", "186281", "266094", "245167"] }
smokeDetector_user_id = { charcoal_room_id: "120914", meta_tavern_room_id: "266345" }
site_filename = { "electronics.stackexchange.com" : "ElectronicsGood.txt", "gaming.stackexchange.com" : "GamingGood.txt", "german.stackexchange.com" : "GermanGood.txt",
                                    "italian.stackexchange.com" : "ItalianGood.txt", "math.stackexchange.com" : "MathematicsGood.txt", "spanish.stackexchange.com" : "SpanishGood.txt",
                                    "stats.stackexchange.com" : "StatsGood.txt" }

wrap=Client("stackexchange.com")
wrap.login(username,password)
wrapm=Client("meta.stackexchange.com")
wrapm.login(username,password)
commit = os.popen("git log --pretty=format:'%h' -n 1").read()
commit_with_author = os.popen("git log --pretty=format:'%h (%cn: *%s*)' -n 1").read()
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector started at [rev " + commit_with_author + "](https://github.com/Charcoal-SE/SmokeDetector/commit/"+ commit +") (owned by Undo)"
room = wrap.get_room(charcoal_room_id)
roomm = wrapm.get_room(meta_tavern_room_id)

specialrooms = [{ "sites": ["english.stackexchange.com"], "room": wrap.get_room("95"), "unwantedReasons": [] }, { "sites": ["askubuntu.com"], "room": wrap.get_room("201"), "unwantedReasons": ["All-caps title"] }]

bayesian_testroom = wrap.get_room("17251")
if "first_start" in sys.argv:
        bayesian_testroom.send_message(s)
        room.send_message(s)
#roomm.send_message(s)
#Commented out because the Tavern folk don't really need to see when it starts

def restart_automatically(time_in_seconds):
    time.sleep(time_in_seconds)
    os._exit(1)

threading.Thread(target=restart_automatically,args=(3600,)).start()

def get_user_from_url(url):
    m = re.compile(r"https?://([\w.]+)/users/(\d+)/[\w-]/?").search(url)
    site = m.group(1)
    user_id = m.group(2)
    return (user_id, site)

def is_whitelisted_user(user):
    return user in whitelisted_users

def is_blacklisted_user(user):
    return user in blacklisted_users

def add_whitelisted_user(user):
    if user in whitelisted_users or user is None:
        return
    whitelisted_users.append(user)
    with open("whitelistedUsers.txt", "w") as f:
        pickle.dump(whitelisted_users, f)

def add_blacklisted_user(user):
    if user in blacklisted_users or user is None:
        return
    blacklisted_users.append(user)
    with open("blacklistedUsers.txt", "w") as f:
        pickle.dump(blacklisted_users, f)

def append_to_latest_questions(host, post_id, title):
    latest_questions.insert(0, (host, post_id, title))
    if len(latest_questions) > 15:
        latest_questions.pop()

def has_already_been_posted(host, post_id, title):
    for post in latest_questions:
        if post[0] == host and post[1] == post_id and post[2] == title:
            return True
    return False

def bayesian_score(title):
    try:
        c=Classify()
        c.validate(["","",title,"good","bad"])
        output = c.execute()
        return output
    except:
        return 0.1

def is_false_positive(post_id, site_name):
    if((str(post_id), site_name) in false_positives):
        return True
    else:
        return False

def checkifspam(data):
    d=json.loads(json.loads(data)["data"])
    try:
        _ = d["ownerUrl"]
    except:
        return False # owner's account doesn't exist anymore, no need to post it in chat: http://chat.stackexchange.com/transcript/message/18380776#18380776
    s= d["titleEncodedFancy"]
    poster = d["ownerDisplayName"]
    print time.strftime("%Y-%m-%d %H:%M:%S"),parser.unescape(s).encode("ascii",errors="replace")
    quality_score = bayesian_score(s)
    print quality_score
    if(quality_score < 0.3 and d["siteBaseHostAddress"] == "stackoverflow.com"):
        print bayesian_testroom.send_message("[ SmokeDetector | BayesianBeta ] Quality score " + str(quality_score*100) + ": [" + s + "](" + d["url"] + ")")
    site = d["siteBaseHostAddress"]
    site=site.encode("ascii",errors="replace")
    sys.stdout.flush()
    test=FindSpam.testpost(s,poster,site)
    if(is_blacklisted_user(get_user_from_url(d["ownerUrl"]))):
        if(len(test) == 0):
            test = "Blacklisted user"
        else:
            test += ", Blacklisted user"
    if (0<len(test)):
        post_id = d["id"]
        if(has_already_been_posted(site, post_id, s) or is_false_positive(post_id, site) or is_whitelisted_user(get_user_from_url(d["ownerUrl"]))):
            return False # Don't repost. Reddit will hate you.
        append_to_latest_questions(site, post_id, s)
        try:
            owner = d["ownerUrl"]
            users_file = open("users.txt", "a")
            users_file.write(site + " " + owner + " " + d["titleEncodedFancy"] + " " + d["url"] + "\n")
            users_file.close()
        except Exception as e:
            print e
        return True
    return False

def fetch_post_id_and_site_from_msg_content(content):
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w ]+: \[.+]\(http:\/\/[\w.]+\/questions\/(\d+)\/.+\) by \[.+\]\((?:.+)\) on `([\w.]+)`$"
    m = re.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        post_id = m.group(1)
        site_name = m.group(2)
        return (post_id, site_name)
    except:
        return None # message is not a report

def fetch_owner_url_from_msg_content(content):
    search_regex = "^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w ]+: \[.+]\(http:\/\/[\w.]+\/questions\/\d+\/.+\) by \[.+\]\((.+)\) on `[\w.]+`$"
    m = re.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        owner_url = m.group(1)
        return owner_url
    except:
        return None

def store_site_and_post_id(site_post_id_tuple):
    if(site_post_id_tuple is None or site_post_id_tuple in false_positives):
        return
    false_positives.append(site_post_id_tuple)
    with open("falsePositives.txt", "w") as f:
        pickle.dump(false_positives, f)

def fetch_title_from_msg_content(content):
    return re.compile(r": \[(.+)\]").findall(content)[0]

def bayesian_learn_title(message_content, doctype):
    try:
        bayesian_learn = Learn()
        bayesian_learn.file_contents = fetch_title_from_msg_content(message_content)
        bayesian_learn.count = 1
        bayesian_learn.doc_type = doctype
        bayesian_learn.execute()
        return True
    except:
        return False

def handlespam(data):
    try:
        d=json.loads(json.loads(data)["data"])
        title = d["titleEncodedFancy"]
        poster = d["ownerDisplayName"]
        reason=", ".join(FindSpam.testpost(title,poster,d["siteBaseHostAddress"]))
        titleToPost = parser.unescape(re.sub(r"([_*\\`\[\]])", r"\\\1", title)).strip()
        s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) by [%s](%s) on `%s`" % (reason,titleToPost,d["url"],poster,d["ownerUrl"],d["siteBaseHostAddress"])
        print parser.unescape(s).encode('ascii',errors='replace')
        if time.time() >= blockedTime:
            room.send_message(s)
            roomm.send_message(s)
            for specialroom in specialrooms:
                sites = specialroom["sites"]
                if d["siteBaseHostAddress"] in sites and reason not in specialroom["unwantedReasons"]:
                    specialroom["room"].send_message(s)
    except:
        print "NOP"
ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
ws.send("155-questions-active")
room.join()
roomm.join()
def watcher(ev,wrap2):
    global blockedTime
    if ev.type_id != 1:
        return;
    print(ev)
    ev_room = str(ev.data["room_id"])
    ev_user_id = str(ev.data["user_id"])
    message_parts = ev.message.content_source.split(" ")
    if(re.compile(":[0-9]+").search(message_parts[0])):
        if((message_parts[1].lower().startswith("false") or message_parts[1].lower().startswith("fp")) and isPrivileged(ev_room, ev_user_id)):
            try:
                msg_id = int(message_parts[0][1:])
                if(ev_room == charcoal_room_id):
                    msg_to_delete = wrap.get_message(msg_id)
                    if(str(msg_to_delete.owner.id) == smokeDetector_user_id[charcoal_room_id]):
                        msg_content = msg_to_delete.content_source
                        site_post_id = fetch_post_id_and_site_from_msg_content(msg_content)
                        store_site_and_post_id(site_post_id)
                        user_added = False
                        if(message_parts[1].lower().startswith("falseu") or message_parts[1].lower().startswith("fpu")):
                            url_from_msg = fetch_owner_url_from_msg_content(msg_content)
                            user = get_user_from_url(url_from_msg)
                            add_whitelisted_user(user)
                            user_added = True
                        learned = bayesian_learn_title(msg_content, "good")
                        if learned:
                            if user_added:
                                ev.message.reply("Registered as false positive, added title to Bayesian doctype 'good', whitelisted user.")
                            else:
                                ev.message.reply("Registered as false positive and added title to Bayesian doctype 'good'.")
                        else:
                            if user_added:
                                ev.message.reply("Registered as false positive and whitelisted user, but could not add the title to the Bayesian doctype 'good'.")
                            else:
                                ev.message.reply("Registered as false positive, but could not add the title to the Bayesian doctype 'good'.")
                        msg_to_delete.delete()
                elif(ev_room == meta_tavern_room_id):
                    msg_to_delete = wrapm.get_message(msg_id)
                    if(str(msg_to_delete.owner.id) == smokeDetector_user_id[meta_tavern_room_id]):
                        msg_content = msg_to_delete.content_source
                        site_post_id = fetch_post_id_and_site_from_msg_content(msg_content)
                        store_site_and_post_id(site_post_id)
                        user_added = False
                        if(message_parts[1].lower().startswith("falseu") or message_parts[1].lower().startswith("fpu")):
                            url_from_msg = fetch_owner_url_from_msg_content(msg_content)
                            user = get_user_from_url(url_from_msg)
                            add_whitelisted_user(user)
                            user_added = True
                        learned = bayesian_learn_title(msg_content, "good")
                        if learned:
                            if user_added:
                                ev.message.reply("Registered as false positive, added title to Bayesian doctype 'good', whitelisted user.")
                            else:
                                ev.message.reply("Registered as false positive and added title to Bayesian doctype 'good'.")
                        else:
                            if user_added:
                                ev.message.reply("Registered as false positive and whitelisted user, but could not add the title to the Bayesian doctype 'good'.")
                            else:
                                ev.message.reply("Registered as false positive, but could not add the title to the Bayesian doctype 'good'.")
                        msg_to_delete.delete()
            except:
                pass # couldn't delete message
        if((message_parts[1].lower().startswith("true") or message_parts[1].lower().startswith("tp")) and isPrivileged(ev_room, ev_user_id)):
            try:
                msg_id = int(message_parts[0][1:])
                msg_content = None
                if(ev_room == charcoal_room_id):
                    msg_true_positive = wrap.get_message(msg_id)
                    if(str(msg_true_positive.owner.id) == smokeDetector_user_id[charcoal_room_id]):
                        msg_content = msg_true_positive.content_source
                elif(ev_room == meta_tavern_room_id):
                    msg_true_positive = wrapm.get_message(msg_id)
                    if(str(msg_true_positive.owner.id) == smokeDetector_user_id[meta_tavern_room_id]):
                        msg_content = msg_true_positive.content_source
                if(msg_content is not None):
                    learned = bayesian_learn_title(msg_content, "bad")
                    user_added = False
                    if(message_parts[1].lower().startswith("trueu") or message_parts[1].lower().startswith("tpu")):
                        url_from_msg = fetch_owner_url_from_msg_content(msg_content)
                        user = get_user_from_url(url_from_msg)
                        add_blacklisted_user(user)
                        user_added = True
                    if(learned):
                        if user_added:
                            ev.message.reply("Registered as true positive: added title to Bayesian doctype 'bad' and blacklisted user.")
                        else:
                            ev.message.reply("Registered as true positive: added title to Bayesian doctype 'bad'.")   
                    else:
                        if user_added:
                            ev.message.reply("User blacklisted, but something went wrong when registering title as true positive.")
                        else:
                            ev.message.reply("Something went wrong when registering title as true positive.")
            except:
                pass
        if(message_parts[1] == "delete" and isPrivileged(ev_room, ev_user_id)):
            try:
                msg_id = int(message_parts[0][1:])
                if(ev_room == charcoal_room_id):
                    msg_to_delete = wrap.get_message(msg_id)
                    if(str(msg_to_delete.owner.id) == smokeDetector_user_id[charcoal_room_id]):
                        msg_to_delete.delete()
                elif(ev_room == meta_tavern_room_id):
                    msg_to_delete = wrapm.get_message(msg_id)
                    if(str(msg_to_delete.owner.id) == smokeDetector_user_id[meta_tavern_room_id]):
                        msg_to_delete.delete()
            except:
                pass # couldn't delete message
    if(ev.content.startswith("!!/alive")):
        if(ev_room == charcoal_room_id):
            room.send_message(':'+str(ev.data["message_id"])+' Of course')
        elif(ev_room == meta_tavern_room_id):
            roomm.send_message(':'+str(ev.data["message_id"]) + ' ' + random.choice(['Yup', 'You doubt me?', 'Of course', '... did I miss something?', 'plz send teh coffee', 'watching this endless list of new questions *never* gets boring', 'kinda sorta']))
    if(ev.content.startswith("!!/rev")):
            postMessageInRoom(ev_room, ':'+str(ev.data["message_id"])+' [' + commit_with_author + '](https://github.com/Charcoal-SE/SmokeDetector/commit/'+ commit +')')
    if(ev.content.startswith("!!/status")):
            postMessageInRoom(ev_room, ':'+str(ev.data["message_id"])+' Running since %s UTC' % startup_utc)
    if(ev.content.startswith("!!/reboot")):
        if(isPrivileged(ev_room, ev_user_id)):
            postMessageInRoom(ev_room, "Goodbye, cruel world")
            os._exit(1)
    if(ev.content.startswith("!!/block")):
        if(isPrivileged(ev_room, ev_user_id)):
            postMessageInRoom(ev_room, "blocked")
            timeToBlock = ev.content[9:].strip()
            timeToBlock = int(timeToBlock) if timeToBlock else 0
            if (0 < timeToBlock < 14400):
                blockedTime = time.time() + timeToBlock
            else:
                blockedTime = time.time() + 900
    if(ev.content.startswith("!!/unblock")):
        if(isPrivileged(ev_room, ev_user_id)):
            blockedTime = time.time()
            postMessageInRoom(ev_room, "unblocked")

def isPrivileged(room_id_str, user_id_str):
    return room_id_str in privileged_users and user_id_str in privileged_users[room_id_str]

def postMessageInRoom(room_id_str, msg):
    if room_id_str == charcoal_room_id:
        room.send_message(msg)
    elif room_id_str == meta_tavern_room_id:
        roomm.send_message(msg)

room.watch_socket(watcher)
roomm.watch_socket(watcher)
try:
    while True:
        a=ws.recv()
        if(a!= None and a!= ""):
            if(checkifspam(a)):
                threading.Thread(target=handlespam,args=(a,)).start()
except Exception, e:
    print sys.exc_info()[0]
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector aborted"
room.send_message(s)
