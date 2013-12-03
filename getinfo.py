#!/usr/bin/env python
#
# Copyright 2013 Stanislav Blokhin (github.com/stanislavb)
#
# This file is part of snmp-lldp.
#
# snmp-lldp is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# snmp-lldp is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with snmp-lldp.  If not, see <http://www.gnu.org/licenses/>.

import logging
import sys
import json
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
parser = ArgumentParser()
parser.add_argument("-f", "--inputfile", help="File to read list of devices from (defaults to reading from stdin)")
parser.add_argument("-c", "--community", default=defaultCommunity, help="SNMP community (default: %s)" % defaultCommunity)
parser.add_argument("-q", "--quiet", action="store_true", help="Do not display or log errors")
parser.add_argument("-l", "--logfile", default=defaultLogfile, help="Log file (Default is logging to STDERR)")
parser.add_argument("-o", "--oidfile", default=defaultOidfile, help="JSON file containing SNMP OIDs (default: oid.json)")
args = parser.parse_args()

# Logging config
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
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
	c = {"sysname": hostname}

	# Dirty fix, ought to be removed
	if stripDomainName:
		hostname = hostname.split('.')[0]

	d = device.Device(hostname)
	try:
		reachable = d.snmpConfig(oid, snmpVersion, args.community, test=True)
	except:
		reachable = False

	if reachable:
		c.update(d.getDeviceInfo())
	return c

if __name__ == "__main__":
	inputlist = []
	devicelist = []
	inputtext = None

	# Load OID data
	with open(args.oidfile) as oidlist:
		oid = json.load(oidlist)

	if args.inputfile:
		try:
			with open(args.inputfile) as f:
				inputtext = f.read()
		except IOError:
			logger.error("Could not read from file %s" % inputfile)

	if not inputtext:
		if sys.stdin.isatty():
			logger.debug("Detected TTY at STDIN")
			print "Reading list of devices from STDIN. Press ^D when done, or ^C to quit."
		inputtext =  "".join(sys.stdin)

	logger.info(inputtext)
	try:
		inputlist = json.loads(inputtext)
	except ValueError:
		logger.error("No valid JSON detected in input")
		inputlist = inputtext.split()

	for hostname in inputlist:
		devicelist.append(getinfo(hostname))

	print(json.dumps(devicelist, sort_keys=False, indent=4, separators=(',', ': ')))
