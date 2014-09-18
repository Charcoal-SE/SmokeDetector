import sqlite3
import os

'''
create table word(word, doctype, count);
create table doctype_count(doctype, count);

create index i1 on word(word, doctype);

delete from word;
update ad_count set count = 0;

'''

class Db:
	def __init__(self):
                dir = os.path.dirname(__file__)
                
		self.conn = sqlite3.connect(os.path.join(dir, './bayes.db'))

	def reset(self):
		c = self.conn.cursor()
		try:
			c.execute('delete from word')
			c.execute('delete from doctype_count')

		finally:
			c.close()
			self.conn.commit()

	def update_word_count(self, c, doctype, word, num_to_add_to_count):
		c.execute('select count from word where doctype=? and word=?', (doctype, word))
		r = c.fetchone()
		if r:
			c.execute('update word set count=? where doctype=? and word=?', (r[0] + num_to_add_to_count, doctype, word))
		else:
			c.execute('insert into word (doctype, word, count) values (?,?,?)', (doctype, word, num_to_add_to_count))

	def update_word_counts(self, d, doctype):
		c = self.conn.cursor()
		try:
			for word, count in d.items():
				self.update_word_count(c, doctype, word, count)
		finally:
			c.close()
			self.conn.commit()

	def get_doctype_counts(self):
		counts = {}
		c = self.conn.cursor()
		try:
			for row in c.execute('select doctype, count from doctype_count'):
				counts[row[0]] = row[1]

			return counts

		finally:
			c.close()
			self.conn.commit()
		
	def get_word_count(self, doctype, word):
		c = self.conn.cursor()
		try:
			c.execute('select count from word where doctype=? and word=?', (doctype, word))
			r = c.fetchone()
			if r:
				return r[0]
			else:
				return 0

		finally:
			c.close()
			self.conn.commit()

	def get_words_count(self, doctype):
		c = self.conn.cursor()
		try:
			c.execute('select sum(count) from word where doctype=?', (doctype, ))
			r = c.fetchone()
			if r:
				return r[0]
			else:
				return 0

		finally:
			c.close()
			self.conn.commit()

	def update_doctype_count(self, num_new_ads, doctype):
		c = self.conn.cursor()
		try:
			counts = self.get_doctype_counts()
			if counts.has_key(doctype):
				current_count = counts[doctype]
			else:
				current_count = 0
			
			if current_count:
				c.execute('update doctype_count set count=? where doctype=?', (current_count + num_new_ads, doctype))
			else:
				c.execute('insert into doctype_count (doctype, count) values (?, ?)', (doctype, num_new_ads))

		finally:
			c.close()
			self.conn.commit()

