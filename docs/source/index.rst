.. Fritz-Backward-Search documentation master file, created by
   sphinx-quickstart on Mon Mar 21 17:54:09 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Fritz-Backward-Search!
=================================  

What it does
------------

* Don't you want to see in your phone display who is calling by name and not just the number?
* Don't you want to see in your Fritz!Box's caller list who has tried calling you during your absence by name?

This `Python <https://www.python.org>`_ script will retrieve the name of someone you have been calling, or someone who has called you, from the
internet via a backward search and saves this number and name in your `Fritz!Box <http://avm.de/produkte/fritzbox/>`_ phone book. 
The update of the phone book is done on a scheduled base. It does not do life updates while a call is coming in. 
If someone has an idea how to trigger this script when a call is coming in please feel free contacting me.

This script can run on a small embedded device such as a `RaspberryPi <https://www.raspberrypi.org>`_. It can run without superuser privileges as a normal user. 

How It Works
------------

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


Contents:

.. toctree::
   :maxdepth: 2
   
   installation
   changelog
   license

Contribute
----------

- Issue Tracker: `github.com/williwacker/fritz-backward-search/issues <https://github.com/williwacker/fritz-backward-search/issues>`_
- Source Code: `github.com/williwacker/fritz-backward-search.git <https://github.com/williwacker/fritz-backward-search.git>`_

Support
-------

If you are having issues, please let me know.
You can add an issue/question to the Issue Tracker.

Disclaimer
----------

The product Fritz! and Fritz!Box is a trademark of the AVM GmbH, Berlin, Germany.   



