import json
from globalvars import GlobalVars
import parsing


class Post:
    _body = ""
    _body_is_summary = False
    _is_answer = False
    _owner_rep = 1
    _post_id = ""
    _post_score = 0
    _post_site = ""
    _title = ""
    _user_name = ""
    _user_url = ""
    _votes = {'downvotes': None, 'upvotes': None}

    def __init__(self, json_data=None, api_response=None):
        if json_data is not None:
            self._parse_json_post(json_data)
        elif api_response is not None:
            self._parse_api_post(api_response)
        else:
            raise ValueError("Must provide either JSON Data or an API Response object for Post object.")
        # self._title = title
        # self._body = body
        # self._user_name = user_name
        # self._user_url = user_url
        # self._post_site = post_site
        # self._post_id = post_id
        # self._is_answer = is_answer
        # self._body_is_summary = body_is_summary
        # self._owner_rep = owner_rep
        # self._post_score = post_score

    def __repr__(self):
        type_name = type(self).__name__
        dataset = ['title=' + self.title, 'body=' + self.body, 'user_name=' + self.user_name,
                   'user_url=' + self.user_url, 'post_site=' + self.post_site, 'post_id=' + self.post_id,
                   'is_answer=' + str(self.is_answer), 'body_is_summary=' + str(self.body_is_summary),
                   'owner_rep=' + str(self.owner_rep), 'post_score=' + self.post_score]
        return "%s(%s)" % (type_name, ', '.join(dataset))

    def _parse_json_post(self, json_data):
        text_data = json.loads(json_data)["data"]
        if text_data == "hb":
            return

        try:
            data = json.loads(text_data)
        except ValueError:
            GlobalVars.charcoal_hq.send_message(u"Encountered ValueError parsing the following:\n{0}".format(json_data),
                                                False)
            return
        if "ownerUrl" not in data:
            # owner's account doesn't exist anymore, no need to post it in chat:
            # http://chat.stackexchange.com/transcript/message/18380776#18380776
            return
        self._title = data["titleEncodedFancy"]
        self._title = parsing.unescape_title(self._title)
        self._body = data["bodySummary"]
        self._user_name = data["ownerDisplayName"]
        self._user_url = data["url"]
        self._post_id = str(data["id"])
        self._post_site = data["siteBaseHostAddress"]
        self._post_site = self._post_site.encode("ascii", errors="replace")
        self._owner_rep = 1
        self._post_score = 0
        self._body_is_summary = True
        self._is_answer = False
        return

        # is_spam, reason, why = check_if_spam(title=title,
        #                                      body=body,
        #                                      user_name=poster,
        #                                      user_url=url,
        #                                      post_site=site,
        #                                      post_id=post_id,
        #                                      is_answer=False,
        #                                      body_is_summary=True,
        #                                      owner_rep=1,
        #                                      post_score=0)

    def _parse_api_post(self, response):
        if "title" not in response or "body" not in response:
            return

        if "IsAnswer" in response and response["IsAnswer"] is True:
            self._is_answer = True
        else:
            self._is_answer = False

        self._title = GlobalVars.parser.unescape(response["title"])
        self._body = GlobalVars.parser.unescape(response["body"])
        self._post_url = response["link"]
        self._post_score = response["score"]
        self._votes['upvotes'] = response["up_vote_count"]
        self._votes['downvotes'] = response["down_vote_count"]
        # noinspection PyBroadException
        try:
            self._user_name = GlobalVars.parser.unescape(response["owner"]["display_name"])
            self._user_url = response["owner"]["link"]
            self._owner_rep = response["owner"]["reputation"]
        except:
            self._user_name = ""
            self._user_url = ""
            self._owner_rep = 0
            pass

        self._post_id = str(response["question_id"])

        return

        # is_spam, reason, why = check_if_spam(title=title,
        #                                      body=body,
        #                                      user_name=owner_name,
        #                                      user_url=owner_link,
        #                                      post_site=site,
        #                                      post_id=q_id,
        #                                      is_answer=False,
        #                                      body_is_summary=False,
        #                                      owner_rep=owner_rep,
        #                                      post_score=post_score)

    @property
    def body(self):
        return self._body

    @property
    def body_is_summary(self):
        return self._body_is_summary

    @property
    def is_answer(self):
        return self._is_answer

    @property
    def owner_rep(self):
        return self._owner_rep

    @property
    def post_id(self):
        return self._post_id

    @property
    def post_score(self):
        return self._post_score

    @property
    def post_site(self):
        return self._post_site

    @property
    def title(self):
        return self._title

    @property
    def user_name(self):
        return self._user_name

    @property
    def user_url(self):
        return self._user_url

    @property
    def up_vote_count(self):
        return self._votes['upvotes']

    @property
    def down_vote_count(self):
        return self._votes['downvotes']

    # is_spam, reason, why = check_if_spam(title=title,
    #                                      body=body,
    #                                      user_name=owner_name,
    #                                      user_url=owner_link,
    #                                      post_site=site,
    #                                      post_id=q_id,
    #                                      is_answer=False,
    #                                      body_is_summary=False,
    #                                      owner_rep=owner_rep,
    #                                      post_score=post_score)
