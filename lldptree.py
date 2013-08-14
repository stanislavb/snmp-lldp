#!/usr/bin/env python
# Author: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

import netsnmp
import sys
import logging
from json import dumps, dump
from argparse import ArgumentParser
from socket import gethostbyname, gaierror

# Config
# Dirty fix for not resolving FQDN properly. This converts 'host.domain.com' into just 'host'. The hostname argument at command line also has to be without domain.
strip_domain_name = True

default_logfile='lldptree.log'

default_outfile='lldptree.json'

# For output to stdout:
#default_outfile=None

default_community='public'

snmp_version=2

# Uncomment to disable logging.
#logging.disable(logging.INFO)

standard_oid = dict(sysname='SNMPv2-MIB::sysName.0',
		    sysdesc='SNMPv2-MIB::sysDescr.0',
		    contact='SNMPv2-MIB::sysContact.0',
		    location='SNMPv2-MIB::sysLocation.0',
		    uptime='SNMPv2-MIB::sysUpTime.0')

if_oid = dict(port_names='IF-MIB::ifName.',
              port_speeds='IF-MIB::ifSpeed.',      # in bits/s
              port_macs='IF-MIB::ifPhysAddress.')

# LLDP OIDs: (Juniper devices with software older than JUNOS 11 lack 1.0.8802 OID)
lldp_oid = dict(remote_sysnames='.1.0.8802.1.1.2.1.4.1.1.9.',
		remote_sysdescs='.1.0.8802.1.1.2.1.4.1.1.10.',
		remote_ports='.1.0.8802.1.1.2.1.4.1.1.7.',
		remote_portdescs='.1.0.8802.1.1.2.1.4.1.1.8.')


device_oid = dict()
# Found among other on HP ProCurve devices, except I.10.* firmware
device_oid['procurve'] = dict(rev='.1.0.8802.1.1.2.1.5.4795.1.2.2.0',
			      bootfirmware='.1.0.8802.1.1.2.1.5.4795.1.2.3.0',
			      firmware='.1.0.8802.1.1.2.1.5.4795.1.2.4.0',
			      serial='.1.0.8802.1.1.2.1.5.4795.1.2.5.0',
			      manufacturer='.1.0.8802.1.1.2.1.5.4795.1.2.6.0',
			      model='.1.0.8802.1.1.2.1.5.4795.1.2.7.0')

# Found among other on Juniper devices
device_oid['juniper'] = dict(model='SNMPv2-SMI::enterprises.2636.3.1.2.0',
			     serial='SNMPv2-SMI::enterprises.2636.3.1.3.0')

# Command line option parsing and help text (-h)
usage="%(prog)s [options] HOST"
parser = ArgumentParser(usage=usage)
parser.add_argument("host", help="hostname or IP address", metavar="HOST")
parser.add_argument("-c", "--community", default=default_community, help="SNMP community (default: %s)" % default_community)
parser.add_argument("-r", "-m", "--recurse", "--map", dest="recurse", action="store_true", help="Generate recursive map of ID:s and child objects")
parser.add_argument("-i", "--info", action="store_true", help="Populate objects with extra device information where available")
parser.add_argument("-p", "--ports", action="store_true", help="Populate objects with port:device mappings")
parser.add_argument("-l", "--logfile", default=default_logfile, help="Log file (default: %s)" % default_logfile)
parser.add_argument("-o", "--outfile", default=default_outfile, help="JSON output file (default: %s)" % default_outfile)
args = parser.parse_args()

# List of devices we've already checked.
checked = []
logging.basicConfig(filename=args.logfile,level=logging.DEBUG)


#
# returns netsnmp.Varbind object if successful, returns None if not.
# returns netsnmp.VarList if walk is set to True
#
def snmpget(host, var, walk=False):
	# Make sure host is resolvable
	try:
		gethostbyname(host)
	except gaierror:
		logging.debug("snmpget(): Couldn't resolve %s", host)
		return None

	# Make sure we have a Varbind
	if not isinstance(var, netsnmp.Varbind):
		logging.debug("snmpget(): %s Assuming OID %s", host, var)
		var = netsnmp.Varbind(var)

	if walk:
		var = netsnmp.VarList(var)
		result = netsnmp.snmpwalk(var, DestHost=host, Version=snmp_version, Community=args.community, Retries=0)
		if result:
			return var
	else:
		result = netsnmp.snmpget(var, DestHost=host, Version=snmp_version, Community=args.community, Retries=0)
		if var.val:
			logging.debug("snmpget(): %s Got value %s", host, var.val)
			return var
	return None


# Shorthand for snmp walking using the snmpget() function
def snmpwalk(host, var):
	return snmpget(host, var, walk=True)

#
# returns real interface name (LLDP OIDs use only numbers while the device might use letters).
#
def get_port_name(host, port):
	# <port names OID><port number> is what we're looking for
	ref = snmpget(host=host, var=if_oid['port_names'] + str(port))
	if ref:
		port = ref.val
	logging.debug("get_port_name(): %s: Returning port name %s", host, port)
	return port

