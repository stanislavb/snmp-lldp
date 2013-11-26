#!/usr/bin/env python
# Author: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

import netsnmp
import logging
from json import dumps, load
from argparse import ArgumentParser
from socket import gethostbyname, gaierror

# Config
# Dirty fix for not resolving FQDN properly. This converts 'host.domain.com' into just 'host'. The hostname argument at command line also has to be without domain.
strip_domain_name = True

default_community='public'

snmp_version=2

# Command line option parsing and help text (-h)
usage="%(prog)s [options] HOST"
parser = ArgumentParser(usage=usage)
parser.add_argument("host", help="hostname or IP address", metavar="HOST")
parser.add_argument("-c", "--community", default=default_community, help="SNMP community (default: %s)" % default_community)
parser.add_argument("-r", "-m", "--recurse", "--map", dest="recurse", action="store_true", help="Generate recursive map of ID:s and child objects")
parser.add_argument("-i", "--info", action="store_true", help="Populate objects with extra device information where available")
parser.add_argument("-p", "--interfaces", action="store_true", help="Populate objects with interface:device mappings")
parser.add_argument("-l", "--logfile", help="Log file (Default is logging to STDERR)")
parser.add_argument("-o", "--oidfile", default='oid.json', help="JSON file containing SNMP OIDs (default: oid.json)")
args = parser.parse_args()

# List of devices we've already checked.
checked = []

# Logging config
logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
logger.addHandler(ch)
if args.logfile:
	fh = logging.WatchedFileHandler(args.logfile)
	fh.setLevel(logging.DEBUG)
	logger.addHandler(fh)

# Load OID data
with open(args.oidfile) as outfile:
	oid = load(outfile)


#
# returns netsnmp.Varbind object if successful, returns None if not.
# returns netsnmp.VarList if walk is set to True
#
def get(host, var, walk=False):
	# Make sure host is resolvable
	try:
		gethostbyname(host)
	except gaierror:
		logger.error("get(): Couldn't resolve %s", host)
		return None

	var = netsnmp.Varbind(var)

	if walk:
		var = netsnmp.VarList(var)
		result = netsnmp.snmpwalk(var, DestHost=host, Version=snmp_version, Community=args.community, Retries=0)
		if result:
			return var
	else:
		result = netsnmp.snmpget(var, DestHost=host, Version=snmp_version, Community=args.community, Retries=0)
		if var.val:
			logger.debug("get(): %s Got value %s", host, var.val)
			return var
	return None


# Shorthand for snmp walking using the snmpget() function
def walk(host, var):
	return get(host, var, walk=True)

#
# returns real interface name (LLDP OIDs use only numbers while the device might use letters).
#
def get_interface_name(host, interface):
	# <interface names OID><interface number> is what we're looking for
	ref = get(host=host, var=oid['if']['interface_names'] + str(interface))
	if ref:
		interface = ref.val
	logger.debug("get_interface_name(): %s: Returning interface name %s", host, interface)
	return interface

#
# returns interface description
#
def get_interface_desc(host, interface):
	# <interface descriptions OID><interface number> is what we're looking for
	ref = get(host=host, var=oid['if']['interface_descs'] + str(interface))
	if ref:
		desc = ref.val
	logger.debug("get_interface_desc(): %s: Returning interface description %s", host, desc)
	return desc
#
# returns interface ID
#
#def get_interface_by_name(host, interfacename):

#
# given subinterface name as input, finds and returns parent interface ID.
#
def get_parent_interface(host, interface, subname):
	parentname = subname.split('.')[0]
	logger.debug("get_parent_interface(): Searching for interface name %s", parentname)
	originalinterface = interface
	while True:
		interface = int(interface) - 1
		name = get_interface_name(host, interface)
		if name == parentname:
			logger.debug("get_parent_interface(): Found name %s on interface number %s", name, interface)
			return interface
		if parentname not in name:
			logger.debug("get_parent_interface(): Encountered name %s. Giving up.", name)
			# Give up
			return originalinterface

#
# returns interface speed
#
def get_interface_speed(host, interface, format='M'):
	speed = None
	divide = { 'G': 1000000000, 'M': 1000000, 'K': 1000, 'B': 1 }
	if format.upper() not in divide:
		format='M'

        # <interface speeds OID><interface number> is what we're looking for
        ref = get(host=host, var=oid['if']['interface_speeds'] + str(interface))
        if ref:
                speed_in_bits = int(ref.val)
		speed = speed_in_bits / divide[format.upper()]
        logger.debug("get_interface_speed(): %s: Returning interface speed %s", host, speed)
        return speed

#		
# returns None if SNMP failed, or a dict with device info.
#
def get_device_info(host):
	# Let's start collecting info
	r = {}
	device_family = None

	# First we poll standard OIDs
	for key in oid['standard']:
		ref = get(host=host,var=oid['standard'][key])
		if ref:
			logger.debug("get_device_info(): %s: %s is %s", host, key, ref.val)
			r[key] = ref.val
			if key is 'sysdesc':
				# Split into words (space separated), take the first one and lowercase it
				device_family = ref.val.split(' ')[0].lower()
				logger.debug("get_device_info(): Found device family %s", device_family)

	# If we have a device family identified, let's look for a matching set of OIDs
	if device_family in oid['device']:
		for key in oid['device'][device_family]:
			ref = get(host=host, var=oid['device'][device_family][key])
			if ref:
				logger.debug("get_device_info(): %s: %s is %s", host, key, ref.val)
				r[key] = ref.val	
	return r


#
# Collects LLDP neighbours from SMTP information, returns dict of oid:neighbour pairs.
#
def get_neighbours(host):
        # lldp VarList will be updated with values we got during the walk.
        # We rather want to use the Varbind objects since we can read
        # interface number value from each OID.
	lldp = walk(var=oid['lldp']['remote_sysnames'], host=host)
	if not lldp:
		return None
	return { x.tag: x.val for x in lldp if x.val }

#
# Returns list of dicts with interface name, speed and neighbour.
#
def get_neighbour_interface_info(host, neighbours=None):
	interfacelist = list()
	if not isinstance(neighbours, dict):
		# neighbours is not a dict. Let's get us something to work with.
		neighbours = get_neighbours(host)

	for n in neighbours.keys():
		# Take the OID's second to last dot separated number. That's our local interface.
		interfacenumber = n.split('.')[-2]
		logger.debug("get_neighbour_interface_info(): %s: From OID %s interface is %s", host, n, interfacenumber)
                interfacename = get_interface_name(host, interfacenumber)
		if '.' in str(interfacename):
			# Do we have a subinterface?
			interfacespeed = get_interface_speed(host, get_parent_interface(host, interfacenumber, interfacename))
		else:
			interfacespeed = get_interface_speed(host, interfacenumber)

                logger.debug("get_neighbour_interface_info(): %s interface %s has neighbour %s, speed %s", host, interfacename, neighbours[n], interfacespeed)
		interfacelist.append({'name': interfacename, 'speed': interfacespeed, 'neighbour': neighbours[n]})

	return interfacelist


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
				logger.debug("branch(): %s has neighbour %s", host, x)
				checked.append(x)
				# Recurse!
				children.append(branch(x))
		if children:
			c['children'] = children
	else:
		c['children'] = neighbours.values()

	if args.interfaces:
		c['interfaces'] = get_neighbour_interface_info(host, neighbours)

	return c


if __name__ == "__main__":
	t = branch(args.host)

	print(dumps(t, sort_keys=False, indent=4, separators=(',', ': ')))
