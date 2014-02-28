import re
import phonenumbers


class FindSpam:
  rules = [
   {'regex': "(?i)\\b(baba(ji)?|nike|vashikaran|here is|porn)\\b", 'all': True,
    'sites': [], 'reason': "Bad keyword detected"},
   {'regex': "\\+\\d{10}|\\+?\\d{2}[\\s\\-]?\\d{8,11}", 'all': True, 
    'sites': ["patents.stackexchange.com"], 'reason': "Phone number detected", 'validation_method': 'phonenumbers'},
   {'regex': "(?i)\\b([Nn]igga|[Nn]igger|niga|[Aa]sshole|crap|fag|[Ff]uck|idiot|[Ss]hit|[Ww]hore)s?\\b", 'all': True,
    'sites': [], 'reason': "Offensive title detected",'insensitive':True},
   {'regex': "^[A-Z0-9\\(\\)\\.\\-\\?\\s'\"]*$", 'all': True, 'sites': [], 'reason': "All-caps title"}
  ]

  @staticmethod
  def testpost(title, site):
    result = [];
    for rule in FindSpam.rules:
      if rule['all'] != (site in rule['sites']):
        if re.compile(rule['regex']).search(title):
          try:
            if getattr(TestClass, "%s" % rule['validation_method'])(title):
              result.append(rule['reason'])
          except KeyError:        # There is no special logic for this rule
            result.append(rule['reason'])
    return result

  @staticmethod
  def testtitle(title):
    regexes=["\\b(baba(ji)?|vashikaran|fashion|here is|porn)\\b","\\+\\d{10}","\\+?\\d{2}\\s?\\d{8}","\\b(asshole|crap|fag|fuck|idiot|shit|whore)s?\\b"]
    result = []
    p = [not not re.compile(s).search(title) for s in regexes]
    if 'vashikaran' in title or 'baba' in title or True in p:
      result.append('Possible spam')
      # magic if matches word
    return result

  @staticmethod
  def phonenumbers(msg):
    try:
      z = phonenumbers.parse(msg, "IN")
      if phonenumbers.is_possible_number(z) and phonenumbers.is_valid_number(z):
        print "Possible %s, Valid %s, Expain: %s" % (phonenumbers.is_possible_number(z), phonenumbers.is_valid_number(z), z)
        return True
    except phonenumbers.phonenumberutil.NumberParseException:
      return False
