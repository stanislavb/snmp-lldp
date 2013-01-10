#!/usr/local/bin/python
# Authors: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

# HP SNMP LLDP OID:
# .1.0.8802.1.1.2.1.4.1.1.5.0.<port number> Local MAC
# .1.0.8802.1.1.2.1.4.1.1.7.0.<port number> Remote port
# .1.0.8802.1.1.2.1.4.1.1.8.0.<port number> Remote port desc
# .1.0.8802.1.1.2.1.4.1.1.9.0.<port number> Remote system name
# .1.0.8802.1.1.2.1.4.1.1.10.0.<port number> Remote system desc

# HP other OID of interest:
# .1.0.8802.1.1.2.1.3.7.1.4.<port number> Actual port name (useful for modules)
# .1.0.8802.1.1.2.1.3.3.0 Local system name
# .1.0.8802.1.1.2.1.3.4.0 Local system desc
# OIDs below not present in I.10.43 firmware:
# .1.0.8802.1.1.2.1.5.4795.1.2.2.0 Hardware revision
# .1.0.8802.1.1.2.1.5.4795.1.2.3.0 Boot ROM firmware version
# .1.0.8802.1.1.2.1.5.4795.1.2.4.0 Current firmware version
# .1.0.8802.1.1.2.1.5.4795.1.2.5.0 Serial number
# .1.0.8802.1.1.2.1.5.4795.1.2.6.0 Manufacturer
# .1.0.8802.1.1.2.1.5.4795.1.2.7.0 Model


import netsnmp
import sys
import logging
from json import dumps, dump

# Config
logging.basicConfig(filename='lldptree.log',level=logging.DEBUG)
# Uncomment to disable INFO and DEBUG level messages.
#logging.disable(logging.INFO)
snmp_community="public"
snmp_version=2
jsonfile='lldptree.json'
oid = dict(remote_names='.1.0.8802.1.1.2.1.4.1.1.9.0',
	   local_ports='.1.0.8802.1.1.2.1.3.7.1.4',
	   sysname='.1.0.8802.1.1.2.1.3.3.0',
	   sysdesc='.1.0.8802.1.1.2.1.3.4.0',
	   firmware='.1.0.8802.1.1.2.1.5.4795.1.2.4.0',
	   serial='.1.0.8802.1.1.2.1.5.4795.1.2.5.0',
	   model='.1.0.8802.1.1.2.1.5.4795.1.2.7.0')

# List of devices we've already checked. We throw in None to eliminate empty records.
checked = set([None])

# returns real local interface name (LLDP uses only numbers while the device might use letters)
def get_port_name(host, port):
	# Did we get an OID?
	if '.' in port:
		# Take the OID's second to last dot separated number. That's our interface.
		logging.debug("get_port_name(): %s: From OID %s port is %s", host, port, port.split('.')[-2])
		port = port.split('.')[-2]
	# <local ports OID>.<port number> is what we're looking for
	ref = netsnmp.Varbind(oid['local_ports'] + "." + port)
	result = netsnmp.snmpget(ref, DestHost=host, Version=snmp_version, Community=snmp_community, Retries=0)
	if result[0]:
		port = ref.val
	logging.debug("get_port_name(): %s: Returning port name %s", host, port)
	return port
		

# returns None if SNMP faioled, or a dict with device info.
def get_device_info(host):
	# Create minimal outline of the device object
	r = dict(sysname=host, neighbours=dict())

	# Get SNMP values for our set of OIDs.
	for var in [ 'sysname', 'sysdesc', 'firmware', 'serial', 'model' ]:
		ref = netsnmp.Varbind(oid[var])
		result = netsnmp.snmpget(ref, DestHost=host, Version=snmp_version, Community=snmp_community, Retries=0)

		if not result[0]:
			# Set SNMP failure flag if sysname failed. Not all devices have all OIDs we ask for
			if var is 'sysname':
				r['snmp_unreachable'] = True
			return r
		else:
			logging.debug("get_device_info(): %s: %s is %s", host, var, ref.val)
			r[var] = ref.val
	return r



# returns None if SNMP failed, or a dict with device info and neighbours.
def neighbours(root):
	global checked
	# Have we already checked this device? Loop prevention.
	if root in checked:
		# Device is checked already. Let's not waste our time.
		logging.debug("neighbours(): %s has already been checked", root)
		return None
	else:
		checked.add(root)
	

	c = get_device_info(root)
	if 'snmp_unreachable' in c:
		# SNMP failed. Bail out.
		return c

	# Overly complicated declaration of what OID we will be checking.
	lldp = netsnmp.VarList(netsnmp.Varbind(oid['remote_names']))

	#ret will be a list of values we got by walking the LLDP tree.
	# lldp VarList will be updated with values we got during the walk.
	# We rather want to use the Varbind objects since we can read
	# port number value from each OID.
	ret = netsnmp.snmpwalk(lldp, DestHost=root, Version=snmp_version, Community=snmp_community, Retries=0)
	logging.debug("neighbours(): %s neighbours are %s", root, ret)

#	if ret:
	for neighbour in lldp:
		# Take the OID's second to last dot separated number. That's our local interface.
		port = get_port_name(root, neighbour.tag)

		#child = neighbour.val
		# Dirty fix for not resolving FQDN properly. This converts 'host.domain.com' into just 'host'.
		child = neighbour.val.split('.')[0]

		logging.debug("neighbours(): %s port %s has neighbour %s", root, port, child)
		# Recursion! Yay!
		n = neighbours(child)
		if n:
			logging.debug("neighbours(): %s: Adding port %s: %s to tree", root, port, n['sysname'])
			c['neighbours'][port] = n

	return c


# We need at least one argument
if len(sys.argv) < 2:
	print("usage: " + sys.argv[0] + " hostname/IP")
        sys.exit(1)

# Index 0 is script name, index 1 is first argument
t = neighbours(sys.argv[1])

# Write to file
with open(jsonfile, 'w') as outfile:
	dump(t, outfile, sort_keys=False, indent=4, separators=(',', ': '))
