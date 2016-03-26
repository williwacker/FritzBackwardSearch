# -*- coding: iso-8859-1 -*-

"""

Read the phone calls list and extract the ones that have no phonebook entry
Do a backward search with the used number and if a name has been found add the entry to the given phonebook

@Werner Kuehn  10.01.2016    Use on your own risk
Werner Kuehn   29.01.2016    Add alternate number search
Werner Kuehn   09.02.2016    Fixed duplicate phonebook entries. Handling of type 2 calls
Werner Kuehn   17.02.2016    Append numbers to existing phonebook entries
Werner Kuehn   18.02.2016    Remove quickdial entry
Werner Kuehn   17.03.2016    Changed html.parser to html.parser.HTMLParser()
Werner Kuehn   21.03.2016    Added config file
Werner Kuehn   23.03.2016    Fixed phone book entry names handling for html special characters

"""

__version__ = '0.1.0'

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

def read_configuration(filename): #read configuration from the configuration file and prepare a preferences dict
	cfg = configparser.ConfigParser()
	cfg.read(filename)
	preferences = {}
	for name, value in cfg.items('DEFAULT'):
		preferences[name] = value
	return preferences
	
def writeLog(logString):
	if args.logfile:
		logFile_out = open(args.logfile,'a')
		logFile_out.write('{} {}{}'.format(time.strftime("%Y-%m-%d %H:%M:%S"),logString,'\n'))
		logFile_out.close()
		

class FritzCalls(object):
	
	def __init__(self,notfoundfile):
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
		number = ''
		nameNotFoundList = open(self.notfoundfile,'r').readlines()
		for callentry in self.calldict['Call']:
			if callentry['Type'] in ('1','2') and callentry['Caller'] != None and callentry['Caller'].isdigit():
				number = callentry['Caller']
			elif callentry['Type'] == '3' and callentry['Called'] != None and callentry['Called'].isdigit():
				number = callentry['Called']
			if number:
				if callentry['Name'] == None or callentry['Name'].startswith(number):
					found = 0
					for ignoreNumber in nameNotFoundList:
						if number == ignoreNumber.rstrip(): 
							found = 1
							break
					if found == 0:
						numberlist[number] = ''
						if callentry['Name'] != None and callentry['Name'].startswith(number):
							startAlternate = callentry['Name'].find('(')
							numberlist[number] = callentry['Name'][startAlternate+1:len(callentry['Name'])-1]
		return numberlist

	def get_names(self,searchlist):				
		foundlist = {}
		nameNotFoundFile_out = open(self.notfoundfile,'a')
		for number in searchlist.keys():
			# remove pre-dial number
			if number.startswith("010"):
				nextZero = number.find('0',3)
				fullnumber = number[nextZero:]
			# add the area code for local numbers
			m = re.search('^[1-9][0-9]+', number)
			if m: 
				fullNumber = '{}{}'.format(self.areaCode,number)
			else:
				fullNumber = number
			name = self.dastelefonbuch(fullNumber)
			if name == None:
				name = self.dasoertliche(fullNumber)
			if name == None and searchlist[number] != '':
				name = self.dastelefonbuch(searchlist[number])
			if name == None and searchlist[number] != '':
				name = self.dasoertliche(searchlist[number])
			if name == None:
				writeLog('{} not found'.format(number))
				nameNotFoundFile_out.write('{}\n'.format(number))
			else:
				foundlist[number] = name
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

	def __init__(self, name):
		if name and type(name) == list:
			name = name[0]
		bookNumbers = connection.call_action('X_AVM-DE_OnTel','GetPhonebookList')['NewPhonebookList']
		self.bookNumber = -1
		for number in bookNumbers:
			if connection.call_action('X_AVM-DE_OnTel','GetPhonebook',NewPhonebookID=number)['NewPhonebookName'] == name:
				self.bookNumber = number
		if self.bookNumber == -1:
			print('Phonebook: {} not found !'.format(name))
			exit(1)
		self.get_phonebook()
						
	def get_phonebook(self):
		self.http = urllib3.PoolManager()
		response = self.http.request('GET', connection.call_action('X_AVM-DE_OnTel','GetPhonebook',NewPhonebookID=self.bookNumber)['NewPhonebookURL'])
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
				phone_entry = fromstring(connection.call_action('X_AVM-DE_OnTel','GetPhonebookEntry',NewPhonebookID=self.bookNumber,NewPhonebookEntryID=id)['NewPhonebookEntryData'])
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
		connection.call_action('X_AVM-DE_OnTel','SetPhonebookEntry',NewPhonebookEntryData='<?xml version="1.0" encoding="utf-8"?>'+tostring(phonebookEntry).decode("utf-8"),NewPhonebookID=self.bookNumber,NewPhonebookEntryID=entry['contact_id'])

	def add_entry(self, phone_number, name):
		phonebookEntry = fromstring('<contact><person><realName></realName></person><telephony><number type="home" prio="1"></number></telephony></contact>')
		for number in phonebookEntry.iter('number'):
			number.text = phone_number
			number.set('type','home')
			number.set('prio','1')
		for realName in phonebookEntry.iter('realName'):
			realName.text = html.parser.HTMLParser().unescape(name)
		connection.call_action('X_AVM-DE_OnTel','SetPhonebookEntry',NewPhonebookEntryData='<?xml version="1.0" encoding="utf-8"?>'+tostring(phonebookEntry).decode("utf-8"),NewPhonebookID=self.bookNumber,NewPhonebookEntryID='')
		self.get_phonebook()
			
	def add_entry_list(self, list):
		if list:
			for number, name in list.items():
				entry = self.get_entry(name=name)
				if entry:
					self.append_entry(entry, number)	
				else:
					self.add_entry(number, name)


