#!/usr/bin/env python
# -*- coding: utf-8 -*-

import http.client
import logging
import os
import re
import urllib
from datetime import datetime

import requests
import urllib3
import xmltodict
import speech_recognition as sr

logger = logging.getLogger(__name__)


class FritzCallsDuringAbsense():

	def __init__(self, connection, prefs):
		self.prefs = prefs
		self.areaCode = (connection.call_action('X_VoIP', 'GetVoIPCommonAreaCode'))['NewVoIPAreaCode']
		self.http = urllib3.PoolManager()
		self.callURLList = connection.call_action('X_AVM-DE_OnTel', 'GetCallList')
		entries = re.search("sid=(.*)$", self.callURLList['NewCallListURL'])
		self.sid = entries.group(0)
		self.unresolved_list = []

	def get_sid(self):
		return self.sid

	def get_fullCode(self, code):
		if code == None or code[:1] == '0':
			return code
		else:
			return self.areaCode + code

	def set_unresolved(self, caller):
		self.unresolved_list.append(caller)

	def get_unresolved(self):
		if self.unresolved_list:
			logger.info(self.unresolved_list)
			for caller in list(self.unresolved_list):
				response = self.http.request('GET', self.callURLList['NewCallListURL'] + '&max=50')
				try:
					calldict = xmltodict.parse(response.data)
				except Exception as e:
					logger.error(str(e))
					logger.error(response.data)
				if response.status != 200:
					logger.error('response status='+str(response.status))
					logger.error(calldict)
				else:
					if 'root' in calldict:
						if 'Call' in calldict['root']:
							self.process_notification(calldict['root']['Call'], caller)
							self.unresolved_list.remove(caller)
					else:
						logger.error(calldict)

	def process_notification(self, calldict, caller):
		for callentry in calldict:
			logger.info(callentry)
			if callentry['Caller'] == caller:
				logger.info("callentry['Type']="+callentry['Type'])
				if callentry['Type'] in ('1', '2'):  # missed incoming calls
					logger.info("callentry['Caller']="+callentry['Caller'])
					callentry['CalledNumber'] = self.get_fullCode(callentry['CalledNumber'])
					callentry['Caller'] = self.get_fullCode(callentry['Caller'])
					phone_message = self.get_phone_message(callentry)  # if callentry['Port'] in ('40') else ""
					logger.info("phone_message="+str(phone_message))
#                    self.telegram(self.get_message(callentry, phone_message))
					self.pushover(self.get_message(callentry, phone_message))
				return

	def get_phone_message(self, callentry):
		# list of phone messages
		phone_message = ""
		# if it is a phone message
		if callentry['Path'] is not None:
			# build download link for phone message
			entries = re.search("(path=)(.*)", callentry['Path'])
			dlpath = entries.group(2)
			dlfile = dlpath.split("/")
			response = self.http.request(
				'GET', '{}/lua/photo.lua?{}&myabfile={}'.format(self.prefs['fritz_ip_address'], self.get_sid(), dlpath))
			wave = open(os.path.join(self.prefs['phone_msg_dir'], '{}.wav'.format(dlfile[-1])), 'wb')
			wave.write(response.data)
			wave.close()
			phone_message = self.speech_to_text(wave.name)
		return phone_message

#    def telegram(self, message):
#        self.http.headers = {'Content-type': 'application/json'}
#        try:
#            self.http.request('GET', 'https://api.telegram.org/bot{}/sendMessage?chat_id={}\&text={}'.format(
#                self.prefs['telegram_token'], self.prefs['telegram_chat_id'], message), timeout=4.0, retries=False)
#        except Exception as e:
#           logger.error(e)

	def telegram(self, bot_message):
		url = f"https://api.telegram.org/bot{self.prefs['telegram_token']}/sendMessage"
		parms = {'chat_id': self.prefs['telegram_chat_id'], 'text': bot_message}
		requests.get(url, parms, timeout=4)

	def pushover(self, message):
		if self.prefs['pushover_token'] and self.prefs['pushover_userkey']:
			conn = http.client.HTTPSConnection("api.pushover.net:443")
			conn.request("POST", "/1/messages.json",
						 urllib.parse.urlencode({
							 "token": self.prefs['pushover_token'],
							 "user": self.prefs['pushover_userkey'],
							 "message": message,
						 }), {"Content-type": "application/x-www-form-urlencoded"})
			conn.getresponse()

	def get_message(self, callentry, phone_message):
		if callentry['Caller'] is None:
			callentry['Caller'] = ""
		if callentry['Name'] is None:
			callentry['Name'] = ""
		calltime = datetime.strptime(callentry['Date'], '%d.%m.%y %H:%M').strftime("%d.%m.%Y %H:%M")
		if phone_message:
			text = '{0} {1} {2} /Message: {3}'.format(
				calltime,
				callentry['Name'].encode('utf-8').decode('utf-8'),
				callentry['Caller'],
				phone_message
			)
		else:
			text = '{} {} {}'.format(
				calltime,
				callentry['Name'].encode('utf-8').decode('utf-8'),
				callentry['Caller']
			)
		return text

	def speech_to_text(self, filename):
		# initialize the recognizer
		r = sr.Recognizer()
		# open the file
		with sr.AudioFile(filename) as source:
			# listen for the data (load audio to memory)
			audio_data = r.record(source)
			# recognize (convert from speech to text)
			text = r.recognize_google(audio_data, language="de-DE")
			return text
