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

# Generates graph from lldptree.py JSON output
#
# Linux requirements:
# apt-get install python-networkx

import sys, json
import networkx as nx
import matplotlib.pyplot as plt
import logging
import networkx as nx
from networkx.readwrite import json_graph

# Config
dotfile = 'lldpgraph.dot'
imagefile = 'lldpgraph.png'
logging.basicConfig(filename='lldpgraph.log',level=logging.DEBUG)
# Uncomment to disable INFO and DEBUG level messages.
#logging.disable(logging.INFO)

# We need at least one argument
if len(sys.argv) < 2:
	print("usage: " + sys.argv[0] + " json_file")
        sys.exit(1)

with open(sys.argv[1]) as outfile:
	j = json.load(outfile)

G = json_graph.tree_graph(j)

# Write dot file to use with graphviz:
# dot -Tpng lldpgraph.dot > lldpgraph.png
nx.write_dot(G, dotfile)

# Same layout using matplotlib
plt.figure(figsize=(40,13))
pos = nx.graphviz_layout(G, prog='dot')
nx.draw(G, pos, alpha=0.5, edge_color='r', font_size=10, font_weight='bold', node_size=0, arrows=False)
plt.savefig(imagefile)
