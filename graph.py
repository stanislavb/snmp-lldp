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

# Generates graph from getinfo.py JSON output

import sys
import json
import argparse
from os import getenv
import logging
import pydot

# Logging config
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Globals
checked = []
graph = pydot.Dot(graph_type='graph', ranksep='1')
# Parse json input from file, return object(s) or None
def get_object_from_file(filename):
	inputtext = None
	j = None
	# Open and read file
	try:
		with open(filename) as f:
			inputtext = f.read()
	except IOError:
		logger.error("Could not read from file %s" % filename)
		return None
	# Try to parse text as json
	try:
		j = json.loads(inputtext)
	except ValueError:
		logger.error("No valid JSON detected in input")
	# Return parsed object or None
	return j

# Parse json input from stdin, return object(s) or None
def get_object_from_stdin():
	inputtext = None
	j = None
	# Read STDIN if it is not a TTY
	if not sys.stdin.isatty():
		inputtext =  "".join(sys.stdin)
	else:
		logger.debug("Detected TTY at STDIN")
		return None
	# Try to parse text as json
	try:
		j = json.loads(inputtext)
	except ValueError:
		logger.error("No valid JSON detected in input")
	# Return parsed object or None
	return j

def build_graph(devicelist, root):
	global checked
	global graph

	if not devicelist:
		logger.error("Device list empty.")
		return None

	if root in checked:
		logger.warning("%s already checked. Skipping." % root)
		return None

	checked.append(root)
	device = devicelist.get(root)

	if not device:
		logger.error("No data on %s" % root)
		return None

	logger.info("Checking %s" % device.get('sysname'))

	if device.get('if') is not None:
		for interface in device.get('if'):
			logger.info("Device %s has neighbour %s" % (device.get('sysname'), interface.get('neighbour')))
			if interface.get('neighbour') not in checked:
				logger.info("Adding relationship to graph")
				edge = pydot.Edge(device.get('sysname'), interface.get('neighbour'), minlen='1.5')
				if interface.get('speed', 10) > 100:
					edge.set_style('bold')										
				graph.add_edge(edge)
				build_graph(devicelist, interface.get('neighbour'))

if __name__ == "__main__":
	# Fallback values
	defaultInfofile = getenv('INFOFILE', 'info.json')
	defaultLogfile = getenv('LOGFILE', None)
	defaultOutfile = getenv('OUTFILE', 'graph.png')

	# Parse command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("root", help="Device to put as root of the graph", metavar="ROOT")
	parser.add_argument("-i", "-f", "--infofile", default=defaultInfofile,
			    help="File to read info about devices from (default: %s, failing that: stdin)" % defaultInfofile)
	parser.add_argument("-o", "--outfile", default=defaultOutfile, help="File to write to (default: %s)" % defaultOutfile)
	parser.add_argument("-l", "--logfile", default=defaultLogfile, help="Log file (default is logging to STDERR)")
	parser.add_argument("-q", "--quiet", action="store_true", help="Do not display or log errors")
	parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity when using logfile.")
	args = parser.parse_args()

	# In the logging module, following levels are defined:
	# Critical: 50, Error: 40, Warn: 30, Info: 20, Debug: 10
	# args.verbose holds the number of '-v' specified.
	# We substract 10 times that value from our default of 40 (Error)
	# If we go too low, use value 10 (Debug)
	loglevel = min((40 - (args.verbose * 10)), 10)

	# Logging handlers
	# If file name provided for logging, write detailed log.
	if args.logfile:
		fh = logging.FileHandler(args.logfile)
		fh.setLevel(loglevel)
		logger.addHandler(fh)
	else:
		# By default, log to stderr.
		ch = logging.StreamHandler()
		ch.setLevel(logging.ERROR)
		logger.addHandler(ch)
	# If quiet mode, disable all logging.
	if args.quiet:
		logger.disabled = True

	# Main logic
	devicelist = get_object_from_file(args.infofile)
	if not devicelist:
		devicelist = get_object_from_stdin()
	if not devicelist:
		logger.error("No JSON found in %s or in stdin. Giving up." % args.infofile)
		sys.exit()

	build_graph(devicelist, args.root)	

	graph.write_png(args.outfile)

