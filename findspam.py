import re


class FindSpam:
  @staticmethod
  def testtitle(title):
    regexes=["\\b(vs?|baba(ji?)|live|watch|free|cheap|online|download|nike|training|dress|fashion|buy|here is|porn)\\b","\\+\\d{10}","\\+?\\d{2}\\s?\\d{8}","\\b(asshole|crap|damn|fag|fuck|idiot|shit|whore)s?\\b"]
    result = []
    p = [not not re.compile(s).search(title) for s in regexes]
    if 'vashikaran' in title or 'baba' in title or True in p:
      result.append('Matched keyword')
      # magic if matches word
    elif title.upper() == title:
      result.append('All caps title')
      # magic if all caps
    return result
