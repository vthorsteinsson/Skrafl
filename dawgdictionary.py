"""

    Word dictionary implemented with a DAWG

    Copyright (C) 2025 Miðeind ehf.
    Original author: Vilhjálmur Þorsteinsson

    DawgDictionary uses a Directed Acyclic Word Graph (DAWG) internally
    to store a large set of words in an efficient structure in terms
    of storage and speed.

    The graph is pre-built using the code in dawgbuilder.py and stored
    in a text-based file to be loaded at run-time by DawgDictionary.

    The main class supports three fundamental query functions:

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

    All of the above query functions are built on top of a generic DAWG navigation function:

    DawgDictionary.navigate(navigator)
        Uses a navigation object to control the traversal of the graph and tabulate
        results. The navigation object should implement a number of interface functions,
        as documented in comments for the navigate() function.

    DawgDictionary.FindNavigator(word)
        A navigation class to find words by exact match. Used by DawgDictionary.find()

    DawgDictionary.PermutationNavigator(rack, minlen)
        A navigation class to find rack permutations. Used by DawgDictionary.find_permutations()

    DawgDictionary.MatchNavigator(rack, minlen)
        A navigation class to find words matching a pattern. Used by DawgDictionary.find_matches()

    See also comments in dawgbuilder.py

    Test code for this module is found in dawgtester.py

"""

import os
import codecs
import threading
import logging
import time
import sys
import pickle

from languages import Alphabet


class _Node:

    """ This class must be at module level for pickling """

    def __init__(self):
        self.final = False
        self.edges = dict()


class DawgDictionary:

    def __init__(self):
        # Initialize an empty graph
        # The root entry will eventually be self._nodes[0]
        self._nodes = None
        # Running counter of nodes read
        self._index = 1
        # Lock to ensure that only one thread loads the dictionary
        self._lock = threading.Lock()

    def _parse_and_add(self, line):
        """ Parse a single line of a DAWG text file and add to the graph structure """
        # The first line is the root (by convention nodeid 0)
        # The first non-root node is in line 2 and has nodeid 2
        assert self._nodes is not None
        nodeid = self._index if self._index > 1 else 0
        self._index += 1
        edgedata = line.split("_")
        final = False
        firstedge = 0
        if len(edgedata) >= 1 and edgedata[0] == "|":
            # Vertical bar denotes final node
            final = True
            firstedge = 1
        if nodeid in self._nodes:
            # We have already seen this node id: use the previously created instance
            newnode = self._nodes[nodeid]
        else:
            # The id is appearing for the first time: add it
            newnode = _Node()
            self._nodes[nodeid] = newnode
        newnode.final = final
        # Process the edges
        for edge in edgedata[firstedge:]:
            e = edge.split(":")
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
                newterminal = _Node()
                newnode.edges[prefix] = newterminal
                self._nodes[edgeid] = newterminal

    def load(self, fname):
        """ Load a DAWG from a text file """
        # Reset the graph contents
        with self._lock:
            # Ensure that we don't have multiple threads trying to load simultaneously
            if self._nodes is not None:
                # Already loaded
                return
            self._nodes = dict()
            self._index = 1
            with codecs.open(fname, mode="r", encoding="utf-8") as fin:
                for line in fin:
                    if line.endswith("\r\n"):
                        # Cut off trailing CRLF (Windows-style)
                        line = line[0:-2]
                    elif line.endswith("\n"):
                        # Cut off trailing LF (Unix-style)
                        line = line[0:-1]
                    if line:
                        self._parse_and_add(line)

    def store_pickle(self, fname):
        """ Store a DAWG in a Python pickle file """
        with open(fname, "wb") as pf:
            pickle.dump(self._nodes, pf, pickle.HIGHEST_PROTOCOL)

    def load_pickle(self, fname):
        """ Load a DAWG from a Python pickle file """
        with self._lock:
            if self._nodes is not None:
                # Already loaded
                return
            with open(fname, "rb") as pf:
                self._nodes = pickle.load(pf)

    def num_nodes(self):
        """ Return a count of unique nodes in the DAWG """
        return 0 if self._nodes is None else len(self._nodes)

    def find(self, word):
        """ Look for a word in the graph, returning True if it is found or False if not """
        nav = FindNavigator(word)
        self.navigate(nav)
        return nav.is_found()

    def __contains__(self, word):
        """ Enable simple lookup syntax: "word" in dawgdict """
        return self.find(word)

    def find_matches(self, pattern, sort=True):
        """ Returns a list of words matching a pattern.
            The pattern contains characters and '?'-signs denoting wildcards.
            Characters are matched exactly, while the wildcards match any character.
        """
        nav = MatchNavigator(pattern, sort)
        self.navigate(nav)
        return nav.result()

    def find_permutations(self, rack, minlen=0):
        """ Returns a list of legal permutations of a rack of letters.
            The list is sorted in descending order by permutation length.
            The rack may contain question marks '?' as wildcards, matching all letters.
            Question marks should be used carefully as they can
            yield very large result sets.
        """
        nav = PermutationNavigator(rack, minlen)
        self.navigate(nav)
        return nav.result()

    def navigate(self, nav):
        """ A generic function to navigate through the DAWG under
            the control of a navigation object.

            The navigation object should implement the following interface:

            def push_edge(firstchar)
                returns True if the edge should be entered or False if not
            def accepting()
                returns False if the navigator does not want more characters
            def accepts(newchar)
                returns True if the navigator will accept and 'eat' the new character
            def accept(matched, final)
                called to inform the navigator of a match and whether it is a final word
            def pop_edge()
                called when leaving an edge that has been navigated; returns False
                if there is no need to visit other edges
            def done()
                called when the navigation is completed
        """
        if self._nodes is None:
            # No graph: no navigation
            nav.done()
            return
        root = self._nodes[0]  # Start at the root
        Navigation(nav).go(root)


