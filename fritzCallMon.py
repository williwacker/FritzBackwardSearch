#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import logging
import os
import socket
import sys
import threading
import time
from queue import Queue

from fritzconnection import FritzConnection

from fritzBackwardSearch import FritzBackwardSearch
from fritzBot import FritzBot
from fritzCallsDuringAbsense import FritzCallsDuringAbsense

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
	- Message is received in runFritzCallsDuringAbsense()
		- if incoming call has't been accepted a telegram message with the callers name, number and phonemessage will be sent
	- A telegram BOT gets started for retrieving the phone messages, and doing backward search 
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
		# initialize FB connection
		if self.prefs['password'] == '':
			logger.error('No password given')
			exit(1)
		self.connection = FritzConnection(
			address=self.prefs['fritz_ip_address'],
			port=self.prefs['fritz_tcp_port'],
			user=self.prefs['fritz_username'],
			password=self.prefs['password'])
		self.fb_queue = Queue()  # Meldungs-Übergabe von runFritzboxCallMonitor() an runFritzBackwardSearch()
		self.fb_absense_queue = Queue()

		self.startFritzboxCallMonitor()
		self.FBS = FritzBackwardSearch()
		self.FCDA = FritzCallsDuringAbsense(self.connection, self.prefs)

#		self.FCDA.get_unresolved()

	def __init_logging__(self):
		numeric_level = getattr(logging, self.prefs['loglevel'].upper(), None)
		if not isinstance(numeric_level, int):
			raise ValueError('Invalid log level: %s' % self.prefs['loglevel'])
		logging.basicConfig(
			filename=self.prefs['logfile'],
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

		worker3 = threading.Thread(target=self.runFritzCallsDuringAbsense, name="runFritzCallsDuringAbsense")
		worker3.setDaemon(True)
		worker3.start()

		worker4 = threading.Thread(target=self.runFritzBot, name="runFritzBot")
		worker4.setDaemon(True)
		worker4.start()

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
					self.fb_absense_queue.put(ln)
				else:
					logger.info("The connection to the Fritzbox call monitor has been stopped!")
					self.fb_queue.put("CONNECTION_LOST")
					break   # back to the Socket-Connect-Loop

	# ###########################################################
	# Running as Thread.
	# Make connection to Fritzbox, do backwardsearch for callers number
	# ###########################################################
	def runFritzBackwardSearch(self):
		while True:
			msgtxt = self.fb_queue.get()
			if not (msgtxt == "CONNECTION_LOST" or msgtxt == "REFRESH"):
#				logger.info(msgtxt)
				msg = msgtxt.decode().split(';')
				if msg[1] == "RING":
					self.FBS.runSearch(s=msg[3])
				if msg[1] == "CALL":
					self.FBS.runSearch(s=msg[5])

	# ###########################################################
	# Running as Thread.
	# Make connection to Fritzbox and retrieve the answering machine message, and inform via Telegram
	# ###########################################################
	def runFritzCallsDuringAbsense(self):
		call_history = {}
		while True:
			msgtxt = self.fb_absense_queue.get()
			logger.info(msgtxt)
			if not (msgtxt == "CONNECTION_LOST" or msgtxt == "REFRESH"):
				type, id, caller, port = msgtxt.decode().split(';')[1:5]
				if type == "RING":
					call_history[id] = caller
					logger.info(call_history)
				elif type == "CONNECT" and port != "40":
					if id in call_history:
						del call_history[id]
					logger.info(call_history)
				elif type == "DISCONNECT":
					logger.info(call_history)
					if id in call_history:
						logger.info('calling FCDA '+call_history[id])
						self.FCDA.get_unresolved(call_history[id])
						del call_history[id]

	# ###########################################################
	# Running as Thread.
	# Start fritzBot
	# ###########################################################

	def runFritzBot(self):
		FritzBot().startBot()

	# ###########################################################
	# Start fritzCallMon Server
	# ###########################################################
	def runServer(self):
		self.srvSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.srvSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self.srvSock.bind(("", int(self.prefs['callmon_server_socket'])))
			self.srvSock.listen(5)
		except Exception as e:
			logger.error("Cannot open socket {} : {}".format(self.prefs['callmon_server_socket'], e))
			return

		while True:
			try:
				self.srvSock.listen(5)
				time.sleep(0.01)
			except:
				logger.info('fritzCallMon has been stopped')
				sys.exit()


if __name__ == '__main__':
	CallMonServer().runServer()