# ---------------------------------------------------------
# cli-section:
# ---------------------------------------------------------

def get_cli_arguments():
	parser = argparse.ArgumentParser(description='Update phonebook with caller list')
	parser.add_argument('-p', '--password',
                        nargs=1, default=prefs['password'],
                        help='Fritzbox authentication password')
	parser.add_argument('-u', '--username',
                        nargs=1, default='',
                        help='Fritzbox authentication username')
	parser.add_argument('-i', '--ip-address',
                        nargs=1, default=prefs['fritz_ip_address'],
                        dest='address',
                        help='IP-address of the FritzBox to connect to. '
                             'Default: %s' % prefs['fritz_ip_address'])
	parser.add_argument('--port',
                        nargs=1, default=prefs['fritz_tcp_port'],
                        help='Port of the FritzBox to connect to. '
                             'Default: %s' % prefs['fritz_tcp_port'])
	parser.add_argument('--phonebook',
                        nargs=1, default=prefs['fritz_phone_book'],
                        help='Existing phone book the numbers should be added to. '
                             'Default: %s' % prefs['fritz_phone_book'])  
	parser.add_argument('-l', '--logfile',
                        nargs=1, default=prefs['log_file'],
                        help='Path/Log file name. '
                             'Default: %s' % prefs['log_file'])                               
	parser.add_argument('-n', '--notfoundfile',
                        nargs=1, default=prefs['name_not_found_file'],
                        help='Path/file name where the numbers not found during backward search are saved to in order to prevent further unnessessary searches. '
                             'Default: %s' % prefs['name_not_found_file'])                               
	parser.add_argument('-s', '--searchnumber',
                        nargs='?', default='',
                        help='Phone number(s) to search for.')                               
	parser.add_argument('-v', '--version',
                        action='version', version=__version__,
                        help='Print the program version')
	args = parser.parse_args()
	return args
		
if __name__ == '__main__':
	prefs = read_configuration(os.path.join(os.path.dirname(__file__),'fritz-backward-search.ini'))
	args = get_cli_arguments()
	if prefs['password'] != '':
		args.password = prefs['password']		
	if args.password == '':
		print('No password given')
		writeLog('No password given')
		exit(1)
	if args.password and type(args.password) == list:
		args.password = args.password[0].rstrip()
	connection = FritzConnection(address=args.address,
                       	   		port=args.port,
                           		user=args.username,
                           		password=args.password)
	phonebook = FritzPhonebook(name=args.phonebook)
	calls     = FritzCalls(notfoundfile=args.notfoundfile)
	unknownCallers = calls.get_unknown()
	if args.searchnumber:
		numbers = re.split('\W+', args.searchnumber)
		for number in re.split('\W+', args.searchnumber):
			unknownCallers[number] = ''
	knownCallers   = calls.get_names(unknownCallers)
	phonebook.add_entry_list(knownCallers)
