import configparser
import logging
import os

#from fritzconnection.lib.fritzwlan import FritzWLAN
from fritzconnection.lib.fritzhosts import FritzHosts

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

	def get_active_devices(self):
		try:
			online_status = {}
			'''
			hosts = [host['mac']
					for host in FritzWLAN(self.connection, service=1).get_hosts_info() if host['status'] == True]  # 2.4GHz
			hosts += [host['mac']
					for host in FritzWLAN(self.connection, service=2).get_hosts_info() if host['status'] == True]  # 5GHz
			hosts += [host['mac']
					for host in FritzWLAN(self.connection, service=3).get_hosts_info() if host['status'] == True]  # GuestAccount
			'''
			hosts = [host['mac'] for host in FritzHosts(self.connection).get_active_hosts() if host['status'] == True]
			for name, mac in self.wlan_prefs.items():
				online_status[name] = 'ON' if mac in hosts else 'OFF'
			# send as mqtt message
			logger.info(online_status)
			cmd = 'mosquitto_pub -d -h homematic-raspi -t server/fritz/maconline/'
			for name, status in online_status.items():
				os.system("{}{} -m {}".format(cmd, name, status))
		except Exception as e:
			logger.error("Cannot post MQTT request: {}".format(e))
