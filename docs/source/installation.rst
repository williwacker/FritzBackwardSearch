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

To install the fritz-backward-search script clone the GitHub repository::

    git clone https://github.com/williwacker/fritz-backward-search.git

2. Installing the Dependencies
------------------------------

There are many ways to install the dependencies but for the common packages we
rely on aptitude::

    aptitude install python3-lxml python3-pip

The fritzconnection and other packages are not in the raspbian repository so they will be
installed using pip by running::

    pip-3.2 install fritzconnection requests urllib3 xmltodict

3. Configuration
----------------

Configuration basically means defining the Fritz!Box parameters and the location of the files.

The first step is to copy the example configuration file ``fritz-backward-search.ini.sample``
to ``fritz-backward-search.ini`` to enable further updates easily.

Starting from the default ``fritz-backward-search.ini`` file typically only three variables
have to be edited: ``NAME_NOT_FOUND_FILE`` which stores the phone numbers that haven't been 
found during backward search in order to prevent unnecessary searching with the next run, 
the ``FRITZ_PHONE_BOOK`` which names the phonebook the search results are stored in. 
This phonebook must exist in the Fritz!Box. And the third parameter is the Fritz!Box password
so fritzconnection can access the Fritz!Box. 
The ``LOG_FILE`` parameter is option. This file will log the search results.

.. note::
   The user under which the ``fritz-backward-search.py`` script is executed has to have read/write permissions to the
   ``NAME_NOT_FOUND_FILE`` and the ``LOG_FILE`` directory.

An example of a typical ``fritz-backward-search.ini`` file is shown here::

	[DEFAULT]
	FRITZ_IP_ADDRESS:    192.168.178.1
	FRITZ_TCP_PORT:      49000
	FRITZ_USERNAME:      dslf-config
	NAME_NOT_FOUND_FILE: /home/fritzbox/nameNotFound.list
	FRITZ_PHONE_BOOK:    Collected_Calls
	PASSWORD:            00000000
	LOG_FILE:            /var/log/fritz-backward-search.log


4. Running as a Cronjob
-----------------------

To update the Fritz!Box phone book the ``fritz-backward-search.py`` script is
executed periodically.

Typically one would add the following line to the user's crontab to update the
phone book every hour. To do so the command ``crontab -e``
opens the user's crontab and the following line is added ::

  0 * * * * [absolute path to script]/fritz-backward-search.py


