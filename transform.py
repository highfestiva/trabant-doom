#!/usr/bin/env python3

from collections import defaultdict
from struct import unpack
from trabant.math import vec3,quat,almosteq
from math import cos,sin

floors   = []
sector_linedefs = []
boxes = []
box_angles = {}
hole_delimitors = {}
column_count = 150
eps = 0.01
cutlimit = 50

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
    #flip_floors()

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
    global floors,box_angles,sector_linedefs,sectors
    sidxes = find_holes()
    print(sidxes)
    print('Adding %i holes.' % len(sidxes))
    for lo_sidx,hi_sidx in sidxes:
        lo,hi = sectors[hi_sidx]
        floor = [(v[0],v[1],lo) for v in floors[lo_sidx]]
        center = sum((vec3(*f) for f in floors[lo_sidx]), vec3()) / len(floors[lo_sidx])
        # Create convex polygons emanating from the hole.
        up = vec3(0,0,1)
        for i in range(0,len(floor)):
            f1,f2 = floor[i-1],floor[i]
            p1,p2 = vec3(*f1),vec3(*f2)
            out = (p2-p1).cross(up)
            if out*((p1+p2)/2-center) < 0:
                out = -out
            box_angles[len(floors)] = out.angle_z(vec3(0,1,0))
            hole_delimitors[len(floors)] = True
            fvs = [vec3(*f) for f in floors[hi_sidx]]
            including = [f for f,p in zip(floors[hi_sidx],fvs) if (p-p1)*out>0]
            floors += [including+[f2,f1]]    # Reverse f order!
            sector_linedefs += [sector_linedefs[lo_sidx]]
            sector_linedefs[hi_sidx] += [(0,0,len(sector_linedefs)-1,-1)]
            sectors += [sectors[lo_sidx]]
            # Drop used vertices.
            drop = including
            if len(drop) > 3:
                if i == 0:  # Exclude extremities on first split.
                    drop.remove(max([(vec3(*f),f) for f in drop], key=lambda vf:(vf[0]-p1).length2())[1])
                    drop.remove(max([(vec3(*f),f) for f in drop], key=lambda vf:(vf[0]-p2).length2())[1])
                for d in drop:
                    floors[hi_sidx].remove(d)
        if len(floors[hi_sidx]) < 3:
            assert False
            floors[hi_sidx] = floors[-1]
            floors = floors[:-1]
            box_angles[hi_sidx] = box_angles[len(floors)]
            del box_angles[len(floors)]

def _get_longest_edges(f):
    lengths,straight_lengths = [],[]
    right,fwd = vec3(1,0,0),vec3(0,1,0)
    for i in range(0,len(f)):
        f1,f2 = f[i-1],f[i]
        p1,p2 = vec3(*f1),vec3(*f2)
        v = p2-p1
        lengths += [(v.length2(), v)]
        if not v*right and not v*fwd:
            straight_lengths += [(v.length2(), v)]
    sl = sorted(straight_lengths, key=lambda e:e[0])[-1][1] if straight_lengths else None
    return sorted(lengths, key=lambda e:e[0])[-1][1], sl

def find_rotated_boxes():
    global floors,box_angles
    for i,f in enumerate(floors):
        if i in box_angles:
            continue
        longest_edge,longest_straight_edge = _get_longest_edges(f)
        if longest_edge*vec3(1,0,0) and longest_edge*vec3(0,1,0) and \
          (longest_straight_edge == None or longest_edge.length() > 1.4*longest_straight_edge.length()):
            #if abs(longest_edge.normalize()*vec3(1,0,0)) < 0.9 and abs(longest_edge.normalize()*vec3(0,1,0)) < 0.9:
            a = longest_edge.angle_z(vec3(1,0,0))
            print('Box %i is rotated %g degrees.' % (i,a*180/3.14159))
            box_angles[i] = a

def _vsplice(vs, i):
    def v(a,b):
        b = b if b <= len(vs) else b-len(vs)
        if a < 0:
                return vs[a:]+vs[:b]
        if b < a:
                return vs[a:]+vs[:b]
        return vs[a:b]
    l = len(vs)//2
    l2 = l + (len(vs)&1)
    #print('_vsplice:', i, i+l+1, i-l2, i+1)
    return v(i,i+l+1), v(i-l2, i+1)

