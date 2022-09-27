from PyQt5.QtCore import QPoint, QPointF, QLineF, QRectF
from math import pi, atan2, cos, sin, sqrt


class Line(QLineF):
    def __init__(self, coords):
        self.x1, self.y1, self.x2, self.y2 = coords
        QLineF.__init__(self, QPointF(self.x1, self.y1), QPointF(self.x2, self.y2) )

    @property
    def coords(self):
        return [self.x1, self.y1, self.x2, self.y2]

    def findParallel(self, d):
        """ returns tuple of coordinates for parallel abscissa in distance d"""
        # following is here to ensure that signum of "d" clearly determines
        # the side of line on whitch the parallel is drawn
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



class Rect(QRectF):
    def __init__(self, coords):
        self.x1, self.y1, self.x2, self.y2 = coords
        QRectF.__init__(self, QPointF(self.x1, self.y1), QPointF(self.x2, self.y2) )

    @property
    def coords(self):
        return [self.x1, self.y1, self.x2, self.y2]

    def normalized(self):
        """ returns a rect with non-negative width and height """
        x1, y1, x2, y2 = self.coords
        if x2 < x1:
            x2, x1 = x1, x2
        if y2 < y1:
            y2, y1 = y1, y2
        return Rect([x1, y1, x2, y2])

    def intersects(self, rect):
        return QRectF.intersects(self, rect)

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
    """ point_on_circle(QPoint center, int radius, QPoint direction, int resolution) """
    dx, dy = direction.x()-center.x(), direction.y()-center.y()
    if resolution:
        angle = round( atan2( dy, dx)/(pi*resolution/180.0))*(pi*resolution/180.0)
    else:
        angle = atan2( dy, dx)
    x = center.x() + round( cos( angle) *radius, 2)
    y = center.y() + round( sin( angle) *radius, 2)
    return QPoint(x,y)


def clockwise_angle_from_east( dx, dy):
    """returns the angle in clockwise direction between the center-east line and direction"""
    angle = atan2( dy, dx)
    if angle < 0:
        angle = 2*pi + angle
    return angle


def on_which_side_is_point( line, point, threshold=0):
    """tells whether a point is on one side of a line or on the other (1,0,-1) - 0 is for point on line.
    line is given as sequence of four coordinates, point as sequence of two coords,
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


def within_range(p1 : QPoint, p2 : QPoint, range_):
    """ check if p1 and p2 has x and y difference not higher than range_ """
    diff = p1 - p2
    return abs(diff.x()) <= range_ and abs(diff.y()) <= range_



def point_distance( x1, y1, x2, y2):
    """ calculate distance between two points """
    return sqrt( (x2-x1)**2 + (y2-y1)**2)

"""def rectangles_intersect(rect1, rect2):
    qrect1 = QRectF( QPointF(rect1[0], rect1[1]), QPointF(rect1[2], rect1[3]) )
    qrect2 = QRectF( QPointF(rect2[0], rect2[1]), QPointF(rect2[2], rect2[3]))
    return qrect1.intersects(qrect2)
"""
