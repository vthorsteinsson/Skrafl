# -*- coding: utf-8 -*-

""" Scrabble word dictionary

Author: Vilhjalmur Thorsteinsson, 2014

The dictionary is encapsulated within the class Skrafldictionary.
The class can resolve whether a particular word is legal or not
by looking it up in a database of allowed Scrabble words.

Skrafldictionary uses a Directed Acyclic Word Graph (DAWG) internally
to store the word database in an efficient structure in terms
of storage and speed.

The DAWG implementation is partially based on Steve Hanov's work
(see http://stevehanov.ca/blog/index.php?id=115).

Dictionary structure:

Suppose the dictionary contains two words, 'word' and 'wolf'.
This will be represented as follows:

root _Dawg -> {
    'w': _DawgNode(final=False, edges -> {
        'o': _DawgNode(final=False, edges -> {
            'r': _DawgNode(final=False, edges -> {
                'd': _DawgNode(final=True, edges -> {})
                }),
            'l': _DawgNode(final=False, edges -> {
                'f': _DawgNode(final=True, edges -> {})
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

    """ A _DawgNode is a node in a Directed Acyclic Word Graph (DAWG).
        It contains:
            * a node identifier (a simple unique sequence number);
            * a dictionary of edges (children) where each entry has a following
                letter together with its child _DawgNode;
            * and a Bool (final) indicating whether this node in the graph represents
                the end of a legal word.

        A _DawgNode has a string representation which can be hashed to
        determine whether it is identical to a previously encountered node,
        i.e. whether it has the same final flag and the same edges with
        following letters leading to the same child nodes. This assumes
        that the child nodes have already been subjected to the same
        test, i.e. whether they are identical to previously encountered
        nodes and, in that case, modified to point to the previous, identical
        subtree. Each tree layer can thus depend on the (shallow) comparisons
        made in previous layers and deep comparisons are not necessary.

    """

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

        # If the next level has more than one choice (child), we can't collapse it
        # into this one
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
            prefix += tail
            parent[prefix] = lastd
            node = lastd

        # If a node with the same signature (key) has already been generated,
        # i.e. having the same final flag and the same edges leading to the same
        # child nodes, replace the edge leading to this node with an edge
        # to the previously generated node.

        if node in self._unique_nodes:
            # Signature matches a previously generated node: replace the edge
            parent[prefix] = self._unique_nodes[node]
        else:
            # This is a new, unique signature: store it in the dictionary of unique nodes
            self._unique_nodes[node] = node

    def _collapse(self, parent):
        """ Collapse and optimize the tree structure with a root in dict d """
        # Iterate through the letter position and
        # attempt to collapse all "simple" branches from it
        for letter, node in list(parent.items()):
            if node:
                self._collapse_branch(parent, letter, node)

    def _collapse_to(self, divergence):
        """ Collapse the tree backwards from the point of divergence """
        j = self._lastlen
        while j > divergence:
            if self._dicts[j]:
                self._collapse(self._dicts[j])
                self._dicts[j] = None
            j -= 1

    def add_word(self, wrd):
        """ Add a word to the DAWG.
            Words are expected to arrive in sorted order.

            As an example, we may have these three words arriving in sequence:

            abbadísar
            abbadísarinnar  [extends last word by 5 letters]
            abbadísarstofa  [backtracks from last word by 5 letters]

        """
        # Sanity check: make sure the word is not too long
        lenword = len(wrd)
        if lenword >= MAXLEN:
            raise Exception("Error: word exceeds maximum length of {0} letters".format(MAXLEN))
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
        """ Complete the optimization of the tree """
        self._collapse_to(0)
        self._lastword = u''
        self._lastlen = 0
        self._collapse(self._root)

    def _dump_level(self, level, d):
        """ Dump a level of the tree and continue into sublevels by recursion """
        for ch, nx in d.items():
            s = u' ' * level + ch
            if nx and nx.final:
                s = s + u'*'
            s += u' ' * (50 - len(s))
            s += nx.__str__()
            print(s.encode('cp850'))
            if nx and nx.edges:
                self._dump_level(level + 1, nx.edges)

    def dump(self):
        """ Write a human-readable text representation of the DAWG to the standard output """
        self._dump_level(0, self._root)
        print("Total of {0} nodes and {1} edges with {2} prefix characters".format(self.num_unique_nodes(),
            self.num_edges(), self.num_edge_chars()))
        for ix, n in enumerate(self._unique_nodes.values()):
            # We don't use ix for the time being
            print(u"Node {0}{1}".format(n.id, u"*" if n.final else u""))
            for prefix, nd in n.edges.items():
                print(u"   Edge {0} to node {1}".format(prefix, nd.id))

    def num_unique_nodes(self):
        """ Count the total number of unique nodes in the graph """
        return len(self._unique_nodes)

    def num_edges(self):
        """ Count the total number of edges between unique nodes in the graph """
        edges = 0
        for n in self._unique_nodes.values():
            edges += len(n.edges)
        return edges

    def num_edge_chars(self):
        """ Count the total number of edge prefix letters in the graph """
        chars = 0
        for n in self._unique_nodes.values():
            for prefix in n.edges:
                # Add the length of all prefixes to the edge, minus the asterisk
                # '*' which indicates a final character within the prefix
                chars += len(prefix) - prefix.count(u'*')
        return chars

    def _output(self, packer, d):
        """ Use a packer to output a level of the tree and continue into sublevels by recursion """
        for prefix, nd in d.items():
            packer.output(prefix, nd.id, nd.final, len(nd.edges))
            self._output(packer, nd.edges)

    def output(self, packer):
        """ Initiate output of the entire tree to a packer """
        packer.start()
        self._output(packer, self._root)
        packer.finish()


class _BinaryDawgPacker:

    """ _BinaryDawgPacker packs the DAWG data to a byte stream.
        The format is as follows:

        For each node:
            BYTE Node header
                [feeeeeee]
                    f = final bit
                    eeee = number of edges
            For each edge out of a node:
                BYTE Prefix header
                    [tfnnnnnn]
                    If t == 1 then
                        f = final bit of single prefix character
                        nnnnnn = single prefix character,
                            coded as an index into AÁBDÐEÉFGHIÍJKLMNOÓPRSTUÚVXYÝÞÆÖ
                    else
                        fnnnnnn = number of prefix characters following
                        n * BYTE Prefix characters
                            [fccccccc]
                                f = final bit
                                ccccccc = prefix character,
                                    coded as an index into AÁBDÐEÉFGHIÍJKLMNOÓPRSTUÚVXYÝÞÆÖ
                DWORD Offset of child node

    """

    def start(self):
        pass

    def output(self, prefix, id, final, num_edges):
        pass

    def finish(self):
        pass


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
                    self._dawg.add_word(line)

    def _load(self):
        """ Load word lists into memory from static text files,
            assumed to be located in the 'resources' subdirectory.
            The text files should contain one word per line,
            encoded in UTF-8 format. Lines may end with CR/LF or LF only.
            Upper or lower case should be consistent throughout.
            All lower case is preferred. The words should appear in
            ascending sort order.
        """
        files = ['testwords.txt'] # Add files to this list as required
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

