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
from datetime import datetime
import traceback
import requests

class UtcDate:
    startup_utc_date = datetime.utcnow()

# !! Important! Be careful when adding code before the add_custom_print_exception function. Any errors thrown there won't be catched, so only insert code here if you are really sure it works fine.

def uncaught_exception(exctype, value, tb):
    now = datetime.utcnow()
    delta = UtcDate.startup_utc_date - now
    seconds = delta.total_seconds()
    tr = os.linesep.join(traceback.format_tb(tb))
    print(tr)
    with open("errorLogs.txt", "a") as f:
        f.write(str(now) + " UTC" + os.linesep + tr + os.linesep + os.linesep)
    if(seconds < 180):
        os._exit(4)
    else:
        os._exit(1)

sys.excepthook = uncaught_exception

def installThreadExcepthook():
    """
    Workaround for sys.excepthook thread bug
    From
    http://spyced.blogspot.com/2007/06/workaround-for-sysexcepthook-bug.html
    (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_id=5470).
    Call once from __main__ before creating any threads.
    If using psyco, call psyco.cannotcompile(threading.Thread.run)
    since this replaces a new-style class method.
    """
    init_old = threading.Thread.__init__
    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run
        def run_with_except_hook(*args, **kw):
            try:
                run_old(*args, **kw)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                sys.excepthook(*sys.exc_info())
        self.run = run_with_except_hook
    threading.Thread.__init__ = init

installThreadExcepthook()

class GlobalVars:
    false_positives = []
    whitelisted_users = []
    blacklisted_users = []
    ignored_posts = []
    startup_utc = datetime.utcnow().strftime("%H:%M:%S")
    latest_questions = []
    blockedTime = 0
    charcoal_room_id = "11540"
    meta_tavern_room_id = "89"
    privileged_users = {}
    smokeDetector_user_id = {}
    site_filename = { "electronics.stackexchange.com" : "ElectronicsGood.txt", "gaming.stackexchange.com" : "GamingGood.txt", "german.stackexchange.com" : "GermanGood.txt",
                      "italian.stackexchange.com" : "ItalianGood.txt", "math.stackexchange.com" : "MathematicsGood.txt", "spanish.stackexchange.com" : "SpanishGood.txt",
                      "stats.stackexchange.com" : "StatsGood.txt" }
    parser=HTMLParser.HTMLParser()
    wrap=Client("stackexchange.com")
    wrapm=Client("meta.stackexchange.com")
    commit = os.popen("git log --pretty=format:'%h' -n 1").read()
    commit_with_author = os.popen("git log --pretty=format:'%h (%cn: *%s*)' -n 1").read()
    on_master = os.popen("git rev-parse --abbrev-ref HEAD").read().strip() == "master"
    charcoal_hq = None
    tavern_on_the_meta = None
    s = ""
    s_reverted = ""
    specialrooms = []
    bayesian_testroom = None

GlobalVars.privileged_users = { GlobalVars.charcoal_room_id: ["117490", "66258", "31768","103081","73046","88521","59776", "31465"], GlobalVars.meta_tavern_room_id: ["259867", "244519","244382","194047","158100","178438","237685","215468","229438","180276", "161974", "244382", "186281", "266094", "245167", "230261", "213575", "241919", "203389"] }
GlobalVars.smokeDetector_user_id = { GlobalVars.charcoal_room_id: "120914", GlobalVars.meta_tavern_room_id: "266345" }

def load_files():
    if(os.path.isfile("falsePositives.txt")):
        with open("falsePositives.txt", "r") as f:
            GlobalVars.false_positives = pickle.load(f)
    if(os.path.isfile("whitelistedUsers.txt")):
        with open("whitelistedUsers.txt", "r") as f:
            GlobalVars.whitelisted_users = pickle.load(f)
    if(os.path.isfile("blacklistedUsers.txt")):
        with open("blacklistedUsers.txt", "r") as f:
            GlobalVars.blacklisted_users = pickle.load(f)
    if(os.path.isfile("ignoredPosts.txt")):
        with open("ignoredPosts.txt", "r") as f:
            GlobalVars.ignored_posts = pickle.load(f)

