import re
class FindSpam:
  @staticmethod
  def testtitle(title):
    result = []
    p = re.compile('\d{10}')
    m = p.match(title)
    if 'vashikaran' in title or 'baba' in title or p:
      result.append('Matched keyword')
      # magic if matches word
    elif title.upper() == title:
      result.append('All caps title')
      # magic if all caps
    return result
