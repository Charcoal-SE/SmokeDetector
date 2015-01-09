import json
import requests

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
        url = "http://api.stackexchange.com/2.2/questions/" + ";".join(str(x) for x in posts)  + "?site=" + site + "&filter=!)Q2A3(bojAapKo*S5jsdVAhh&key=IAkbitmze4B8KpacUfLqkw(("
        response = requests.get(url).json()

        for post in response["items"]:
            print post["owner"]["display_name"]