if("ChatExchangeU" in os.environ):
    username=os.environ["ChatExchangeU"]
else:
    print "Username: "
    username=raw_input()
if("ChatExchangeP" in os.environ):
    password=os.environ["ChatExchangeP"]
else:
    password=getpass.getpass("Password: ")

load_files()

GlobalVars.wrap.login(username,password)
GlobalVars.wrapm.login(username,password)
GlobalVars.s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector started at [rev " + GlobalVars.commit_with_author + "](https://github.com/Charcoal-SE/SmokeDetector/commit/"+ GlobalVars.commit +") (hosted by Undo)"
GlobalVars.s_reverted="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector started in [reverted mode](https://github.com/Charcoal-SE/SmokeDetector/blob/master/RevertedMode.md) at [rev " + GlobalVars.commit_with_author + "](https://github.com/Charcoal-SE/SmokeDetector/commit/"+ GlobalVars.commit +") (hosted by Undo)"
GlobalVars.charcoal_hq = GlobalVars.wrap.get_room(GlobalVars.charcoal_room_id)
GlobalVars.tavern_on_the_meta = GlobalVars.wrapm.get_room(GlobalVars.meta_tavern_room_id)

GlobalVars.specialrooms = [{ "sites": ["english.stackexchange.com"], "room": GlobalVars.wrap.get_room("95"), "unwantedReasons": [] }, { "sites": ["askubuntu.com"], "room": GlobalVars.wrap.get_room("201"), "unwantedReasons": ["All-caps title", "Phone number detected"] }]

GlobalVars.bayesian_testroom = GlobalVars.wrap.get_room("17251")
if "first_start" in sys.argv and GlobalVars.on_master:
    GlobalVars.charcoal_hq.send_message(GlobalVars.s)
    GlobalVars.bayesian_testroom.send_message(GlobalVars.s)
    #GlobalVars.tavern_on_the_meta.send_message(GlobalVars.s)
    #Commented out because the Tavern folk don't really need to see when it starts
elif "first_start" in sys.argv and not GlobalVars.on_master:
    GlobalVars.charcoal_hq.send_message(GlobalVars.s_reverted)
    GlobalVars.bayesian_testroom.send_message(GlobalVars.s_reverted)

def restart_automatically(time_in_seconds):
    time.sleep(time_in_seconds)
    os._exit(1)

threading.Thread(target=restart_automatically,args=(3600,)).start()

def get_user_from_url(url):
    m = re.compile(r"https?://([\w.]+)/users/(\d+)/.+/?").search(url)
    site = m.group(1)
    user_id = m.group(2)
    return (user_id, site)

def postMessageInRoom(room_id_str, msg):
    if room_id_str == GlobalVars.charcoal_room_id:
        GlobalVars.charcoal_hq.send_message(msg)
    elif room_id_str == GlobalVars.meta_tavern_room_id:
        GlobalVars.tavern_on_the_meta.send_message(msg)

def is_whitelisted_user(user):
    return user in GlobalVars.whitelisted_users

def is_blacklisted_user(user):
    return user in GlobalVars.blacklisted_users

def is_ignored_post(postid_site_tuple):
    return postid_site_tuple in GlobalVars.ignored_posts

def add_whitelisted_user(user):
    if user in GlobalVars.whitelisted_users or user is None:
        return
    GlobalVars.whitelisted_users.append(user)
    with open("whitelistedUsers.txt", "w") as f:
        pickle.dump(GlobalVars.whitelisted_users, f)

def add_blacklisted_user(user):
    if user in GlobalVars.blacklisted_users or user is None:
        return
    GlobalVars.blacklisted_users.append(user)
    with open("blacklistedUsers.txt", "w") as f:
        pickle.dump(GlobalVars.blacklisted_users, f)

def append_to_latest_questions(host, post_id, title):
    GlobalVars.latest_questions.insert(0, (host, post_id, title))
    if len(GlobalVars.latest_questions) > 15:
        GlobalVars.latest_questions.pop()

def has_already_been_posted(host, post_id, title):
    for post in GlobalVars.latest_questions:
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
    if((str(post_id), site_name) in GlobalVars.false_positives):
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
    print time.strftime("%Y-%m-%d %H:%M:%S"),GlobalVars.parser.unescape(s).encode("ascii",errors="replace")
    quality_score = bayesian_score(s)
    print quality_score
    if(quality_score < 0.3 and d["siteBaseHostAddress"] == "stackoverflow.com"):
        print GlobalVars.bayesian_testroom.send_message("[ SmokeDetector | BayesianBeta ] Quality score " + str(quality_score*100) + ": [" + s + "](" + d["url"] + ")")
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
        if(has_already_been_posted(site, post_id, s) or is_false_positive(post_id, site) or is_whitelisted_user(get_user_from_url(d["ownerUrl"])) or is_ignored_post((str(post_id), site))):
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
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[.+]\(http:\/\/[\w.]+\/questions\/(\d+)\/.+\) by \[.+\]\((?:.+)\) on `([\w.]+)`$"
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
    search_regex = r"^\[ \[SmokeDetector\]\(https:\/\/github.com\/Charcoal-SE\/SmokeDetector\) \] [\w\s,-]+: \[.+]\(http:\/\/[\w.]+\/questions\/\d+\/.+\) by \[.+\]\((.+)\) on `[\w.]+`$"
    m = re.compile(search_regex).search(content)
    if m is None:
        return None
    try:
        owner_url = m.group(1)
        return owner_url
    except:
        return None

def store_site_and_post_id(site_post_id_tuple):
    if(site_post_id_tuple is None or site_post_id_tuple in GlobalVars.false_positives):
        return
    GlobalVars.false_positives.append(site_post_id_tuple)
    with open("falsePositives.txt", "w") as f:
        pickle.dump(GlobalVars.false_positives, f)

def add_ignored_post(postid_site_tuple):
    if(postid_site_tuple is None or postid_site_tuple in GlobalVars.ignored_posts):
        return
    GlobalVars.ignored_posts.append(postid_site_tuple)
    with open("ignoredPosts.txt", "w") as f:
        pickle.dump(GlobalVars.ignored_posts, f)

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
        titleToPost = GlobalVars.parser.unescape(re.sub(r"([_*\\`\[\]])", r"\\\1", title)).strip()
        s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) by [%s](%s) on `%s`" % (reason,titleToPost.strip(),d["url"],poster.strip(),d["ownerUrl"],d["siteBaseHostAddress"])
        print GlobalVars.parser.unescape(s).encode('ascii',errors='replace')
        if time.time() >= GlobalVars.blockedTime:
            GlobalVars.charcoal_hq.send_message(s)
            GlobalVars.tavern_on_the_meta.send_message(s)
            for specialroom in GlobalVars.specialrooms:
                sites = specialroom["sites"]
                if d["siteBaseHostAddress"] in sites and reason not in specialroom["unwantedReasons"]:
                    specialroom["room"].send_message(s)
    except:
        print "NOP"
ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
ws.send("155-questions-active")
GlobalVars.charcoal_hq.join()
GlobalVars.tavern_on_the_meta.join()
def watcher(ev,wrap2):
    if ev.type_id != 1:
        return;
    print(ev)
    ev_room = str(ev.data["room_id"])
    ev_user_id = str(ev.data["user_id"])
    message_parts = ev.message.content_source.split(" ")
    second_part_lower = "" if len(message_parts) < 2 else message_parts[1].lower()
    content_lower = ev.content.lower()
    if(re.compile(":[0-9]+").search(message_parts[0])):
        if((second_part_lower.startswith("false") or second_part_lower.startswith("fp")) and isPrivileged(ev_room, ev_user_id)):
            try:
                should_delete = True
                msg_id = int(message_parts[0][1:])
                msg_content = None
                msg_to_delete = wrap2.get_message(msg_id)
                if(str(msg_to_delete.owner.id) == GlobalVars.smokeDetector_user_id[ev_room]):
                    msg_content = msg_to_delete.content_source
                if (msg_content is not None):
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
                        if user_added and site_post_id is not None:
                            ev.message.reply("Registered as false positive, added title to Bayesian doctype 'good', whitelisted user.")
                        elif site_post_id is not None:
                            ev.message.reply("Registered as false positive and added title to Bayesian doctype 'good'.")
                        else:
                            ev.message.reply("Could not register title as false positive.")
                            should_delete = False
                    else:
                        if user_added and site_post_id is not None:
                            ev.message.reply("Registered as false positive and whitelisted user, but could not add the title to the Bayesian doctype 'good'.")
                        elif site_post_id is not None:
                            ev.message.reply("Registered as false positive, but could not add the title to the Bayesian doctype 'good'.")
                        else:
                            ev.message.reply("Could not register title as false positive.")
                            should_delete = False
                    if should_delete:
                        msg_to_delete.delete()
            except:
                pass # couldn't delete message
        if((second_part_lower.startswith("true") or second_part_lower.startswith("tp")) and isPrivileged(ev_room, ev_user_id)):
            try:
                msg_id = int(message_parts[0][1:])
                msg_content = None
                msg_true_positive = wrap2.get_message(msg_id)
                if(str(msg_true_positive.owner.id) == GlobalVars.smokeDetector_user_id[ev_room]):
                    msg_content = msg_true_positive.content_source
                if(msg_content is not None):
                    learned = bayesian_learn_title(msg_content, "bad")
                    user_added = False
                    if(message_parts[1].lower().startswith("trueu") or message_parts[1].lower().startswith("tpu")):
                        url_from_msg = fetch_owner_url_from_msg_content(msg_content)
                        user = get_user_from_url(url_from_msg)
                        add_blacklisted_user(user)
                        user_added = True
                    if learned:
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
        if(second_part_lower.startswith("ignore") and isPrivileged(ev_room, ev_user_id)):
            try:
                msg_id = int(message_parts[0][1:])
                msg_content = None
                msg_ignore = wrap2.get_message(msg_id)
                if(str(msg_ignore.owner.id) == GlobalVars.smokeDetector_user_id[ev_room]):
                    msg_content = msg_ignore.content_source
                if(msg_content is not None):
                    post_id_site = fetch_post_id_and_site_from_msg_content(msg_content)
                    add_ignored_post(post_id_site)
                    ev.message.reply("Post ignored; alerts about it will not longer be posted.")
            except:
                pass
        if((second_part_lower == "delete" or second_part_lower == "remove" or second_part_lower == "gone") and isPrivileged(ev_room, ev_user_id)):
            try:
                msg_id = int(message_parts[0][1:])
                msg_to_delete = wrap2.get_message(msg_id)
                if(str(msg_to_delete.owner.id) == GlobalVars.smokeDetector_user_id[ev_room]):
                    msg_to_delete.delete()
            except:
                pass # couldn't delete message
    if(content_lower.startswith("!!/wut")):
        ev.message.reply("Whaddya mean, 'wut'? Humans...")
    if(content_lower.startswith("!!/lick")):
        ev.message.reply("*licks ice cream cone*")
    if(content_lower.startswith("!!/hats")):
        wb_end = datetime(2015, 1, 5, 0, 0, 0)
        now = datetime.utcnow()
        diff = wb_end - now
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        daystr = "days" if diff.days != 1 else "day"
        hourstr = "hours" if hours != 1 else "hour"
        minutestr = "minutes" if minutes != 1 else "minute"
        secondstr = "seconds" if seconds != 1 else "second"
        ev.message.reply("HATS ARE AWESOME. Winter Bash will end in %s %s, %s %s, %s %s and %s %s. :(" % (diff.days, daystr, hours, hourstr, minutes, minutestr, seconds, secondstr))
    if(content_lower.startswith("!!/alive")):
        if(ev_room == GlobalVars.charcoal_room_id):
            ev.message.reply('Of course')
        elif(ev_room == GlobalVars.meta_tavern_room_id):
            ev.message.reply(random.choice(['Yup', 'You doubt me?', 'Of course', '... did I miss something?', 'plz send teh coffee', 'Watching this endless list of new questions *never* gets boring', 'Kinda sorta']))
    if(content_lower.startswith("!!/rev")):
            ev.message.reply('[' + GlobalVars.commit_with_author + '](https://github.com/Charcoal-SE/SmokeDetector/commit/'+ GlobalVars.commit +')')
    if(content_lower.startswith("!!/status")):
            ev.message.reply('Running since %s UTC' % GlobalVars.startup_utc)
    if(content_lower.startswith("!!/reboot")):
        if(isPrivileged(ev_room, ev_user_id)):
            postMessageInRoom(ev_room, "Goodbye, cruel world")
            os._exit(5)
    if(content_lower.startswith("!!/stappit")):
        if(isPrivileged(ev_room, ev_user_id)):
            postMessageInRoom(ev_room, "Goodbye, cruel world")
            os._exit(6)
    if(content_lower.startswith("!!/updatesubmodule")):
        if(isPrivileged(ev_room, ev_user_id)):
            ev.message.reply("Updating submodules, will reboot after finished.")
            os._exit(7)
    if(content_lower.startswith("!!/master")):
        if(isPrivileged(ev_room, ev_user_id)):
            ev.message.reply("Checking out to master and restarting...")
            os._exit(8)
    if(content_lower.startswith("!!/gimmehat")):
        if(isPrivileged(ev_room, ev_user_id)):
            postMessageInRoom(GlobalVars.meta_tavern_room_id, "I'm tired of not having a hat...")
    if(content_lower.startswith("!!/block")):
        if(isPrivileged(ev_room, ev_user_id)):
            ev.message.reply("blocked")
            timeToBlock = ev.content[9:].strip()
            timeToBlock = int(timeToBlock) if timeToBlock else 0
            if (0 < timeToBlock < 14400):
                GlobalVars.blockedTime = time.time() + timeToBlock
            else:
                GlobalVars.blockedTime = time.time() + 900
    if(content_lower.startswith("!!/unblock")):
        if(isPrivileged(ev_room, ev_user_id)):
            GlobalVars.blockedTime = time.time()
            ev.message.reply("unblocked")
    if(content_lower.startswith("!!/pull")):
        if(isPrivileged(ev_room, ev_user_id)):
            r = requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/git/refs/heads/master')
            latest_sha = r.json()["object"]["sha"]
            r = requests.get('https://api.github.com/repos/Charcoal-SE/SmokeDetector/commits/' + latest_sha + '/statuses')
            states = []
            for status in r.json():
                state = status["state"]
                states.append(state)
            if ("success" in states):
                ev.message.reply("Pulling latest from master -- CI build passed.")
                os._exit(3)
            elif ("error" in states or "failure" in states):
                ev.message.reply("CI build failed! :( Please check your commit.")
            elif ("pending" in states or not states):
                ev.message.reply("CI build is still pending, wait until the build has finished and then pull again.")

