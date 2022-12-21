from math import pi, atan2, cos, sin, sqrt


class Line:
    def __init__(self, coords):
        self.x1, self.y1, self.x2, self.y2 = coords

    @property
    def coords(self):
        return [self.x1, self.y1, self.x2, self.y2]

    def findParallel(self, d):
        """ returns tuple of coordinates for parallel abscissa in distance d"""
        # following is here to ensure that signum of "d" clearly determines
        # on which side of line the parallel is drawn
        x1, y1, x2, y2 = self.x1, self.y1, self.x2, self.y2
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
        return (x, y, x0, y0)

    def intersectionOfLine(self,line):
        """ returns x,y, 0 if succesful or 1 if parallel
        y=mx+c is used
        parallel_detection_threshold is a negative decadic logarithm of minimal displacement
        of m that is considered parallel """
        x1,y1,x2,y2 = self.coords
        x3,y3,x4,y4 = line
        parallel_detection_threshold=3

        if x1-x2 == 0:
            if x3-x4 == 0:
                return 0,0,1,0 # lines paralell
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
                return 0,0,1,0            #lines paralell
            c2 = y3 - m2 * x3
            c1 = y1 - m1 * x1
            rex = -(c2-c1)/(m2-m1)
            rey = (c1*m2-c2*m1)/(m2-m1)
        #check if point is on the lines
        online1 = Line([x1,y1,x2,y2]).contains([rex,rey])
        online2 = Line([x3,y3,x4,y4]).contains([rex,rey])
        if online1 and online2:
            online = 3
        elif online1:
            online = 1
        elif online2:
            online = 2
        else:
            online = 0
        # x-coord, y-coord , paralell(0 or 1), on line (0=no line, 1=on line 1-2, 2=on line 3-4, 3=on both)
        return rex,rey,0,online

    def contains(self, point):
        """ computes if point is between the points defining the line """
        x1, y1, x2, y2 = self.coords
        x, y = point
        if point_distance(x1,y1,x,y) + point_distance(x2,y2,x,y) > 1.02 * point_distance(x1,y1,x2,y2):
            return False
        return True


# Later, it may be converted to [x,y,w,h] format instead of [x1,y1, x2,y2]
# rect is used in Atom.boundingBox(), SelectTool.onMouseMove()

class Rect:
    def __init__(self, coords):
        self.x1, self.y1, self.x2, self.y2 = coords

    @property
    def coords(self):
        return [self.x1, self.y1, self.x2, self.y2]

    def center(self):
        return [(self.x1+self.x2)/2, (self.y1+self.y2)/2]

    def normalized(self):
        """ returns a rect with non-negative width and height """
        x1, y1, x2, y2 = self.coords
        if x2 < x1:
            x2, x1 = x1, x2
        if y2 < y1:
            y2, y1 = y1, y2
        return Rect([x1, y1, x2, y2])

    def intersects(self, rect):
        """ returns true if this Rect intersects rect """
        xs = [self.x1, self.x2, rect.x1, rect.x2]
        ys = [self.y1, self.y2, rect.y1, rect.y2]

        dx = max( xs) - min( xs) # distance between two most distant vertical edges
        dy = max( ys) - min( ys)

        w1 = abs( self.x1 - self.x2)
        h1 = abs( self.y1 - self.y2)
        w2 = abs( rect.x1 - rect.x2)
        h2 = abs( rect.y1 - rect.y2)

        if w1+w2 > dx and h1+h2 > dy:
            return True
        return False

    def intersectionOfLine(self, line):
        """finds a point where a line and a rectangle intersect,
        line is given as lists of length 4"""
        lx0, ly0, lx1, ly1 = line
        rx0, ry0, rx1, ry1 = self.normalized().coords

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

        if point_distance( lx0, ly0, xx, xy) < point_distance( lx0, ly0, yx, yy):
            return (yx, yy)
        else:
            return (xx, xy)


def point_on_circle( center, radius, direction, resolution = 15):
    """ finds a point in a circle in a particular direction """
    dx, dy = direction[0]-center[0], direction[1]-center[1]
    if resolution:
        angle = round( atan2( dy, dx)/(pi*resolution/180.0))*(pi*resolution/180.0)
    else:
        angle = atan2( dy, dx)
    x = center[0] + round( cos( angle) *radius, 2)
    y = center[1] + round( sin( angle) *radius, 2)
    return x, y


def clockwise_angle_from_east( dx, dy):
    """returns the angle in clockwise direction between the center-east line and direction"""
    angle = atan2( dy, dx)
    if angle < 0:
        angle = 2*pi + angle
    return angle


