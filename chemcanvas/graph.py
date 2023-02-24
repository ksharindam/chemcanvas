#!python3
from functools import reduce
import operator, warnings


class Vertex:
    """simple vertex class, normaly would not be needed but it can speed up many analytical tasks
    to store data directly in vertex and not get them from the graph connectivity matrix.
    vertex has a value attribute used to store arbitrary object"""

    def __init__( self):
        # TODO : rename properties_ to properties
        self.properties_ = {} # used to store intermediate properties such as distances etc.
        #self.value = None  # used to store any object associated with the vertex
        self._neighbors = {} # set of all neighbors in {edge:vertex} format

    @property
    def degree(self):
        return len(self.neighbors)

    @property
    def neighbors(self):
        return [v for (e,v) in self._neighbors.items() if not e.disconnected]

    @property
    def neighbor_edges(self):
        return [e for e in self._neighbors.keys() if not e.disconnected]

    @property
    def edges(self):
        return list( self._neighbors.keys() )

    def addNeighbor(self, v, e):
        """ adds a neighbor connected via e"""
        self._neighbors[e] = v

    def removeNeighbor(self, v):
        to_del = None
        for k, vv in self._neighbors.items():
            if v == vv:
                to_del = k
                break
        if to_del:
            del self._neighbors[ to_del]
        else:
            raise Exception("cannot remove non-existing neighbor")

    def getNeighborConnectedVia(self, e):
        return self._neighbors[ e]

    def getEdgeLeadingTo(self, vtx):
        for e, v in self._neighbors.items():
          if v == vtx:
            return e
        return None

    def getNeighborsWithDistance(self, d):
        ret = []
        for v in self.neighbors:
          if 'd' in v.properties_ and v.properties_['d'] == d:
            ret.append( v)
        return ret

    def getNeighborEdgePairs(self):
        for e,v in self._neighbors.items():
          if not e.disconnected:
            yield e,v



class Edge:
    def __init__( self):
        self.vertices = []
        self.disconnected = False
        #self.setVertices(vs)
        #self.properties_ = {}

    @property
    def neighbor_edges(self):
        neighbor_edges = set(self.vertices[0].neighbor_edges + self.vertices[1].neighbor_edges)
        return list(neighbor_edges - set([self]))

#    def setVertices(self, vs):
#        assert len(vs)==2
#        self.vertices.clear()
#        self.vertices += vs




