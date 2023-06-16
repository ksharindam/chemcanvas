# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2022-2023 Arindam Chaudhuri <arindamsoft94@gmail.com>

def list_difference( list_):
  """return a list of differences between list members,
  the list is by 1 shorter than the original"""
  result = []
  for i in range( len( list_)-1):
    result.append( list_[i]-list_[i+1])
  return result


def difference(a, b):
    """ returns (a-b), i.e items of a which are not in b """
    ret = list( a)  # needed for type conversion of tuple for instance
    for i in b:
        if i in ret:
            ret.remove( i)
    return ret

def filter_unique(self, l):
    return list(dict.fromkeys(l)) # keeps order from python 3.7

def bbox_of_bboxes(bboxes):
    if len(bboxes)==0:
        return
    xs = []
    ys = []
    for (x1, y1, x2, y2) in bboxes:
        xs += [x1, x2]
        ys += [y1, y2]
    return [min(xs), min(ys), max(xs), max(ys)]

