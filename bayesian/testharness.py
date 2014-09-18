from __future__ import division
import sys
import os
from classify import Classify
from db import Db

classifier = Classify()

def is_doctype_valid(doctype):
	return Db().get_words_count(doctype) > 0

def check_file(f):
	results = []
	for line in open(f, 'r').readlines():
		try:
			classifier.set_text(line)
			results += [classifier.execute()]
		except ValueError:
			pass
	
	return results

def check_dir(d):
	results = []
	for f in os.listdir(d):
		if f.endswith(".js"):
			results += check_file(os.path.join(d,f))

	return results

def show_results(results):
	result_count = len(results)
	if result_count:
		print 'Tested with %s document%s' % (result_count, '' if result_count == 1 else 's')
		print 'Result was %1.2f (0 = %s, 1 = %s)' % (sum(results) / result_count, doctype_other, doctype_expected)
	else :
		print 'No documents found'

if __name__ == '__main__':
	usage = 'Usage: %s <file> <expected doctype> <other doctype>' % sys.argv[0]

	if len(sys.argv) != 4:
		raise ValueError(usage)

	input_file = sys.argv[1]
	doctype_expected = sys.argv[2]
	doctype_other = sys.argv[3]

	classifier.set_doctypes(doctype_expected, doctype_other)

	results = None
	if os.path.isfile(input_file):
		results = check_file(input_file)
	elif os.path.isdir(input_file):	
		results = check_dir(input_file)
	else:
		raise ValueError("Unable to find file/directory '%s'\n%s" % (input_file, usage))

	show_results(results)
