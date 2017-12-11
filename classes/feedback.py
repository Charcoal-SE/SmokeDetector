import threading
from metasmoke import Metasmoke


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
        threading.Thread(name="metasmoke feedback send on " + url,
                         target=Metasmoke.send_feedback_for_post,
                         args=(url, type, msg.owner.name, msg.owner.id, msg._client.host,)).start()


TRUE_FEEDBACKS = {
    "true": Feedback(Feedback.TRUE_POSITIVE, always_silent=False, blacklist=False),
    "tp": Feedback(Feedback.TRUE_POSITIVE, blacklist=False, always_silent=False),
    "trueu": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=False),
    "tpu": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=False),

    "k": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "spam": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "rude": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "abusive": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),
    "offensive": Feedback(Feedback.TRUE_POSITIVE, blacklist=True, always_silent=True),

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
