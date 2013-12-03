#!/usr/bin/env python
# Author: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

import netsnmp
import logging
from socket import gethostbyname, gaierror

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ResolveError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Connection:
	__doc__ = "SNMP connection to a single host, containing common data like authentication"

	def __init__(self, host, version=2, community='public'):
		logger.debug("Creating snmp.Connection instance for host %s" % host)
		# Make sure host is resolvable
		try:
			gethostbyname(host)
		except gaierror:
			logger.warning("Cannot resolve host %s" % host)
			raise ResolveError("Couldn't resolve hostname %s" % host)

		self.session = netsnmp.Session(DestHost=host, Version=version, Community=community, Retries=0)

	def get(self, var):
		try:
			varlist = netsnmp.VarList(var)
		except TypeError:
			logger.debug("SNMP get on OID %s failed with TypeError.", var)
			return None

		result = self.session.get(varlist)
		if varlist[0].val:
			logger.debug("Got value %s", varlist[0].val)
			return varlist[0].val

		logger.debug("SNMP get on OID %s failed.", var)
		return None
	
	def walk(self, var):
		try:
			varlist = netsnmp.VarList(var)
		except TypeError:
			logger.debug("SNMP get on OID %s failed with TypeError.", var)
			return None

		result = self.session.walk(varlist)
		if result:
			return { x.tag: x.val for x in varlist if x.val }

		logger.debug("SNMP walk on OID %s failed.", var)
		return None

	def walkGet(self, var):
		result = self.walk(var)
		if not result:
			logger.debug("Since walk failed, trying get.")
			result = self.get(var)
		return result

	def populateDict(self, indata, keepValuesOnFailure=False):
		outdata = {}
		for key in indata:
			oid = indata[key]
			value = self.walkGet(oid)
			if value:
				outdata[key] = value
			elif keepValuesOnFailure:
				logger.debug("%s: OID %s is invalid, keeping it", key, oid)
				outdata[key] = oid
		return outdata

	def populateList(self, indata, keepValuesOnFailure=False):
		outdata = []
		for oid in indata:
			value = self.walkGet(oid)
			if value:
				outdata.append(value)
			elif keepValuesOnFailure:
				logger.debug("OID %s is invalid, keeping it", oid)
				outdata.append(oid)
		return outdata
