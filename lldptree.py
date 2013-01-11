#!/usr/local/bin/python
# Author: Stanislav Blokhin

# FreeBSD requirements:
# Compile net-snmp with python bindings

# Standard OIDs:
# SNMPv2-MIB::sysDescr.0
# SNMPv2-MIB::sysContact.0
# SNMPv2-MIB::sysName.0
# SNMPv2-MIB::sysLocation.0

# IF-MIB::ifName.<port number>
# IF-MIB::ifSpeed.<port number> (in bits/s)
# IF-MIB::ifPhysAddress.<port number> MAC address

# Juniper specific OIDs:
# SNMPv2-SMI::enterprises.2636.3.1.2.0 Model short description
# SNMPv2-SMI::enterprises.2636.3.1.3.0 Serial number

# LLDP OIDs: (Juniper devices seem to lack 1.0.8802 OID)
# .1.0.8802.1.1.2.1.4.1.1.7.0.<port number> Remote port
# .1.0.8802.1.1.2.1.4.1.1.8.0.<port number> Remote port desc
# .1.0.8802.1.1.2.1.4.1.1.9.0.<port number> Remote system name
# .1.0.8802.1.1.2.1.4.1.1.10.0.<port number> Remote system desc
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
from argparse import ArgumentParser
from socket import gethostbyname, gaierror

# Config
default_logfile='lldptree.log'
default_community="public"
snmp_version=2
# Uncomment to disable logging.
#logging.disable(logging.INFO)
oid = dict(remote_names='.1.0.8802.1.1.2.1.4.1.1.9.0',
	   local_ports='IF-MIB::ifName',
	   sysname='SNMPv2-MIB::sysName.0',
	   sysdesc='SNMPv2-MIB::sysDescr.0',
	   contact='SNMPv2-MIB::sysContact.0',
	   location='SNMPv2-MIB::sysLocation.0',
	   firmware='.1.0.8802.1.1.2.1.5.4795.1.2.4.0',
	   serial='.1.0.8802.1.1.2.1.5.4795.1.2.5.0',
	   model='.1.0.8802.1.1.2.1.5.4795.1.2.7.0')

# Command line option parsing and help text (-h)
usage="%(prog)s [options] HOST"
parser = ArgumentParser(usage=usage)
parser.add_argument("host", help="hostname or IP address", metavar="HOST")
parser.add_argument("-c", "--community", default=default_community, help="SNMP community (default: %s)" % default_community)
parser.add_argument("-m", "--map", action="store_true", help="Generate simple map of ID:s and child objects")
parser.add_argument("-i", "--info", action="store_true", help="Populate objects with extra device information where available")
parser.add_argument("-p", "--ports", action="store_true", help="Populate objects with port:device mappings")
parser.add_argument("-l", "--logfile", default=default_logfile, help="Log file (default: %s)" % default_logfile)
args = parser.parse_args()

logging.basicConfig(filename=args.logfile,level=logging.DEBUG)
# List of devices we've already checked.
checked = set()

#
# returns netsnmp.Varbind object if successful, returns None if not.
#
def snmpget(host, var):
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
	result = netsnmp.snmpget(var, DestHost=host, Version=snmp_version, Community=args.community, Retries=0)
	if result:
		logging.debug("snmpget(): %s Got value %s", host, result)
		return var
	else:
		return None

#
# returns real local interface name (LLDP uses only numbers while the device might use letters).
#
def get_port_name(host, port):
	# Did we get an OID?
	if '.' in port:
		# Take the OID's second to last dot separated number. That's our interface.
		logging.debug("get_port_name(): %s: From OID %s port is %s", host, port, port.split('.')[-2])
		port = port.split('.')[-2]
	# <local ports OID>.<port number> is what we're looking for
	ref = netsnmp.Varbind(oid['local_ports'] + "." + port)
	result = netsnmp.snmpget(ref, DestHost=host, Version=snmp_version, Community=args.community, Retries=0)
	if result[0]:
		port = ref.val
	logging.debug("get_port_name(): %s: Returning port name %s", host, port)
	return port

#		
# returns None if SNMP failed, or a dict with device info.
#
def get_device_info(host):
	# Create minimal outline of the device object
	r = dict(sysname=host, neighbours=dict())

	# Get SNMP values for our set of OIDs.
	for var in [ 'sysname', 'sysdesc', 'contact', 'location', 'firmware', 'serial', 'model' ]:
		ref = snmpget(host=host, var=oid[var])

		if not ref:
			# Set SNMP failure flag if sysname failed. Not all devices have all OIDs we ask for
			if var is 'sysname':
				r['snmp_unreachable'] = True
			return r
		else:
			logging.debug("get_device_info(): %s: %s is %s", host, var, ref.val)
			r[var] = ref.val
	return r

#
# Collects LLDP neighbours from SMTP information, returns dict of port:neighbour pairs
#
def get_lldp_neighbours(host):
	neighbours = dict()

        # Overly complicated declaration of what OID we will be checking.
        lldp = netsnmp.VarList(netsnmp.Varbind(oid['remote_names']))

        #ret will be a list of values we got by walking the LLDP tree.
        # lldp VarList will be updated with values we got during the walk.
        # We rather want to use the Varbind objects since we can read
        # port number value from each OID.
        ret = netsnmp.snmpwalk(lldp, DestHost=host, Version=snmp_version, Community=args.community, Retries=0)
        logging.debug("get_lldp_neighbours(): %s neighbours are %s", host, ret)

        for neighbour in lldp:
                # Take the OID's second to last dot separated number. That's our local interface.
                port = get_port_name(host, neighbour.tag)

                #child = neighbour.val
                # Dirty fix for not resolving FQDN properly. This converts 'host.domain.com' into just 'host'.
                child = neighbour.val.split('.')[0]

                logging.debug("get_lldp_neighbours(): %s port %s has neighbour %s", host, port, child)
                # Recursion! Yay!
                n = branch(child)
                if n:
                        logging.debug("get_lldp_neighbours(): %s: Adding port %s: %s to tree", host, port, n['sysname'])
                        neighbours[port] = n
	return neighbours


#
# returns None if SNMP failed, or a dict with device info and neighbours.
#
def branch(host):
	global checked

	# Sometimes LLDP neighbour reports no name at all
	if not host:
		return None

	# Have we already checked this device? Loop prevention.
	if host in checked:
		# Device is checked already. Let's not waste our time.
		logging.debug("branch(): %s has already been checked", host)
		return None
	else:
		checked.add(host)

	c = get_device_info(host)
	if 'snmp_unreachable' in c:
		# SNMP failed. Bail out.
		return c

	c['neighbours'] = get_lldp_neighbours(host)
	return c


t = branch(args.host)

# Write to file
with open('lldptree.json', 'w') as outfile:
	dump(t, outfile, sort_keys=False, indent=4, separators=(',', ': '))
