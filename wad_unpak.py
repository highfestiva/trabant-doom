#!/usr/bin/env python3

'''Unpacks Doom WAD files.'''

from collections import defaultdict
from struct import unpack
from trabant.math import vec3

linedefs = []
sidedefs = []
vertexes = []
segs     = []
ssectors = []
sectors  = []

rdint    = lambda b: unpack("<L", b)[0]
rdshort  = lambda b: unpack("<h", b)[0]
rdushort = lambda b: unpack("<H", b)[0]
intify   = lambda i: -1 if i==0xffff else i

def ldefs(d):
	global linedefs
	for i in range(0, len(d), 14):
		v1,v2,rside,lside = rdushort(d[i+0:i+2]),rdushort(d[i+2:i+4]),rdushort(d[i+10:i+12]),rdushort(d[i+12:i+14])
		rside,lside = intify(rside),intify(lside)
		linedefs += [(v1,v2,rside,lside)]

def sdefs(d):
	global sidedefs
	for i in range(0, len(d), 30):
		side = rdushort(d[i+28:i+30])
		sidedefs += [side]

def vtxs(d):
	global vertexes
	for i in range(0, len(d), 4):
		x,y = rdshort(d[i+0:i+2]),rdshort(d[i+2:i+4])
		x,y = x,y
		vertexes += [(x,y)]

def sgs(d):
	global segs
	for i in range(0, len(d), 12):
		v1,v2,ld,direction = rdushort(d[i+0:i+2]),rdushort(d[i+2:i+4]),rdushort(d[i+6:i+8]),rdushort(d[i+10:i+12])
		segs += [(v1,v2,ld,direction)]

def ssects(d):
	global ssectors
	for i in range(0, len(d), 4):
		seg_cnt,seg_idx = rdushort(d[i+0:i+2]),rdushort(d[i+2:i+4])
		ssectors += [(seg_cnt,seg_idx)]

def sects(d):
	global sectors
	for i in range(0, len(d), 26):
		z1,z2 = rdshort(d[i+0:i+2]),rdshort(d[i+2:i+4])
		z1,z2 = z1,z2
		sectors += [(z1,z2)]

def dowrite(**kwargs):
	s = ''
	for k,v in kwargs.items():
		s += '%s = %s\n' % (k,str(v))
	open('cached.py', 'wt').write(s)

def rdfiles(d, i, c):
	for _ in range(c):
		fpos = rdint(d[i+0:i+4])
		flen = rdint(d[i+4:i+8])
		name = d[i+8:i+16].replace(b'\x00', b'').decode()
		print(name, fpos, flen)
		if name == 'LINEDEFS':
			ldefs(d[fpos:fpos+flen])
		elif name == 'SIDEDEFS':
			sdefs(d[fpos:fpos+flen])
		elif name == 'VERTEXES':
			vtxs(d[fpos:fpos+flen])
		elif name == 'SEGS':
			sgs(d[fpos:fpos+flen])
		elif name == 'SSECTORS':
			ssects(d[fpos:fpos+flen])
		elif name == 'SECTORS':
			sects(d[fpos:fpos+flen])
			dowrite(linedefs=linedefs, sidedefs=sidedefs, vertexes=vertexes, segs=segs, ssectors=ssectors, sectors=sectors)
			break
		i += 16

d = open('Doom1.wad','rb').read()
i,l = 0,len(d)
while i < l:
	if d[i:i+4] == b'IWAD':
		dcnt = rdint(d[i+4:i+8])
		dpos = rdint(d[i+8:i+12])
		print('directory at', dpos, dcnt)
		rdfiles(d, i+dpos, dcnt)
		i += dpos+16*dcnt
	else:
		print('ERROR')
		break
