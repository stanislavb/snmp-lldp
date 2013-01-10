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
lldptree.py switch
</pre>

As result we get a lot of SNMP error messages to STDERR when it fails to resolve LLDP neighbour names. That isn't very useful, is it? But look, there is also a log file with debug info and a json file generated with highly useful information.

JSON object structure includes information gathered through SNMP: system name of the device, system description and for almost all HP ProCurve switches also model, firmware version, serial number and LLDP neighbours in a dict with local port as key (yay, recursion!).
