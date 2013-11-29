#!/usr/bin/env python
# Author: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

import netsnmp
import logging
from socket import gethostbyname, gaierror

class ResolveError(Exception):
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
			raise ResolveError("Couldn't resolve hostname %s" % host)

		self.session = netsnmp.Session(DestHost=host, Version=version, Community=community, Retries=0)

	def get(self, var):
		var = netsnmp.VarList(var)
		result = self.session.get(var)
		if var[0].val:
			logger.debug("get(): %s Got value %s", host, var[0].val)
			return var[0].val
		return None
	
	def walk(self, var):
		var = netsnmp.VarList(var)
		result = self.session.walk(var)
		if result:
			return { x.tag: x.val for x in var if x.val }
		return None

	def walkget(self, var):
		result = self.walk(var)
		if not result:
			result = self.get(var)
		return result

	def populatedict(self, indata):
		outdata = dict.fromkeys(indata)
		for key, oid in indata:
			value = self.walkget(oid)
			if not value:
				# invalid OID - keep old value
				outdata[key] = oid
			else:
				outdata[key] = value
		return outdata

	def populatelist(self, indata):
		outdata = []
		for oid in indata:
			value = self.walkget(oid)
			if not value:
				# invalid OID - keep old value
				outdata.append(oid)
			else:
				outdata.append(value)
		return outdata