def get_parent_interface(host, port, subname):
	parentname = subname.split('.')[0]
	logging.debug("get_parent_interface(): Searching for interface name %s", parentname)
	originalport = port
	while True:
		port = int(port) - 1
		name = get_port_name(host, port)
		if name == parentname:
			logging.debug("get_parent_interface(): Found name %s on port number %s", name, port)
			return port
		if parentname not in name:
			logging.debug("get_parent_interface(): Encountered name %s. Giving up.", name)
			# Give up
			return originalport
		

#
# returns port speed
#
def get_port_speed(host, port, format='M'):
	speed = None
	divide = { 'G': 1000000000, 'M': 1000000, 'K': 1000, 'B': 1 }
	if format.upper() not in divide:
		format='M'

        # <port speeds OID><port number> is what we're looking for
        ref = snmpget(host=host, var=if_oid['port_speeds'] + str(port))
        if ref:
                speed_in_bits = int(ref.val)
		speed = speed_in_bits / divide[format.upper()]
        logging.debug("get_port_speed(): %s: Returning port speed %s", host, speed)
        return speed

#		
# returns None if SNMP failed, or a dict with device info.
#
def get_device_info(host):
	# Let's start collecting info
	r = {}
	device_family = None

	# First we poll standard OIDs
	for key in standard_oid:
		ref = snmpget(host=host,var=standard_oid[key])
		if ref:
			logging.debug("get_device_info(): %s: %s is %s", host, key, ref.val)
			r[key] = ref.val
			if key is 'sysdesc':
				# Split into words (space separated), take the first one and lowercase it
				device_family = ref.val.split(' ')[0].lower()
				logging.debug("get_device_info(): Found device family %s", device_family)

	# If we have a device family identified, let's look for a matching set of OIDs
	if device_family in device_oid:
		for key in device_oid[device_family]:
			ref = snmpget(host=host, var=device_oid[device_family][key])
			if ref:
				logging.debug("get_device_info(): %s: %s is %s", host, key, ref.val)
				r[key] = ref.val	
	return r


#
# Collects LLDP neighbours from SMTP information, returns dict of oid:neighbour pairs.
#
def get_neighbours(host):
        # lldp VarList will be updated with values we got during the walk.
        # We rather want to use the Varbind objects since we can read
        # port number value from each OID.
	lldp = snmpwalk(var=lldp_oid['remote_sysnames'], host=host)
	if not lldp:
		return None
	return { x.tag: x.val for x in lldp if x.val }

#
# Returns list of dicts with port name, speed and neighbour.
#
def get_neighbour_port_info(host, neighbours=None):
	portlist = list()
	if not isinstance(neighbours, dict):
		# neighbours is not a dict. Let's get us something to work with.
		neighbours = get_neighbours(host)

	for n in neighbours.keys():
		# Take the OID's second to last dot separated number. That's our local interface.
		portnumber = n.split('.')[-2]
		logging.debug("get_neighbour_port_info(): %s: From OID %s port is %s", host, n, portnumber)
                portname = get_port_name(host, portnumber)
		if '.' in str(portname):
			# Do we have a subinterface?
			portspeed = get_port_speed(host, get_parent_interface(host, portnumber, portname))
		else:
			portspeed = get_port_speed(host, portnumber)

                logging.debug("get_neighbour_port_info(): %s port %s has neighbour %s, speed %s", host, portname, neighbours[n], portspeed)
		portlist.append({'name': portname, 'speed': portspeed, 'neighbour': neighbours[n]})

	return portlist


#
# returns None if SNMP failed, or a dict with device info and neighbours.
#
def branch(host):
	# List of devices we've already checked.
	global checked

	c = {}

	if strip_domain_name:
		host = host.split('.')[0]

	# Sometimes LLDP neighbour reports no name at all
	if not host:
		return None

	if args.info:
		c = get_device_info(host)
	c['id'] = host

	neighbours = get_neighbours(host)
	if not neighbours:
		return c

	if args.recurse:
		children = []
		for x in neighbours.values():
			# Have we already checked this device? Loop prevention.
			if x and (x not in checked):
				logging.debug("branch(): %s has neighbour %s", host, x)
				checked.append(x)
				# Recurse!
				children.append(branch(x))
		if children:
			c['children'] = children
	else:
		c['children'] = neighbours.values()

	if args.ports:
		c['ports'] = get_neighbour_port_info(host, neighbours)

	return c


#
# Writes object to file in JSON format
#
def write_json_file(object, file=args.outfile):
	with open(file, 'w') as outfile:
		dump(object, outfile, sort_keys=False, indent=4, separators=(',', ': '))

t = branch(args.host)

if args.outfile is not None:
	write_json_file(t)
else:
	dumps(t, sort_keys=False, indent=4, separators=(',', ': '))
