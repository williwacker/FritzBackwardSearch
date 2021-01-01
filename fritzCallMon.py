#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import json
import logging
import os
import select
import socket
import sys
import threading
import time
from queue import Queue

from fritzBackwardSearch import FritzBackwardSearch

"""

Fritzbox Call Monitor

Adopted from here: http://dede67.bplaced.net/PhythonScripte/callmon/callmon.html

 - The thread (worker1) receives the CallMonitor messages from the Fritzbox and writes them to the fb_queue.

 - The thread (worker2) receives from the fb_queue and calls the FritzBackwardSearch class, which updates the Fritzbox phonebook

 - The message from the Fritzbox has the following flow:
   - Message is received in thread runFritzboxCallMonitor()
   - Message gets passed via self.fb_queue to the thread runFritzBackwardSearch()
   - Message is received in runFritzBackwardSearch()
	 - split message
	 - call of the FritzBackwardSearch instance with passing the caller number


08.04.2016 0.2.0 WK  Added fritzCallMon.py, made fritzBackwardSearch module callable

"""

logger = logging.getLogger(__name__)


class CallMonServer():

	def __init__(self):
		fname = os.path.join(os.path.dirname(__file__), 'fritzBackwardSearch.ini')
		if os.path.isfile(fname):
			self.prefs = self.__read_configuration__(fname)
		else:
			logger.error('{} not found'.format(fname))
			exit(1)
		self.__init_logging__()
		self.fb_queue = Queue()  # Meldungs-Übergabe von runFritzboxCallMonitor() an runFritzBackwardSearch()

		self.startFritzboxCallMonitor()
		self.FBS = FritzBackwardSearch()

	def __init_logging__(self):
		numeric_level = getattr(logging, self.prefs['loglevel'].upper(), None)
		if not isinstance(numeric_level, int):
			raise ValueError('Invalid log level: %s' % loglevel)
		logging.basicConfig(
			filename=self.prefs['logfile_1'],
			level=numeric_level,
			format=('%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(message)s'),
			datefmt='%Y-%m-%d %H:%M:%S',
		)

	def __read_configuration__(self, filename):  # read configuration from the configuration file and prepare a preferences dict
		cfg = configparser.ConfigParser()
		cfg.read(filename)
		preferences = {}
		for name, value in cfg.items('DEFAULT'):
			if name == 'status_to_terminal':
				preferences[name] = cfg.getboolean('DEFAULT', 'status_to_terminal')
			else:
				preferences[name] = value
		return preferences

	# ###########################################################
	# Empfangs-Thread und Verarbeitungs-Thread aufsetzen.
	# Funktion verändert:
	#   startet zwei Threads
	# ###########################################################
	def startFritzboxCallMonitor(self):
		worker1 = threading.Thread(target=self.runFritzboxCallMonitor, name="runFritzboxCallMonitor")
		worker1.setDaemon(True)
		worker1.start()

		worker2 = threading.Thread(target=self.runFritzBackwardSearch, name="runFritzBackwardSearch")
		worker2.setDaemon(True)
		worker2.start()

	# ###########################################################
	# Running as Thread.
	# Make connection to Fritzbox, receive messages from the Fritzbox and pass over to queue
	# ###########################################################
	def runFritzboxCallMonitor(self):
		while True:  # Socket-Connect-Loop
			self.recSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				self.recSock.connect((self.prefs['fritz_ip_address'], int(self.prefs['fritz_callmon_port'])))
			except socket.herror as e:
				logger.error("%s %s" % ("socket.herror", str(e)))
				time.sleep(10)
				continue
			except socket.gaierror as e:
				logger.error("%s %s" % ("socket.gaierror", str(e)))
				time.sleep(10)
				continue
			except socket.timeout as e:
				logger.error("%s %s" % ("socket.timeout", str(e)))
				continue
			except socket.error as e:
				logger.error("%s %s" % ("socket.error", str(e)))
				time.sleep(10)
				continue
			except Exception as e:
				logger.error(str(e))
				time.sleep(10)
				continue
			logger.info("The connection to the Fritzbox call monitor has been established!")

			while True:  # Socket-Receive-Loop
				try:
					ln = self.recSock.recv(256).strip()
				except:
					ln = ""

				if ln != "":
					self.fb_queue.put(ln)
				else:
					logger.info("The connection to the Fritzbox call monitor has been stopped!")
					self.fb_queue.put("CONNECTION_LOST")
					break   # back to the Socket-Connect-Loop

	# ###########################################################
	# Running as Thread.
	# ###########################################################
	def runFritzBackwardSearch(self):
		while True:
			msgtxt = self.fb_queue.get()
			if not (msgtxt == "CONNECTION_LOST" or msgtxt == "REFRESH"):
				logger.info(msgtxt)
				msg = msgtxt.decode().split(';')
				if msg[1] == "RING":
					self.FBS.runSearch(s=msg[3])
				if msg[1] == "CALL":
					self.FBS.runSearch(s=msg[5])

	def runServer(self):
		self.srvSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.srvSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self.srvSock.bind(("", int(self.prefs['callmon_server_socket'])))
			self.srvSock.listen(5)
		except Exception as e:
			logger.error("%s Cannot open socket %d:" % (int(self.prefs['callmon_server_socket'])), e)
			return

		while True:
			try:
				None
			except:
				logger.info('fritzCallMon has been stopped')
				sys.exit()


if __name__ == '__main__':
	myServer = CallMonServer()
	myServer.runServer()
