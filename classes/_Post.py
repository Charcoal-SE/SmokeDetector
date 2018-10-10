# coding=utf-8
import json
from helpers import log
import html
from typing import AnyStr, Union


class PostParseError(Exception):
    """
    Error raised when a JSON entry could not be parsed.
    """
    pass


class Post:
    def __init__(self, json_data=None, api_response=None, parent=None):
        # type: (AnyStr, dict, Post) -> None

        self._body = ""
        self._body_is_summary = False
        self._is_answer = False
        self._owner_rep = 1
        self._parent = None  # If not None, _is_answer should be 'true' because there would then be a parent post.
        self._post_id = ""
        self._post_score = 0
        self._post_site = ""
        self._post_url = ""
        self._title = ""
        self._user_name = ""
        self._user_url = ""
        self._votes = {'downvotes': None, 'upvotes': None}
        self._edited = False

        if parent is not None:
            if not isinstance(parent, Post):
                raise TypeError("Parent object for a Post object must also be a Post object.")
            else:
                self._parent = parent

        if json_data is not None:
            self._parse_json_post(json_data)
        elif api_response is not None:
            self._parse_api_post(api_response)
        else:
            raise PostParseError("Must provide either JSON Data or an API Response object for Post object.")

        return  # Required for PEP484 compliance

    def __repr__(self):
        type_name = type(self).__name__
        dataset = ['title=' + self.title, 'body=' + self.body, 'user_name=' + self.user_name,
                   'user_url=' + self.user_url, 'post_site=' + self.post_site, 'post_id=' + self.post_id,
                   'is_answer=' + str(self.is_answer), 'body_is_summary=' + str(self.body_is_summary),
                   'owner_rep=' + str(self.owner_rep), 'post_score=' + str(self.post_score)]
        return "%s(%s)" % (type_name, ', '.join(dataset))

    def __setitem__(self, key, item):
        # type: (str, Union[str, object]) -> None
        setattr(self, key, item)
        return  # PEP compliance

    def __getitem__(self, item):
        # type: (str) -> object
        return getattr(self, item)

    # noinspection PyTypeChecker
    def _get_title_ignore_type(self):
        # type: () -> str
        return self.parent.title if self.is_answer else self.title

    def _parse_json_post(self, json_data):
        # type: (str) -> None

        text_data = json.loads(json_data)["data"]
        if text_data == "hb":
            return

        try:
            data = json.loads(text_data)
        except ValueError:
            log('error', u"Encountered ValueError parsing the following:\n{0}".format(json_data))
            return

        if "ownerUrl" not in data:
            # owner's account doesn't exist anymore, no need to post it in chat:
            # http://chat.stackexchange.com/transcript/message/18380776#18380776
            return

        element_map = {
            'titleEncodedFancy': '_title',
            'bodySummary': '_body',
            'ownerDisplayName': '_user_name',
            'url': '_user_url',
            'id': '_post_id',
            'siteBaseHostAddress': '_post_site',
        }

        self._process_element_mapping(element_map, data, is_api_response=False)

        self._title = self._unescape_title(self._title)
        self._post_id = str(self._post_id)
        self._post_site = self._post_site.encode("ascii", errors="replace")
        self._owner_rep = 1
        self._post_score = 0
        self._body_is_summary = True
        self._is_answer = False

        return  # PEP compliance

    def _parse_api_post(self, response):
        # type: (dict) -> None

        if "title" not in response or "body" not in response:
            return

        self._title = html.unescape(response["title"])
        self._body = html.unescape(response["body"])

        if "IsAnswer" in response and response["IsAnswer"] is True:
            self._is_answer = True
        else:
            if "answers" in response and response["answers"] != []:
                self._answers = []
                for answer in response["answers"]:
                    self._answers.append(Post(api_response=answer))
            else:
                self._answers = []
            self._is_answer = False

        if "BodyIsSummary" in response and response["BodyIsSummary"] is True:
            self._body_is_summary = True

        # Map response elements to the corresponding variable for the Post object internally.
        element_map = {
            'site': '_post_site',
            'link': '_post_url',
            'score': '_post_score',
            'up_vote_count': "_votes['upvotes']",
            'down_vote_count': "_votes['downvotes']",
            'owner': {
                'display_name': '_user_name',
                'link': '_user_url',
                'reputation': '_owner_rep'
            },
            'question_id': '_post_id',
            'answer_id': '_post_id',
            'edited': '_edited',
        }

        self._process_element_mapping(element_map, response, is_api_response=True)

    def _process_element_mapping(self, element_map, data, is_api_response=False):
        # type: (dict, dict, bool) -> None
        # Take the API response map, and start setting the elements (and sub-elements, where applicable)
        # to the attributes and variables in the object.
        for (element, varmap) in element_map.items():
            try:
                if is_api_response and element == 'owner':
                    for (subelement, subvarmap) in element_map['owner'].items():
                        try:
                            self[subvarmap] = (html.unescape(data['owner'][subelement]) if subelement == 'display_name'
                                               else data['owner'][subelement])
                        except KeyError:
                            # Go to next subkey
                            continue
                    continue  # Go to next key because we're done processing the 'owner' key.

                if data[element] is None:
                    continue

                # Other keys
                self[varmap] = data[element]
            except KeyError:
                # Executes if the 'element' requested isn't part of the response.
                continue  # Go to next key

    @staticmethod
    def _unescape_title(title):
        return str(html.unescape(title).strip())

    @property
    def answers(self):
        # noinspection PyBroadException
        try:
            return self._answers
        except AttributeError:
            return None

    @property
    def body(self):
        return str(self._body)

    @property
    def body_is_summary(self):
        return bool(self._body_is_summary)

    @property
    def is_answer(self):
        return bool(self._is_answer)

    @property
    def owner_rep(self):
        return int(self._owner_rep)

    @property
    def parent(self):
        return self._parent

    @property
    def post_id(self):
        return str(self._post_id)

    @property
    def post_score(self):
        return int(self._post_score)

    @property
    def post_site(self):
        if type(self._post_site) in [bytes, bytearray]:
            self._post_site = self._post_site.decode('utf-8')

        return self._post_site

    # noinspection PyBroadException
    @property
    def post_url(self):
        try:
            return str(self._post_url)
        except (AttributeError, ValueError):
            return "NoLink"

    @property
    def title(self):
        return str(self._title)

    @property
    def user_link(self):
        # Alias for self.user_url
        return str(self.user_url)

    @property
    def user_name(self):
        return str(self._user_name)

    @property
    def user_url(self):
        return str(self._user_url)

    @property
    def up_vote_count(self):
        return self._votes['upvotes']

    @property
    def down_vote_count(self):
        return self._votes['downvotes']

    @property
    def title_ignore_type(self):
        return self._get_title_ignore_type()

    @property
    def edited(self):
        return self._edited
