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
        # Initialize an empty node dict.
        # The root entry will eventually be self._nodes[0]
        self._nodes = dict()

    def _parse_and_add(self, line):
        """ Parse a single line of a DAWG text file and add to the graph structure """
        nodedata = line.split(u' ')
        if nodedata[0] == u"Root":
            nodeid = 0
        else:
            nodeid = int(nodedata[0])
        edgedata = nodedata[1].split(u'_')
        final = False
        firstedge = 0
        if len(edgedata) >= 1 and edgedata[0] == u'*':
            # Asterisk denotes final node
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
        """ We've found an edge with a matching prefix: loop through the prefix """
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
            # Check whether the next prefix character is an asterisk, denoting finality
            if j < lenp and prefix[j] == '*':
                final = True
                j += 1
            if index >= len(word):
                # The word is hereby exhausted:
                # We have a match if this was a final char in the prefix,
                # or if the prefix is exhausted and the next node is terminal
                return final or ((j >= lenp) and ((nextnode is None) or nextnode.final))
        return self._nav_from_node(nextnode, word, index)

    def find(self, word):
        root = self._nodes[0] # Start at the root
        return self._nav_from_node(root, word, 0)


class DawgTester:

    def __init__(self):
        self._dawg = None

    def _test(self, word):
        print(u"\"{0}\" is {1}found".format(word, u"" if self._dawg.find(word) else u"not "))

    def go(self, fname, relpath):
        self._dawg = DawgDictionary()
        fpath = os.path.abspath(os.path.join(relpath, fname + ".text.dawg"))
        self._dawg.load(fpath)
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

