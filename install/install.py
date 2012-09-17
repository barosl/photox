#!/usr/bin/env python

import sys
sys.path.append('..')
from photox import fb_query, fb_acc_tok_for_app, cfg, VERIFY_TOKEN
sys.path.remove('..')
import urllib, urllib2
import os
import json

def fb_real_time_list(acc_tok):
	return fb_query('%s/subscriptions' % cfg['app_id'], acc_tok, True)

def fb_real_time_add(fields, cb_url, acc_tok):
	args = {'object': 'user', 'fields': fields, 'callback_url': cb_url, 'verify_token': VERIFY_TOKEN}
	data = urllib2.urlopen('https://graph.facebook.com/%s/subscriptions?access_token=%s' % (cfg['app_id'], acc_tok), data=urllib.urlencode(args)).read()
	return json.loads(data)

def on_real_time():
	acc_tok = fb_acc_tok_for_app()

	fb_real_time_add('feed', cfg['app_url']+'cb/', acc_tok)

	res = fb_real_time_list(acc_tok)
	for row in res: print row

def on_db():
	os.system('sqlite3 ../photox.db < photox.sql')

if __name__ == '__main__':
	print '* Subscribing to real-time updates...'
	on_real_time()

	print '* Installing database schemas...'
	on_db()
