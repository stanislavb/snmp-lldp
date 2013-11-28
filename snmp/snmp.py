#!/usr/bin/env python
# Author: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

import netsnmp
import logging
from socket import gethostbyname, gaierror

class HostnameError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Connection:
	__doc__ = "SNMP connection to a single host, containing common data like authentication"

	def __init__(self, host, version=2, community='public'):
		# Make sure host is resolvable
		try:
			gethostbyname(host)
		except gaierror:
			raise HostnameError("Couldn't resolve hostname %s", host)

		self.session = netsnmp.Session(DestHost=host, Version=version, Community=community, Retries=0)

	#
	# returns netsnmp.Varbind object if successful, returns None if not.
	# returns netsnmp.VarList if walk is set to True
	#
	def get(self, var, walk=False):
		var = netsnmp.Varbind(var)

		if walk:
			var = netsnmp.VarList(var)
			result = self.session.snmpwalk(var)
			if result:
				return var
		else:
			result = self.session.snmpget(var)
			if var.val:
				logger.debug("get(): %s Got value %s", host, var.val)
				return var
		return None
	
	# Shorthand for snmp walking using the snmpget() function
	def walk(self, var):
		return get(host, var, walk=True)

