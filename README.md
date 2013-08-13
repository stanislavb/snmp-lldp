SNMP LLDP
=========

Build LLDP tree from SNMP information

Prerequisites
-------------
* Net-SNMP with python bindings
* Be able to resolve device IP from name reported through LLDP
* Same SNMP community configured on all devices
(a dirty hack exists in the code to convert FQDN like ’switch.example.com’ to just ’switch’)

Limitations
-----------
* **Currently this script only handles LLDP for HP ProCurve and Juniper JUNOS devices**
* HP ProCurve firmware I.10.43 and perhaps the whole I-series seems to lack OIDs for model, firmware version, serial number.
* Juniper JUNOS older than version 11 seems to lack LLDP OIDs
* Script can only reach devices which report a resolvable hostname over LLDP and have the same SNMP community configured.
* SNMP version 1 and 2 only
* If a device is connected to another with several ports, only the first port gets registered in the tree.

Usage
-----
Run the script with hostname of a SNMP and LLDP enabled device as argument. That device will become root of the generated tree.
<pre>
usage: lldptree.py [options] HOST

positional arguments:
  HOST                  hostname or IP address

optional arguments:
  -h, --help            show this help message and exit
  -c COMMUNITY, --community COMMUNITY
                        SNMP community (default: public)
  -m, --map             Generate recursive map of ID:s and child objects
  -i, --info            Populate objects with extra device information where
                        available
  -p, --ports           Populate objects with port:device mappings
  -l LOGFILE, --logfile LOGFILE
                        Log file (default: lldptree.log)
  -o OUTFILE, --outfile OUTFILE
                        JSON output file (default: lldptree.json)
</pre>

As result we get a log file with debug info and a json file generated with highly useful information. JSON object structure includes information gathered through SNMP: system name of the device, system description and for almost all HP ProCurve switches also model, firmware version, serial number and LLDP neighbours in a dict with local port as key (yay, recursion!).

Output examples
---------------

Output always includes an "id" field and a list of "children" which are directly connected devices reported in the LLDP table. The "-m" flag does a recursive lookup.
<pre>
$ lldptree.py -m -c public switch001
$ cat lldptree.json

{
    "id": "switch001",
    "children": [
        {
            "id": "switch008",
            "children": [
                {
                    "id": "switch036"
                },
                {
                    "id": "switch005"
                },
                {
                    "id": "switch001",
                    "children": [
                        {
                            "id": "switch028"
                        },
                        {
                            "id": "switch019"
                        },
                        {
                            "id": "switch014"
                        },
                        {
                            "id": "switch032"
                        },
                        {
                            "id": "switch045",
                            "children": [
                                {
                                    "id": "switch056"
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

The "-i" flag adds some interesting info fields about the device. Different information is available from HP and Juniper devices.

<pre>
$ lldptree.py -i -c public switch001
$ cat lldptree.json 

{
    "sysname": "switch001.example.net",
    "uptime": "1297101183",
    "firmware": "E.11.03",
    "bootfirmware": "E.05.05",
    "sysdesc": "ProCurve J4819A Switch 5308xl, revision E.11.03, ROM E.05.05 (/sw/code/build/alpmo(alp11))",
    "rev": "Rev 0",
    "id": "switch001",
    "children": [
        "switch008.example.net",
        "switch028.example.net",
        "switch019.example.net",
        "switch014.example.net",
        "switch032.example.net",
        "switch045.example.net"
        "switch034.example.net",
        "switch013.example.net",
        "switch033.example.net",
        "switch025.example.net",
        "switch043.example.net",
        "switch029.example.net",
        "switch052.example.net",
        "switch001.example.net",
        "switch002.example.net",
        "switch026.example.net",
        "switch010.example.net",
        "switch060.example.net",
        "switch024.example.net",
        "switch011.example.net"
        "switch049.example.net",
        "switch001.example.net",
        "switch061.example.net",
        "switch030.example.net",
    ],
    "location": "KI1102094",
    "model": "J4819A",
    "serial": "SG78D34XLY ",
    "manufacturer": "Hewlett-Packard"
}
</pre>

The "-p" flag adds a list of ports under "ports" on each device record. Port information includes port speed and port name, including letters on modular HP devices and names like "ge-0/0/0" on Juniper devices. It also differs from the children list in that the port list can contain the same neighbour several times, for example in an LACP connection, and in a recursive lookup it also includes the parent device, which the list of children doesn't include to avoid loops.

<pre>
$ lldptree.py -p -c example-SNMP switch001
$ cat lldptree.json 
{
    "ports": [
        {
            "neighbour": "switch008.example.net",
            "speed": 100,
            "name": "G9"
        },
        {
            "neighbour": "switch028.example.net",
            "speed": 1000,
            "name": "A2"
        },
        {
            "neighbour": "switch019.example.net",
            "speed": 100,
            "name": "C21"
        },
        {
            "neighbour": "switch014.example.net",
            "speed": 100,
            "name": "C3"
        },
        {
            "neighbour": "switch032.example.net",
            "speed": 1000,
            "name": "E1"
        },
        {
            "neighbour": "switch045.example.net",
            "speed": 100,
            "name": "H11"
        }
	# output truncated
    ],
    "id": "switch001",
    "children": [
        "switch008.example.net",
        "switch028.example.net",
        "switch019.example.net",
        "switch014.example.net",
        "switch032.example.net",
        "switch045.example.net"
        "switch034.example.net",
        "switch013.example.net",
        "switch033.example.net",
        "switch025.example.net",
        "switch043.example.net",
        "switch029.example.net",
        "switch052.example.net",
        "switch001.example.net",
        "switch002.example.net",
        "switch026.example.net",
        "switch010.example.net",
        "switch060.example.net",
        "switch024.example.net",
        "switch011.example.net"
        "switch049.example.net",
        "switch001.example.net",
        "switch061.example.net",
        "switch030.example.net"
    ]

}
</pre>