def convexify():
    global floors,sector_linedefs
    i = 0
    while i < len(floors):
        f = floors[i]
        for j in range(0,len(f)):
            f1,f2,f3 = f[j-2],f[j-1],f[j]
            p1,p2,p3 = vec3(*f1),vec3(*f2),vec3(*f3)
            if (p2-p1).cross((p3-p2)).z < 0:
                assert len(f) > 3
                a,b = _vsplice(f, j-1)
                floors[i] = a
                floors += [b]
                sector_linedefs += [sector_linedefs[i]]
                assert len(floors[i]) >= 3 and len(floors[-1]) >= 3
                _flip(i, a)
                _flip(len(floors)-1, b)
                if i in box_angles:
                    box_angles[len(floors)-1] = box_angles[i]
                if i in hole_delimitors:
                    hole_delimitors[len(floors)-1] = True
                i -= 1
                break
        i += 1

def _flip(i, f):
        ps = [vec3(*v) for v in f]
        z = 0
        for j in range(0,len(ps)):
            p1,p2,p3 = ps[j-2],ps[j-1],ps[j]
            z += -1 if (p2-p1).cross(p3-p2).z < 0 else +1
        if z < 0:
            print('flipping floor %i' % i)
            floors[i] = list(reversed(f))

def flip_floors():
    global floors
    # Have all vertices in counter-clockwise order.
    for i,f in enumerate(floors):
        _flip(i, f)

def lowest_neighbor(fidx, m):
    for _,_,rs,ls in sector_linedefs[fidx]:
        if rs >= 0:
            lo,hi = sectors[rs]
            m = min(m,lo)
        if ls >= 0:
            lo,hi = sectors[ls]
            m = min(m,lo)
    return m

def boxify():
    global boxes
    gx,gy,gz = lambda p:p.x, lambda p:p.y, lambda p:p.z
    for i,f in enumerate(floors):
        q,iq = quat(),quat()
        if i in box_angles:
            q  =  q.rotate_z(+box_angles[i])
            iq = iq.rotate_z(-box_angles[i])
        # Rotate and calculate size.
        sps = [q*vec3(*v) for v in f]
        g = lambda f,l: l(f(sps,key=l))
        minx,miny,minz,maxx,maxy,maxz = g(min,gx), g(min,gy), g(min,gz), g(max,gx), g(max,gy), g(max,gz)
        s = maxx-minx, maxy-miny, maxz-minz
        c = iq * vec3((maxx+minx)/2, (maxy+miny)/2, (maxz+minz)/2)
        #print(c,s)
        boxes += [(iq,c,s)]

def _boxcoords(c,s,q=None):
    s1,s2,s3,s4 = -s,s.with_y(-s.y),s,s.with_x(-s.x)
    if q != None:
        s1,s2,s3,s4 = q*s1,q*s2,q*s3,q*s4
    return c+s1,c+s2,c+s3,c+s4

def _midcoords(p1,p2):
    z = (p1.z+p2.z)/2
    s,t = vec3(p1).with_z(z),vec3(p2).with_z(z)
    return s.with_x((s.x+t.x)/2), s.with_y((s.y+t.y)/2), t.with_x((s.x+t.x)/2), t.with_y((s.y+t.y)/2)

def mask_aabb_enclosed(crds, p1,p2):
    mask = 0
    for i,c in enumerate(crds):
        if c.x >= p1.x-eps and c.x <= p2.x+eps and \
           c.y >= p1.y-eps and c.y <= p2.y+eps and \
           c.z >= p1.z-eps and c.z <= p2.z+eps:
            mask |= 1<<i
    return mask

def remove_redundant_boxes():
    global boxes,box_angles,hole_delimitors
    drop = defaultdict(int)
    for i,c in enumerate(boxes):
        ciq,cc,cs = c
        c1,c2,c3,c4 = _boxcoords(vec3(*cc),(vec3(*cs)/2).with_z(0))
        c5,c6,c7,c8 = _midcoords(c1,c3)
        for j,b in enumerate(boxes):
            biq,bc,bs = b
            if i == j or drop[j] == 0xff or ciq.q[0] != 1 or biq.q[0] != 1:
                continue
            b1,_,b2,_ = _boxcoords(vec3(*bc),vec3(*bs)/2)
            mask = mask_aabb_enclosed([c1,c2,c3,c4,c5,c6,c7,c8], b1,b2)
            if mask:
                drop[i] |= mask
    for i,mask in sorted(drop.items(), reverse=True):
        if mask == 0xff:
            print('dropping box', i)
            for j,a in list(box_angles.items()):
                if j > i:
                    del box_angles[j]
                    box_angles[j-1] = a
            for j in list(hole_delimitors.keys()):
                if j > i:
                    del hole_delimitors[j]
                    hole_delimitors[j-1] = True
            del boxes[i]
            del floors[i]

