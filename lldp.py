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

# FreeBSD requirements:
# Compile net-snmp with python bindings

import logging
from json import dumps, load
from argparse import ArgumentParser
from os import getenv
import device

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
parser.add_argument("-q", "--quiet", action="store_true", help="Do not display or log errors")
parser.add_argument("-l", "--logfile", default=defaultLogfile, help="Log file (Default is logging to STDERR)")
parser.add_argument("-o", "--oidfile", default=defaultOidfile, help="JSON file containing SNMP OIDs (default: oid.json)")
args = parser.parse_args()

# List of devices we've already checked.
checked = []

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

#
# returns None if SNMP failed, or a dict with device info and neighbours.
#
def gettree(host, trunk="id", branches="children"):
	# List of devices we've already checked.
	global checked
	c = {trunk: host}

	try:
		d = device.Device(host)
		d.snmpConfig(oid, snmpVersion, args.community)
	except:
		return c

	neighbours = d.getNeighbours()
	if not neighbours:
		return c

	children = []

	# Have we already checked this device? Loop prevention.
	for x in neighbours.values():
		if x and (x not in checked):
			logger.debug("%s has neighbour %s", host, x)
			# Recurse!
			checked.append(x)
			children.append(gettree(x))
	if children:
		c[branches] = children
	return c

if __name__ == "__main__":
	# Load OID data
	with open(args.oidfile) as oidlist:
		oid = load(oidlist)

	checked.append(args.host)
	t = gettree(args.host)

	if "tree" not in args.command:
		t = checked

	print(dumps(t, sort_keys=False, indent=4, separators=(',', ': ')))
