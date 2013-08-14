LLDP graph
==========

Make hopefully pretty graph out of JSON output of the tree generating script.

Requirements (Ubuntu packages)
------------
* python-networkx
* graphviz (to convert dot file to picture)

Usage
-----

The script takes a path to a JSON file as command line argument. It is compatible with JSON output of the tree generating script. It outputs a dot and a png file. The dot file can be converted to a pretty graph.
<pre>
python lldpgraph.py lldptree.json
dot -Tpng lldpgraph.dot > prettygraph.png
</pre>
