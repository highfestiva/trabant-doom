#!/usr/bin/env python3

from collections import defaultdict
from struct import unpack
from trabant.math import vec3

floors   = []
sector_linedefs = []

for l in open('level.py'):
	k,v = l.split(' = ')
	# print(k, v)
	# print()
	globals()[k] = eval(v)

def verify_base():
	# print(linedefs)
	# print(vertexes)
	# print(sectors)
	# print()
	# s = (40,)
	# for v1,v2,rs,ls in linedefs:
		# if rs in s or ls in s:
			# print(v1,v2,rs,ls)
	# print()
	for v1,v2,rs,ls in linedefs:
		assert v1 >= 0 and v1 < len(vertexes) and v2 >= 0 and v2 < len(vertexes)
		assert rs >= -1 and rs < len(sectors) and ls >= -1 and ls < len(sectors)

def compress():
	global linedefs, sidedefs, sectors
	# s = list(set(sectors))
	# vd = []
	# for sidx in sidedefs:
		# sector = sectors[sidx]
		# new_idx = s.index(sector)
		# vd += [new_idx]
	# sidedefs = vd
	# sectors = s
	for i,l in enumerate(linedefs):
		v1,v2,rside,lside = l
		rsect = -1 if rside < 0 else sidedefs[rside]
		lsect = -1 if lside < 0 else sidedefs[lside]
		linedefs[i] = (v1,v2,rsect,lsect)

def create_seg_floors():
	global floors,sector_linedefs
	fs = []
	for si,sd in enumerate(sectors):
		lo,hi = sd
		lds = [(v1,v2,rs,ls) for v1,v2,rs,ls in linedefs if rs==si or ls==si]
		sector_linedefs += [lds]
		v_lds = defaultdict(list)
		for v1,v2,rs,ls in lds:
			v_lds[v1] += [(v1,v2,rs,ls)]
			v_lds[v2] += [(v1,v2,rs,ls)]
		head = min(lds, key=lambda ld: min(ld[0],ld[1]))
		ld = head
		head_vidx = min(head[0],head[1])
		vidx = max(head[0],head[1])
		v = [head_vidx]
		#d = []
		while vidx != head_vidx:
			v += [vidx]
			#d += [ld]
			adjoining = v_lds[vidx]
			ld = adjoining[0] if adjoining[0] != ld else adjoining[1]
			vidx = ld[0] if ld[0] != vidx else ld[1]
		fs += [(lo,v)]
	for s,f in enumerate(fs):
		fl = []
		z,v = f
		for vidx in v:
			x,y = vertexes[vidx]
			fl += [(x,y,z)]
		floors += [fl]
	correct_floors()

def find_holes():
	holes = []
	for sidx,lds in enumerate(sector_linedefs):
		print(sidx, lds)
		other_sidxes = [(rs if ls==sidx else ls) for _,_,rs,ls in lds]
		sidx2 = other_sidxes[0]
		if len(set(other_sidxes)) == 1 and sidx2 >= 0:
			print('checking for hole (or pedistal):', sidx, sidx2)
			lo1,hi1 = sectors[sidx]
			lo2,hi2 = sectors[sidx2]
			if lo1 < lo2:
				print('adding hole!')
				holes += [(sidx,sidx2)]
	return holes

def create_floor_holes():
	global floors
	sidxes = find_holes()
	print(sidxes)
	print('Adding %i holes.' % len(sidxes))
	for lo_sidx,hi_sidx in sidxes:
		lo,hi = sectors[hi_sidx]
		floor = [(v[0],v[1],lo) for v in floors[lo_sidx]]
		# Create convex polygons emanating from the hole.
		up = vec3(0,0,1)
		for i in range(0,len(floor)):
			f1,f2 = floor[i-1],floor[i]
			p1,p2 = vec3(*f1),vec3(*f2)
			out = (p2-p1).cross(up)
			fvs = [vec3(*f) for f in floors[hi_sidx]]
			including = [f for f,p in zip(floors[hi_sidx],fvs) if (p-p1)*out>=0]
			floors += [including+[f2,f1]]	# reverse f order!
		floors[hi_sidx] = floors[-1]
		floors = floors[:-1]

def convexify():
	global floors
	for i,f in enumerate(floors):
		# Attempt starting at center corner if concave.
		f1,f2 = f[:2]
		p1,p2 = vec3(*f1),vec3(*f2)
		for j in range(2,len(f)):
			f3 = f[j]
			p3 = vec3(*f3)
			if (p2-p1).cross((p3-p2)).z < 0:
				f = f[j-1:] + f[:j-1]
				floors[i] = f
				break
			p2 = p3
		# Break up if still concave
		f1,f2 = f[:2]
		p1,p2 = vec3(*f1),vec3(*f2)
		for j in range(2,len(f)):
			f3 = f[j]
			p3 = vec3(*f3)
			if (p2-p1).cross((p3-p2)).z < 0:
				if j < 5:
					# Just split two ways and try again later.
					print('splitting', f)
					floors += [f[-2:]+f[:2]]
					floors += [f[2:-2]]
					floors[i] = []
				else:
					g = f[j-2:]+f[:1]
					floors[i] = f[:j-2]
					floors += [g]
					print(floors[i], floors[-1])
					assert floors[i] and floors[-1]
				break
			p2 = p3
	# Drop empty floors.
	floors = [f for f in floors if f]

def correct_floors():
	global floors
	# Have all vertices in counter-clockwise order.
	for i,f in enumerate(floors):
		p1,p2,p3 = [vec3(*v) for v in f[:3]]
		if (p2-p1).cross(p3-p2).z < 0:
			print('flipping floor %i' % i)
			floors[i] = list(reversed(f))

def output():
	print('floors = [')
	for f in floors:
		print(str(f)+',')
	print(']')


compress()
verify_base()
create_seg_floors()
create_floor_holes()
#convexify()
correct_floors()
output()
