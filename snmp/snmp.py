#!/usr/bin/env python
# FreeBSD requirements:
# Compile net-snmp with python bindings

import netsnmp
import logging
from socket import gethostbyname, gaierror

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ResolveError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Connection:
    __doc__ = "SNMP connection to a single host, containing common data like authentication"

    # Configuring SNMP session towards a single host.
    def __init__(self, host, version=2, community='public'):
        logger.debug("Creating snmp.Connection instance for host %s" % host)
        # Make sure host is resolvable
        try:
            gethostbyname(host)
        except gaierror:
            logger.warning("Cannot resolve host %s" % host)
            raise ResolveError("Couldn't resolve hostname %s" % host)

        self.session = netsnmp.Session(DestHost=host, Version=version, Community=community, Retries=0)

    # SNMP get on a single OID. Returns value or None.
    def get(self, var):
        try:
            varlist = netsnmp.VarList(var)
        except TypeError:
            logger.debug("SNMP get on OID %s failed with TypeError.", var)
            return None

        self.session.get(varlist)
        if varlist[0].val:
            logger.debug("Got value %s", varlist[0].val)
            return varlist[0].val

        logger.debug("SNMP get on OID %s failed.", var)
        return None

    # SNMP walk on an OID. Returns dict of {OID: value} pairs or None.
    def walk(self, var):
        try:
            varlist = netsnmp.VarList(var)
        except TypeError:
            logger.debug("SNMP get on OID %s failed with TypeError.", var)
            return None

        result = self.session.walk(varlist)
        if result:
            return {x.tag: x.val for x in varlist if x.val}

        logger.debug("SNMP walk on OID %s failed.", var)
        return None

    # Optimization attempt. Assemble a VarList of desired OIDs, run a single session,
    # then reassemble values into dict to return.
    def dictGet(self, indict):
        outdict = {}
        varlist = netsnmp.VarList()
        for key in indict:
            oid = indict[key]
            try:
                varbind = netsnmp.Varbind(oid)
            except TypeError:
                break
            # Using a key here that netsnmp library is unlikely to implement in the future.
            varbind.snmp_dict_key = key
            varlist.varbinds.append(varbind)

        # Magic happens
        self.session.get(varlist)

        for varbind in varlist:
            if varbind.val:
                outdict[varbind.snmp_dict_key] = varbind.val
        return outdict

    # Try walking the OID, then getting it.
    # Why walk first? Walk will succeed on more variations of misspelled OIDs,
    # Either with missing bits of hierarchy or a forgotten trailing dot.
    def walkGet(self, var):
        result = self.walk(var)
        if not result:
            logger.debug("Since walk failed, trying get.")
            result = self.get(var)
        return result

    # Takes dict of OIDs as input, returns dict with values.
    def populateDict(self, indata, keepValuesOnFailure=False):
        outdata = {}
        for key in indata:
            oid = indata[key]
            value = self.walkGet(oid)
            if value:
                outdata[key] = value
            elif keepValuesOnFailure:
                logger.debug("%s: OID %s is invalid, keeping it", key, oid)
                outdata[key] = oid
        return outdata

    # Takes list of OIDs as input, returns list of values.
    # When is this even useful?
    def populateList(self, indata, keepValuesOnFailure=False):
        outdata = []
        for oid in indata:
            value = self.walkGet(oid)
            if value:
                outdata.append(value)
            elif keepValuesOnFailure:
                logger.debug("OID %s is invalid, keeping it", oid)
                outdata.append(oid)
        return outdata
