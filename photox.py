#!/usr/bin/env python

from flask import Flask, render_template, request, redirect, url_for, g
import urllib, urllib2
import cgi
import json
from cfg import cfg
import sqlite3

VERIFY_TOKEN = 'photox-vrfc'
DB_FILE = 'photox.db'

app = Flask(__name__)

def fb_query(path, acc_tok, has_data=False):
	data = urllib.urlopen('https://graph.facebook.com/%s?%s' % (path, urllib.urlencode(dict(access_token=acc_tok)))).read()
	res = json.loads(data)
	return res[u'data'] if has_data else res

def fb_acc_tok_for_code(code):
	args = {'client_id': cfg['app_id'], 'client_secret': cfg['app_secret'], 'code': code, 'redirect_uri': cfg['app_url']+'done/'}
	res = cgi.parse_qs(urllib.urlopen('https://graph.facebook.com/oauth/access_token?'+urllib.urlencode(args)).read())
	return res['access_token'][-1]

def fb_acc_tok_for_app():
	args = {'client_id': cfg['app_id'], 'client_secret': cfg['app_secret'], 'grant_type': 'client_credentials'}
	res = cgi.parse_qs(urllib.urlopen('https://graph.facebook.com/oauth/access_token?'+urllib.urlencode(args)).read())
	return res['access_token'][-1]

@app.before_request
def db_before_req():
	g.db = sqlite3.connect(DB_FILE)

@app.teardown_request
def db_teardown_req(exc):
	if hasattr(g, 'db'):
		g.db.close()

def db_query(query, args=(), one=False):
	cur = g.db.execute(query, args)
	res = [dict((cur.description[idx][0], val) for idx, val in enumerate(row)) for row in cur.fetchall()]
	return (res[0] if res else None) if one else res

@app.route('/')
def index():
	add_app_url = 'https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&scope=%s' % (cfg['app_id'], cfg['app_url']+'done/', 'user_photos,read_stream')
	return render_template('index.html', add_app_url=add_app_url)

@app.route('/done/')
def done():
	code = request.args.get('code')
	if code:
		acc_tok = fb_acc_tok_for_code(code)
		print '* acc_tok:', acc_tok

		res = fb_query('me', acc_tok)
		db_query('DELETE FROM users WHERE id=?', (res[u'id'],))
		db_query('INSERT INTO users(id, acc_tok, name, url) VALUES(?, ?, ?, ?)', (res[u'id'], acc_tok, res[u'name'], res[u'link']))
		g.db.commit()

#		res = fb_query('me/albums', acc_tok, True)
#		for row in res: print u'* %s / %s' % (row[u'name'], row[u'type'])

		return render_template('done.html')
	else:
		return redirect(url_for('index'))

@app.route('/cb/', methods=['GET', 'POST'])
def cb():
	if request.method == 'GET' and request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
		return request.args['hub.challenge']

	elif request.method == 'POST':
		tags = db_query('SELECT * FROM tags')

		for row in request.json['entry']:
			acc_tok = db_query('SELECT acc_tok FROM users WHERE id=?', (row[u'uid'],), True)[u'acc_tok']

			res = fb_query(row[u'id']+'/albums', acc_tok, True)
			row = [x for x in res if x[u'type'] == u'wall'][0]

			res = fb_query(row[u'id']+'/photos', acc_tok, True)
			for row in res:
				if db_query('SELECT * FROM img_visits WHERE id=?', (row[u'id'],), True): continue

				text = row[u'name']

				tag_id = -1
				for tag in tags:
					if tag[u'name'] in text:
						tag_id = tag[u'id']
						break

				if tag_id != -1:
					db_query('INSERT INTO imgs(id, img, thumb, text, ctime, url, user, tag, confirmed, added) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime(\'now\'))',
						(row[u'id'], row[u'source'], row[u'picture'], row[u'name'], row[u'created_time'], row[u'link'], row[u'from'][u'id'], tag_id, False))
					g.db.commit()

				db_query('INSERT INTO img_visits(id) VALUES(?)', (row[u'id'],))
				g.db.commit()

	return '!!'

@app.route('/admin/')
def admin():
	return render_template('admin.html')

@app.route('/admin/tags/', methods=['GET', 'POST'])
@app.route('/admin/tags/<int:tag_id>/del/', methods=['GET', 'POST'])
def tags(tag_id=None):
	if request.form.get('mode') == 'add':
		name = request.form.get('name')
		score = request.form.get('score')
		if not name or not score: return 'Invalid input'

		db_query('INSERT INTO tags(name, score) VALUES(?, ?)', (name, score))
		g.db.commit()

		return redirect(url_for('tags'))

	elif tag_id:
		db_query('DELETE FROM tags WHERE id=?', (tag_id,))
		g.db.commit()

		return redirect(url_for('tags'))

	tags = db_query('SELECT * FROM tags ORDER BY name')
	return render_template('tags.html', tags=tags)

@app.route('/admin/imgs/')
@app.route('/admin/imgs/<int:img_id>/<int:confirmed>/')
def imgs(img_id=None, confirmed=None):
	if confirmed is not None:
		db_query('UPDATE imgs SET confirmed=? WHERE id=?', (confirmed, img_id))
		g.db.commit()
		return '!!'

	imgs = db_query('SELECT *, users.name AS user_name, tags.name AS tag_name, users.url AS user_url, imgs.url AS img_url, imgs.id AS img_id FROM imgs JOIN users ON imgs.user = users.id JOIN tags ON imgs.tag = tags.id ORDER BY added DESC')
	return render_template('imgs.html', imgs=imgs)

@app.route('/admin/users/')
def users():
	users = db_query('SELECT \'https://graph.facebook.com/\' || users.id || \'/picture\' AS user_img, users.name AS user_name, SUM(score) AS sum_of_scores FROM imgs JOIN tags ON imgs.tag = tags.id JOIN users ON imgs.user = users.id WHERE confirmed = 1 GROUP BY user ORDER BY sum_of_scores DESC')
	return render_template('users.html', users=users)

if __name__ == '__main__':
	app.run(host='', port=1234, debug=True)
