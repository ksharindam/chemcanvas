# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
# Copyright (C) 2022-2025 Arindam Chaudhuri <arindamsoft94@gmail.com>
from functools import reduce
import operator, warnings
import copy


class Vertex:
    """simple vertex class, normaly would not be needed but it can speed up many analytical tasks
    to store data directly in vertex and not get them from the graph connectivity matrix.
    vertex has a value attribute used to store arbitrary object"""
    attrs_to_copy = ()

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
        # only used by Atom
        return list( self._neighbors.keys() )

    def add_neighbor(self, v, e):
        """ adds a neighbor connected via e"""
        self._neighbors[e] = v

    def remove_neighbor(self, v):
        to_del = None
        for k, vv in self._neighbors.items():
            if v == vv:
                to_del = k
                break
        if to_del:
            del self._neighbors[ to_del]
        else:
            raise Exception("cannot remove non-existing neighbor")

    def get_neighbor_edge_pairs(self):
        for e,v in self._neighbors.items():
          if not e.disconnected:
            yield e,v

    def get_edge_leading_to(self, a):
        for e, v in self._neighbors.items():
            if a == v:
                return e
        return None

    def copy( self):
        other = self.__class__()
        for attr in self.attrs_to_copy:
            setattr( other, attr, copy.copy( getattr( self, attr)))
        return other



