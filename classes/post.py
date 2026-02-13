# coding=utf-8
import json
from helpers import log
from models.se_api import StackExchangePostItem
import html
from typing import AnyStr, Optional, Union

from models.se_api import StackExchangePostItem, StackExchangeOwner

from models.se_api import StackExchangePostItem, StackExchangeOwner


class PostParseError(Exception):
    """
    Error raised when a JSON entry could not be parsed.
    """
    pass


class Post:
    def __init__(self, json_data: Optional[AnyStr] = None, api_response: Optional[Union[dict, StackExchangePostItem]] = None, parent: Optional["Post"] = None) -> None:
        self._body = ""
        self._body_is_summary = False
        self._markdown = None
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

    def __repr__(self):
        type_name = type(self).__name__
        dataset = ['title=' + self.title, 'body=' + self.body, 'user_name=' + self.user_name,
                   'user_url=' + self.user_url, 'post_site=' + self.post_site, 'post_id=' + self.post_id,
                   'is_answer=' + str(self.is_answer), 'body_is_summary=' + str(self.body_is_summary),
                   'owner_rep=' + str(self.owner_rep), 'post_score=' + str(self.post_score)]
        return "%s(%s)" % (type_name, ', '.join(dataset))

    def __setitem__(self, key: str, item: Union[str, object]) -> None:
        setattr(self, key, item)

    def __getitem__(self, item: str) -> object:
        return getattr(self, item)

    # noinspection PyTypeChecker
    def _get_title_ignore_type(self) -> str:
        return self.parent.title if self.is_answer else self.title

    def _parse_json_post(self, json_data: str) -> None:
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
            # https://chat.stackexchange.com/transcript/message/18380776#18380776
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

    def _parse_api_post(self, response: Union[dict, StackExchangePostItem]) -> None:
        if isinstance(response, dict):
            if "title" not in response or "body" not in response:
                return
            # 兼容历史代码中将 get_user_from_url 返回的元组直接塞进 owner.display_name 的用法，
            # 在构造 Pydantic 模型前，将非字符串 display_name 规范化为字符串，避免校验错误。
            owner = response.get("owner")
            if isinstance(owner, dict):
                display_name = owner.get("display_name")
                if display_name is not None and not isinstance(display_name, str):
                    owner["display_name"] = str(display_name)
            item = StackExchangePostItem.from_dict(response)
        elif isinstance(response, StackExchangePostItem):
            item = response
        else:
            raise TypeError("api_response must be a dict or StackExchangePostItem instance.")

        # 标题与正文
        if item.title is None or item.body is None:
            return

        self._title = html.unescape(item.title)
        self._body = html.unescape(item.body)

        if item.body_markdown is not None:
            self._markdown = html.unescape(item.body_markdown)

        # 回答/问题标记与子答案
        if getattr(item, "IsAnswer", None):
            self._is_answer = True
        else:
            answers = item.answers or []
            self._answers = []
            for answer_item in answers:
                self._answers.append(Post(api_response=answer_item))
            self._is_answer = False

        # 摘要标记
        if getattr(item, "BodyIsSummary", None):
            self._body_is_summary = True

        # 站点与链接
        if item.site is not None:
            self._post_site = item.site
        if item.link is not None:
            self._post_url = item.link

        # 分数与投票
        if item.score is not None:
            self._post_score = item.score
        if item.up_vote_count is not None:
            self._votes['upvotes'] = item.up_vote_count
        if item.down_vote_count is not None:
            self._votes['downvotes'] = item.down_vote_count

        # 所有者信息
        if item.owner is not None:
            if item.owner.display_name is not None:
                self._user_name = html.unescape(item.owner.display_name)
            if item.owner.link is not None:
                self._user_url = item.owner.link
            if item.owner.reputation is not None:
                self._owner_rep = item.owner.reputation

        # 帖子 ID：保持先 question_id 后 answer_id 的顺序
        if item.question_id is not None:
            self._post_id = item.question_id
        if item.answer_id is not None:
            self._post_id = item.answer_id

        # 编辑标记
        if item.edited is not None:
            self._edited = item.edited

    def _process_element_mapping(self, element_map: dict, data: dict, is_api_response: bool = False) -> None:
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
    def _unescape_title(title: str) -> str:
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
    def markdown(self):
        return self._markdown

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

    @title.setter
    def title(self, value):
        self._title = value

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
