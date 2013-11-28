#!/usr/bin/env python
# Author: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

import snmp
import logging
from json import dumps, load
from argparse import ArgumentParser
from socket import gethostbyname, gaierror

# Config
# Dirty fix for not resolving FQDN properly. This converts 'host.domain.com' into just 'host'. The hostname argument at command line also has to be without domain.
stripDomainName = True

# Fallback values
defaultCommunity = 'public'
defaultLogfile = None
defaultOidfile = 'oid.json'
snmpVersion=2

# Command line option parsing and help text (-h)
usage="%(prog)s [options] HOST"
parser = ArgumentParser(usage=usage)
parser.add_argument("host", help="hostname or IP address", metavar="HOST")
parser.add_argument("-c", "--community", default=defaultCommunity, help="SNMP community (default: %s)" % defaultCommunity)
parser.add_argument("-r", "-m", "--recurse", "--map", dest="recurse", action="store_true", help="Generate recursive map of ID:s and child objects")
parser.add_argument("-i", "--info", action="store_true", help="Populate objects with extra device information where available")
parser.add_argument("-p", "--interfaces", action="store_true", help="Populate objects with interface:device mappings")
parser.add_argument("-q", "--quiet", action="store_true", help="Do not display or log errors")
parser.add_argument("-l", "--logfile", default=defaultLogfile, help="Log file (Default is logging to STDERR)")
parser.add_argument("-o", "--oidfile", default=defaultOidfile, help="JSON file containing SNMP OIDs (default: oid.json)")
args = parser.parse_args()

# List of devices we've already checked.
checked = []

# Logging config
logger = logging.getLogger(__name__)
# By default, log to stderr.
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
logger.addHandler(ch)
# If file name provided for logging, write detailed log.
if args.logfile:
	fh = logging.WatchedFileHandler(args.logfile)
	fh.setLevel(logging.DEBUG)
	logger.addHandler(fh)
# If quiet mode, disable all logging.
if args.quiet:
	logger.disabled = True

# Load OID data
with open(args.oidfile) as outfile:
	oid = load(outfile)

#
# returns None if SNMP failed, or a dict with device info and neighbours.
#
def branch(host):
	# List of devices we've already checked.
	global checked

	c = {}

	if stripDomainName:
		host = host.split('.')[0]

	# Sometimes LLDP neighbour reports no name at all
	if not host:
		return None

	try:
		d = Device(host)
		d.snmpConfig(

	if args.info:
		c = getDeviceInfo(host)
	c['id'] = host

	neighbours = getNeighbours(host)
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
		c['interfaces'] = getNeighbourInterfaceInfo(host, neighbours)

	return c


if __name__ == "__main__":
	t = branch(args.host)

	print(dumps(t, sort_keys=False, indent=4, separators=(',', ': ')))
