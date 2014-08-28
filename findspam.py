import re


class FindSpam:
  rules = [
   {'regex': "(?i)\\b(baba(ji)?|nike|vashikaran|sumer|kolcak|porn|molvi|judi bola|ituBola.com|lost lover|11s)\\b", 'all': True,
    'sites': [], 'reason': "Bad keyword detected"},
   {'regex': "\\+\\d{10}|\\+?\\d{2}[\\s\\-]?\\d{8,1o}", 'all': True,
    'sites': ["patents.stackexchange.com"], 'reason': "Phone number detected"},
   {'regex': "(?i)\\b(nigg?a|nigger|asshole|crap|fag|fuck(ing?)?|idiot|shit|whore)s?\\b", 'all': True,
    'sites': [], 'reason': "Offensive title detected",'insensitive':True},
   {'regex': "^(?=.*[A-Z])[^a-z]*$", 'all': True, 'sites': [], 'reason': "All-caps title"}
  ]

  @staticmethod
  def testpost(title, site):
    result = [];
    for rule in FindSpam.rules:
      if rule['all'] != (site in rule['sites']):
        if re.compile(rule['regex']).search(title):
          result.append(rule['reason'])
    return result
