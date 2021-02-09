#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Read the phone calls list and extract the ones that have no phonebook entry
Do a backward search with the used number and if a name has been found add the entry to the given phonebook

@Werner Kuehn - Use at your own risk
29.01.2016           Add alternate number search
09.02.2016           Fixed duplicate phonebook entries. Handling of type 2 calls
17.02.2016           Append numbers to existing phonebook entries
18.02.2016           Remove quickdial entry
17.03.2016           Changed html.parser to html.parser.HTMLParser()
21.03.2016           Added config file
23.03.2016           Fixed phone book entry names handling for html special characters
08.04.2016 0.2.0 WK  Added fritzCallMon.py, made fritzBackwardSearch module callable
27.04.2016 0.2.2 WK  Enhanced search by removing numbers at the end in case someone has dialed more numbers
03.08.2016 0.2.3 WK  Fix duplicate phonebook entries caused by following call of Type 10
27.12.2016 0.2.4 WK  Improve search by adding zero at the end
25.07.2017 0.2.5 WK  Correct html conversion in dastelefonbuch
09.08.2017 0.2.6 WK  Add area code length into suzzy search. Avoid adding pre-dial numbers into the phone book
27.08.2017 0.2.7 WK  Replace & in phonebook name with u. as AVM hasn't fixed this problem yet