class Wordbase:

    """ Container for a singleton instance of the word database """

    _dawg = None
    _lock = threading.Lock()

    @staticmethod
    def _load():
        """ Load a DawgDictionary, from either a text file or a pickle file """
        with Wordbase._lock:
            if Wordbase._dawg is not None:
                # Already loaded: nothing to do
                return
            # Compare the file times of the text version vs. the pickled version
            fname = os.path.abspath(os.path.join("resources", "ordalisti.text.dawg"))
            pname = os.path.abspath(os.path.join("resources", "ordalisti.dawg.pickle"))
            try:
                fname_t = os.path.getmtime(fname)
            except os.error:
                fname_t = None
            try:
                pname_t = os.path.getmtime(pname)
            except os.error:
                pname_t = None

            dawg = DawgDictionary()

            if fname_t is None or (pname_t is not None and pname_t >= fname_t):
                # We have a newer pickle file: use it
                logging.info(
                    "Instance {0} loading DAWG from pickle file {1}".format(
                        os.environ.get("INSTANCE_ID", ""), pname
                    )
                )
                t0 = time.time()
                dawg.load_pickle(pname)
                t1 = time.time()
                logging.info(
                    "Loaded {0} graph nodes in {1:.2f} seconds".format(
                        dawg.num_nodes(), t1 - t0
                    )
                )
            else:
                # Load in the traditional way, from the text file
                assert fname_t is not None
                logging.info(
                    "Instance {0} loading DAWG from text file {1}".format(
                        os.environ.get("INSTANCE_ID", ""), fname
                    )
                )
                t0 = time.time()
                dawg.load(fname)
                t1 = time.time()
                logging.info(
                    "Loaded {0} graph nodes in {1:.2f} seconds".format(
                        dawg.num_nodes(), t1 - t0
                    )
                )

            # Do not assign Wordbase._dawg until fully loaded, to prevent race conditions
            Wordbase._dawg = dawg

    @staticmethod
    def dawg():
        if Wordbase._dawg is None:
            Wordbase._load()
        assert Wordbase._dawg is not None
        return Wordbase._dawg


