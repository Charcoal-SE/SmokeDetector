import re
import phonenumbers

class FindSpam:
  rules = [
   {'regex': "(?i)\\b(baba(ji)?|nike|vashi?k[ae]r[ae]n|sumer|kolcak|porn|molvi|judi bola|ituBola.com|lost lover|11s|acai|skin care|me2.do|black magic|bam2u)\\b", 'all': True,
    'sites': [], 'reason': "Bad keyword detected"},
   {'regex': "(?i)\\b(weight loss)\\b", 'all': True,
    'sites': ["fitness.stackexchange.com"], 'reason': "Bad keyword detected"},
   {'regex': "\\d(?:_*\\d){9}|\\+?\\d_*\\d[\\s\\-]?(?:_*\\d){8,10}", 'all': True,
    'sites': ["patents.stackexchange.com"], 'reason': "Phone number detected", 'validation_method': 'checkphonenumbers'},
   {'regex': "(?i)\\b(nigg?(a|er)|asshole|crap|fag|fuck(ing?)?|idiot|shit|whore)s?\\b|ಌ", 'all': True,
    'sites': [], 'reason': "Offensive title detected",'insensitive':True},
   {'regex': "^(?=.*[A-Z])[^a-z]*$", 'all': True, 'sites': [], 'reason': "All-caps title"}
  ]

  @staticmethod
  def testpost(title, site):
    result = [];
    for rule in FindSpam.rules:
      if rule['all'] != (site in rule['sites']):
        matched = re.compile(rule['regex']).findall(title)
        if matched:
          try:
            if getattr(FindSpam, "%s" % rule['validation_method'])(matched):
              result.append(rule['reason'])
          except KeyError:        # There is no special logic for this rule
            result.append(rule['reason'])
    return result

  @staticmethod
  def checkphonenumbers(matched):
    for phone_number in matched:
      try:
        z = phonenumbers.parse(phone_number, "IN")
        if phonenumbers.is_possible_number(z) and phonenumbers.is_valid_number(z):
          print "Possible %s, Valid %s, Explain: %s" % (phonenumbers.is_possible_number(z), phonenumbers.is_valid_number(z), z)
          return True
      except phonenumbers.phonenumberutil.NumberParseException:
        pass
    return False
