# -*- coding: utf-8 -*-

""" Word dictionary implemented using DAWG

Author: Vilhjalmur Thorsteinsson, 2014

DawgDictionary uses a Directed Acyclic Word Graph (DAWG) internally
to store a large set of words in an efficient structure in terms
of storage and speed.

The class supports three main query functions:

DawgDictionary.find(word)
    Returns True if the word is found in the dictionary, or False if not.
    The __contains__ operator is supported, so "'myword' in dawgdict" also works.

DawgDictionary.find_matches(pattern)
    Returns a list of words that match the pattern. The pattern can contain
    wildcards ('?'). For example, result = dawgdict.find_matches("ex???") returns
    a list of all 5-letter words starting with "ex".

DawgDictionary.find_permutations(rack)
    Returns a list of all permutations of the given rack, i.e. valid words
    consisting of one or more letters from the rack in various orders.
    The rack may contain wildcards ('?'). For example, result = dawgdict.find_permutations("se?")
    returns a list of all words from 1 to 3 characters that can be constructed from
    the letters "s" and "e" and any one additional letter.

See also comments in dawgbuilder.py

Test code for this module is found in dawgtester.py

"""

import os
import codecs

from languages import Alphabet

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
        # Process the edges
        for edge in edgedata[firstedge:]:
            e = edge.split(u':')
            prefix = e[0]
            edgeid = int(e[1])
            if edgeid == 0:
                # Edge leads to null/zero, i.e. is final
                newnode.edges[prefix] = None
            elif edgeid in self._nodes:
                # Edge leads to a node we've already seen
                newnode.edges[prefix] = self._nodes[edgeid]
            else:
                # Edge leads to a new, previously unseen node: Create it
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

    def num_nodes(self):
        """ Return a count of unique nodes in the DAWG """
        return 0 if self._nodes is None else len(self._nodes)

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
        if not word:
            return False
        if self._nodes is None:
            # Must load the graph before searching
            return False
        root = self._nodes[0] # Start at the root
        if root is None:
            # No root: no match
            return False
        return self._nav_from_node(root, word, 0)

    def __contains__(self, word):
        """ Enable simple lookup syntax: "word" in dawgdict """
        return self.find(word)

    def _match_from_node(self, node, pattern, index, matched, matchlist):
        """ Starting from a given node, navigate the graph attempting to
            match the pattern from the index position """
        if node is None:
            # Nothing more to do (we assume that a match has already been recorded)
            return
        assert pattern is not None
        assert index < len(pattern)
        # Go through the edges of this node and follow all that match a
        # letter in the rack (which can be '?', matching all edges)
        chmatch = pattern[index]
        wildcard = (chmatch == u'?')
        for prefix, nextnode in node.edges.items():
            if wildcard or (prefix[0] == chmatch):
                # This edge is a candidate: navigate through it
                self._match_from_edge(pattern, index, prefix, nextnode, matched, matchlist)
                if not wildcard:
                    # No more than one edge can match the pattern if it's not a wildcard
                    return

    def _match_from_edge(self, pattern, index, prefix, nextnode, matched, matchlist):
        """ The letter at pattern[index] matches the prefix of this edge """
        assert index < len(pattern)
        assert (pattern[index] == u'?') or (pattern[index] == prefix[0])
        lenp = len(prefix)
        j = 0
        while j < lenp:
            prefj = prefix[j]
            if (pattern[index] != u'?') and (pattern[index] != prefj):
                # Not a wildcard and the prefix does not match the pattern: we're done
                return
            # So far, we have a match
            matched += prefj
            index += 1
            j += 1
            final = False
            # Check whether the next prefix character is a vertical bar, denoting finality
            if j < lenp and prefix[j] == '|':
                final = True
                j += 1
            if index >= len(pattern):
                # The pattern is hereby exhausted:
                # We have a match if this was a final char in the prefix,
                # or if the prefix is exhausted and the next node is terminal
                if final or ((j >= lenp) and ((nextnode is None) or nextnode.final)):
                    matchlist.append(matched)
                return
        # This edge is exchausted and fully matched: proceed to the following node,
        # if we have one
        if nextnode:
            assert index < len(pattern)
            self._match_from_node(nextnode, pattern, index, matched, matchlist)

    def find_matches(self, pattern):
        """ Returns a list of words matching a pattern.
            The pattern contains characters and '?'-signs denoting wildcards.
            Characters are matched exactly, while the wildcards match any character.
        """
        matchlist = []
        if self._nodes is None:
            # No graph: no matches
            return matchlist
        if not pattern:
            # Nothing to search for
            return matchlist
        root = self._nodes[0] # Start at the root
        if root is None:
            # No root: no matches
            return matchlist
        self._match_from_node(root, pattern, 0, u'', matchlist)
        # Sort results in ascending lexicographic order
        matchlist.sort(key = Alphabet.sortkey)
        return matchlist

    def _perm_from_node(self, node, matched, rack, permlist):
        """ Starting from a given node, navigate the graph using the word and an index into it """
        if (not rack) or (node is None):
            # Nothing more to do (we assume that a match has already been recorded)
            return
        # Go through the edges of this node and follow all that match a
        # letter in the rack (which can be '?', matching all edges)
        for prefix, nextnode in node.edges.items():
            if (prefix[0] in rack) or (u'?' in rack):
                # This edge is a candidate: navigate through it
                self._perm_from_edge(matched, rack, prefix, nextnode, permlist)

    def _perm_from_edge(self, matched, rack, prefix, nextnode, permlist):
        """ There is a letter in the rack matching the prefix of this edge """
        lenp = len(prefix)
        j = 0
        while j < lenp and rack:
            # We first try an exact match and only resort to the wildcard '?' if necessary
            exactmatch = prefix[j] in rack
            if (not exactmatch) and (u'?' not in rack):
                # Can't continue with this prefix - we no longer have rack letters matching it
                return
            # Add a letter to the matched path
            matched += prefix[j]
            # Remove the letter or the wildcard from the rack
            if exactmatch:
                rack = rack.replace(prefix[j], '', 1)
            else:
                rack = rack.replace(u'?', '', 1)
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
            self._perm_from_node(nextnode, matched, rack, permlist)

    def find_permutations(self, rack):
        """ Returns a list of legal permutations of a rack of letters.
            The list is sorted in descending order by permutation length.
            The rack may contain question marks '?' as wildcards, matching all letters.
            Question marks should be used carefully as they can
            yield very large result sets.
        """
        permlist = []
        if self._nodes is None:
            # No graph: no permutations
            return permlist
        if not rack:
            # No rack to permute
            return permlist
        root = self._nodes[0] # Start at the root
        if root is None:
            # No root: no permutations
            return permlist
        self._perm_from_node(root, u'', rack, permlist)
        # Sort in descending order by length of permutation
        # and within that, in ascending lexicographic order
        permlist.sort(key = lambda x: (-len(x), Alphabet.sortkey(x)))
        return permlist

