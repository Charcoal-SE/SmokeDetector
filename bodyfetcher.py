import json
import requests
from spamhandling import *
from chatcommunicate import *
from datahandling import *
from parsing import get_user_from_url

class BodyFetcher:
    queue = {}

    specialCases = {"stackoverflow.com" : 5, "serverfault.com" : 5, "superuser.com" : 5}

    def addToQueue(self, post):
        d=json.loads(json.loads(post)["data"])
        sitebase = d["siteBaseHostAddress"]
        postid = d["id"]
        if sitebase in self.queue:
            self.queue[sitebase].append(postid)
        else:
            self.queue[sitebase] = [postid]

        print self.queue
        self.checkQueue()

    def checkQueue(self):
        for site, values in self.queue.iteritems():
            if site in self.specialCases:
                if len(self.queue[site]) >= self.specialCases[site]:
                    print "site " + site + " met special case quota, fetching..."
                    self.makeApiCallForSite(site)
                    return

        # if we don't have any sites with their queue filled, take the first one without a special case
        for site, values in self.queue.iteritems():
            if site not in self.specialCases:
                self.makeApiCallForSite(site)
                return


    def makeApiCallForSite(self, site):
        posts = self.queue.pop(site)
        url = "http://api.stackexchange.com/2.2/questions/" + ";".join(str(x) for x in posts)  + "?site=" + site + "&filter=!-Kh)95tdb6R0joni_wabz(1g(16eESDja&key=IAkbitmze4B8KpacUfLqkw(("
        response = requests.get(url).json()

        for post in response["items"]:
            result = FindSpam.testbody(post["body"],site)
            if result != []:
                try:
                    reason = ", ".join(result)
                    s="[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] %s: [%s](%s) by [%s](%s) on `%s`" % \
                      (reason,post["title"].strip(), post["link"],post["owner"]["display_name"].strip(), post["owner"]["link"], site)
                    print GlobalVars.parser.unescape(s).encode('ascii',errors='replace')
                    if time.time() >= GlobalVars.blockedTime:
                        GlobalVars.charcoal_hq.send_message(s)
                        GlobalVars.tavern_on_the_meta.send_message(s)
                        for specialroom in GlobalVars.specialrooms:
                            sites = specialroom["sites"]
                            if site in sites and reason not in specialroom["unwantedReasons"]:
                                # specialroom["room"].send_message(s)
                except:
                    print "NOP"
