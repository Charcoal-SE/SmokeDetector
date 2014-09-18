from db import Db
from mode import Mode

class Status(Mode):

	def validate(self, args):
		if len(args) != 2:
			raise ValueError('Usage: %s status' % args[0])

	def execute(self):
		db = Db()
		return db.get_doctype_counts().items()

	def output(self, results):
		bar = '=' * 40
		print '%s\nStatus:\n%s\n' % (bar, bar)

		if results:
			for doctype, count in results:
				print '%s: %s' % (doctype, count)
		else:
			print 'No data'

		print '\n%s' % bar