def shrink_rotated_boxes():
    global boxes
    shortened_count = 0
    drop = defaultdict(int)
    for i,c in enumerate(boxes):
        ciq,cc,cs = c
        if ciq.q[0] == 1:
            continue
        #cq = ciq.inverse()
        cc,cs = vec3(*cc),vec3(*cs)
        c1,c2,c3,c4 = _boxcoords(cc,(cs/2).with_z(0), ciq)
        ## cminx,cmaxx = min([c1,c2,c3,c4], key=lambda c:c.x), max([c1,c2,c3,c4], key=lambda c:c.x)
        cminy,cmaxy = min([c1,c2,c3,c4], key=lambda c:c.y), max([c1,c2,c3,c4], key=lambda c:c.y)
        for j,b in enumerate(boxes):
            biq,bc,bs = b
            bc,bs = vec3(*bc),vec3(*bs)/2
            if biq.q[0] != 1 or not almosteq(cc.z+cs.z/2,bc.z+bs.z):
                continue
            bmin,bmax = bc-bs,bc+bs
            ## if cminx.x<bmin.x and cmaxx.x>bmax.x:
                ## bminy,bmaxy = min(bmin.y,bmax.y),max(bmin.y,bmax.y)
                ## mincloser = (abs(cminx.x-bc.x) < abs(cmaxx.x-bc.x))
                ## print('OUT HERE!', i, cminx, cmaxx, bmin, bmax, mincloser, abs(cmaxx.y-bminy), abs(cmaxx.y-bmaxy), (not mincloser and abs(cmaxx.y-bminy)<cutlimit and abs(cmaxx.y-bmaxy)<cutlimit))
                ## if mincloser and abs(cminx.y-bminy)<cutlimit and abs(cminx.y-bmaxy)<cutlimit:
                    ## d = bmin.x-cminx.x
                    ## if d > 0.1:
                        ## print('HERE MIN X!', d)
                        ## if cs.x > cs.y:
                            ## a = vec3(1,0,0).angle_z(cq*vec3(1,0,0))
                            ## v = cq*vec3(d/cos(a),0,0)
                            ## print('vector is:', v, v.length(), cq*vec3(1,0,0))
                            ## cs.x -= v.length()
                            ## cc -= v/2
                            ## print('SHOTENED 1!', i, boxes[i])
                            ## boxes[i] = ciq,tuple(cc),tuple(cs)
                            ## print('SHOTENED 2!', i, boxes[i])
                            ## shortened_count += 1
                        ## break
                ## elif not mincloser and abs(cmaxx.y-bminy)<cutlimit and abs(cmaxx.y-bmaxy)<cutlimit:
                    ## d = cmaxx.x-bmax.x
                    ## if d > 0.1:
                        ## print('HERE MAX X!', d)
                        ## if cs.x > cs.y:
                            ## a = vec3(1,0,0).angle_z(cq*vec3(1,0,0))
                            ## v = cq*vec3(d/cos(a),0,0)
                            ## print('vector is:', v, v.length(), cq*vec3(1,0,0))
                            ## cs.x -= v.length()
                            ## cc -= v/2
                            ## print('SHOTENED 3!', i, boxes[i])
                            ## boxes[i] = ciq,tuple(cc),tuple(cs)
                            ## print('SHOTENED 4!', i, boxes[i])
                            ## print('shortener was', j)
                            ## shortened_count += 1
                        ## break
            if cminy.y<bmin.y and cmaxy.y>bmax.y:
                bminx,bmaxx = min(bmin.x,bmax.x),max(bmin.x,bmax.x)
                mincloser = (abs(cminy.y-bc.y) < abs(cmaxy.y-bc.y))
                print('OUT HERE!', i, j, cminy, cmaxy, bmin, bmax, mincloser, abs(cmaxy.x-bminx), abs(cmaxy.x-bmaxx), (not mincloser and abs(cmaxy.x-bminx)<cutlimit and abs(cmaxy.x-bmaxx)<cutlimit))
                if mincloser and cminy.x-bminx>-cutlimit and cminy.x-bmaxx<cutlimit:
                    # Don't cut on the wrong side of a hole-delimitor.
                    fy1,fy2 = vec3(*floors[i][-1]),vec3(*floors[i][-2])
                    if i in hole_delimitors and ((cminy-fy1).length2()<(bmin-fy1).length2() or (cminy-fy2).length2()<(bmin-fy2).length2()):
                        print('SKIPPING %i due to hole_delimitor.' % i)
                        continue
                    print('NOT HOLE DELIMITOR:', hole_delimitors, fy1,fy2)
                    d = bmin.y-cminy.y
                    if d > 0.1:
                        print('HERE MIN Y!', d)
                        if cs.x > cs.y:
                            a = vec3(0,1,0).angle_z(ciq*vec3(1,0,0))
                            v = ciq*vec3(d/cos(a),0,0)
                            print('vector is:', v, v.length(), ciq*vec3(1,0,0), d, a, cos(a))
                            cs.x -= v.length()
                            cc += v/2
                            print('SHOTENED 1!', i, boxes[i])
                            boxes[i] = ciq,tuple(cc),tuple(cs)
                            print('SHOTENED 2!', i, boxes[i])
                            print('shortener was', j)
                            shortened_count += 1
                        break
                ## elif not mincloser and cmaxy.x-bminx>-cutlimit and cmaxy.x-bmaxx<cutlimit:
                    ## d = cmaxy.y-bmax.y
                    ## if d > 0.1:
                        ## print('HERE MAX Y!', d)
                        ## if cs.x > cs.y:
                            ## a = vec3(0,1,0).angle_z(ciq*vec3(1,0,0))
                            ## v = ciq*vec3(d/cos(a),0,0)
                            ## print('vector is:', v, v.length(), ciq*vec3(1,0,0))
                            ## cs.x -= v.length()
                            ## cc -= v/2
                            ## print('SHOTENED 3!', i, boxes[i])
                            ## boxes[i] = ciq,tuple(cc),tuple(cs)
                            ## print('SHOTENED 4!', i, boxes[i])
                            ## print('shortener was', j)
                            ## shortened_count += 1
                        ## break
    return shortened_count

