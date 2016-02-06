#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Quake prototype, mainly intended for computers.

from trabant import *
from time import time
import floors

# Helper functions.
rotz = lambda a: quat().rotate_z(a)
is_shoot_tap = lambda: (fasttap() or check_reset_time_tap()) if is_touch_device() else click(left=True)

# Load map.
vertices = [(x-240,y+320,z) for floor in floors.floors for x,y,z in floor]
triangles = []
vi = 0
for floor in floors.floors:
    for j in range(1,len(floor)-1):
        triangles += [vi+j,vi+j+1,vi]
    vi += len(floor)
print(vertices)
print(triangles)
create_mesh(vertices, triangles, static=True)

bgcol = vec3(0.4,0.8,1)
bg(col=bgcol)
gravity((0,0,0), friction=0, bounce=0.1)
def create_avatar(pos, col):
    # Create a man-like capsule. OK, maybe not man-like but a capsule then.
    avatar = create_capsule(pos, col=col)
    avatar.create_engine(walk_abs_engine, strength=30, max_velocity=3)
    avatar.floortime = time()
    avatar.powerup = 1
    return avatar
player = create_avatar((-15,0,4), '#00f0')    # Alpha=0 means invisible. We hide in case we use some rendering mode which displays backfacing polygons.
avatars = (player,)
grenades = []
cam(distance=0, fov=60, target=player, target_relative_angle=True)

yaw,pitch = -pi/2,0    # Start looking to the right, towards the center of the map.
#gravity((0,0,-15), friction=1, bounce=4)    # Higer gravity than Earth in Doom. Bounce is a state variable. We want bouncing grenades.

while loop():
    # Update mouse look angles.
    yaw,pitch = yaw-mousemove().x*0.09, pitch-mousemove().y*0.05
    pitch = max(min(pitch,pi/2),-pi/2)    # Allowed to look straight up and straight down, but no further.

    # XY movement relative to the current yaw angle, jumps are controlled with Z velocity.
    xyrot = rotz(yaw)
    player.engine[0].force(xyrot * keydir() * 4 * player.powerup)
    #if keydir().z>0 and time()-player.floortime < 0.1 and timeout(0.3, first_hit=True):
    ## if keydir().z != 0:
        ## player.vel(player.vel()+vec3(0,0,keydir().z*6))
    if keydir().length2() == 0:
        player.vel(vec3()) 

    # Look around.
    cam(angle=(pitch,0,yaw))
    [avatar.avel((0,0,0)) for avatar in avatars]    # Angular velocity. Makes sure the avatars doesn't start rotating for some reason.
    [avatar.orientation(quat()) for avatar in avatars]    # Keep avatars straight at all times.

    # Throw grenades.
    if is_shoot_tap() and timeout(1, timer=2, first_hit=True): # Limit shooting frequency.
            orientation = xyrot.rotate_x(pitch)
            vel = player.vel()
            pos = player.pos() + vel*0.05 + orientation*vec3(0,1,0)
            vel = vel + orientation*vec3(0,10,0)
            grenade = create_sphere(pos=pos, vel=vel, radius=0.05, col='#3a3')
            grenade.starttime = time()
            grenades += [grenade]
            sound(sound_bang, pos)

    # Check if grenade exploded or if a player touched ground.
    for obj,obj2,force,pos in collisions():
        # Store time of last floor touch so we know if we're able to jump.
        if force.z > force.length()/2 and obj in avatars:    # Check that force is mostly aimed upwards (i.e. stepping on ground).
            obj.floortime = time()    # Last time we touched the floor.