class Graph:
    """ provides a minimalistic graph implementation suitable for analysis of chemical problems,
    even if some care was taken to make the graph work with nonsimple graphs, there are cases where it won't!"""

    uses_cache = True

    def __init__(self, vertices=[]):
        # we could simply use self.vertices = vertices, but it causes weired behaviour.
        # i.e when vertices argument not passed, vertices should be empty list. but instead
        # it is vertices of previous Graph
        self.vertices = vertices or []  # this is overriden by Molecule.atoms
        self.edges = set()              # this is overriden by Molecule.bonds
        self.disconnected_edges = set()
        self._cache = {}

    def _flush_cache( self):
        """ clear cache. TODO : replace all _flush_cache with self._cache.clear() """
        self._cache = {}

    def clear_cache(self):
        self._cache.clear()


    def deleteVertex( self, v):
        self.vertices.remove( v)
        self._flush_cache()



    def edge_subgraph_to_vertex_subgraph( self, cycle):
        ret = set()
        for e in cycle:
            v1, v2 = e.vertices
            ret.add( v1)
            ret.add( v2)
        return ret


    def get_connected_components( self):
        """ returns the connected components of graph as list of set of vertices"""
        comp = set() # just processed component
        not_processed = set( self.vertices)
        recent = set() # [not_processed.pop()]
        while not_processed:
            recent = set( reduce( operator.add, [v.neighbors for v in recent], [])) & not_processed
            if not recent:
                if comp:
                    yield comp
                recent = set( [not_processed.pop()])
                comp = recent
            else:
                comp.update( recent)
                not_processed -= recent
        # when there is only one atom in the last piece it is not yielded in the loop
        yield comp


    def is_connected(self):
        """ Check if all components of the Graph is connected """
        if len( self.edges) < len( self.vertices) - 1:
            # in this case it cannot be connected
            return False
        i = 0
        for x in self.get_connected_components():
            i += 1
            if i > 1:
                return False
        return True

    def temporarily_disconnect_edge(self, e):
        self.edges.remove( e)
        self.disconnected_edges.add( e)
        e.disconnected = True
        self._flush_cache()
        return e

    def reconnect_temporarily_disconnected_edge( self, e):
        assert e in self.disconnected_edges
        self.disconnected_edges.remove( e)
        self.edges.add( e)
        e.disconnected = False
        self._flush_cache()

    def reconnect_temporarily_disconnected_edges( self):
        while self.disconnected_edges:
            e = self.disconnected_edges.pop()
            e.disconnected = False
            self.edges.add( e)
        self._flush_cache()

    def clean_distance_from_vertices( self):
        for i in self.vertices:
            try:
                del i.properties_['d']
            except KeyError:
                pass


    def mark_vertices_with_distance_from( self, v):
        """returns the maximum d"""
        self.clean_distance_from_vertices()
        d = 0
        to_mark = set([v])
        while to_mark:
            to_mark_next = set()
            for i in to_mark:
                i.properties_['d'] = d

            for i in to_mark:
                for j in i.neighbors:
                    if 'd' not in j.properties_:
                        to_mark_next.add( j)

            to_mark = to_mark_next
            d += 1

        return d-1


    def is_edge_a_bridge( self, e):
        """ tells whether an edge is bridge between two rings (e.g in biphenyl) """
        start = e.vertices[0]
        # find number of vertices accessible from one of the edge endpoints
        self.mark_vertices_with_distance_from( start)
        c1 = len( [v for v in self.vertices if 'd' in v.properties_])
        # disconnect the eddge
        self.temporarily_disconnect_edge( e)
        # find the number of vertices accessible now
        self.mark_vertices_with_distance_from( start)
        c2 = len( [v for v in self.vertices if 'd' in v.properties_])
        # if they differ, we've got a bridge
        if c1 > c2:
            x = 1
        else:
            x = 0
        self.reconnect_temporarily_disconnected_edge( e)
        return x


    def temporarily_strip_bridge_edges( self):
        """strip all edges that are bridge, thus leaving only the cycles connected """
        bridge_found = True
        while bridge_found:
            vs = [v for v in self.vertices if v.degree == 1]
            while vs:
                for v in vs:
                    # we have to ask the degree, because the bond might have been stripped in this run
                    if v.degree:
                        e = v.neighbor_edges[0]
                        self.temporarily_disconnect_edge( e)
                vs = [v for v in self.vertices if v.degree == 1]

            bridge_found = False
            for e in self.edges:
                if self.is_edge_a_bridge( e):
                    bridge_found = True
                    break
            if bridge_found:
                self.temporarily_disconnect_edge( e)


    def _get_smallest_cycles_for_vertex( self, v, to_reach=None, came_from=None, went_through=None):
        """ingenious generator-based breadth-first search (BFS) to find smallest
        cycles for given vertex. It yields None or cycles for each depth level"""
        ret = []
        for e, neigh in v.getNeighborEdgePairs():
            if neigh == to_reach and e != came_from:
                ret.append( frozenset( [came_from, e]))
        yield ret

        gens = []
        w = went_through and went_through+[v] or [v]
        for e, neigh in v.getNeighborEdgePairs():
            # we dont want to go back, therefore we use went_through
            if (not went_through or neigh not in went_through) and not e == came_from:
                gens.append( self._get_smallest_cycles_for_vertex( neigh, to_reach=to_reach, came_from=e, went_through=w))
        while 1:
            all_rets = []
            for gen in gens:
                rets = next(gen)
                new_rets = []
                if rets:
                    for ret in rets:
                        if came_from:
                            ret = set( ret)
                            ret.update( set( [came_from]))
                            ret = frozenset( ret)
                        new_rets.append( ret)
                    all_rets.extend( frozenset( new_rets))
            yield all_rets


    def get_smallest_independent_cycles_e( self):
        """returns a set of smallest possible independent cycles as list of Sets of edges,
        other cycles in graph are guaranteed to be combinations of them.
        Gasteiger J. (Editor), Engel T. (Editor), Chemoinformatics : A Textbook,
        John Wiley & Sons 2001, ISBN 3527306811, 174."""
        assert self.is_connected()
        ncycles = len( self.edges) - len( self.vertices) + 2 - len( list( self.get_connected_components()))

        # check if the graph is connected, don't know if we should do it...
        if ncycles < 0:
            warnings.warn( "The number of edges is smaller than number of vertices-1, the molecule must be disconnected, which means there is something wrong with it.", UserWarning, 3)
            ncycles = 0

        # trivial case of linear molecule
        if ncycles == 0:
            return set()

        # the code itself
        self.temporarily_strip_bridge_edges()
        cycles = set()

        vs = [v for v in self.vertices if v.degree]
        while vs and len( cycles) < ncycles:
            new_cycles = set()
            vs2 = [v for v in vs if v.degree == 2]
            # disconnect something if there are no vertices of degree 2
            removed_e = None
            if not vs2:
                for v in vs:
                    if v.degree == 3:
                        removed_e = list( v.neighbor_edges)[0]
                        self.temporarily_disconnect_edge( removed_e)
                        break
            vs2 = [v for v in vs if v.degree == 2]
            assert len( vs2) > 0
            # get rings for all degree==2 vertices
            for v in vs2:
                gen = self._get_smallest_cycles_for_vertex( v, to_reach=v)
                for x in gen:
                    if x:
                        new_cycles.update( set( x))
                        break
            if removed_e:
                # we removed an edge - we need to check what cycles it would influence
                # we can also assume that there are only two vertices with degree 2
                # after the removal of this edge and these are the end vertices
                # therefore the code to detect longest path of degree 2 vertices is
                # superfluous
                to_disconnect = [list( removed_e.vertices[0].neighbor_edges)[0]]
                # reconnect the edge removed on the top
                if removed_e:
                    self.reconnect_temporarily_disconnected_edge( removed_e)
            else:
                # strip the cycles
                to_disconnect = set()
                for cycle in new_cycles:
                    # find the longest degree==2 chain in each cycle
                    paths = set()
                    to_go = set( [v for v in self.edge_subgraph_to_vertex_subgraph( cycle) if v.degree == 2])
                    while to_go:
                        now = set( [to_go.pop()])
                        path = set( now)
                        while now:
                            now = reduce( operator.or_, [set( [n for n in v.neighbors if n.degree == 2]) for v in now])
                            now &= to_go
                            to_go -= now
                            path.update( now)
                        if path:
                            paths.add( frozenset( path))
                    l = max( map( len, paths))
                    path = [p for p in paths if len( p) == l][0]
                    # now mark them for disconnection
                    v1 = set( path).pop()
                    to_disconnect.add( list( v1.neighbor_edges)[0])
            # disconnect what needs to be disconnected
            [self.temporarily_disconnect_edge( e) for e in to_disconnect]

            # add new_cycles to cycles
            cycles.update( new_cycles)

            # strip the degree==1 vertices
            vs1 = [v for v in self.vertices if v.degree == 1]
            while vs1:
                for v in vs1:
                    # we have to ask the degree, because the bond might have been stripped in this run
                    if v.degree:
                        e = v.neighbor_edges[0]
                        self.temporarily_disconnect_edge( e)
                vs1 = [v for v in self.vertices if v.degree == 1]

            vs = [v for v in self.vertices if v.degree]

        # remove extra cycles in some cases like adamantane
        if len( cycles) - ncycles > 0:
            # sort cycles according to length
            cs = [(len( c), c) for c in cycles]
            cs.sort()
            cs = [c[1] for c in cs]
            # now try to remove the biggest ones
            while len( cs) - ncycles > 0:
                c = set( cs.pop( -1))
                if not c <= reduce( operator.or_, map( set, cs)):
                    cs.insert( 0, c)
            cycles = set( [frozenset( _c) for _c in cs])

        # count the cycles and report warnings if their number is wrong
        if len( cycles) < ncycles:
            warnings.warn( "The number of cycles found (%d) is smaller than the theoretical value %d (|E|-|V|+1)" % (len( cycles), ncycles), UserWarning, 2)
        elif len( cycles) > ncycles:
            warnings.warn( "The number of independent cycles found (%d) is larger than the theoretical value %d (|E|-|V|+1), but I cannot improve it." % (len( cycles), ncycles), UserWarning, 2)

        self.reconnect_temporarily_disconnected_edges()

        return cycles


    def get_smallest_independent_cycles( self):
        """returns a set of smallest possible independent cycles,
        other cycles in graph are guaranteed to be combinations of them"""
        return list(map( self.edge_subgraph_to_vertex_subgraph,
                            self.get_smallest_independent_cycles_e()))


    def get_smallest_independent_cycles_dangerous_and_cached( self):
        try:
            #print("number of cached rings", len(self._cache['cycles']))
            return self._cache['cycles']
        except KeyError:
            self._cache['cycles'] = self.get_smallest_independent_cycles()
            #print("number of rings", len(self._cache['cycles']))
            return self._cache['cycles']

    #def addVertex( self, v=None):
        """adds a vertex to a graph, if v argument is not given creates a new one.
        returns None if vertex is already present or the vertex instance if successful"""
    '''    if not v:
            v = Vertex()
        if v not in self.vertices:
            self.vertices.append( v)
        else:
            print("Added vertex is already present in graph %s" % str(v))
            return None
        self._flush_cache()
        return v'''


    """def addEdge( self, v1, v2, e=None):
        adds an edge to a graph connecting vertices v1 and v2, if e argument is not given creates a new one.
        returns None if operation fails or the edge instance if successful
        i1 = self._getVertexIndex( v1)
        i2 = self._getVertexIndex( v2)
        if i1 == None or i2 == None:
            print("Adding edge to a vertex not present in graph failed (of course)")
            return None
        # to get the vertices if v1 and v2 were indexes
        v1 = self.vertices[ i1]
        v2 = self.vertices[ i2]
        if not e:
            e = Edge()
        e.setVertices([v1,v2])
        self.edges.add(e)
        v1.addNeighbor(v2, e)
        v2.addNeighbor(v1, e)
        self._flush_cache()
        return e"""
