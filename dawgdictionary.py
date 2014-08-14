# -*- coding: utf-8 -*-

""" Word dictionary implemented using DAWG

Author: Vilhjalmur Thorsteinsson, 2014

DawgDictionary uses a Directed Acyclic Word Graph (DAWG) internally
to store a large set of words in an efficient structure in terms
of storage and speed.

The DAWG implementation is partially based on Steve Hanov's work
(see http://stevehanov.ca/blog/index.php?id=115).

See also comments in dawgbuilder.py

"""

import os
import codecs

class DawgDictionary:

    class _Node:

        def __init__(self):
            self.final = False
            self.edges = dict()

    def __init__(self):
        # Initialize an empty graph
        # The root entry will eventually be self._nodes[0]
        self._nodes = None
        # Running counter of nodes read
        self._index = 1

    def _parse_and_add(self, line):
        """ Parse a single line of a DAWG text file and add to the graph structure """
        # The first line is the root (by convention nodeid 0)
        # The first non-root node is in line 2 and has nodeid 2
        assert self._nodes is not None
        nodeid = self._index if self._index > 1 else 0
        self._index += 1
        edgedata = line.split(u'_')
        final = False
        firstedge = 0
        if len(edgedata) >= 1 and edgedata[0] == u'|':
            # Vertical bar denotes final node
            final = True
            firstedge = 1
        if nodeid in self._nodes:
            # We have already seen this node id: use the previously created instance
            newnode = self._nodes[nodeid]
        else:
            # The id is appearing for the first time: add it
            newnode = DawgDictionary._Node()
            self._nodes[nodeid] = newnode
        newnode.final = final
        for edge in edgedata[firstedge:]:
            e = edge.split(u':')
            prefix = e[0]
            edgeid = int(e[1])
            if edgeid == 0:
                newnode.edges[prefix] = None
            elif edgeid in self._nodes:
                newnode.edges[prefix] = self._nodes[edgeid]
            else:
                newterminal = DawgDictionary._Node()
                newnode.edges[prefix] = newterminal
                self._nodes[edgeid] = newterminal

    def load(self, fname):
        """ Load a DAWG from a text file """
        # Reset the graph contents
        self._nodes = dict()
        self._index = 1
        with codecs.open(fname, mode='r', encoding='utf-8') as fin:
            for line in fin:
                if line.endswith(u'\r\n'):
                    # Cut off trailing CRLF (Windows-style)
                    line = line[0:-2]
                elif line.endswith(u'\n'):
                    # Cut off trailing LF (Unix-style)
                    line = line[0:-1]
                if line:
                    self._parse_and_add(line)

    def _nav_from_node(self, node, word, index):
        """ Starting from a given node, navigate the graph using the word and an index into it """
        if index >= len(word):
            # The word is exhausted: it is valid if we're at a null or final node
            return (node is None) or node.final
        if node is None:
            # The word is not exhausted but we're at a null node: no match
            return False
        # Go through the edges of this node and try to find a path
        for prefix, nextnode in node.edges.items():
            if prefix[0] == word[index]:
                # Found a matching prefix: navigate it
                return self._follow_edge(word, index, prefix, nextnode)
        # No matching prefix, so no outgoing edges: no match
        return False

    def _follow_edge(self, word, index, prefix, nextnode):
        """ Found an edge with a matching prefix: loop through the prefix """
        lenp = len(prefix)
        j = 0
        while j < lenp:
            if word[index] != prefix[j]:
                # The prefix does not match the word: we're done
                return False
            # So far, we have a match
            index += 1
            j += 1
            final = False
            # Check whether the next prefix character is a vertical bar, denoting finality
            if j < lenp and prefix[j] == '|':
                final = True
                j += 1
            if index >= len(word):
                # The word is hereby exhausted:
                # We have a match if this was a final char in the prefix,
                # or if the prefix is exhausted and the next node is terminal
                return final or ((j >= lenp) and ((nextnode is None) or nextnode.final))
        return self._nav_from_node(nextnode, word, index)

    def find(self, word):
        """ Look for a word in the graph, returning True if it is found or False if not """
        if self._nodes is None:
            # Must load the graph before searching
            return False
        root = self._nodes[0] # Start at the root
        if root is None:
            # No root: no match
            return False
        return self._nav_from_node(root, word, 0)

    def num_nodes(self):
        """ Return a count of unique nodes in the DAWG """
        return 0 if self._nodes is None else len(self._nodes)

    def _append_perm_from_node(self, node, matched, rack, permlist):
        """ Starting from a given node, navigate the graph using the word and an index into it """
        if not rack or node is None:
            # Nothing more to do
            return
        # Go through the edges of this node and try to find a path
        for prefix, nextnode in node.edges.items():
            if prefix[0] in rack:
                # This edge is open: navigate through it
                self._append_perm_from_edge(matched, rack, prefix, nextnode, permlist)

    def _append_perm_from_edge(self, matched, rack, prefix, nextnode, permlist):
        """ There is a letter in the rack matching this prefix """
        lenp = len(prefix)
        j = 0
        while j < lenp and rack:
            if prefix[j] not in rack:
                # Can't continue with this prefix - no matching rack letters
                return False
            # Add a letter to the matched path so far
            matched += prefix[j]
            # Remove the letter from the rack
            rack.replace(prefix[j], '', 1)
            # So far, we have a match
            j += 1
            final = False
            # Check whether the next prefix character is a vertical bar, denoting finality
            if j < lenp and prefix[j] == '|':
                final = True
                j += 1
            if final:
                # We have found a complete word
                permlist.append(matched)
            elif not rack:
                # If the rack is hereby exhausted, we're at the end of the
                # prefix and there is no next node, we also have a match
                if (j >= lenp) and ((nextnode is None) or nextnode.final):
                    permlist.append(matched)
        if rack:
            # Gone through the entire edge and still not done: continue
            # with the next node
            self._append_perm_from_node(nextnode, matched, rack, permlist)

    def find_permutations(self, rack):
        """ Returns a list of legal permutations of a rack of letters """
        permlist = []
        if self._nodes is None:
            # No graph: no permutations
            return permlist
        root = self._nodes[0] # Start at the root
        if root is None:
            # No root: no permutations
            return permlist
        self._append_perm_from_node(root, '', rack, permlist)
        return permlist

import time

class DawgTester:

    def __init__(self):
        self._dawg = None

    def _test(self, word):
        print(u"\"{0}\" is {1}found".format(word, u"" if self._dawg.find(word) else u"not "))

    def go(self, fname, relpath):
        self._dawg = DawgDictionary()
        fpath = os.path.abspath(os.path.join(relpath, fname + ".text.dawg"))
        t0 = time.time()
        self._dawg.load(fpath)
        t1 = time.time()
        print("DAWG load took {0:.2f} seconds".format(t1 - t0))
        self._test(u"abbadísarinnar")
        self._test(u"absintufyllirí")
        self._test(u"absolútt")
        self._test(u"aborri")
        self._test(u"abs")
        self._test(u"halló")
        self._test(u"hraðskákmótin")
        self._test(u"jólahraðskákmótið")
        self._test(u"nafnskírteinið")
        self._test(u"abstraktmálarið")
        self._test(u"abstraktmálari")
        self._test(u"abstraktmálar")
        self._test(u"abstraktmála")
        self._test(u"prófun")
        self._test(u"")
        self._test(u"abo550")
        self._dawg = None


def test():
    # Test navivation in the DAWG
    dt = DawgTester()
    dt.go("ordalisti", "resources")

