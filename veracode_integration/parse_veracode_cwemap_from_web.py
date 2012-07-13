#!/usr/bin/python

"""
Instructions: Copy paste the table into a text file name veracode_cwe_list.txt
Then run this.
https://analysiscenter.veracode.com/auth/helpCenter/review/review_cwe.html
"""

f = open('veracode_cwe_list.raw')
inp = [x.strip('\n') for x in f.readlines()]
f.close()

cat = ''
ret = {}
for line in inp:
  if not line[0].isdigit():
    cat = line
    ret[cat] = []
    continue
  zz = line.split('\t')
  ret[cat].append(zz[:3])

f = open('veracode_cwe_map.repr', 'w')
f.write(repr(ret))
f.close()
