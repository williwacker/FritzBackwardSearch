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

"""

__version__ = '0.2.3'

from fritzconnection import FritzConnection
import urllib3
import xmltodict
import re
import argparse
import html.parser
from xml.etree.ElementTree import XML, fromstring, tostring
import copy
import configparser
import os
import time

args = argparse.Namespace()
args.logfile = ''

class FritzCalls(object):
	
	def __init__(self, connection, notfoundfile):
		self.areaCode    = (connection.call_action('X_VoIP','GetVoIPCommonAreaCode'))['NewVoIPAreaCode']
		self.notfoundfile = notfoundfile
		if notfoundfile and type(notfoundfile) is list:
			self.notfoundfile = notfoundfile[0]
		self.http = urllib3.PoolManager()
		callURLList = connection.call_action('X_AVM-DE_OnTel','GetCallList')
		response = self.http.request('GET', callURLList['NewCallListURL'])
		self.calldict = xmltodict.parse(response.data)['root']
		
	def get_unknown(self): # get list of callers not listed with their name
		numberlist = {}
		for callentry in self.calldict['Call']:
			number = None
			if callentry['Type'] in ('1','2') and callentry['Caller'] != None and callentry['Caller'].isdigit():
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
		
	def remove_not_found(self,numberlist_in):
		numberlist_out = {}
		nameNotFoundList = open(self.notfoundfile,'r').readlines()
		for number in numberlist_in.keys():
			found = 0
			for ignoreNumber in nameNotFoundList:
				if number == ignoreNumber.rstrip():
					found = 1
					break
			if found == 0:
				numberlist_out[number] = ''
		return numberlist_out

	def get_names(self,searchlist):				
		foundlist = {}
		nameNotFoundFile_out = open(self.notfoundfile,'a')
		for number in searchlist.keys():
			origNumber = number
			# remove pre-dial number
			if number.startswith("010"):
				nextZero = number.find('0',3)
				fullNumber = number[nextZero:]
			else:
				# add the area code for local numbers
				m = re.search('^[1-9][0-9]+', number)
				if m: 
					fullNumber = '{}{}'.format(self.areaCode,number)
				else:
					fullNumber = number
			name = None;
			numberLogged = False
			numberSaved  = False
			while (name == None and len(fullNumber) > 6):
				name = self.dastelefonbuch(fullNumber)
				if name == None:
					name = self.dasoertliche(fullNumber)
				if name == None and searchlist[number] != '':
					name = self.dastelefonbuch(searchlist[number])
				if name == None and searchlist[number] != '':
					name = self.dasoertliche(searchlist[number])
				if name == None:
					writeLog('{} not found'.format(fullNumber))
					nameNotFoundFile_out.write('{}\n'.format(fullNumber))
					if fullNumber != number and not numberLogged:
						nameNotFoundFile_out.write('{}\n'.format(number))
					numberLogged = True
					fullNumber = fullNumber[:-1]
				else:
					foundlist[fullNumber] = name
					if fullNumber != number and not numberSaved:
						foundlist[number] = name
					numberSaved = True
		nameNotFoundFile_out.close()
		return foundlist
		
	def dastelefonbuch(self,number):
		lurl = self.http.request('GET', 'http://www3.dastelefonbuch.de/?kw={}&s=a20000&cmd=search&ort_ok=0&sp=3&vert_ok=0&aktion=23'.format(number))
		line = lurl.data.decode("utf-8",'ignore')
		for ch in ["\r\n","\r","\n"]:
			line = line.replace(ch, '')
		m = re.search('<div class="name" title="(.*?)">', line)
		if m:
			writeLog('{} = {}({})'.format(number,'dastelefonbuch',m.group(1)))
			return m.group(1)

	def dasoertliche(self,number):
		lurl = self.http.request('GET', 'http://www3.dasoertliche.de/Controller?zvo_ok=&book=22&plz=&quarter=&district=&ciid=&form_name=search_inv&buc=22&kgs={}&buab=&zbuab=&page=5&context=4&action=43&ph={}&image=Finden'.format(number,number))
		line = lurl.data.decode("iso-8859-15")
		for ch in ["\r\n","\r","\n"]:
			line = line.replace(ch, '')
		m = re.search('class="name "><span class="">(.*?)&nbsp;</span>', line)
		if m:
			writeLog('{} = {}({})'.format(number,'dasoertliche',m.group(1).encode('ascii', 'xmlcharrefreplace').decode('ascii')))
			return m.group(1).encode('ascii', 'xmlcharrefreplace').decode('ascii')
		
	
class FritzPhonebook(object):

	def __init__(self, connection, name):
		self.connection = connection
		if name and type(name) == list:
			name = name[0]
		bookNumbers = self.connection.call_action('X_AVM-DE_OnTel','GetPhonebookList')['NewPhonebookList']
		self.bookNumber = -1
		for number in bookNumbers:
			if connection.call_action('X_AVM-DE_OnTel','GetPhonebook',NewPhonebookID=number)['NewPhonebookName'] == name:
				self.bookNumber = number
		if self.bookNumber == -1:
			logMessage = 'Phonebook: {} not found !'.format(name)
			writeLog(logMessage,True)
			exit(1)
		self.get_phonebook()
						
	def get_phonebook(self):
		self.http = urllib3.PoolManager()
		response = self.http.request('GET', self.connection.call_action('X_AVM-DE_OnTel','GetPhonebook',NewPhonebookID=self.bookNumber)['NewPhonebookURL'])
		self.phonebook = fromstring(re.sub("!-- idx:(\d+) --",lambda m: "idx>"+m.group(1)+"</idx",response.data.decode("utf-8")))

	def get_entry(self,name=None,number=None,uid=None,id=None):
		for contact in self.phonebook.iter('contact'):
			if name != None:
				for realName in contact.iter('realName'):
					if html.parser.HTMLParser().unescape(realName.text) == html.parser.HTMLParser().unescape(name):
						for idx in contact.iter('idx'):
							return {'contact_id':idx.text,'contact':contact}
			elif number != None:
				for realNumber in contact.iter('number'):
					if realNumber.text == number:
						for idx in contact.iter('idx'):
							return {'contact_id':idx.text,'contact':contact}
			elif uid != None:
				for uniqueid in contact.iter('uniqueid'):
					if uniqueid.text == uid:
						for idx in contact.iter('idx'):
							return {'contact_id':idx.text,'contact':contact}
			elif id != None:
				phone_entry = fromstring(self.connection.call_action('X_AVM-DE_OnTel','GetPhonebookEntry',NewPhonebookID=self.bookNumber,NewPhonebookEntryID=id)['NewPhonebookEntryData'])
				return {'contact_id':id,'contact':phone_entry}

	def append_entry(self, entry, phone_number):
		phonebookEntry = self.get_entry(id=entry['contact_id'])['contact']
		for realName in phonebookEntry.iter('realName'):
			realName.text = realName.text.replace('& ','&#38; ')
		for number in phonebookEntry.iter('number'):
			if 'quickdial' in number.attrib:
				del number.attrib['quickdial']
			newnumber = copy.deepcopy(number)
			newnumber.text = phone_number
			newnumber.set('type','home')
			newnumber.set('prio','1')
		for telephony in phonebookEntry.iter('telephony'):
			telephony.append(newnumber)
		self.connection.call_action('X_AVM-DE_OnTel','SetPhonebookEntry',NewPhonebookEntryData='<?xml version="1.0" encoding="utf-8"?>'+tostring(phonebookEntry).decode("utf-8"),NewPhonebookID=self.bookNumber,NewPhonebookEntryID=entry['contact_id'])

	def add_entry(self, phone_number, name):
		phonebookEntry = fromstring('<contact><person><realName></realName></person><telephony><number type="home" prio="1"></number></telephony></contact>')
		for number in phonebookEntry.iter('number'):
			number.text = phone_number
			number.set('type','home')
			number.set('prio','1')
		for realName in phonebookEntry.iter('realName'):
			realName.text = html.parser.HTMLParser().unescape(name)
		self.connection.call_action('X_AVM-DE_OnTel','SetPhonebookEntry',NewPhonebookEntryData='<?xml version="1.0" encoding="utf-8"?>'+tostring(phonebookEntry).decode("utf-8"),NewPhonebookID=self.bookNumber,NewPhonebookEntryID='')
		self.get_phonebook()
			
	def add_entry_list(self, list):
		if list:
			for number, name in list.items():
				entry = self.get_entry(name=name)
				if entry:
					self.append_entry(entry, number)	
				else:
					self.add_entry(number, name)



	
class FritzBackwardSearch(object):
	
	def __init__(self):
		fname = os.path.join(os.path.dirname(__file__),'fritzBackwardSearch.ini')
		if os.path.isfile(fname):
			self.prefs = self.__read_configuration__(fname)
		else:
			writeLog('{} not found'.format(fname),True)
			exit(1)
		global args
		args = self.__get_cli_arguments__()

	def __read_configuration__(self,filename): #read configuration from the configuration file and prepare a preferences dict
		cfg = configparser.ConfigParser()
		cfg.read(filename)
		preferences = {}
		for name, value in cfg.items('DEFAULT'):
			preferences[name] = value
		return preferences
			
	# ---------------------------------------------------------
	# cli-section:
	# ---------------------------------------------------------

	def __get_cli_arguments__(self):
		parser = argparse.ArgumentParser(description='Update phonebook with caller list')
		parser.add_argument('-p', '--password',
							nargs=1, default=self.prefs['password'],
							help='Fritzbox authentication password')
		parser.add_argument('-u', '--username',
							nargs=1, default='',
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
		parser.add_argument('-n', '--notfoundfile',
							nargs=1, default=self.prefs['name_not_found_file'],
							help='Path/file name where the numbers not found during backward search are saved to in order to prevent further unnessessary searches. '
								 'Default: %s' % self.prefs['name_not_found_file'])                               
		parser.add_argument('-s', '--searchnumber',
							nargs='?', default='',
							help='Phone number(s) to search for.')                               
		parser.add_argument('-v', '--version',
							action='version', version=__version__,
							help='Print the program version')
		return parser.parse_args()
	
	def runSearch(self,s=''):
		if self.prefs['password'] != '':
			args.password = self.prefs['password']		
		if args.password == '':
			writeLog('No password given',True)
			exit(1)
		if args.password and type(args.password) == list:
			args.password = args.password[0].rstrip()
		self.connection = FritzConnection(
								address=args.address,
								port=args.port,
								user=args.username,
								password=args.password)
		phonebook = FritzPhonebook(self.connection, name=args.phonebook)
		calls     = FritzCalls(self.connection, notfoundfile=args.notfoundfile)
		unknownCallers = calls.get_unknown()
		print(unknownCallers)
		exit(0)
		searchnumber = ''
		if args.searchnumber:
			searchnumber = args.searchnumber
		if s:
			if searchnumber != '':
				searchnumber = ','.join((searchnumber,str(s)))
			else:
				searchnumber = s
		for number in re.split('\W+', searchnumber):
			if not phonebook.get_entry(number=number):
				unknownCallers[number] = ''
			else:
				writeLog('{} already in {}'.format(number, args.phonebook))
		unknownCallers = calls.remove_not_found(unknownCallers)
		knownCallers   = calls.get_names(unknownCallers)
		phonebook.add_entry_list(knownCallers)
		
		
	
def writeLog(logString, print_to_console=False):
	if args.logfile != '':
		logFile_out = open(args.logfile,'a')
		logFile_out.write('{} {}{}'.format(time.strftime("%Y-%m-%d %H:%M:%S"),logString,'\n'))
		logFile_out.close()
	if print_to_console:
		print(logString)

if __name__ == '__main__':
	FBS = FritzBackwardSearch()
#   to search for a number specify it in here:
#	FBS.runSearch(s=(123,123))
	FBS.runSearch()
