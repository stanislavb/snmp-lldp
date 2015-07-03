#!/usr/bin/env python
import snmp

c = snmp.Connection("localhost")

l = [".1.3.6.1.2.1.1.1.0",
     ".1.3.6.1.2.1.1.2.0",
     ".1.3.6.1.2.1.1.3.0",
     ".1.3.6.1.2.1.1.4.0",
     ".1.3.6.1.2.1.1.5.0",
     ".1.3.6.1.2.1.1.6.0",
     ".1.3.6.1.2.1.1.7.0",
     ".1.3.6.1.2.1.1.8.0"]

lmixed = [".1.3.6.1.2.1.1.1.0",
          ".1.3.6.1.2.1.1.2.",
          ".1.3.6.1.2.1.1.3",
          ".1.3.6.1.2.1.1.",
          ".1.3.6.1.2.1.1",
          ".1.3.6.1.2.1.a.b.c.d",
          "1.3.6.1.2.1.1.7.0",
          "test",
          ""]

d = {"sysDescr": ".1.3.6.1.2.1.1.1.0",
     "sysObjectID": ".1.3.6.1.2.1.1.2.0",
     "sysUpTime": ".1.3.6.1.2.1.1.3.0",
     "sysContact": ".1.3.6.1.2.1.1.4.0",
     "sysName": ".1.3.6.1.2.1.1.5.0",
     "sysLocation": ".1.3.6.1.2.1.1.6.0",
     "sysServices": ".1.3.6.1.2.1.1.7.0",
     "sysORLastChange": ".1.3.6.1.2.1.1.8.0"}

dmixed = {"sysDescr": ".1.3.6.1.2.1.1.1.0",
          "sysObjectID": ".1.3.6.1.2.1.1.2.",
          "sysUpTime": ".1.3.6.1.2.1.1.3",
          "sysContact": ".1.3.6.1.2.1.1.",
          "sysName": ".1.3.6.1.2.1.1",
          "sysLocation": ".1.3.6.1.2.1.a.b.c.d",
          "sysServices": "1.3.6.1.2.1.1.7.0",
          "sysORLastChange": "test",
          "nonetest": ""}

# Legit input
r = c.get(".1.3.6.1.2.1.1.1.0")
print r
print not r

r = c.walk(".1.3.6.1.2.1.1.1")
print r
print not r

r = c.populateDict(d)
print r
print not r

r = c.populateList(l)
print r
print not r

r = c.dictGet(d)
print r
print not r
