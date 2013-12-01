#!/usr/bin/env python
# Author: Stanislav Blokhin

import snmp
import logging

logger = logging.getLogger(__name__)

class Device:
	__doc__ = "Networked device"

	__init__(self, hostname):
		self.hostname = hostname

	snmpConfig(self, oid, version=2, community="public"):
		self.snmp = snmp.Connection(host=self.hostname, version=version, community=community)
		self.oid = oid	

	#
	# returns real interface name (LLDP OIDs use only numbers while the device might use letters).
	#
	def getInterfaceName(self, interface):
		# <interface names OID><interface number> is what we're looking for
		name = self.snmp.get(oid['if']['interface_names'] + str(interface))
		if name:
			interface = name
		logger.debug("Returning interface name %s", interface)
		return interface

	#
	# returns interface description
	#
	def getInterfaceDesc(self, interface):
		# <interface descriptions OID><interface number> is what we're looking for
		desc = self.snmp.get(oid['if']['interface_descs'] + str(interface))
		logger.debug("Returning interface description %s", desc)
		return desc
	#
	# returns interface ID
	#
	#def getInterfaceByName(self, interfacename):

	#
	# given subinterface name as input, finds and returns parent interface ID.
	#
	def getParentInterface(self, interface, subname):
		parentname = subname.split('.')[0]
		logger.debug("Searching for interface name %s", parentname)

		originalinterface = interface
		while True:
		interface = int(interface) - 1
			name = getInterfaceName(interface)
			if name == parentname:
				logger.debug("Found name %s on interface number %s", name, interface)
				return interface
			if parentname not in name:
				logger.debug("Encountered name %s. Giving up.", name)
				# Give up
				return originalinterface

	#
	# returns interface speed
	#
	def getInterfaceSpeed(self, interface, format='M'):
		speed = None
		divide = { 'G': 1000000000, 'M': 1000000, 'K': 1000, 'B': 1 }
		if format.upper() not in divide:
			format='M'

	        # <interface speeds OID><interface number> is what we're looking for
        	speed = self.snmp.get(oid['if']['interface_speeds'] + str(interface))
	        if speed:
        	        speedInBits = int(speed)
			speed = speedInBits / divide[format.upper()]
	        logger.debug("Returning interface speed %s", speed)
	        return speed


	def getDeviceInfo(self):
		# Let's start collecting info
		r = {}
		self.deviceFamily = None

		# First we poll standard OIDs
		deviceinfo = self.snmp.populateDict(oid['standard'])
		if 'sysdesc' in oidvalues:
			# Split into words (space separated), take the first one and lowercase it
			self.deviceFamily = deviceinfo['sysdesc'].split(' ')[0].lower()
			logger.debug("Found device family %s", self.deviceFamily)
		
		# If we have a device family identified, let's look for a matching set of OIDs
		if self.deviceFamily in oid['device']:
			familyinfo = self.snmp.populateDict(oid['device'][self.deviceFamily]
			deviceinfo = deviceinfo + familyinfo

		self.info = deviceinfo
		return deviceinfo


	#
	# Collects LLDP neighbours from SMTP information, returns dict of oid:neighbour pairs.
	#
	def getNeighbours(self):
		lldp = self.snmp.walk(oid['lldp']['remote_sysnames'])
		if not lldp:
			return None
		return lldp

	#
	# Returns list of dicts with interface name, speed and neighbour.
	#
	def getNeighbourInterfaceInfo(self, neighbours=None):
		interfacelist = list()
		if not isinstance(neighbours, dict):
			# neighbours is not a dict. Let's get us something to work with.
			neighbours = getNeighbours()

		for n in neighbours.keys():
			# Take the OID's second to last dot separated number. That's our local interface.
			interfacenumber = n.split('.')[-2]
			logger.debug("From OID %s interface is %s", n, interfacenumber)
        	        interfacename = getInterfaceName(interfacenumber)
			if '.' in str(interfacename):
				# Do we have a subinterface?
				interfacenumber = getParentInterface(interfacenumber, interfacename)
				
			interfacespeed = getInterfaceSpeed(interfacenumber)

        	        logger.debug("%s interface %s has neighbour %s, speed %s", self.hostname, interfacename, neighbours[n], interfacespeed)
			interfacelist.append({'name': interfacename, 'speed': interfacespeed, 'neighbour': neighbours[n]})

		return interfacelist
