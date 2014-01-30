import re
class FindSpam:
  @staticmethod
  def testtitle(title):
    p = re.compile('\d{10}')
    m = p.match(title)
    if 'vashikaran' in title or 'baba' in title or p:
      # magic if matches word
    elif title.upper() == title:
      # magic if all caps
