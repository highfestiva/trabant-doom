#!/usr/bin/env python3

'''Unpacks Quake I pak0.pak files.'''

from struct import unpack

rdint = lambda b: unpack("<L", b)[0]

d = open('pak0.pak','rb').read()
i,l = 0,len(d)
while i < l:
	if d[i:i+4] == b'PACK':
		doff = rdint(d[i+4:i+8])
		dlen = rdint(d[i+8:i+12])
		print('directory at', doff, dlen)
		rdfiles(d, i+doff, i+doff+dlen)
		i += doff+dlen
