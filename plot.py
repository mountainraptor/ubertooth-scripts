#!/usr/bin/python

import os, sys, argparse, subprocess, time, sqlite3

INTERVAL = 60

conn = sqlite3.connect('bt-laps.sqlite')

cursor = conn.cursor()

r = cursor.execute('SELECT MIN(epoch) FROM lapTable;')
minepoch = r.fetchone()[0]
r = cursor.execute('SELECT MAX(epoch) FROM lapTable;')
maxepoch = r.fetchone()[0]

print minepoch, maxepoch

curepoch = minepoch - (minepoch % INTERVAL)

print curepoch


for i in range(curepoch, maxepoch + INTERVAL, INTERVAL):
	r = cursor.execute('SELECT COUNT FROM lapTable WHERE epoch >= ? AND epoch < ?', (curepoch, curepoch + INTERVAL))
	print curepoch, r.fetchone()
