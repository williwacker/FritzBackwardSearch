import configparser
import logging
import os
import itertools
from sys import platform
from fritzconnection.lib.fritzwlan import FritzWLAN
from fritzconnection.core.exceptions import FritzServiceError

logger = logging.getLogger(__name__)


class FritzWLANStatus(object):

	def __init__(self, connection, prefs):
		fname = os.path.join(os.path.dirname(__file__), 'fritzBackwardSearch.ini')
		if os.path.isfile(fname):
			self.wlan_prefs = self.__read_wlan_configuration__(fname)
		else:
			logger.error('{} not found'.format(fname))
			exit(1)

		self.prefs = prefs
		self.connection = connection

	def __read_wlan_configuration__(self, filename):
		cfg = configparser.ConfigParser(default_section=None)
		cfg.read(filename)
		wlan = {}
		for name, value in cfg.items('WLAN'):
			wlan[name] = value.replace('-', ':')
		return wlan
	
	def get_active_macs(self):
		"""
		Gets a FritzWLAN instance and returns a list of mac addresses
		from the active devices
		"""
		active_macs = list()
		# iterate over all wlans:
		for n in itertools.count(1):
			self.fwlan.service = n
			try:
				hosts_info = self.fwlan.get_hosts_info()
			except FritzServiceError:
				break
			else:
				active_macs.extend(entry['mac'] for entry in hosts_info)
		return active_macs	

	def get_active_devices(self):
		self.fwlan = FritzWLAN(self.connection)
		active_macs = self.get_active_macs()
		online_status = {}
		for name, mac in self.wlan_prefs.items():
			online_status[name] = 'ON' if mac in active_macs else 'OFF'
		# send as mqtt message
		logger.info(online_status)
		if platform == "linux":
			try:
				cmd = 'mosquitto_pub -d -h homematic-raspi -t server/fritz/maconline/'
				for name, status in online_status.items():
					os.system("{}{} -m {}".format(cmd, name, status))
			except Exception as e:
				logger.error("Cannot post MQTT request: {}".format(e))