def on_which_side_is_point( line, point, threshold=0):
    """tells whether a point is on one side of a line or on the other.
    return vals are [1,0,-1] -> 0 is for point on line.
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


def within_range(p1, p2, range_):
    """ check if p1 and p2 has x and y difference not higher than range_ """
    return abs(p1[0]-p2[0]) <= range_ and abs(p1[1]-p2[1]) <= range_



def point_distance( x1, y1, x2, y2):
    """ calculate distance between two points """
    return sqrt( (x2-x1)**2 + (y2-y1)**2)


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
    t.rotateY( atan2( x, z))
    x,y,z = t.transform( *point)
    # Rotate around x-axis so that it will coincide with z-axis
    t.rotateX( -atan2( y, sqrt(x**2+z**2)))
    x,y,z = t.transform( *point)
    if z < 0:
        t.rotateX( pi)
    #t.set_move( *mov)
    return t


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

    def transformPoints( self, points):
        """ transforms a list of [x,y] pairs """
        ret = []
        for pt in points:
            ret.append( self.transform( pt[0], pt[1]))
        return ret

    def transformCoords( self, coords):
        """ transforms a list that cointains alternating x, y values (not list of pairs)"""
        ret = []
        for j in range( 0, len( coords), 2):
            x, y = self.transform( coords[j], coords[j+1])
            ret += [x,y]
        return ret


    def scale(self, scale):
        """ same scaling for both dimensions"""
        self.mat = matrix_multiply_3([[scale,0,0],[0,scale,0],[0,0,1]], self.mat)

    def scaleXY(self, sx, sy):
        self.mat = matrix_multiply_3([[sx,0,0],[0,sy,0],[0,0,1]], self.mat)

    def rotate(self, angle):
        """ rotate counter clockwise (positive direction).
        On the screen, the y-axis is flipped. so it will appear clockwise rotation """
        self.mat = matrix_multiply_3([[cos(angle),-sin(angle),0],[sin(angle),cos(angle),0],[0,0,1]], self.mat)

    def translate(self, dx, dy):
        self.mat = matrix_multiply_3([[1,0,dx],[0,1,dy],[0,0,1]], self.mat)



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

    def transformCoords( self, coords):
        ret = []
        for j in range( 0, len( coords), 3):
            ret += self.transform( coords[j], coords[j+1], coords[j+2])
        return ret

    def transformPoints( self, l):
        ret = []
        for pt in points:
            ret.append( self.transform( pt[0], pt[1], pt[2]))
        return ret

    def translate( self, dx, dy, dz):
        mat = [[1,0,0,dx], [0,1,0,dy], [0,0,1,dz], [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def rotate( self, xa, ya, za):
        self.rotateX( xa)
        self.rotateY( ya)
        self.rotateZ( za)

    def rotateX( self, xa):
        mat = [[1,0,0,0],
               [0, cos(xa), sin(xa), 0],
               [0, -sin(xa), cos(xa), 0],
               [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def rotateY( self, ya):
        mat = [[cos(ya), 0, -sin(ya), 0],
               [0, 1, 0, 0],
               [sin(ya), 0, cos(ya), 0],
               [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def rotateZ( self, za):
        mat = [[cos(za), sin(za), 0, 0],
               [-sin(za), cos(za), 0, 0],
               [0,0,1,0],
               [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def scaleXYZ( self, sx, sy, sz):
        mat = [[sx,0,0,0], [0,sy,0,0], [0,0,sz,0], [0,0,0,1]]
        self.mat = matrix_multiply_4(mat, self.mat)

    def scale( self, scale):
        self.scaleXYZ(scale, scale, scale)

    def getInverse( self):
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
    return (((_m[0][0] * _m[1][1] * _m[2][2]) + (_m[0][1] * _m[1][2] * _m[2][0]) + (_m[0][2] * _m[1][0] * _m[2][1])) - ((_m[2][1] * _m[1][2] * _m[0][0]) + (_m[2][2] * _m[1][0] * _m[0][1]) + (_m[2][0] * _m[1][1] * _m[0][2])))

def matrix_determinant( m):
    _d3 = matrix_determinant_3
    a = m[0][0] * _d3([[m[1][1],m[1][2],m[1][3]],[m[2][1],m[2][2],m[2][3]],[m[3][1],m[3][2],m[3][3]]])
    b = m[0][1] * _d3([[m[1][0],m[1][2],m[1][3]],[m[2][0],m[2][2],m[2][3]],[m[3][0],m[3][2],m[3][3]]])
    c = m[0][2] * _d3([[m[1][0],m[1][1],m[1][3]],[m[2][0],m[2][1],m[2][3]],[m[3][0],m[3][1],m[3][3]]])
    d = m[0][3] * _d3([[m[1][0],m[1][1],m[1][2]],[m[2][0],m[2][1],m[2][2]],[m[3][0],m[3][1],m[3][2]]])
    return a-b+c-d


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
    det = matrix_determinant(mat)
    for i in range(n):
        for j in range(n):
            part = _part( i, j)
            part_det = matrix_determinant_3( part)
            sign = (i+j)%2 and -1.0 or 1.0
            inv[i][j] = sign * part_det / det
    return matrix_transpose(inv)
