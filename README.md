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
* **Currently this script only handles LLDP for HP ProCurve devices**
* HP ProCurve firmware I.10.43 and perhaps the whole I-series seems to lack OIDs for model, firmware version, serial number.
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
