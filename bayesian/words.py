import re
from collections import defaultdict

commonWords = ('the','be','to','of','and','a','in','that','have','it','is','im','are','was','for','on','with','he','as','you','do','at','this','but','his','by','from','they','we','say','her','she','or','an','will','my','one','all','would','there','their','what','so','up','out','if','about','who','get','which','go','me','when','make','can','like','time','just','him','know','take','person','into','year','your','some','could','them','see','other','than','then','now','look','only','come','its','over','think','also','back','after','use','two','how','our','way','even','because','any','these','us')

def cleanUpWord(word):
	word = word.lower()
	if (len(word) < 2):
		return None
	elif (word.isdigit()):
		return None
	elif (word in commonWords):
		return None
	
	return word

def list_to_dict(l):
	d = defaultdict(int)
	add_list_to_dict(l, d)
	return d

def add_list_to_dict(l, d):
	for word in l:
		d[word] += 1

def text_to_list(text):
	cleaned_words = map(cleanUpWord, re.split('\W+', text.strip()))
	return filter(lambda word : word and (len(word) > 0), cleaned_words)