def isPrivileged(room_id_str, user_id_str):
    return room_id_str in GlobalVars.privileged_users and user_id_str in GlobalVars.privileged_users[room_id_str]

GlobalVars.charcoal_hq.watch_socket(watcher)
GlobalVars.tavern_on_the_meta.watch_socket(watcher)
while True:
    try:
        a=ws.recv()
        if(a!= None and a!= ""):
            if(checkifspam(a)):
                threading.Thread(target=handlespam,args=(a,)).start()
    except Exception, e:
        now = datetime.utcnow()
        delta = UtcDate.startup_utc_date - now
        seconds = delta.total_seconds()
        if(seconds < 60):
            os._exit(4)
        ws = websocket.create_connection("ws://qa.sockets.stackexchange.com/")
        ws.send("155-questions-active")
        tr = traceback.format_exc()
        print(tr)
        exception_only = ''.join(traceback.format_exception_only(type(e), e)).strip()
        GlobalVars.charcoal_hq.send_message("Recovered from `" + exception_only + "`")
        with open("errorLogs.txt", "a") as f:
            f.write(str(now) + " UTC" + os.linesep + tr + os.linesep + os.linesep)

now = datetime.utcnow()
delta = UtcDate.startup_utc_date - now
seconds = delta.total_seconds()
if(seconds < 60):
    os._exit(4)
s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] SmokeDetector aborted"
GlobalVars.charcoal_hq.send_message(s)
