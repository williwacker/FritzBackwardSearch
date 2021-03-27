#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import re
from datetime import datetime

import urllib3
import xmltodict

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
				logger.info(self.prefs)
				response = self.http.request('GET', self.callURLList['NewCallListURL'] + '&max=50')
				if response.status != 200:
					logger.error('response status='+str(response.status))
				calldict = xmltodict.parse(response.data)
				if 'root' in calldict:
					if 'Call' in calldict['root']:
						self.process_notification(calldict['root']['Call'], caller)
						self.unresolved_list.remove(caller)
				else:
					logger.info(calldict)

	def process_notification(self, calldict, caller):
		for callentry in calldict:
			logger.info(callentry)
			if callentry['Caller'] == caller:
				logger.info("callentry['Type']="+callentry['Type'])
				if callentry['Type'] == '2' or (callentry['Type'] == '1' and callentry['Port'] == '40'):  # missed incoming calls
					logger.info("callentry['Caller']="+callentry['Caller'])
					callentry['CalledNumber'] = self.get_fullCode(callentry['CalledNumber'])
					callentry['Caller'] = self.get_fullCode(callentry['Caller'])
					phone_message = self.get_phone_message(callentry) if callentry['Port'] in ('40') else ""
					logger.info("phone_message="+str(phone_message))
					self.put_telegram_message(callentry, phone_message)
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
			phone_message = "{}".format(dlfile[-1])
		return phone_message

	def put_telegram_message(self, callentry, phone_message):
		if callentry['Caller'] is None:
			callentry['Caller'] = ""
		if callentry['Name'] is None:
			callentry['Name'] = ""
		calltime = datetime.strptime(callentry['Date'], '%d.%m.%y %H:%M').strftime("%Y.%m.%d %H:%M")
		if phone_message:
			text = '{0} {1} {2} /getab{3}'.format(
				calltime,
				callentry['Name'].encode('utf-8').decode('utf-8'),
				callentry['Caller'],
				phone_message.split('.')[2]
			)
		else:
			text = '{} {} {}'.format(
				calltime,
				callentry['Name'].encode('utf-8').decode('utf-8'),
				callentry['Caller']
			)
		self.http.request(
			'GET', 'https://api.telegram.org/bot{}/sendMessage?chat_id={}\&text={}'.format(self.prefs['telegram_token'],
																						   self.prefs['telegram_chat_id'],
																						   text)
		)
