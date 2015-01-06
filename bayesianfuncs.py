from bayesian.classify import Classify
from bayesian.learn import Learn
from parsing import fetch_title_from_msg_content


def bayesian_score(title):
    try:
        c = Classify()
        c.validate(["", "", title, "good", "bad"])
        output = c.execute()
        return output
    except:
        return 0.1


def bayesian_learn_title(message_content, doctype):
    try:
        bayesian_learn = Learn()
        title = fetch_title_from_msg_content(message_content)
        if title is None:
            return False
        bayesian_learn.file_contents = title
        bayesian_learn.count = 1
        bayesian_learn.doc_type = doctype
        bayesian_learn.execute()
        return True
    except:
        return False