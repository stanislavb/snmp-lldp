#!/usr/bin/env python
# Author: Stanislav Blokhin

import snmp
import logging
from json import dumps, load, loads
from argparse import ArgumentParser
from os import getenv
import fileinput
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
parser = ArgumentParser()
parser.add_argument("-c", "--community", default=defaultCommunity, help="SNMP community (default: %s)" % defaultCommunity)
parser.add_argument("-q", "--quiet", action="store_true", help="Do not display or log errors")
parser.add_argument("-l", "--logfile", default=defaultLogfile, help="Log file (Default is logging to STDERR)")
parser.add_argument("-o", "--oidfile", default=defaultOidfile, help="JSON file containing SNMP OIDs (default: oid.json)")
args = parser.parse_args()

# Logging config
logger = logging.getLogger(__name__)
# By default, log to stderr.
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
logger.addHandler(ch)
# If file name provided for logging, write detailed log.
if args.logfile:
	fh = logging.FileHandler(args.logfile)
	fh.setLevel(logging.DEBUG)
	logger.addHandler(fh)
# If quiet mode, disable all logging.
if args.quiet:
	logger.disabled = True

def getinfo(hostname):
	c = {"hostname": hostname}

	# Dirty fix, ought to be removed
	if stripDomainName:
		host = host.split('.')[0]

	try:
		d = device.Device(host)
		d.snmpConfig(oid, snmpVersion, args.community)
	except snmp.ResolveError:
		return c
	c.update(d.getDeviceInfo())
	return c

if __name__ == "__main__":
	# Load OID data
	with open(args.oidfile) as outfile:
		oid = load(outfile)

	for line in lineinput.input():
		inputtext+=str(line)
	inputlist = loads(inputtext)

	for hostname in inputlist:
		t.append(getinfo(hostname))

	print(dumps(t, sort_keys=False, indent=4, separators=(',', ': ')))
