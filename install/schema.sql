CREATE TABLE users(id INTEGER PRIMARY KEY, acc_tok TEXT, name TEXT, url TEXT);
CREATE TABLE tags(id INTEGER PRIMARY KEY, name TEXT, score INTEGER);
CREATE TABLE imgs(id INTEGER PRIMARY KEY, img TEXT, thumb TEXT, text TEXT, ctime DATETIME, url TEXT, user INTEGER, tag INTEGER, confirmed BOOLEAN, added DATETIME);
CREATE TABLE img_visits(id INTEGER PRIMARY KEY);
