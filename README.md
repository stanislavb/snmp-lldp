SNMP LLDP
=========

Build LLDP tree from SNMP information

Prerequisites
-------------
* Net-SNMP with python bindings
* Be able to resolve device IP from name reported through LLDP
* Same SNMP community configured on all devices

**A dirty hack exists in the code to convert FQDN like ’switch.example.com’ to just ’switch’. Look for stripDomainName = True in lldp.py and getinfo.py**

Limitations
-----------
* **Currently this script only handles LLDP for HP ProCurve and Juniper JUNOS devices**
* HP ProCurve firmware I.10.43 and perhaps the whole I-series seems to lack OIDs for model, firmware version, serial number.
* Juniper JUNOS older than version 11 seems to lack LLDP OIDs
* Script can only reach devices which report a resolvable hostname over LLDP and have the same SNMP community configured.
* SNMP version 1 and 2 only
* If a device is connected to another with several ports, only the first port gets registered in the tree.

Future features
---------------
* Network interface information
* VLAN information

lldp.py usage
-------------
Run the script with hostname of a SNMP and LLDP enabled device as argument. That device will become root of the generated lldp tree structure.
<pre>
usage: lldp.py [options] COMMAND HOST

positional arguments:
  COMMAND               list or tree (default: list)
  HOST                  hostname or IP address

optional arguments:
  -h, --help            show this help message and exit
  -c COMMUNITY, --community COMMUNITY
                        SNMP community (default: public)
  -q, --quiet           Do not display or log errors
  -l LOGFILE, --logfile LOGFILE
                        Log file (Default is logging to STDERR)
  -o OIDFILE, --oidfile OIDFILE
                        JSON file containing SNMP OIDs (default: oid.json)

</pre>

If COMMAND is list, the JSON output to STDOUT is a list of hostnames detected recursively through LLDP.
<pre>
[
	"switch001.example.net",
	"switch008.example.net",
	"switch036.example.net",
	# output truncated
]
</pre>

If COMMAND is tree, output is JSON tree structure in following format:
<pre>
{
    "id": "switch001.example.net",
    "children": [
        {
            "id": "switch008.example.net",
            "children": [
                {
                    "id": "switch036.example.net"
                },
                {
                    "id": "switch005.example.net"
                },
                {
                    "id": "switch001.example.net",
                    "children": [
                        {
                            "id": "switch028.example.net"
                        },
                        {
                            "id": "switch019.example.net"
                        },
                        {
                            "id": "switch014.example.net"
                        },
                        {
                            "id": "switch032.example.net"
                        },
                        {
                            "id": "switch045.example.net",
                            "children": [
                                {
                                    "id": "switch056.example.net"
                                }
                            ]
                        }
			# output truncated
                    ]
                }
            ]
        }
    ]
}
</pre>

getinfo.py usage
----------------

getinfo.py is designed to be run with lldp.py list output as input, either through stdin (pipe, for example) or by specifying a text file with the '-f' flag. Something like this:
<pre>
export SNMPCOMMUNITY=secretcommunity
lldp.py list switch001.example.net | getinfo.py > deviceinfo.json
-or-
lldp.py list switch001.example.net > list.json
getinfo.py -f list.json
-or-
lldp.py list switch001.example.net > list.json
cat list.json | getinfo.py
</pre>

Other flags:
<pre>
usage: getinfo.py [-h] [-f INPUTFILE] [-c COMMUNITY] [-q] [-l LOGFILE]
                  [-o OIDFILE]

optional arguments:
  -h, --help            show this help message and exit
  -f INPUTFILE, --inputfile INPUTFILE
                        File to read list of devices from (defaults to reading
                        from stdin)
  -c COMMUNITY, --community COMMUNITY
                        SNMP community (default: public)
  -q, --quiet           Do not display or log errors
  -l LOGFILE, --logfile LOGFILE
                        Log file (Default is logging to STDERR)
  -o OIDFILE, --oidfile OIDFILE
                        JSON file containing SNMP OIDs (default: oid.json)
</pre>

License
-------
Copyright 2013 Stanislav Blokhin (github.com/stanislavb)

This file is part of snmp-lldp.

snmp-lldp is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

snmp-lldp is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with snmp-lldp.  If not, see <http://www.gnu.org/licenses/>.
