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

Contents:

.. toctree::
   :maxdepth: 2
   
   how
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