class Edge:
    attrs_to_copy = ("disconnected",)

    def __init__( self):
        self.vertices = []
        self.disconnected = False
        self.properties_ = {}

    @property
    def neighbor_edges(self):
        neighbor_edges = set(self.vertices[0].neighbor_edges + self.vertices[1].neighbor_edges)
        return list(neighbor_edges - set([self]))

    @property
    def neighbor_edges2( self):
        """returns 2 lists of neighbor edges (one for one side, one for the other)"""
        v1, v2 = self.vertices
        out1 = [e for e in v1.neighbor_edges if e!=self]
        out2 = [e for e in v2.neighbor_edges if e!=self]
        return out1, out2


    def set_vertices(self, vs):
        assert len(vs)==2
        self.vertices.clear()
        self.vertices += list(vs)

    def copy( self):
        other = self.__class__()
        for attr in self.attrs_to_copy:
            setattr( other, attr, copy.copy( getattr( self, attr)))
        return other



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

    def get_pieces_after_edge_removal(self, e):
        self.temporarily_disconnect_edge( e)
        ps = [i for i in self.get_connected_components()]
        self.reconnect_temporarily_disconnected_edge( e)
        return ps

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
        """ tells whether an edge is not ring memmber """
        start = e.vertices[0]
        # find number of vertices accessible from one of the edge endpoints
        self.mark_vertices_with_distance_from( start)
        c1 = len( [v for v in self.vertices if 'd' in v.properties_])
        # disconnect the eddge
        self.temporarily_disconnect_edge( e)
        # find the number of vertices accessible now
        self.mark_vertices_with_distance_from( start)
        c2 = len( [v for v in self.vertices if 'd' in v.properties_])
        self.reconnect_temporarily_disconnected_edge( e)
        # if they differ, we've got a bridge
        if c1 > c2:
            return True
        return False


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
        for e, neigh in v.get_neighbor_edge_pairs():
            if neigh == to_reach and e != came_from:
                ret.append( frozenset( [came_from, e]))
        yield ret

        gens = []
        w = went_through and went_through+[v] or [v]
        for e, neigh in v.get_neighbor_edge_pairs():
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

    def add_vertex( self, v=None):
        """adds a vertex to a graph, if v argument is not given creates a new one.
        returns None if vertex is already present or the vertex instance if successful"""
        if not v:
            v = Vertex()
        if v not in self.vertices:
            self.vertices.append( v)
        else:
            print("Added vertex is already present in graph %s" % str(v))
            return None
        self._flush_cache()
        return v


    def add_edge( self, v1, v2, e=None):
        """adds an edge to a graph connecting vertices v1 and v2, if e argument is not given creates a new one.
        returns None if operation fails or the edge instance if successful"""
        i1 = self._get_vertex_index( v1)
        i2 = self._get_vertex_index( v2)
        if i1 == None or i2 == None:
            print("Adding edge to a vertex not present in graph failed (of course)")
            return None
        # to get the vertices if v1 and v2 were indexes
        v1 = self.vertices[ i1]
        v2 = self.vertices[ i2]
        if not e:
            e = Edge()
        e.set_vertices([v1,v2])
        self.edges.add(e)
        v1.add_neighbor(v2, e)
        v2.add_neighbor(v1, e)
        self._flush_cache()
        return e

    def vertex_subgraph_to_edge_subgraph(self, cycle):
        ret = set()
        for v1 in cycle:
            for (e,n) in v1.get_neighbor_edge_pairs():
                if n in cycle:
                    ret.add( e)
        return ret

    def get_induced_subgraph_from_vertices( self, vs):
        """it creates a new graph, however uses the old vertices and edges!"""
        g = Graph()
        for v in vs:
            g.add_vertex( v)
        for e in self.vertex_subgraph_to_edge_subgraph( vs):
            v1, v2 = e.vertices
            if v1 in vs and v2 in vs:
                g.add_edge( v1, v2, e)  # BUG - it should copy the edge?
        return g

    def get_new_induced_subgraph( self, vertices, edges):
        """returns a induced subgraph that is newly created and can be therefore freely
        changed without worry about the original."""
        sub = Graph()
        vertex_map = {}
        i = 0
        for v in vertices:
            new_v = v.copy()
            sub.add_vertex( new_v)
            vertex_map[v] = i
            i += 1
        for e in edges:
            new_e = e.copy()
            v1, v2 = e.vertices
            sub.add_edge( vertex_map[v1], vertex_map[v2], new_e)
        return sub

    def is_edge_a_bridge_fast_and_dangerous( self, e):
        """should be used only in case of repetitive questions for the same edge in cases
        where no edges are added to the graph between the questions (if brigde==1 the value
        is stored and returned, which is safe only in case no edges are added)"""
        try:
            return e.properties_['bridge']
        except:
            if self.is_edge_a_bridge( e):
                e.properties_['bridge'] = 1
                return 1
            else:
                return 0


    def mark_edges_with_distance_from( self, e1):
        for e in self.edges:
            try:
                del e.properties_['d']
            except KeyError:
                pass
        marked = set( [e1])
        new = set( [e1])
        dist = 0
        e1.properties_['dist'] = dist
        while new:
            new_new = set()
            dist += 1
            for e in new:
                for ne in e.neighbor_edges:
                    if not ne in marked:
                        ne.properties_['dist'] = dist
                        new_new.add( ne)
            new = new_new
            marked.update( new)

    def get_path_between_edges( self, e1, e2):
        self.mark_edges_with_distance_from( e1)
        if not "dist" in e2.properties_:
            return None
        else:
            path = [e2]
            _e = e2
            for i in range( e2.properties_['dist']-1, -1, -1):
                _e = [ee for ee in _e.neighbor_edges if ee.properties_['dist'] == i][0]
                path.append( _e)
            return path

    def is_tree( self):
        return self.is_connected() and len( self.vertices)-1 == len( self.edges)

    def contains_cycle( self):
        """this assumes that the graph is connected"""
        assert self.is_connected()# TODO : remove
        return not self.is_tree()

    def sort_vertices_in_path( self, path, start_from=None):
        """returns None if there is no path"""
        rng = copy.copy( path)
        if start_from:
            a = start_from
            rng.remove( a)
        else:
            a = None
            # for acyclic path we need to find one end
            for at in path:
                if len( [v for v in at.neighbors if v in path]) == 1:
                    a = at
                    rng.remove( at)
                    break
            if not a:
                a = rng.pop() # for rings
        out = [a]
        while rng:
            try:
                a = [i for i in a.neighbors if i in rng][0]
            except IndexError:
                return None
            out.append( a)
            rng.remove( a)
        return out

    def defines_connected_subgraph_v(self, vertices):
        sub = self.get_new_induced_subgraph( vertices, self.vertex_subgraph_to_edge_subgraph( vertices))
        return sub.is_connected()

    def _get_vertex_index( self, v):
        """if v is already an index, return v, otherwise return index of v on None"""
        if type( v) == int and v < len( self.vertices):
            return v
        try:
            return self.vertices.index( v)
        except ValueError:
            return None
