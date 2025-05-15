# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from math import pi, atan2, cos, sin, asin, sqrt, degrees

# ----- CARTESIAN COORDINATE va SCREEN COORDINATE ---------
# cartesian coordinate system has origin at bottom left, while screen
# coordinate has origin at top left corner i.e it has flipped y-axis.
# this make some differences, such as ...
# 1. Anticlockwise in cartesian system becomes clockwise on screen.
# 2. left side in cartesian, becomes right side on screen.


# ---------------------------- POINT -------------------------------

# Points that are passed to or returned by a function must be a tuple not a list
# It follows the mathematical convention of expressing coordinates as (x,y)

def point_distance( p1, p2):
    """ calculate distance between two points """
    return sqrt( (p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)

def points_within_range(p1, p2, range_):
    """ check if p1 and p2 has x and y difference not higher than range_ """
    return abs(p1[0]-p2[0]) <= range_ and abs(p1[1]-p2[1]) <= range_


# ------------------------------- LINE --------------------------------

def line_contains_point(line, point):
    """ checks if line contains point """
    x1, y1, x2, y2 = line
    x, y = point
    if point_distance((x1,y1), (x,y)) + point_distance((x2,y2), (x,y)) > 1.02 * point_distance((x1,y1),(x2,y2)):
        return False
    return True

def line_length(line):
    return sqrt( (line[2]-line[0])**2 + (line[3]-line[1])**2)


def line_extend_by(line, d):
    """ returns the point upto which it gets extended.
    -ve value of d will make it shorter """
    x1,y1,x2,y2 = line
    if x1-x2 == 0:
        rex = x2
        if y2 > y1:
            rey = y2 + d
        else:
            rey = y2 - d
    else:
        m = (y1-y2)/(x1-x2)
        dx = sqrt( d**2 / (1 + m**2))
        dy = m * dx
        if dy < 0:
            dy=-dy
        if d<0:
            dx,dy = -dx, -dy
        if x2 > x1:
            rex = x2 + dx
        else:
            rex = x2 - dx
        if y2 > y1:
            rey = y2 + dy
        else:
            rey = y2 - dy
    return rex, rey


def line_get_point_at_distance(line, d):
    """ returns a point at perpendicular distance d from line's end point.
    -ve value of d gives point from opposite side (right side on screen) """
    x1,y1,x2,y2 = line
    if round( y2, 3) -round( y1, 3) != 0:
        if y2 < y1:
            d = -d
        k = -(x2-x1)/(y2-y1)
        x0 = ( d + sqrt( k**2 +1)*x2)/ sqrt( k**2 +1)
        y0 = y2 + k*( x0 -x2)
    else:
        if x1 > x2:
            d = -d
        x0 = x2
        y0 = y2 - d
    return x0, y0


def line_get_parallel(line, d):
    """ returns the parallel line at distance d.
    -ve value of d gives line from opposide side (right side on screen) """
    x1, y1, x2, y2 = line
    if round( y2, 3) - round( y1, 3) != 0:
        if y2 < y1:
          d = -d
        k = -(x2-x1)/(y2-y1)
        x = ( d + sqrt( k**2 +1)*x1)/ sqrt( k**2 +1)
        y = y1 + k*( x -x1)
        x0 = ( d + sqrt( k**2 +1)*x2)/ sqrt( k**2 +1)
        y0 = y2 + k*( x0 -x2)
    else:
        if x1 > x2:
          d = -d
        x, x0 = x1, x2
        y = y1 - d
        y0 = y2 - d
    return x,y, x0,y0


def line_get_intersection_of_line(line, line2):
    """ returns x,y, status. (status -> 0=successful, 1=parallel) """
    x1,y1,x2,y2 = line
    x3,y3,x4,y4 = line2
    # parallel_detection_threshold is a negative decadic logarithm of
    # minimal displacement of m that is considered parallel
    parallel_detection_threshold = 3

    if x1-x2 == 0:
        if x3-x4 == 0:
            return 0,0,1 # parallel
        m2 = (y3-y4)/(x3-x4)
        c2 = y3 - m2 * x3
        rex,rey = x1,m2*x1+c2
    elif x3-x4 == 0:
        m1 = (y1-y2)/(x1-x2)
        c1 = y1 - m1 * x1
        rex,rey = x3,m1*x3+c1
    else:
        m1 = (y1-y2)/(x1-x2)
        m2 = (y3-y4)/(x3-x4)
        if round(m1-m2,parallel_detection_threshold) == 0:
            return 0,0,1 # parallel
        c2 = y3 - m2 * x3
        c1 = y1 - m1 * x1
        rex = -(c2-c1)/(m2-m1)
        rey = (c1*m2-c2*m1)/(m2-m1)
    return rex,rey, 0


def line_get_side_of_point( line, point, threshold=0):
    """ tells whether a point is on one side of a line or on the other.
    return vals are 1=left, -1=right, 0=point on line. (sides are for screen coordinate)
    threshold means what smallest angle is considered to still be on the line"""
    x1, y1, x2, y2 = line
    x, y = point
    a = atan2( y-y1, x-x1)
    b = atan2( y2-y1, x2-x1)
    if a*b < 0 and abs(a-b) > pi:
        if a < 0:
          a += 2*pi
        else:
          b += 2*pi
    if abs( a-b) <= threshold or abs( abs( a-b) -pi) <= threshold:
        return 0
    elif a-b < 0:
        return 1
    else:
        return -1


def line_get_angle_from_east(line):
    """ returns the angle between the center-east line and 'line'.
    angle is clockwise on screen """
    angle = atan2( line[3]-line[1], line[2]-line[0])
    if angle < 0:
        angle += 2*pi
    return angle


# ---------------------------- RECTANGLE ---------------------------

# [x1,y1, x2,y2] format is more convinent than [x,y,w,h] format for most calculations

def rect_get_center(rect):
    """ get center of rect i.e intersection of two diagonals """
    return (rect[0]+rect[2])/2, (rect[1]+rect[3])/2


def rect_contains_point(rect, pt):
    x1,y1,x2,y2 = rect_normalize(rect)
    return x1 <= pt[0] <= x2 and y1 <= pt[1] <= y2


def rect_normalize(rect):
    """ returns a rect with non-negative width and height """
    x1, y1, x2, y2 = rect
    if x2 < x1:
        x2, x1 = x1, x2
    if y2 < y1:
        y2, y1 = y1, y2
    return [x1, y1, x2, y2]


def rect_get_intersection_of_line(rect, line):
    """ returns a point where 'line' intersects the rectangle 'rect' """
    lx0, ly0, lx1, ly1 = line
    rx0, ry0, rx1, ry1 = rect_normalize(rect)

    # find which end of line is in the rect and reverse the line if needed
    if (lx0 > rx0) and (lx0 < rx1) and (ly0 > ry0) and (ly0 < ry1):
        lx0, lx1 = lx1, lx0
        ly0, ly1 = ly1, ly0

    # the computation itself
    ldx = lx1 - lx0
    ldy = ly1 - ly0

    if abs( ldx) > 0.0001:
        # we calculate using y = f(x)
        k = ldy/ldx
        q = ly0 - k*lx0
        if ldx < 0:
            xx = rx1
        else:
            xx = rx0
        xy = k*xx + q
        # the result must be in the rectangle boundaries
        # but sometimes is not because rounding problems
        if not ry0 <= xy <= ry1:
            xx = lx0
            xy = ly0
    else:
        xx = lx0
        xy = ly0

    if abs( ldy) > 0.0001:
        # we calculate using x = f(y)
        k = ldx/ldy
        q = lx0 - k*ly0
        if ldy < 0:
            yy = ry1
        else:
            yy = ry0
        yx = k*yy + q
        # the result must be in the rectangle boundaries
        # but sometimes is not because rounding problems
        if not rx0 <= yx <= rx1:
            yy = ly0
            yx = lx0
    else:
        yy = ly0
        yx = lx0

    if point_distance((lx0,ly0), (xx,xy)) < point_distance((lx0,ly0), (yx,yy)):
        return yx, yy
    else:
        return xx, xy


def rect_intersects_rect(rect1, rect2):
    """ returns true if this rect1 intersects rect2 """
    xs = rect1[0], rect1[2], rect2[0], rect2[2]
    ys = rect1[1], rect1[3], rect2[1], rect2[3]

    dx = max( xs) - min( xs) # distance between two most distant vertical edges
    dy = max( ys) - min( ys)

    w1 = abs( rect1[0] - rect1[2] )
    h1 = abs( rect1[1] - rect1[3] )
    w2 = abs( rect2[0] - rect2[2] )
    h2 = abs( rect2[1] - rect2[3] )

    if w1+w2 > dx and h1+h2 > dy:
        return True
    return False


# ---------------------------- POLYGON --------------------------------

def calc_polygon_coords(sides, center, radius):
    """ Calculate the coordinates of a regular polygon """
    coords = []
    angle = pi/2 - pi/sides
    for i in range(sides):
        x = center[0] + round( cos( angle) *radius, 2)
        y = center[1] + round( sin( angle) *radius, 2)
        coords.append((x,y))
        angle += 2*pi/sides
    return coords


# ---------------------------- CIRCLE --------------------------------

def circle_get_point( center, radius, direction, resolution=0):
    """ finds a point in a circle in a particular direction """
    dx, dy = direction[0]-center[0], direction[1]-center[1]
    if resolution:
        angle = round( atan2( dy, dx)/(pi*resolution/180.0))*(pi*resolution/180.0)
    else:
        angle = atan2( dy, dx)
    x = center[0] + round( cos( angle) *radius, 2)
    y = center[1] + round( sin( angle) *radius, 2)
    return x, y


def calc_arc(p1, p2, p3):
    """ returns center, radius, start angle and span angle of the arc through given points """
    x1,y1, x2,y2, x3,y3 = *p1, *p2, *p3

    temp = x2*x2 + y2*y2
    bc = (x1*x1 + y1*y1 - temp) / 2
    cd = (temp - x3*x3 - y3*y3) / 2
    det = (x1-x2)*(y2-y3) - (x2-x3)*(y1-y2)

    if abs(det) < 1.0e-6:
        return (0,0), 0, 0, 0

    # center and radius of circle
    cx = (bc*(y2-y3) - cd*(y1-y2)) / det
    cy = (cd*(x1-x2) - bc*(x2-x3)) / det
    r = sqrt((cx-x1)**2 + (cy-y1)**2)
    # get span angle
    ang1 = degrees(atan2(cy-y1, x1-cx))
    if ang1 < 0: ang1 += 360
    ang2 = degrees(atan2(cy-y2, x2-cx))
    while ang2 < ang1: ang2 += 360
    ang3 = degrees(atan2(cy-y3, x3-cx))
    while ang3 < ang1: ang3 += 360
    span_ang = ang3-ang1 if ang3>ang2 else ang3-ang1-360
    return (cx, cy), r, ang1, span_ang


def other_chord_point(x1, y1, L, cx, cy, clockwise=False):
    """ calculate other point of chord when one point, length and center are given """
    sign = -1 if clockwise else 1
    # calculate radius (distance between center and given point)
    r = sqrt((x1-cx)**2 + (y1-cy)**2)
    if L>2*r:
        return line_get_point_at_distance([cx,cy,x1,y1], -sign*L)
    # calculate anglular distance bewteen given point and midpoint of chord
    ang = asin(L/(2*r))
    x2, y2 = rotate_point(x1,y1, cx,cy, 2*ang*sign)
    return x2, y2


# -------------------------- BEZIER CURVE ------------------------------

def calc_control_points(K):
    n = len(K)-1
    cp1 = [0] * n
    cp2 = [0] * n

    # rhs vector (initialized with left most segment )
    a = [0]
    b = [2]
    c = [1]
    r = [ K[0] + 2*K[1] ]

    # internal segments
    for i in range(1,n-1):
        a.append(1)
        b.append(4)
        c.append(1)
        r.append(4 * K[i] + 2 * K[i+1])

    # right segment
    a.append(2)
    b.append(7)
    c.append(0)
    r.append(8*K[n-1] + K[n])

    # solves Ax=b with the Thomas algorithm (from Wikipedia)
    for i in range(1, n):
        m = a[i]/b[i-1]
        b[i] = b[i] - m * c[i-1]
        r[i] = r[i] - m * r[i-1]

    cp1[n-1] = r[n-1]/b[n-1]
    for i in range(n-2, -1, -1):
        cp1[i] = (r[i] - c[i] * cp1[i+1]) / b[i]

    # we have cp1, now compute cp2
    for i in range(n-1):
        cp2[i] = 2*K[i+1] - cp1[i+1]

    cp2[n-1] = 0.5 * (K[n] + cp1[n-1])

    return cp1, cp2


def calc_spline_through_points(knots):
    # calculate a spline that goes through the 'knots'.
    # returns a list of points like [K1, cp1, cp2, K2, cp3, cp4, K3 ...]
    cp1_x, cp2_x = calc_control_points([p[0] for p in knots])
    cp1_y, cp2_y = calc_control_points([p[1] for p in knots])
    spline = [ knots[0] ]
    for i in range(len(knots)-1):
        spline += [(cp1_x[i],cp1_y[i]), (cp2_x[i],cp2_y[i]), knots[i+1]]
    return spline

def quad_bezier_through_points(knots):
    a, b, c = knots
    cp_x = 2*b[0] - 0.5*a[0] - 0.5*c[0]
    cp_y = 2*b[1] - 0.5*a[1] - 0.5*c[1]
    return [a, (cp_x, cp_y), c]


def quad_to_cubic_bezier(pts):
    # converts a quadratic bezier to cubic bezier
    # 'pts' is list of three points, the middle point is control point.
    a, b, c = pts
    cp1_x = a[0] + 2/3*(b[0] - a[0])
    cp1_y = a[1] + 2/3*(b[1] - a[1])
    cp2_x = c[0] + 2/3*(b[0] - c[0])
    cp2_y = c[1] + 2/3*(b[1] - c[1])
    return [a, (cp1_x, cp1_y), (cp2_x, cp2_y), c]

def bezier_point(c, t):
    xt = pow(1-t,3)*c[0][0] + 3*t*pow(1-t,2)*c[1][0] + 3*pow(t,2)*(1-t)*c[2][0] + pow(t,3)*c[3][0]
    yt = pow(1-t,3)*c[0][1] + 3*t*pow(1-t,2)*c[1][1] + 3*pow(t,2)*(1-t)*c[2][1] + pow(t,3)*c[3][1]
    return xt, yt

def bezier_closest_point(curve, pt):
    scans = 25 # More scans -> better chance of being correct
    d_min = 999999 # or can use sys.maxint
    for i in range(scans, -1, -1):
        # should use squared val of distance, to avoid a sqrt()
        d2 = point_distance(pt, bezier_point(curve, i/scans))
        if (d2<d_min):
            d_min = d2
            d_i = i

    t0 = max((d_i-1)/scans, 0)
    t1 = min((d_i+1)/scans, 1)
    d2_for_t = lambda _t : point_distance(pt, bezier_point(curve, _t))
    t = local_minimum(t0, t1, d2_for_t)
    return bezier_point(curve,t)

""" Find a minimum point for a bounded function. May be a local minimum.
 * minX   : the smallest input value
 * maxX   : the largest input value
 * func      : a function that returns a value `y` given an `x`
 * precision      : how close in `x` the bounds must be before returning
 * returns: the `x` value that produces the smallest `y`
 *"""
def local_minimum(minX, maxX, func, precision=1e-4):
    m = minX
    n = maxX
    while (n-m) > precision:
        k = (n+m)/2
        if (func(k-precision) < func(k+precision)):
            n = k
        else:
            m = k
    return k


# --------------------- Other Helper Functions ------------------------

def get_size_to_fit(w, h, max_w, max_h):
    out_w = max_w
    out_h = max_w/w*h
    if out_h > max_h:
        out_h = max_h
        out_w = max_h/h*w
    return out_w, out_h


def rotate_point(px, py, cx, cy, angle):
    """ rotate the point (px,py) around (cx,cy) by radian angle """
    # Translate the point so that the center of rotation is the origin
    dx = px - cx
    dy = py - cy
    # Perform the rotation
    rot_x = dx*cos(angle) - dy*sin(angle)
    rot_y = dx*sin(angle) + dy*cos(angle)
    # Translate back to the original center, and return
    return cx+rot_x, cy+rot_y



def create_transformation_to_coincide_two_lines(to_transform, ref_line):
    x1,y1,x2,y2 = ref_line
    xt1,yt1,xt2,yt2 = to_transform
    scale_ratio = sqrt( ((x1-x2)**2 + (y1-y2)**2) / ((xt1-xt2)**2 + (yt1-yt2)**2) )
    tfm = Transform()
    tfm.translate( -xt1, -yt1)
    tfm.rotate( atan2( xt1-xt2, yt1-yt2) - atan2( x1-x2, y1-y2))
    tfm.scale(scale_ratio)
    tfm.translate(x1, y1)
    return tfm


def create_transformation_to_coincide_point_with_z_axis( mov, point):
    """takes 3d coordinates 'point' (vector mov->point) and returns a Transform3D
    that performs rotation to get 'point' onto z axis (x,y)=(0,0)
    with positive 'z'.
    NOTE: this is probably far from efficient, but it works
    """
    t = Transform3D()
    # translate line to keep one end at origin
    a,b,c = mov
    t.translate( -a, -b, -c)
    x,y,z = t.transform( *point)
    # Rotate around y axis so that it will lie in the yz-plane
    t.rotate_y( atan2( x, z))
    x,y,z = t.transform( *point)
    # Rotate around x-axis so that it will coincide with z-axis
    t.rotate_x( -atan2( y, sqrt(x**2+z**2)))
    x,y,z = t.transform( *point)
    if z < 0:
        t.rotate_x( pi)
    #t.set_move( *mov)
    return t


def create_transformation_to_rotate_around_line(line, angle):
    a,b,c, u,v,w = line
    u -= a
    v -= b
    w -= c
    u2 = u*u
    v2 = v*v
    w2 = w*w
    cosT = cos(angle)
    sinT = sin(angle)
    l2 = u2 + v2 + w2
    l =  sqrt(l2)

    if (l2 < 0.000000001):
        raise ValueError("RotationMatrix: direction vector too short!")

    m11 = (u2 + (v2 + w2) * cosT)/l2
    m12 = (u*v * (1 - cosT) - w*l*sinT)/l2
    m13 = (u*w * (1 - cosT) + v*l*sinT)/l2
    m14 = (a*(v2 + w2) - u*(b*v + c*w)
        + (u*(b*v + c*w) - a*(v2 + w2))*cosT + (b*w - c*v)*l*sinT)/l2

    m21 = (u*v * (1 - cosT) + w*l*sinT)/l2
    m22 = (v2 + (u2 + w2) * cosT)/l2
    m23 = (v*w * (1 - cosT) - u*l*sinT)/l2
    m24 = (b*(u2 + w2) - v*(a*u + c*w)
        + (v*(a*u + c*w) - b*(u2 + w2))*cosT + (c*u - a*w)*l*sinT)/l2

    m31 = (u*w * (1 - cosT) - v*l*sinT)/l2
    m32 = (v*w * (1 - cosT) + u*l*sinT)/l2
    m33 = (w2 + (u2 + v2) * cosT)/l2
    m34 = (c*(u2 + v2) - w*(a*u + b*v)
        + (w*(a*u + b*v) - c*(u2 + v2))*cosT + (a*v - b*u)*l*sinT)/l2

    t = Transform3D( [[m11,m12,m13,m14],[m21,m22,m23,m24],[m31,m32,m33,m34],[0,0,0,1]])
    return t



# row major matrix is made up of row vectors
# column major matrix is made up column vectors

# Here, and in OpenGl and in most Mathematical texts vectors are considered as column vector.
# For column major matrix and column vector, we pre-multiply the transformation matrix. i.e -
# t' = M * t
# If first scaled, rotated and then translated - then ...
# t' = T * R * S * t = (T * R * S) * t

# In some other cases, row major matrix and row vector is used.
# For a row vector (t), we post-multiply the row-major transformation matrix (M)
# t' = t * M     or t'  =  t * S * R * T  =  t * (S * R * T)

# In both cases, the operation that is applied first has to be written closer to the vector.
# see https://stackoverflow.com/questions/33958379/opengl-transform-matrix-order-is-backwards

# Here we access the matrix element of ith row and j th column by M[i][j]
# As M[i] represents ith row

class Transform:
    """ this class provides basic interface for coordinate transforms """
    def __init__( self, mat = None):
        if mat:
            self.mat = mat
            return
        self.mat = [[1,0,0],[0,1,0],[0,0,1]]

    def transform(self, x, y):
        """ Transform a point """
        x, y, w = matrix_multiply_3(self.mat, [[x], [y], [1]])
        return x[0], y[0]

    def transform_points( self, points):
        """ transforms a list of (x,y) pairs """
        ret = []
        for pt in points:
            ret.append( self.transform( pt[0], pt[1]))
        return ret

    def transform_coords( self, coords):
        """ transforms a list that cointains alternating x, y values (not list of pairs)"""
        ret = []
        for j in range( 0, len( coords), 2):
            x, y = self.transform( coords[j], coords[j+1])
            ret += [x,y]
        return ret


    def scale(self, scale):
        """ same scaling for both dimensions"""
        self.mat = matrix_multiply_3([[scale,0,0],[0,scale,0],[0,0,1]], self.mat)

    def scale_xy(self, sx, sy):
        self.mat = matrix_multiply_3([[sx,0,0],[0,sy,0],[0,0,1]], self.mat)

    def rotate(self, angle):
        """ rotate counter clockwise (positive direction) """
        self.mat = matrix_multiply_3([[cos(angle),-sin(angle),0],[sin(angle),cos(angle),0],[0,0,1]], self.mat)

    def translate(self, tx, ty):
        self.mat = matrix_multiply_3([[1,0,tx],[0,1,ty],[0,0,1]], self.mat)

    def get_scale_x(self):
        return sqrt(self.mat[0][0]**2 + self.mat[1][0]**2)

    def get_scale_y(self):
        return sqrt(self.mat[0][1]**2 + self.mat[1][1]**2)



class Transform3D:
    """ this class provides basic interface for 3D coordinate transforms"""
    def __init__( self, mat=None):
        if mat:
            self.mat = mat
            return
        self.mat = [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]

    def transform( self, x, y, z):
        x, y, z, w = matrix_multiply_4(self.mat, [[x], [y], [z], [1]])
        return x[0], y[0], z[0]

    def transform_coords( self, coords):
        ret = []
        for j in range( 0, len( coords), 3):
            ret += self.transform( coords[j], coords[j+1], coords[j+2])
        return ret

    def transform_points( self, points):
        ret = []
        for pt in points:
            ret.append( self.transform( pt[0], pt[1], pt[2]))
        return ret

    def translate( self, dx, dy, dz):
        mat = [[1,0,0,dx], [0,1,0,dy], [0,0,1,dz], [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def rotate( self, xa, ya, za):
        self.rotate_x( xa)
        self.rotate_y( ya)
        self.rotate_z( za)

    def rotate_x( self, xa):
        mat = [[1,0,0,0],
               [0, cos(xa), sin(xa), 0],
               [0, -sin(xa), cos(xa), 0],
               [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def rotate_y( self, ya):
        mat = [[cos(ya), 0, -sin(ya), 0],
               [0, 1, 0, 0],
               [sin(ya), 0, cos(ya), 0],
               [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def rotate_z( self, za):
        mat = [[cos(za), sin(za), 0, 0],
               [-sin(za), cos(za), 0, 0],
               [0,0,1,0],
               [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def scale_xyz( self, sx, sy, sz):
        mat = [[sx,0,0,0], [0,sy,0,0], [0,0,sz,0], [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def scale( self, scale):
        self.scale_xyz(scale, scale, scale)

    def get_inverse( self):
        return Transform3D(matrix_inverse(self.mat))


# Matrix Multiplication
# A.B = AB where, A = mxn matrix, B = nxp matrix , AB = mxp matrix
# ABij will be the dot product of ith row of A and jth column of B

# This function is restricted to n=3
def matrix_multiply_3(A, B):
    AB = []
    for i in range( len(A)):
        AB.append([])
        for j in range( len(B[0]) ):
            AB[i].append( A[i][0]*B[0][j] + A[i][1]*B[1][j] + A[i][2]*B[2][j] )
    return AB

# This function is restricted to n=4
def matrix_multiply_4(A, B):
    AB = []
    for i in range( len(A)):
        AB.append([])
        for j in range( len(B[0]) ):
            AB[i].append( A[i][0]*B[0][j] + A[i][1]*B[1][j] + A[i][2]*B[2][j] + A[i][3]*B[3][j])
    return AB

# A is a matrix and c is a scalar, then the matrices cA and Ac are obtained
# by left or right multiplying all entries of A by c
def matrix_multiply_scaler(A, c):
    cA = []
    for i in range( len( A)):
        cA.append([])
        for j in range( len(A)):
            cA[i].append( c * A[i][j])
    return cA

# swich rows and columns
def matrix_transpose(mat):
    m = len(mat)
    ret = [[0]*m]*m # mxm matrix
    for i in range(m):
        for j in range(m):
            ret[j][i] = mat[i][j]
    return ret


def matrix_determinant_3( _m):
    return (((_m[0][0] * _m[1][1] * _m[2][2]) + (_m[0][1] * _m[1][2] * _m[2][0]) + (_m[0][2] * _m[1][0] * _m[2][1])) -
            ((_m[2][1] * _m[1][2] * _m[0][0]) + (_m[2][2] * _m[1][0] * _m[0][1]) + (_m[2][0] * _m[1][1] * _m[0][2])))

def matrix_determinant_4( m):
    _d3 = matrix_determinant_3
    a = m[0][0] * _d3([[m[1][1],m[1][2],m[1][3]],[m[2][1],m[2][2],m[2][3]],[m[3][1],m[3][2],m[3][3]]])
    b = m[0][1] * _d3([[m[1][0],m[1][2],m[1][3]],[m[2][0],m[2][2],m[2][3]],[m[3][0],m[3][2],m[3][3]]])
    c = m[0][2] * _d3([[m[1][0],m[1][1],m[1][3]],[m[2][0],m[2][1],m[2][3]],[m[3][0],m[3][1],m[3][3]]])
    d = m[0][3] * _d3([[m[1][0],m[1][1],m[1][2]],[m[2][0],m[2][1],m[2][2]],[m[3][0],m[3][1],m[3][2]]])
    return a-b+c-d

# get inverse of 4x4 matrix
def matrix_inverse(mat):
    def _part( a, b):
        _ret = [[0]*3]*3
        for i in range(n):
            if i == a:
                continue
            elif i > a:
                i2 = i - 1
            else:
                i2 = i
            for j in range(n):
                if j == b:
                    continue
                elif j > b:
                    j2 = j - 1
                else:
                    j2 = j
                _ret[i2][j2] = mat[i][j]
        return _ret

    n = len(mat)
    inv = [[0]*n]*n
    det = matrix_determinant_4(mat)
    for i in range(n):
        for j in range(n):
            part = _part( i, j)
            part_det = matrix_determinant_3( part)
            sign = (i+j)%2 and -1.0 or 1.0
            inv[i][j] = sign * part_det / det
    return matrix_transpose(inv)


# --------------- PLANE --------------------

def plane_normal_from_3_points( point1, point2, point3):
    for point in (point1,point2,point3):
        if None in point:
            return None  # some coords are missing
    x1,y1,z1 = point1
    x2,y2,z2 = point2
    x3,y3,z3 = point3
    #m0 = [[x1,y1,z1],[x2,y2,z2],[x3,y3,z3]]
    m1 = [[1,y1,z1],[1,y2,z2],[1,y3,z3]]
    m2 = [[x1,1,z1],[x2,1,z2],[x3,1,z3]]
    m3 = [[x1,y1,1],[x2,y2,1],[x3,y3,1]]
    #d0 = m0.get_determinant()
    d1 = matrix_determinant_3(m1)
    d2 = matrix_determinant_3(m2)
    d3 = matrix_determinant_3(m3)
    a = d1 #/d0
    b = d2 #/d0
    c = d3 #/d0
    return a,b,c


def angle_between_planes( plane1, plane2):
    a1,b1,c1 = plane1
    a2,b2,c2 = plane2
    cos = (a1*a2 + b1*b2 + c1*c2) / sqrt( a1**2+b1**2+c1**2) / sqrt( a2**2+b2**2+c2**2)
    return cos
