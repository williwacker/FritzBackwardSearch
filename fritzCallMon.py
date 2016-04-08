#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import select
import threading
import time
import sys
import os
import configparser
from queue import Queue
import json
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

__version__ = '0.2.0'

# ###########################################################
#
class CallMonServer():

	def __init__(self):
		fname = os.path.join(os.path.dirname(__file__),'fritzBackwardSearch.ini')
		if os.path.isfile(fname):
			self.prefs = self.__read_configuration__(fname)
		else:
			print('{} not found'.format(fname))
			exit(1)
		self.fb_queue=Queue() # Meldungs-Übergabe von runFritzboxCallMonitor() an runFritzBackwardSearch()

		self.startFritzboxCallMonitor() 
		self.FBS = FritzBackwardSearch()
    
	def __read_configuration__(self,filename): #read configuration from the configuration file and prepare a preferences dict
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
	def startFritzboxCallMonitor(self):
		worker1=threading.Thread(target=self.runFritzboxCallMonitor, name="runFritzboxCallMonitor")
		worker1.setDaemon(True)
		worker1.start()

		worker2=threading.Thread(target=self.runFritzBackwardSearch, name="runFritzBackwardSearch")
		worker2.setDaemon(True)
		worker2.start()

	# ###########################################################
	# Running as Thread.
	# Make connection to Fritzbox, receive messages from the Fritzbox and pass over to queue
	def runFritzboxCallMonitor(self):
		while True: # Socket-Connect-Loop
			self.recSock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				self.recSock.connect((self.prefs['fritz_ip_address'], int(self.prefs['fritz_callmon_port'])))
			except socket.herror as e:
				print("socket.herror", e)
				time.sleep(10)
				continue
			except socket.gaierror as e:
				print("socket.gaierror", e)
				time.sleep(10)
				continue
			except socket.timeout as e:
				print("socket.timeout", e)
				continue
			except socket.error as e:
				print("socket.error", e)
				time.sleep(10)
				continue
			except Exception as e:
				self.writeLog("Error: %s"%(str(e)),self.prefs['status_to_terminal'])
				time.sleep(10)
				continue
			self.writeLog("The connection to the Fritzbox call monitor has been established!",self.prefs['status_to_terminal'])

			while True: # Socket-Receive-Loop
				try:
					ln=self.recSock.recv(256).strip()
				except:
					ln=""

				if ln!="":
					self.fb_queue.put(ln)
				else:
					self.writeLog("The connection to the Fritzbox call monitor has been stopped!",self.prefs['status_to_terminal'])
					self.fb_queue.put("CONNECTION_LOST")
					break   # back to the Socket-Connect-Loop

	# ###########################################################
	# Running as Thread.
	def runFritzBackwardSearch(self):
		while True:
			msgtxt=self.fb_queue.get()
			if not (msgtxt=="CONNECTION_LOST" or msgtxt=="REFRESH"):
				print(msgtxt)
				msg = msgtxt.decode().split(';')
				if msg[1] == "RING":
					self.FBS.runSearch(s=msg[3])
				if msg[1] == "CALL":
					self.FBS.runSearch(s=msg[5])


	def runServer(self):
		self.srvSock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.srvSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self.srvSock.bind(("", int(self.prefs['callmon_server_socket'])))
			self.srvSock.listen(5)
		except Exception as e:
			tm=time.strftime("%Y.%m.%d-%H:%M:%S")
			self.writeLog(("%s Cannot open socket %d:"%(tm, self.prefs['callmon_server_socket']), e),True)
			return

		while True:
			if os.path.isfile(self.prefs['process_stop_file']):
				None
			else:
				self.writeLog('fritzCallMon has been stopped',self.prefs['status_to_terminal'])
				break
				
	def writeLog(self,logString, print_to_console=False):
		if self.prefs['logfile'] != '':
			logFile_out = open(self.prefs['logfile'],'a')
			logFile_out.write('{} {}{}'.format(time.strftime("%Y-%m-%d %H:%M:%S"),logString,'\n'))
			logFile_out.close()
		if print_to_console:
			print(logString)				


if __name__=='__main__':
	myServer=CallMonServer()
	myServer.runServer()

