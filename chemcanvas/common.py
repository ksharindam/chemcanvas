
def list_difference( list_):
  """return a list of differences between list members,
  the list is by 1 shorter than the original"""
  result = []
  for i in range( len( list_)-1):
    result.append( list_[i]-list_[i+1])
  return result


def difference( a,b):
    "returns difference of 2 lists ( a-b)"
    ret = list( a)  # needed for type conversion of tuple for instance
    for i in b:
        if i in ret:
            ret.remove( i)
    return ret

def filter_unique(self, l):
    return list(dict.fromkeys(l)) # keeps order from python 3.7
