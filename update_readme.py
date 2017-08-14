#!/usr/bin/python
#
# This simple script updates ReadMe.md file with stuff that is an output
# of calling other commands. It is assumed that all input files have been
# generated before.
#
# The actual output file that is generated is called ReadMe.md.new

import re

with open('ReadMe.md', 'r') as f:
    readme = f.read()

with open('sync_cli.c', 'r') as f:
    sync_cli = f.read()

m = re.search(r"(.*```c)(.*)(```.*)", readme, re.DOTALL | re.MULTILINE)
if m is None:
    sys.exit("ReadMe.md didn't follow assumed format")

with open('ReadMe.md.new', 'w') as f:
    f.write(m.group(1))
    f.write('\n')
    f.write(sync_cli)
    f.write(m.group(3))
