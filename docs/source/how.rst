How It Works
============

Access to the `Fritz!Box <http://avm.de/produkte/fritzbox/>`_ relies on the `TR-064
standard <http://avm.de/fileadmin/user_upload/Global/Service/Schnittstellen/AVM_TR-064_overview.pdf>`_.

The script retrieves the phone caller list from the Fritz!Box, extracts the entries that do not have a name associated, compares this list with the one from previous searches 
where the name was not found because people have rejected backward searching, and does a backward search via currently two German phone searching platforms 
(`Das Oertliche <http://www3.dasoertliche.de/>`_ and `Das Telefonbuch <http://www.dastelefonbuch.de/R%C3%BCckw%C3%A4rts-Suche>`_). In case the name is found it gets added to the defined
`Fritz!Box <http://avm.de/produkte/fritzbox/>`_ phone book. This can be either the normal phone book, or a separate one, only for collected phone numbers. 

The script comes with an ``fritz-backward-search.ini`` file where you can specify all connection settings. But for special purposes you can use the command line interface to 
overwrite these settings.::

	usage: fritz-backward-search.py [-h] [-p PASSWORD] [-u USERNAME] [-i ADDRESS]
					[--port PORT] [--phonebook PHONEBOOK]
					[-l LOGFILE] [-n NOTFOUNDFILE]
					[-s [SEARCHNUMBER]] [-v]

	Update phonebook with caller list

	optional arguments:
	  -h, --help            show this help message and exit
	  -p PASSWORD, --password PASSWORD
				Fritzbox authentication password
	  -u USERNAME, --username USERNAME
				Fritzbox authentication username
	  -i ADDRESS, --ip-address ADDRESS
				IP-address of the FritzBox to connect to. Default:
				192.168.178.1
	  --port PORT           Port of the FritzBox to connect to. Default: 49000
	  --phonebook PHONEBOOK
				Existing phone book the numbers should be added to.
				Default: Collected_Calls
	  -l LOGFILE, --logfile LOGFILE
				Path/Log file name. Default:
				/var/log/fritz-backward-search.log
	  -n NOTFOUNDFILE, --notfoundfile NOTFOUNDFILE
				Path/file name where the numbers not found during
				backward search are saved to in order to prevent
				further unnessessary searches. Default:
				/var/fritz/nameNotFound.list
	  -s [SEARCHNUMBER], --searchnumber [SEARCHNUMBER]
				Phone number(s) to search for.
	  -v, --version         Print the program version
	

For testing purposes, or for adding individual number(s), the script can be called via this command line interface and passing one or more numbers.::

	fritz-backward.search.py -s 1234,2298