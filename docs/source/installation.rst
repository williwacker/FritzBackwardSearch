Installation
============

Prerequisites
-------------

Fritz-Backward-Search is working on a standard Python 3.5 environment and relies on the
following packages for querying the Fritz!Box.

* `fritzconnection <https://pypi.python.org/pypi/fritzconnection/0.4.6>`_
* `lxml <https://pypi.python.org/pypi/lxml/3.5.0>`_
* `requests <https://pypi.python.org/pypi/requests/2.9.1>`_ 



To get the scripts you need `Git <https://git-scm.com/>`_ to clone the
repository using the URL ``https://github.com/williwacker/fritz-backward-search.git``

Installation on a RaspberryPi Running Raspian
---------------------------------------------


1. Downloading the Scripts
--------------------------

To install the fritzBackwardSearch scripts clone the GitHub repository::

    git clone https://github.com/williwacker/fritz-backward-search.git
    
2. Installing the fritzCallMon as a service
-------------------------------------------

In order to start the Call monitor during startup you will need to update the scripts with your 
installation directory and define it as a service. This will be done by the ``install.sh`` script::

    cd <your installation dir>
    sudo sh install.sh

3. Installing the Dependencies
------------------------------

There are many ways to install the dependencies but for the common packages we
rely on aptitude::

    aptitude install python3-lxml python3-pip

The fritzconnection and other packages are not in the raspbian repository so they will be
installed using pip by running::

    pip-3.2 install fritzconnection requests urllib3 xmltodict
    
4. Configuration
----------------

Configuration basically means defining the Fritz!Box parameters and the location of the files.

The first step is to copy the example configuration file ``fritzBackwardSearch.ini.sample``
to ``fritzBackwardSearch.ini`` to enable further updates easily.::

	cd <your installation dir>
	sudo mv fritzBackwardSearch.ini.sample fritzBackwardSearch.ini

Starting from the default ``fritzBackwardSearch.ini`` file typically only three variables
have to be edited: ``NAME_NOT_FOUND_FILE`` which stores the phone numbers that haven't been 
found during backward search in order to prevent unnecessary searching with the next run, 
the ``FRITZ_PHONE_BOOK`` which names the phonebook the search results are stored in. 
This phonebook must exist in the Fritz!Box. And the third parameter is the Fritz!Box password
so fritzconnection can access the Fritz!Box. 
The ``LOGFILE`` parameter is option. This file will log the search results.

.. note::
   The user under which the ``fritzBackwardSearch.py`` script is executed has to have read/write permissions to the
   ``NAME_NOT_FOUND_FILE`` and the ``LOGFILE`` directory.

An example of a typical ``fritzBackwardSearch.ini`` file is shown here::

	[DEFAULT]
	FRITZ_IP_ADDRESS:      192.168.178.1
	FRITZ_TCP_PORT:        49000
	FRITZ_CALLMON_PORT:    1012
	CALLMON_SERVER_SOCKET: 26260
	FRITZ_USERNAME:        dslf-config
	NAME_NOT_FOUND_FILE:   /home/fritzbox/nameNotFound.list
	FRITZ_PHONE_BOOK:      Collected_Calls
	PASSWORD:              00000000
	LOGFILE:               /var/log/fritzBackwardSearch.log
	STATUS_TO_TERMINAL:    True
	PROCESS_STOP_FILE:     /var/run/fritzCallMon.pid
