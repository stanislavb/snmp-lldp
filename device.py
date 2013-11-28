#!/usr/bin/env python
# Author: Stanislav Blokhin

import snmp
import logging

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
		ref = self.snmp.get(oid['if']['interface_names'] + str(interface))
		if ref:
			interface = ref.val
		logger.debug("%s: Returning interface name %s", host, interface)
		return interface

	#
	# returns interface description
	#
	def getInterfaceDesc(self, interface):
		# <interface descriptions OID><interface number> is what we're looking for
		ref = self.snmp.get(oid['if']['interface_descs'] + str(interface))
		if ref:
			desc = ref.val
		logger.debug("%s: Returning interface description %s", host, desc)
		return desc
	#
	# returns interface ID
	#
	#def getInterfaceByName(self, interfacename):

	#
	# given subinterface name as input, finds and returns parent interface ID.
	#
	def getParentInterface(host, interface, subname):
		parentname = subname.split('.')[0]
		logger.debug("Searching for interface name %s", parentname)
		originalinterface = interface
		while True:
		interface = int(interface) - 1
			name = getInterfaceName(host, interface)
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
	def getInterfaceSpeed(host, interface, format='M'):
		speed = None
		divide = { 'G': 1000000000, 'M': 1000000, 'K': 1000, 'B': 1 }
		if format.upper() not in divide:
			format='M'

	        # <interface speeds OID><interface number> is what we're looking for
        	ref = self.snmp.get(oid['if']['interface_speeds'] + str(interface))
	        if ref:
        	        speedInBits = int(ref.val)
			speed = speedInBits / divide[format.upper()]
	        logger.debug("%s: Returning interface speed %s", host, speed)
	        return speed


	def getDeviceInfo(host):
		# Let's start collecting info
		r = {}
		self.deviceFamily = None

		# First we poll standard OIDs
		for key in oid['standard']:
			ref = self.snmp.get(oid['standard'][key])
			if ref:
				logger.debug("g%s: %s is %s", host, key, ref.val)
				self.info[key] = ref.val
				if key is 'sysdesc':
					# Split into words (space separated), take the first one and lowercase it
					self.deviceFamily = ref.val.split(' ')[0].lower()
					logger.debug("Found device family %s", self.deviceFamily)

		# If we have a device family identified, let's look for a matching set of OIDs
		if self.deviceFamily in oid['device']:
			for key in oid['device'][self.deviceFamily]:
				ref = self.snmp.get(oid['device'][self.deviceFamily][key])
				if ref:
					logger.debug("%s: %s is %s", host, key, ref.val)
					r[key] = ref.val
		self.info = r
		return r


	#
	# Collects LLDP neighbours from SMTP information, returns dict of oid:neighbour pairs.
	#
	def getNeighbours(host):
	        # lldp VarList will be updated with values we got during the walk.
	        # We rather want to use the Varbind objects since we can read
	        # interface number value from each OID.
		lldp = self.snmp.walk(oid['lldp']['remote_sysnames'])
		if not lldp:
			return None
		return { x.tag: x.val for x in lldp if x.val }

	#
	# Returns list of dicts with interface name, speed and neighbour.
	#
	def getNeighbourInterfaceInfo(host, neighbours=None):
		interfacelist = list()
		if not isinstance(neighbours, dict):
			# neighbours is not a dict. Let's get us something to work with.
			neighbours = getNeighbours(host)

		for n in neighbours.keys():
			# Take the OID's second to last dot separated number. That's our local interface.
			interfacenumber = n.split('.')[-2]
			logger.debug("%s: From OID %s interface is %s", host, n, interfacenumber)
        	        interfacename = getInterfaceName(host, interfacenumber)
			if '.' in str(interfacename):
				# Do we have a subinterface?
				interfacenumber = getParentInterface(host, interfacenumber, interfacename)
				
			interfacespeed = getInterfaceSpeed(host, interfacenumber)

        	        logger.debug("%s interface %s has neighbour %s, speed %s", host, interfacename, neighbours[n], interfacespeed)
			interfacelist.append({'name': interfacename, 'speed': interfacespeed, 'neighbour': neighbours[n]})

		return interfacelist

