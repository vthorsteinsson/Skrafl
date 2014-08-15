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
        if (not rack) or (node is None):
            # Nothing more to do (we assume that a match has already been recorded)
            return
        # Go through the edges of this node and follow all that match a
        # letter in the rack
        for prefix, nextnode in node.edges.items():
            if prefix[0] in rack:
                # This edge is a candidate: navigate through it
                self._append_perm_from_edge(matched, rack, prefix, nextnode, permlist)

    def _append_perm_from_edge(self, matched, rack, prefix, nextnode, permlist):
        """ There is a letter in the rack matching the prefix of this edge """
        lenp = len(prefix)
        j = 0
        while j < lenp and rack:
            if prefix[j] not in rack:
                # Can't continue with this prefix - we no longer have rack letters matching it
                return
            # Add a letter to the matched path
            matched += prefix[j]
            # Remove the letter from the rack
            rack = rack.replace(prefix[j], '', 1)
            # So far, we have a match
            j += 1
            final = False
            # Check whether the next prefix character is a vertical bar, denoting finality
            if j < lenp and prefix[j] == '|':
                final = True
                j += 1
            if final:
                # We have found a complete valid word
                permlist.append(matched)
        # We're done following the prefix for as long as it goes and
        # as long as the rack lasts
        if j < lenp:
            # We didn't complete the prefix, so the rack must be out:
            # we're done
            return
        # We completed the prefix
        if (nextnode is None) or nextnode.final:
            # We're at a final state, explicit or implicit: add the match
            permlist.append(matched)
        if rack and (nextnode is not None):
            # Gone through the entire edge and still have rack letters left:
            # continue with the next node
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
        self._append_perm_from_node(root, u'', rack, permlist)
        # Sort in ascending order by length of permutation
        permlist.sort(key = lambda x: len(x))
        return permlist

import time

class DawgTester:

    def __init__(self):
        self._dawg = None

    def _test(self, word):
        print(u"\"{0}\" is {1}found".format(word, u"" if self._dawg.find(word) else u"not ").encode('cp850'))

    def _test_true(self, word):
        if not self._dawg.find(word):
            print(u"Error: \"{0}\" was not found".format(word).encode('cp850'))

    def _test_false(self, word):
        if self._dawg.find(word):
            print(u"Error: \"{0}\" was found".format(word).encode('cp850'))

    def go(self, fname, relpath):
        """ Load a DawgDictionary and test its functionality """

        print("DawgDictionary tester")
        print("Author: Vilhjalmur Thorsteinsson")
        print

        self._dawg = DawgDictionary()
        fpath = os.path.abspath(os.path.join(relpath, fname + ".text.dawg"))
        t0 = time.time()
        self._dawg.load(fpath)
        t1 = time.time()

        print("DAWG loaded in {0:.2f} seconds".format(t1 - t0))
        print("Checking a set of random words:")
        self._test_true(u"abbadísarinnar")
        self._test_true(u"absintufyllirí")
        self._test_false(u"absolútt")
        self._test_true(u"aborri")
        self._test_false(u"abs")
        self._test_true(u"halló")
        self._test_true(u"hraðskákmótin")
        self._test_true(u"jólahraðskákmótið")
        self._test_true(u"nafnskírteinið")
        self._test_false(u"abstraktmálarið")
        self._test_true(u"abstraktmálari")
        self._test_false(u"abstraktmálar")
        self._test_false(u"abstraktmála")
        self._test_true(u"prófun")
        self._test_false(u"")
        self._test_false(u"abo550")

        # All two-letter words accepted by the Icelandic Scrabble(tm)-like game
        # at ordaleikur.appspot.com
        smallwords = [
            u"að", u"af", u"ak", u"al", u"an", u"ar", u"as", u"at", u"ax",
            u"áa", u"áð", u"ái", u"ál", u"ám", u"án", u"ár", u"ás", u"át",
            u"bí", u"bú", u"bý", u"bæ",
            u"dá", u"do", u"dó", u"dý",
            u"eð", u"ef", u"eg", u"ei", u"ek", u"el", u"em", u"en", u"er", u"et", u"ex", u"ey",
            u"ég", u"él", u"ét",
            u"fa", u"fá", u"fé", u"fæ",
            u"gá",
            u"ha", u"há", u"hí", u"hó", u"hý", u"hæ",
            u"ið", u"il",
            u"íð", u"íl", u"ís",
            u"já", u"jó", u"jú",
            u"ká", u"ku", u"kú",
            u"la", u"lá", u"lé", u"ló", u"lý", u"læ",
            u"má", u"mi", u"mó", u"mý",
            u"ná", u"né", u"nó", u"nú", u"ný", u"næ",
            u"of", u"og", u"ok", u"op", u"or",
            u"óa", u"óð", u"óf", u"ói", u"ók", u"ól", u"óm", u"ón", u"óp", u"ós", u"óx",
            u"pí", u"pú",
            u"rá", u"re", u"ré", u"rí", u"ró", u"rú", u"rý", u"ræ",
            u"sá", u"sé", u"sí", u"so", u"sú", u"sý", u"sæ",
            u"tá", u"te", u"té", u"ti", u"tí", u"tó", u"tý",
            u"um", u"un",
            u"úa", u"úð", u"úf", u"úi", u"úr", u"út",
            u"vá", u"vé", u"ví", u"vó",
            u"yl", u"ym", u"yr", u"ys",
            u"ýf", u"ýg", u"ýi", u"ýk", u"ýl", u"ýr", u"ýs", u"ýt",
            u"þá", u"þó", u"þú", u"þý",
            u"æð", u"æf", u"æg", u"æi", u"æl", u"æp", u"ær", u"æs", u"æt",
            u"öl", u"ör", u"ös", u"öt", u"öx"]

        letters = u'aábdðeéfghiíjklmnoóprstuúvxyýþæö'

        print("Checking small words:")

        # Check all possible two-letter combinations, allowing only those in the list
        for first in letters:
            for second in letters:
                word = first + second
                if word in smallwords:
                    self._test_true(word)
                else:
                    self._test_false(word)

        print("Finding permutations:")
        t0 = time.time()
        word = u"einstök"
        permlist = self._dawg.find_permutations(word)
        t1 = time.time()
        print(u"Permutations of \"{0}\":".format(word).encode('cp850'))
        cnt = 0
        for word in permlist:
            print(u"\"{0}\"".format(word).encode('cp850')),
            cnt += 1
            if cnt % 6 == 0:
                print
        print
        print(u"{0} permutations found in {1:.2f} seconds".format(cnt, t1 - t0))
        print
        print(u"Test finished")

        self._dawg = None


def test():
    # Test navivation in the DAWG
    dt = DawgTester()
    dt.go("ordalisti", "resources")