class Navigation:

    """ Manages the state for a navigation while it is in progress """

    def __init__(self, nav):
        self._nav = nav
        # If the navigator has a method called accept_resumable(),
        # note it and call it with additional state information instead of
        # plain accept()
        self._resumable = callable(getattr(nav, "accept_resumable", None))

    def _navigate_from_node(self, node, matched):
        """ Starting from a given node, navigate outgoing edges """
        # Go through the edges of this node and follow the ones
        # okayed by the navigator
        for prefix, nextnode in node.edges.items():
            if self._nav.push_edge(prefix[0]):
                # This edge is a candidate: navigate through it
                self._navigate_from_edge(prefix, nextnode, matched)
                if not self._nav.pop_edge():
                    # Short-circuit and finish the loop if pop_edge() returns False
                    break

    def _navigate_from_edge(self, prefix, nextnode, matched):
        """ Navigate along an edge, accepting partial and full matches """
        # Go along the edge as long as the navigator is accepting
        lenp = len(prefix)
        j = 0
        while j < lenp and self._nav.accepting():
            # See if the navigator is OK with accepting the current character
            if not self._nav.accepts(prefix[j]):
                # Nope: we're done with this edge
                return
            # So far, we have a match: add a letter to the matched path
            matched += prefix[j]
            j += 1
            # Check whether the next prefix character is a vertical bar, denoting finality
            final = False
            if j < lenp and prefix[j] == "|":
                final = True
                j += 1
            elif (j >= lenp) and ((nextnode is None) or nextnode.final):
                # If we're at the final char of the prefix and the next node is final,
                # set the final flag as well (there is no trailing vertical bar in this case)
                final = True
            # Tell the navigator where we are
            if self._resumable:
                # The navigator wants to know the position in the graph
                # so that navigation can be resumed later from this spot
                self._nav.accept_resumable(prefix[j:], nextnode, matched)
            else:
                # Normal navigator: tell it about the match
                self._nav.accept(matched, final)
        # We're done following the prefix for as long as it goes and
        # as long as the navigator was accepting
        if j < lenp:
            # We didn't complete the prefix, so the navigator must no longer
            # be interested (accepting): we're done
            return
        if self._nav.accepting() and (nextnode is not None):
            # Gone through the entire edge and still have rack letters left:
            # continue with the next node
            self._navigate_from_node(nextnode, matched)

    def go(self, root):
        """ Perform the navigation using the given navigator """
        if root is None:
            # No root: no navigation
            self._nav.done()
            return
        # The ship is ready to go
        if self._nav.accepting():
            # Leave shore and navigate the open seas
            self._navigate_from_node(root, "")
        self._nav.done()

    def resume(self, prefix, nextnode, matched):
        """ Resume navigation from a previously saved state """
        self._navigate_from_edge(prefix, nextnode, matched)


class FindNavigator:

    """ A navigation class to be used with DawgDictionary.navigate()
        to find a particular word in the dictionary by exact match
    """

    def __init__(self, word):
        self._word = word
        self._len = len(word)
        self._index = 0
        self._found = False

    def push_edge(self, firstchar):
        """ Returns True if the edge should be entered or False if not """
        # Enter the edge if it fits where we are in the word
        return self._word[self._index] == firstchar

    def accepting(self):
        """ Returns False if the navigator does not want more characters """
        # Don't go too deep
        return self._index < self._len

    def accepts(self, newchar):
        """ Returns True if the navigator will accept the new character """
        if newchar != self._word[self._index]:
            return False
        # Match: move to the next index position
        self._index += 1
        return True

    def accept(self, matched, final):
        """ Called to inform the navigator of a match and whether it is a final word """
        if final and self._index == self._len:
            # Yes, this is what we were looking for
            assert matched == self._word
            self._found = True

    def pop_edge(self):
        """ Called when leaving an edge that has been navigated """
        # We only need to visit one outgoing edge, so short-circuit the edge loop
        return False

    def done(self):
        """ Called when the whole navigation is done """
        pass

    def is_found(self):
        return self._found


