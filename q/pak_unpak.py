#!/usr/bin/env python3

'''Unpacks Quake I pak0.pak files.'''

from struct import unpack

rdint = lambda b: unpack("<L", b)[0]

def rdfiles(d, i, l):
	while i < l:
		name = d[i:i+56].replace(b'\x00', b'').decode()
		fpos = rdint(d[i+56:i+60])
		flen = rdint(d[i+60:i+64])
		#print(name, fpos, flen)
		if name == 'maps/hip1m1.bsp':
			open(name.split('/')[-1], 'wb').write(d[fpos:fpos+flen])
			print('wrote file', name)
		i += 64

d = open('pak0.pak','rb').read()
i,l = 0,len(d)
while i < l:
	if d[i:i+4] == b'PACK':
		doff = rdint(d[i+4:i+8])
		dlen = rdint(d[i+8:i+12])
		print('directory at', doff, dlen)
		rdfiles(d, i+doff, i+doff+dlen)
		i += doff+dlen
