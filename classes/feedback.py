import itertools
import regex

from tasks import Tasks
import metasmoke


class Feedback:
    TRUE_POSITIVE = "tp"
    FALSE_POSITIVE = "fp"
    NAA = "naa"

    def __init__(self, feedback, blacklist=False, always_silent=False):
        self.blacklist = blacklist
        self.always_silent = always_silent

        self._type = feedback + ("u" if blacklist else "") + ("-" if always_silent else "")

    def send(self, url, msg):
        Feedback.send_custom(self._type, url, msg)

    @staticmethod
    def send_custom(type, url, msg):
        Tasks.do(metasmoke.Metasmoke.send_feedback_for_post, url, type, msg.owner.name, msg.owner.id, msg._client.host)


TRUE_FEEDBACKS = {
    "true": Feedback(Feedback.TRUE_POSITIVE, blacklist=False, always_silent=False),
    "tp": Feedback(Feedback.TRUE_POSITIVE, blacklist=False, always_silent=False),
    "trueu": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=False),
    "tpu": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=False),

    "k": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "spam": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "rude": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "abuse": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "abusive": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "offensive": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "r/a": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),

    "v": Feedback(Feedback.TRUE_POSITIVE, blacklist=False, always_silent=True),
    "vand": Feedback(Feedback.TRUE_POSITIVE, blacklist=False, always_silent=True),
    "vandalism": Feedback(Feedback.TRUE_POSITIVE, blacklist=False, always_silent=False)
}

FALSE_FEEDBACKS = {
    "false": Feedback(Feedback.FALSE_POSITIVE, blacklist=False, always_silent=False),
    "fp": Feedback(Feedback.FALSE_POSITIVE, blacklist=False, always_silent=False),
    "falseu": Feedback(Feedback.FALSE_POSITIVE, blacklist=True, always_silent=False),
    "fpu": Feedback(Feedback.FALSE_POSITIVE, blacklist=True, always_silent=False),

    "f": Feedback(Feedback.FALSE_POSITIVE, blacklist=False, always_silent=True),
    "notspam": Feedback(Feedback.FALSE_POSITIVE, blacklist=False, always_silent=True),
}

NAA_FEEDBACKS = {
    "naa": Feedback(Feedback.NAA, blacklist=False, always_silent=False),
    "n": Feedback(Feedback.NAA, blacklist=False, always_silent=True),
}

FEEDBACK_REGEX = regex.compile(r"(?i)\b({})\b".format("|".join(itertools.chain(TRUE_FEEDBACKS.keys(),
                                                                               FALSE_FEEDBACKS.keys(),
                                                                               NAA_FEEDBACKS.keys()))))