"""

__version__ = '0.2.7'

import argparse
import configparser
import copy
import datetime
import html.parser
import logging
import os
import re
from xml.etree.ElementTree import XML, fromstring, tostring

import certifi
import urllib3
import xmltodict
from bs4 import BeautifulSoup
from fritzconnection import FritzConnection

logger = logging.getLogger(__name__)

args = argparse.Namespace()
args.logfile = ''


class FritzCalls(object):

	def __init__(self, connection, notfoundfile):
		self.areaCode = (connection.call_action('X_VoIP', 'GetVoIPCommonAreaCode'))['NewVoIPAreaCode']
		self.notfoundfile = notfoundfile
		if notfoundfile and type(notfoundfile) is list:
			self.notfoundfile = notfoundfile[0]
		self.http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
		callURLList = connection.call_action('X_AVM-DE_OnTel', 'GetCallList')
		response = self.http.request('GET', callURLList['NewCallListURL'])
		self.calldict = xmltodict.parse(response.data)['root']

	# not working yet
	def remove_known(self):  # remove all callers listed by name
		for i in self.calldict['Call']:
			remove = True
			callentry = self.calldict['Call'][i]
			if (callentry['Type'] in ('1', '2') and callentry['Caller'] != None and callentry['Caller'].isdigit()) \
					or (callentry['Type'] == '3' and callentry['Called'] != None and callentry['Called'].isdigit()):
				if callentry['Name'] == None or callentry['Name'].startswith(
						callentry['Caller']) or callentry['Name'].startswith(
						callentry['Called']):
					remove = False
			if remove:
				del self.calldict['Call'][i]

	def get_unknown(self):  # get list of callers not listed with their name
		numberlist = {}
		for callentry in self.calldict['Call']:
			if datetime.datetime.strptime(callentry['Date'], "%d.%m.%y %H:%M") < datetime.datetime.today() - datetime.timedelta(days=7):
				break
			number = None
			if callentry['Type'] in ('1', '2') and callentry['Caller'] != None and callentry['Caller'].isdigit():
				number = callentry['Caller']
			elif callentry['Type'] == '3' and callentry['Called'] != None and callentry['Called'].isdigit():
				number = callentry['Called']
			if number:
				if callentry['Name'] == None or callentry['Name'].startswith(number):
					numberlist[number] = ''
					if callentry['Name'] != None and callentry['Name'].startswith(number):
						startAlternate = callentry['Name'].find('(')
						numberlist[number] = callentry['Name'][startAlternate+1:len(callentry['Name'])-1]
		return numberlist

	def get_names(self, searchlist, nameNotFoundList):
		foundlist = {}
		for number in searchlist:
			origNumber = number
			# remove international numbers
			if number.startswith("00"):
				fullNumber = ""
				logger.info("Ignoring international number {}".format(number))
				nameNotFoundList.append(number)
			# remove pre-dial number
			elif number.startswith("010"):
				nextZero = number.find('0', 3)
				number = number[nextZero:]
				fullNumber = number
			else:
				# add the area code for local numbers
				m = re.search('^[1-9][0-9]+', number)
				if m:
					fullNumber = '{}{}'.format(self.areaCode, number)
				else:
					fullNumber = number
			name = None
			numberLogged = False
			numberSaved = False
			l_onkz = FritzBackwardSearch().get_ONKz_length(fullNumber)
			while (name == None and len(fullNumber) >= (l_onkz + 3)):
				name = self.dasoertliche(fullNumber)
#				if not name and searchlist[number] != '':
#					name = self.dasoertliche(searchlist[number])
				if not name:
					logger.info('{} not found'.format(fullNumber))
					nameNotFoundList.append(fullNumber)
					if fullNumber != number and not numberLogged:
						nameNotFoundList.append(number)
					if origNumber != number and not numberLogged:
						nameNotFoundList.append(origNumber)
					numberLogged = True
					# don't do fuzzy search for mobile numbers and 0800
					if fullNumber[0:3] in ("015", "016", "017") or fullNumber[0:4] in ("0800"):
						fullNumber = ""
					elif fullNumber[-1] == "0":
						fullNumber = fullNumber[:-2]+"0"
					else:
						fullNumber = fullNumber[:-2]+"0"
				else:
					foundlist[fullNumber] = name
					if fullNumber != number and not numberSaved:
						foundlist[number] = name
					numberSaved = True
		return foundlist

	def dasoertliche(self, number):
		url = 'https://www.dasoertliche.de/Controller?form_name=search_inv&ph={}'.format(number)
		headers = {
			'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36'}
		response = self.http.request('GET', url, headers=headers)
		content = response.data.decode("utf-8", "ignore") \
			.replace('\t', '').replace('\n', '').replace('\r', '').replace('&nbsp;', ' ')
		soup = BeautifulSoup(content, 'html.parser')
		name = soup.find('span', class_='st-treff-name')
		if name:
			logger.info('{} = dasoertliche({})'.format(number, name.get_text().encode(
				'ascii', 'xmlcharrefreplace').decode('ascii')))
			return name.get_text().encode('ascii', 'xmlcharrefreplace').decode('ascii').replace(' & ', ' u. ')


class FritzPhonebook(object):

	def __init__(self, connection, name):
		self.connection = connection
		if name and type(name) == list:
			name = name[0]
		bookNumbers = self.connection.call_action('X_AVM-DE_OnTel', 'GetPhonebookList')['NewPhonebookList'].split(",")
		self.bookNumber = -1
		for number in bookNumbers:
			a = connection.call_action('X_AVM-DE_OnTel', 'GetPhonebook', NewPhonebookID=number)
			if a['NewPhonebookName'] == name:
				self.bookNumber = number
				logger.debug("PhonebookNumber = {}".format(number))
				break
		if self.bookNumber == -1:
			logger.error('Phonebook: {} not found !'.format(name), True)
			exit(1)
		self.get_phonebook()

	def get_phonebook(self):
		self.http = urllib3.PoolManager()
		response = self.http.request('GET', self.connection.call_action(
			'X_AVM-DE_OnTel', 'GetPhonebook', NewPhonebookID=self.bookNumber)['NewPhonebookURL'])
		self.phonebook = fromstring(
			re.sub("!-- idx:(\d+) --", lambda m: "idx>"+m.group(1)+"</idx", response.data.decode("utf-8")))

	def get_entry(self, name=None, number=None, uid=None, id=None):
		for contact in self.phonebook.iter('contact'):
			if name != None:
				for realName in contact.iter('realName'):
					if html.parser.HTMLParser().unescape(realName.text) == html.parser.HTMLParser().unescape(name):
						for idx in contact.iter('idx'):
							return {'contact_id': idx.text, 'contact': contact}
			elif number != None:
				for realNumber in contact.iter('number'):
					if realNumber.text == number:
						for idx in contact.iter('idx'):
							return {'contact_id': idx.text, 'contact': contact}
			elif uid != None:
				for uniqueid in contact.iter('uniqueid'):
					if uniqueid.text == uid:
						for idx in contact.iter('idx'):
							return {'contact_id': idx.text, 'contact': contact}
			elif id != None:
				phone_entry = fromstring(self.connection.call_action(
					'X_AVM-DE_OnTel', 'GetPhonebookEntry', NewPhonebookID=self.bookNumber,
					NewPhonebookEntryID=id)['NewPhonebookEntryData'])
				return {'contact_id': id, 'contact': phone_entry}

	def append_entry(self, entry, phone_number):
		phonebookEntry = self.get_entry(id=entry['contact_id'])['contact']
		for realName in phonebookEntry.iter('realName'):
			realName.text = realName.text.replace('& ', '&#38; ')
		for number in phonebookEntry.iter('number'):
			if 'quickdial' in number.attrib:
				del number.attrib['quickdial']
			newnumber = copy.deepcopy(number)
			newnumber.text = phone_number
			newnumber.set('type', 'home')
			newnumber.set('prio', '1')
			for telephony in phonebookEntry.iter('telephony'):
				telephony.append(newnumber)
		self.connection.call_action('X_AVM-DE_OnTel', 'SetPhonebookEntry',
									NewPhonebookEntryData='<?xml version="1.0" encoding="utf-8"?>' +
									tostring(phonebookEntry).decode("utf-8"),
									NewPhonebookID=self.bookNumber, NewPhonebookEntryID=entry['contact_id'])

	def add_entry(self, phone_number, name):
		phonebookEntry = fromstring(
			'<contact><person><realName></realName></person><telephony><number type="home" prio="1"></number></telephony></contact>')
		for number in phonebookEntry.iter('number'):
			number.text = phone_number
			number.set('type', 'home')
			number.set('prio', '1')
		for realName in phonebookEntry.iter('realName'):
			realName.text = html.parser.HTMLParser().unescape(name)
		self.connection.call_action('X_AVM-DE_OnTel', 'SetPhonebookEntry',
									NewPhonebookEntryData='<?xml version="1.0" encoding="utf-8"?>' +
									tostring(phonebookEntry).decode("utf-8"),
									NewPhonebookID=self.bookNumber, NewPhonebookEntryID='')
		self.get_phonebook()

	def add_entry_list(self, entry_list):
		if entry_list:
			for number, name in entry_list.items():
				entry = self.get_entry(name=name)
				if entry:
					self.append_entry(entry, number)
				else:
					self.add_entry(number, name)


class FritzBackwardSearch(object):

	def __init__(self):
		fname = os.path.join(os.path.dirname(__file__), 'fritzBackwardSearch.ini')
		if os.path.isfile(fname):
			self.prefs = self.__read_configuration__(fname)
		else:
			logger.error('{} not found'.format(fname), True)
			exit(1)
		self.__init_logging__()
		global args
		args = self.__get_cli_arguments__()
		self.__read_ONKz__()
		self.connection = FritzConnection(
			address=args.address,
			port=args.port,
			user=args.username,
			password=args.password)
		self.phonebook = FritzPhonebook(self.connection, name=args.phonebook)
		self.notfoundfile = args.notfoundfile
		if args.notfoundfile and type(args.notfoundfile) is list:
			self.notfoundfile = args.notfoundfile[0]
		try:
			self.nameNotFoundList = open(self.notfoundfile, 'r').read().splitlines()
		except:
			self.nameNotFoundList = open(self.notfoundfile, 'w+').read().splitlines()

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
			preferences[name] = value
		logger.debug(preferences)
		return preferences

	def __read_ONKz__(self):  # read area code numbers
		self.onkz = []
		fname = args.areacodefile
		if os.path.isfile(fname):
			with open(fname, 'r') as csvfile:
				for row in csvfile:
					self.onkz.append(row.strip().split('\t'))
		else:
			logger.error('{} not found'.format(fname))
			exit

	def get_ONKz_length(self, phone_number):
		for row in self.onkz:
			if phone_number[0:len(row[0])] == row[0]:
				return len(row[0])
		# return 4 as default length if not found (e.g. 0800)
		return 4

	# ---------------------------------------------------------
	# cli-section:
	# ---------------------------------------------------------

	def __get_cli_arguments__(self):
		parser = argparse.ArgumentParser(description='Update phonebook with caller list')
		parser.add_argument('-p', '--password',
							nargs=1, default=self.prefs['password'],
							help='Fritzbox authentication password')
		parser.add_argument('-u', '--username',
							nargs=1, default=self.prefs['fritz_username'],
							help='Fritzbox authentication username')
		parser.add_argument('-i', '--ip-address',
							nargs=1, default=self.prefs['fritz_ip_address'],
							dest='address',
							help='IP-address of the FritzBox to connect to. '
							'Default: %s' % self.prefs['fritz_ip_address'])
		parser.add_argument('--port',
							nargs=1, default=self.prefs['fritz_tcp_port'],
							help='Port of the FritzBox to connect to. '
							'Default: %s' % self.prefs['fritz_tcp_port'])
		parser.add_argument('--phonebook',
							nargs=1, default=self.prefs['fritz_phone_book'],
							help='Existing phone book the numbers should be added to. '
							'Default: %s' % self.prefs['fritz_phone_book'])
		parser.add_argument('-l', '--logfile',
							nargs=1, default=self.prefs['logfile'],
							help='Path/Log file name. '
							'Default: %s' % self.prefs['logfile'])
		parser.add_argument('-a', '--areacodefile',
							nargs=1, default=self.prefs['area_code_file'],
							help='Path/file name where the area codes are listed. '
							'Default: %s' % self.prefs['area_code_file'])
		parser.add_argument(
			'-n', '--notfoundfile', nargs=1, default=self.prefs['name_not_found_file'],
			help='Path/file name where the numbers not found during backward search are saved to in order to prevent further unnessessary searches. '
			'Default: %s' % self.prefs['name_not_found_file'])
		parser.add_argument('-s', '--searchnumber',
							nargs='?', default='',
							help='Phone number(s) to search for.')
		parser.add_argument('-v', '--version',
							action='version', version=__version__,
							help='Print the program version')
		return parser.parse_args()

	def runSearch(self, s=''):
		if self.prefs['password'] != '':
			args.password = self.prefs['password']
		if args.password == '':
			logger.error('No password given', True)
			exit(1)
		if args.password and type(args.password) == list:
			args.password = args.password[0].rstrip()
		calls = FritzCalls(self.connection, notfoundfile=args.notfoundfile)
		unknownCallers = calls.get_unknown()
		searchnumber = []
		nameList = ''
		if args.searchnumber:
			if type(args.searchnumber) == tuple:
				searchnumber += args.searchnumber
			else:
				searchnumber.append(args.searchnumber)
		if s:
			if type(s) == tuple:
				searchnumber += s
			else:
				searchnumber.append(s)
		if searchnumber:
			for number in searchnumber:
				logger.info("Searching for {}".format(number))
				contact = self.phonebook.get_entry(number=number)
				if not contact:
					if number in self.nameNotFoundList:
						logger.info('{} already in nameNotFoundList'.format(number))
					else:
						unknownCallers[number] = ''
						logger.info('{} not found'.format(number))
						nameList += 'not found\n'
				else:
					logger.info('{} already in {}'.format(number, args.phonebook))
					for realName in contact['contact'].iter('realName'):
						nameList += realName.text.replace('& ', '&#38; ')+'\n'
		else:
			logger.error("Searchnumber nicht gesetzt")
		nameNotFoundList_length = len(self.nameNotFoundList)
		unknownCallers = set(unknownCallers.keys()).difference(set(self.nameNotFoundList))
		logger.debug("Length unknownCallers = {}".format(len(unknownCallers)))
		knownCallers = calls.get_names(unknownCallers, self.nameNotFoundList)
		if len(self.nameNotFoundList) > nameNotFoundList_length:
			with open(self.notfoundfile, "w") as outfile:
				outfile.write("\n".join(self.nameNotFoundList))
		self.phonebook.add_entry_list(knownCallers)
		return nameList


if __name__ == '__main__':
	FBS = FritzBackwardSearch()
#   to search for a number specify it in here:
#	FBS.runSearch(s=('111', '1550'))
#	FBS.runSearch(s=('333'))
	FBS.runSearch()
