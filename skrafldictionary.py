# -*- coding: utf-8 -*-

""" Scrabble word dictionary

Original author: Vilhjalmur Thorsteinsson, 2014

Dictionary structure:

Suppose the dictionary contains two words, 'word' and 'wolf'.
This will be represented as follows:

root -> {
    'w': _Node(final=False, next -> {
        'o': _Node(final=False, next -> {
            'r': _Node(final=False, next -> {
                'd': _Node(final=True, next -> {})
                }),
            'l': _Node(final=False, next -> {
                'f': _Node(final=True, next -> {})
                })
            })
        })
    }

"""

import os
import itertools
import codecs

MAXLEN = 48 # Longest possible word to be processed

class _DawgNode:

    # Running count of node identifiers
    _nextid = 0

    def __init__(self):
        self.id = _DawgNode._nextid
        _DawgNode._nextid += 1
        self.edges = dict()
        self.final = False
        self._strng = None # Cached string representation of this node
        self._hash = None # A hash of the final flag and a shallow traversal of the edges

    def __str__(self):
        """ Return a string representation of this node, cached if possible """
        if not self._strng:
            # We don't have a cached string representation: create it
            arr = []
            if self.final: 
                arr.append("*")
            for letter, node in self.edges.items():
                arr.append(letter)
                arr.append(str(node.id))
            self._strng = "_".join(arr)
        return self._strng

    def __hash__(self):
        """ Return a hash of this node, cached if possible """
        if not self._hash:
            # We don't have a cached hash: create it
            self._hash = self.__str__().__hash__()
        return self._hash

    def __eq__(self, other):
        """ Use string equality based on the string representation of nodes """
        return self.__str__() == other.__str__()

class _Dawg:

    def __init__(self):
        self._lastword = u''
        self._lastlen = 0
        self._root = dict()
        # Initialize empty list of starting dictionaries
        self._dicts = [None] * MAXLEN
        self._dicts[0] = self._root
        # Initialize the result list of unique nodes
        self._unique_nodes = dict()

    def _collapse_branch(self, parent, prefix, node):
        """ Attempt to collapse a single branch of the tree """

        # TBD: Calculate a hash for this branch. Work out whether
        # a branch with the same hash has already been generated, and if
        # so, check for equality with it. If equal, collapse this branch
        # into a pointer to the previously generated branch.

        if node in self._unique_nodes:
            parent[prefix] = self._unique_nodes[node]
        else:
            self._unique_nodes[node] = node
        # If the next level has more than one choice (child), we can't collapse it
        # into this one
        """
        di = node.edges
        if di and len(di) == 1:
            # Only one child: we can collapse
            lastd = None
            tail = None
            for ch, nx in di.items():
                # There will only be one iteration of this loop
                tail = ch
                lastd = nx
            # Delete the child node and put a string of characters into the root instead
            del parent[prefix]
            if node.final:
                tail = u'*' + tail
            parent[prefix + tail] = lastd
        """

    def _collapse(self, parent):
        """ Collapse and optimize the tree structure with a root in dict d
        """
        # Iterate through the letter position and
        # attempt to collapse all "simple" branches from it
        for letter, node in list(parent.items()):
            if node:
                self._collapse_branch(parent, letter, node)

    def _collapse_to(self, divergence):
        """ Collapse the tree backwards from the point of divergence
        """
        j = self._lastlen
        while j > divergence:
            if self._dicts[j]:
                self._collapse(self._dicts[j])
                self._dicts[j] = None
            j -= 1

    def addword(self, wrd):
        """ Add a word to the dictionary.
            For optimal results, words are expected to arrive in sorted order.

            As an example, we may have these three words arriving in sequence:

            abbadísar
            abbadísarinnar  [extends last word by 5 letters]
            abbadísarstofa  [backtracks from last word by 5 letters]

        """
        # Sanity check: make sure the word is not too long
        lenword = len(wrd)
        if lenword >= MAXLEN:
            raise Exception(u"Error: word exceeds maximum length of {0} letters".format(MAXLEN))
        # First see how many letters we have in common with the
        # last word we processed
        i = 0
        while i < lenword and i < self._lastlen and wrd[i] == self._lastword[i]:
            i += 1
        # Start from the point of last divergence in the tree
        # In the case of backtracking, collapse all previous outstanding branches
        self._collapse_to(i)
        # Add the (divergent) rest of the word
        d = self._dicts[i] # Note that self._dicts[0] is self._root
        nd = None
        while i < lenword:
            nd = _DawgNode()
            # Add a new starting letter to the working dictionary,
            # with a fresh node containing an empty dictionary of subsequent letters
            d[wrd[i]] = nd
            d = nd.edges
            i += 1
            self._dicts[i] = d
        # We are at the node for the final letter in the word: mark it as such
        if nd:
            nd.final = True
        # Save our position to optimize the handling of the next word
        self._lastword = wrd
        self._lastlen = lenword

    def finish(self):
        # Complete the optimization of the tree
        self._collapse_to(0)
        self._lastword = u''
        self._lastlen = 0

    def _dumplevel(self, level, d):
        for ch, nx in d.items():
            s = u' ' * level + ch
            if nx and nx.final:
                s = s + u'*'
            s += u' ' * (50 - len(s))
            s += nx.__str__()
            print(s.encode('cp850'))
            if nx and nx.edges:
                self._dumplevel(level + 1, nx.edges)

    def dump(self):
        self._dumplevel(0, self._root)

class Skrafldictionary:

    """ A Skrafldictionary allows efficient checking of words to see
        whether they are valid, i.e. contained in the dictionary of
        legal words.

        Here it is implemented as a DAWG (Directed Acyclic Word Graph).
    """

    def __init__(self):
        self._dawg = _Dawg()

    def _load_file(self, fname):
        """ Load a word list file, assumed to contain one word per line """
        with codecs.open(fname, mode='r', encoding='utf-8') as fin:
            for line in fin:
                if line.endswith(u'\r\n'):
                    # Cut off trailing CRLF (Windows-style)
                    line = line[0:-2]
                elif line.endswith(u'\n'):
                    # Cut off trailing LF (Unix-style)
                    line = line[0:-1]
                if line and len(line) < MAXLEN:
                    self._dawg.addword(line)

    def _load(self):
        """ Load word lists into memory from static preprocessed text files """
        files = ['testwords.txt']
        for f in files:
            fpath = os.path.abspath(os.path.join('resources', f))
            print("Loading word list " + fpath)
            self._load_file(fpath)
        self._dawg.finish()

    def go(self):
        """ Start the dictionary loading """
        print("Here we go...")
        self._load()
        print("Dumping...")
        self._dawg.dump()

def test():
   sd = Skrafldictionary()
   sd.go()

