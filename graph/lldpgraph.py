#!/usr/local/bin/python
# Authors: Stanislav Blokhin

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

# We take our custom lldp tree json, convert 'sysname' keys into 'id',
# convert dicts of 'neighbours' into lists of 'children' and skip the rest.
def edit_for_graph(before):
	after = {'id': before['sysname'], 'children': list()}
	if 'neighbours' in before:
		for port, node in before['neighbours'].items():
			# RECURSION ENGAGED
			logging.debug("%s has child %s", before['sysname'], node['sysname'])
			c = edit_for_graph(node)
			after['children'].append(c)
	return after

# We need at least one argument
if len(sys.argv) < 2:
	print("usage: " + sys.argv[0] + " json_file")
        sys.exit(1)

with open(sys.argv[1]) as outfile:
	j = edit_for_graph(json.load(outfile))

G = json_graph.tree_graph(j)

# Write dot file to use with graphviz:
# dot -Tpng lldpgraph.dot > lldpgraph.png
nx.write_dot(G, dotfile)

# Same layout using matplotlib
plt.figure(figsize=(40,13))
pos = nx.graphviz_layout(G, prog='dot')
nx.draw(G, pos, alpha=0.5, edge_color='r', font_size=10, font_weight='bold', node_size=0, arrows=False)
plt.savefig(imagefile)