class PermutationNavigator:

    """ A navigation class to be used with DawgDictionary.navigate()
        to find all permutations of a rack
    """

    def __init__(self, rack, minlen=0):
        self._rack = rack
        self._stack = []
        self._result = []
        self._minlen = minlen

    def push_edge(self, firstchar):
        """ Returns True if the edge should be entered or False if not """
        # Follow all edges that match a letter in the rack
        # (which can be '?', matching all edges)
        if not ((firstchar in self._rack) or ("?" in self._rack)):
            return False
        # Fit: save our rack and move into the edge
        self._stack.append(self._rack)
        return True

    def accepting(self):
        """ Returns False if the navigator does not want more characters """
        # Continue as long as there is something left on the rack
        return bool(self._rack)

    def accepts(self, newchar):
        """ Returns True if the navigator will accept the new character """
        exactmatch = newchar in self._rack
        if (not exactmatch) and ("?" not in self._rack):
            # Can't continue with this prefix - we no longer have rack letters matching it
            return False
        # We're fine with this: accept the character and remove from the rack
        if exactmatch:
            self._rack = self._rack.replace(newchar, "", 1)
        else:
            self._rack = self._rack.replace("?", "", 1)
        return True

    def accept(self, matched, final):
        """ Called to inform the navigator of a match and whether it is a final word """
        if final and len(matched) >= self._minlen:
            self._result.append(matched)

    def pop_edge(self):
        """ Called when leaving an edge that has been navigated """
        self._rack = self._stack.pop()
        # We need to visit all outgoing edges, so return True
        return True

    def done(self):
        """ Called when the whole navigation is done """
        self._result.sort(key=lambda x: (-len(x), Alphabet.sortkey(x)))

    def result(self):
        return self._result


class MatchNavigator:

    """ A navigation class to be used with DawgDictionary.navigate()
        to find all words matching a pattern
    """

    def __init__(self, pattern, sort):
        self._pattern = pattern
        self._lenp = len(pattern)
        self._index = 0
        self._chmatch = pattern[0]
        self._wildcard = self._chmatch == "?"
        self._stack = []
        self._result = []
        self._sort = sort

    def push_edge(self, firstchar):
        """ Returns True if the edge should be entered or False if not """
        # Follow all edges that match a letter in the rack
        # (which can be '?', matching all edges)
        if not self._wildcard and (firstchar != self._chmatch):
            return False
        # Fit: save our index and move into the edge
        self._stack.append((self._index, self._chmatch, self._wildcard))
        return True

    def accepting(self):
        """ Returns False if the navigator does not want more characters """
        # Continue as long as there is something left to match
        return self._index < self._lenp

    def accepts(self, newchar):
        """ Returns True if the navigator will accept the new character """
        if not self._wildcard and (newchar != self._chmatch):
            return False
        self._index += 1
        if self._index < self._lenp:
            self._chmatch = self._pattern[self._index]
            self._wildcard = self._chmatch == "?"
        return True

    def accept(self, matched, final):
        """ Called to inform the navigator of a match and whether it is a final word """
        if final and self._index == self._lenp:
            # We have an entire pattern match
            # (Note that this could be relaxed to also return partial (shorter) pattern matches)
            self._result.append(matched)

    def pop_edge(self):
        """ Called when leaving an edge that has been navigated """
        self._index, self._chmatch, self._wildcard = self._stack.pop()
        # We need to continue visiting edges only if this is a wildcard position
        return self._wildcard

    def done(self):
        """ Called when the whole navigation is done """
        if self._sort:
            self._result.sort(key=Alphabet.sortkey)

    def result(self):
        return self._result
