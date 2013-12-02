#!/usr/bin/env python
# Author: Stanislav Blokhin

import device

d = device.Device("localhost")

print d.hostname

from json import load

with open("oid.json") as outfile:
	oid = load(outfile)

d.snmpConfig(oid)
i = d.getDeviceInfo()

print i