def set_box_heights():
    global boxes
    gx,gy,gz = lambda p:p.x, lambda p:p.y, lambda p:p.z
    for i,b in enumerate(boxes):
        q,c,s = b
        c,s = vec3(*c),vec3(*s)
        before = minz = c.z-s.z
        minz = lowest_neighbor(i, minz)
        if minz == before:
            minz -= 32
        s.z += before-minz
        c.z -= (before-minz)/2
        boxes[i] = (q,tuple(c),tuple(s))

def output():
    strs = [('%g'%f) for q,c,s in boxes for f in list(c)+list(s)]
    qstrs = [('%g'%f) for q,c,s in boxes for f in q.q]
    scnt = defaultdict(int)
    def e(s):
        scnt[s] += 1
    [e(s) for s in strs+qstrs]
    sidx = [k for k,v in sorted(scnt.items(),key=lambda j:-j[1])]
    s2idx = {k:i for i,kv in enumerate(sorted(scnt.items(),key=lambda j:-j[1])) for k,v in [kv]}
    print(sidx)
    print(s2idx)
    for s in strs:
        #print(s, sidx[s2idx[s]])
        assert s == sidx[s2idx[s]]
    l = ''
    b = ''
    r = ''
    t = 'floor_lookup = ['
    for s in sidx:
        t += '%s,'%s
        if len(t) > column_count:
            l += t+'\n'
            t = ''
    l += t
    t = 'floor_boxes = ['
    for i in strs:
        t += '%s,'%s2idx[i]
        if len(t) > column_count:
            b += t+'\n'
            t = ''
    b += t
    t = 'box_quats = {'
    for i in range(0,len(qstrs),4):
        if qstrs[i] == '1':
            continue
        s = [('%s'%s2idx[qs]) for qs in qstrs[i:i+4]]
        s = ','.join(s)
        t += '%i:(%s),' % (i/4,s)
        if len(t) > column_count:
            r += t+'\n'
            t = ''
    r += t
    print(l+']')
    print(b+']')
    print(r+'}')

assert _vsplice([1,2,3,4], -1) == ([4,1,2],[2,3,4])
assert _vsplice([1,2,3,4], +0) == ([1,2,3],[3,4,1])
assert _vsplice([1,2,3,4], +1) == ([2,3,4],[4,1,2])
assert _vsplice([1,2,3,4], +2) == ([3,4,1],[1,2,3])
assert _vsplice([1,2,3,4,5], -1) == ([5,1,2],[2,3,4,5])
assert _vsplice([1,2,3,4,5], +0) == ([1,2,3],[3,4,5,1])
assert _vsplice([1,2,3,4,5], +1) == ([2,3,4],[4,5,1,2])
assert _vsplice([1,2,3,4,5], +2) == ([3,4,5],[5,1,2,3])
assert _vsplice([1,2,3,4,5], +3) == ([4,5,1],[1,2,3,4])

compress()
verify_base()
create_seg_floors()
create_floor_holes()
flip_floors()
convexify()
find_rotated_boxes()
#flip_floors()
boxify()
set_box_heights()
remove_redundant_boxes()
while shrink_rotated_boxes():
    pass
output()
