#!/usr/bin/python

import os, sys, argparse, subprocess, time, sqlite3
import signal

HASH_MAP_SIZE = 2048
p = None
STORE_EXTRA_INFO=False
HASH_ADDRESS=False

class LapEntry(object):
   def __init__(self, epoch, channel, lap, errors, clk100ns, clk1, signal, noise, snr):
      self.epoch = epoch
      self.channel = channel
      if (HASH_ADDRESS):
         self.addr = buffer(md5.new(lap).digest())
      else:
         self.addr = buffer(lap)
      self.errors = errors
      self.clk100ns = clk100ns
      self.clk1 = clk1
      self.signal = signal
      self.noise = noise
      self.snr = snr
      self.lastEpoch = epoch

   def __eq__(self, other):
      try:
         return (self.addr == other.addr)#(''.join('{:02x}'.format(ord(x)) for x in str(self.addr)) == ''.join('{:02x}'.format(ord(x)) for x in str(other.addr)))
      except:
         return False

   def isNextValid(self, nextLapEntry):
      try:
         if (self.addr == nextLapEntry.addr and self.clk100ns < nextLapEntry.clk100ns and self.clk1 < nextLapEntry.clk1):
            return True
         else:
            return False
      except:
         print 'Error comparing next entry'
         return False
   
   def __repr__(self):
      return 'AddrHash %s, errors = %d, ch = %d, signal = %d' % (''.join('{:02x}'.format(ord(x)) for x in str(self.addr)), self.errors, self.channel, self.snr)

def textToLapEntry(line):
   s = line.replace('= ', '=').split(' ')
   if len(s) != 9:
      print 'Error parsing line ' + line
      return None
   #TODO try:
   time = int(s[0].split('=')[1])
   channel = int(s[1].split('=')[1])
   lap = s[2].split('=')[1].decode('hex')
   errors = int(s[3].split('=')[1])
   clk100ns = int(s[4].split('=')[1])
   clk1 = int(s[5].split('=')[1])
   signal = int(s[6].split('=')[1])
   noise = int(s[7].split('=')[1])
   snr = int(s[8].split('=')[1])
   return LapEntry(time, channel, lap, errors, clk100ns, clk1, signal, noise, snr)

def isValidEntry(entry, previousEntry):
   if (entry.errors == 0):
      return True
   if (previousEntry != None):
      return True
   return False

def updateHashAndCommitValidEntries(hashMap, entry, dB):
   hashIdx = hashFunction(entry)
   previousEntry = None
   valid = False
   if (hashMap[hashIdx] != None):
      (previousEntry, previousValid) = hashMap[hashIdx]
      print '\tPrevious found'
      #if previous entry in hashMap is a match and not too old we consider
      #them to be the same
      if not (previousEntry == entry):
         previousEntry = None
         print '\t\tEntries do not match'
      elif (entry.epoch - previousEntry.epoch) > 15:
         previousEntry = None
         print '\t\tPrevious entry stale'
   
   if (previousEntry != None or entry.errors == 0):
      valid = True
      print '\tValid entry'
      if (previousEntry != None and previousValid == False):
         print '\t\tAdding previously invalid entry'
         dB.addEntry(previousEntry)
      dB.addEntry(entry)
      
   hashMap[hashIdx] = (entry, valid)

def hashFunction(lapEntry):
   return hash(lapEntry.addr) % HASH_MAP_SIZE

def preexec_function():
   # Ignore the SIGINT signal by setting the handler to the standard
   # signal handler SIG_IGN.
   signal.signal(signal.SIGINT, signal.SIG_IGN)

def runUbertoothRx(dB, maxErrors):
   global p
   hashMap = [None] * HASH_MAP_SIZE
   p = subprocess.Popen(['unbuffer', 'ubertooth-rx', '-e', str(maxErrors), '-s'], stdout=subprocess.PIPE, preexec_fn = preexec_function)
   while p.poll() is None:
      entry = p.stdout.readline()
      #print entry
      le = textToLapEntry(entry)
      if (le == None):
         continue
      print le
      updateHashAndCommitValidEntries(hashMap, le, dB)
      dB.commitTimer()
   dB.commitOutstandingEntries()

class lapDb(object):
   FLUSH_INTERVAL = 10
   def __init__(self, dBFile):
      self.lastFlush = None
      self.conn = sqlite3.connect(dBFile)
      self.cursor = self.conn.cursor()
      #check to see if table is created
      try:
         self.cursor.execute('SELECT * FROM lapTable LIMIT 1')
      except Exception as e:
         self.cursor.execute('CREATE TABLE lapTable(addrHash BLOB NOT NULL, epoch INT NOT NULL, errors INT NOT NULL, snr INT NOT NULL, extrainfo STRING)')
         self.conn.commit()
      
   def addSingleEntry(self, entry):
      self.addEntryIfValid(entry)
      self.commitOutstandingEntries()
      
   def addEntry(self, entry):
      self.cursor.execute('INSERT INTO lapTable VALUES(?, ?, ?, ?, ?)', (entry.addr, entry.epoch, entry.errors, entry.snr, None  ))
      if (self.lastFlush == None):
         self.lastFlush = time.time()
      
   def commitOutstandingEntries(self):
      print 'Flushing database entries'
      self.conn.commit()
      self.lastFlush = None
      
   def commitTimer(self):
      if (self.lastFlush != None):
         if (time.time() > self.lastFlush + lapDb.FLUSH_INTERVAL):
            self.commitOutstandingEntries()

def signal_handler(signal, frame):
   print('You pressed Ctrl+C!')
   if (p != None):
      p.terminate()
   else:
      sys.exit(0)

def main():
   signal.signal(signal.SIGINT, signal_handler)
   parser = argparse.ArgumentParser(description='Log bluetooth LAPs to sqlite dB using ubertooth-rx')
   parser.add_argument('-d', '--database-folder', help='SQLite dB file to store data in', default='./')
   parser.add_argument('-e', '--max-errors', help='Max number of errors in decoded packet for ubertooth', default=3)
   
   config = parser.parse_args()
   
   num = 0
   while True:
      dbpath = '%s/bt-db_%04d.sqlite' % (config.database_folder, num)
      num += 1
      if (not os.path.isfile(dbpath)):
         break
      
   print 'using db ' + dbpath
      
   dB = lapDb(dbpath)
   
   runUbertoothRx(dB, config.max_errors)


if __name__ == "__main__":
    main()
