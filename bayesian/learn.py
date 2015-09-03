from db import Db
from mode import Mode
from words import list_to_dict
from words import text_to_list

class Learn(Mode):
	def validate(self, args):
		valid_args = False
		usage = 'Usage: {} learn <doc type> <file> <count>'.format(args[0])

		if len(args) == 5:
			doc_type = args[2]
			
			file_contents = None
			try:
				file_contents = open(args[3], 'r').read()
			except Exception as e:
				raise ValueError(usage + '\nUnable to read specified file "{}", the error message was: {}'.format(args[3], e))

			count = 0
			try:
				count = int(args[4])
			except:
				raise ValueError(usage + '\nEnter an integer value for the "count" parameter')			

			self.file_contents = file_contents
			self.count = count
			self.doc_type = doc_type

		else:
			raise ValueError(usage)				

	def execute(self):
		db = Db()
		l = text_to_list(self.file_contents)
		d = list_to_dict(l)
		db.update_word_counts(d, self.doc_type)
		db.update_doctype_count(self.count, self.doc_type)
		return self.count

	def output(self, _):
		print "Processed {} documents of type '{}'".format(self.count, self.doc_type)
