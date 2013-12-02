#!/usr/bin/env python
# Author: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

import snmp
import logging
from json import dumps, load
from argparse import ArgumentParser
from os import getenv

import device

# Config
# Dirty fix for not resolving FQDN properly. This converts 'host.domain.com' into just 'host'. The hostname argument at command line also has to be without domain.
stripDomainName = True

# Fallback values
defaultCommunity = getenv('SNMPCOMMUNITY', 'public')
defaultLogfile = getenv('LOGFILE', None)
defaultOidfile = getenv('OIDFILE', 'oid.json')
snmpVersion=2

# Command line option parsing and help text (-h)
usage="%(prog)s [options] COMMAND HOST"
parser = ArgumentParser(usage=usage)
parser.add_argument("command", help="list or tree (default: list)", metavar="COMMAND")
parser.add_argument("host", help="hostname or IP address", metavar="HOST")
parser.add_argument("-c", "--community", default=defaultCommunity, help="SNMP community (default: %s)" % defaultCommunity)
#parser.add_argument("-r", "-m", "--recurse", "--map", dest="recurse", action="store_true", help="Generate recursive map of ID:s and child objects")
#parser.add_argument("-i", "--info", action="store_true", help="Populate objects with extra device information where available")
#parser.add_argument("-p", "--interfaces", action="store_true", help="Populate objects with interface:device mappings")
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

#
# returns None if SNMP failed, or a dict with device info and neighbours.
#
def gettree(host, trunk="id", branches="children"):
	# List of devices we've already checked.
	global checked
	checked.append(host)
	c = {}

	# Sometimes LLDP neighbour reports no name at all
	if not host:
		return None

	# Dirty fix, ought to be removed
	if stripDomainName:
		host = host.split('.')[0]

	try:
		d = device.Device(host)
		d.snmpConfig(oid, snmpVersion, args.community)
	except snmp.ResolveError:
		return None

	c[trunk] = host

	neighbours = d.getNeighbours()
	if not neighbours:
		return c

	children = []
	for x in neighbours.values():
		# Have we already checked this device? Loop prevention.
		if x and (x not in checked):
			logger.debug("%s has neighbour %s", host, x)
			# Recurse!
			children.append(gettree(x))
	if children:
		c[branches] = children
	else:
		c[branches] = neighbours.values()
	return c

if __name__ == "__main__":
	# Load OID data
	with open(args.oidfile) as outfile:
		oid = load(outfile)

	t = gettree(args.host)

	if "tree" not in args.command:
		t = checked

	print(dumps(t, sort_keys=False, indent=4, separators=(',', ': ')))
