#!/usr/bin/env python3

"""

    DAWG dictionary builder

    Copyright (C) 2022 Miðeind ehf.
    Original author: Vilhjálmur Þorsteinsson

    DawgBuilder uses a Directed Acyclic Word Graph (DAWG)
    to store a large set of words in an efficient structure in terms
    of storage and speed.

    The DAWG implementation is partially based on Steve Hanov's work
    (see http://stevehanov.ca/blog/index.php?id=115), which references
    a paper by Daciuk et al (http://www.aclweb.org/anthology/J00-1002.pdf).

    This implementation compresses node sequences with single edges between
    them into single multi-letter edges. It also removes redundant edges
    to "pure" final nodes.

    DawgBuilder reads a set of text input files containing plain words,
    one word per line, and outputs a text file with a compressed
    graph. This file is read by the DawgDictionary class; see
    dawgdictionary.py

    The output file is structured as a sequence of lines. Each line
    represents a node in the graph and contains information about
    outgoing edges from the node. Nodes are referred to by their
    line number, where the starting root node is in line 1 and subsequent
    nodes are numbered starting with 2.

    A node (line) is represented as follows:

    ['|']['_' prefix ':' nextnode]*

    If the node is a final node (i.e. a valid word is completed at
    the node), the first character in the line is
    a vertical bar ('|') followed by an underscore.
    The rest of the line is a sequence of edges where each edge
    is described by a prefix string followed by a colon (':')
    and the line number of the node following that edge. Edges are
    separated by underscores ('_'). The prefix string can contain
    embedded vertical bars indicating that the previous character was
    a final character in a valid word.

    Example:

    The following input word list (cf. http://tinyurl.com/kvhbyo2):

    car
    cars
    cat
    cats
    do
    dog
    dogs
    done
    ear
    ears
    eat
    eats

    generates this output graph:

    do:3_ca:2_ea:2
    t|s:0_r|s:0
    |_g|s:0_ne:0

    The root node in line 1 has three outgoing edges, "do" to node 3, "ca" to node 2, and "ea" to node 2.

    Node 2 (in line 2) has two edges, "t|s" to node 0 and "r|s" to node 0. This means that "cat" and
    "cats", "eat" and "eats" are valid words (on the first edge), as well as "car" and "cars",
    "ear" and "ears" (on the second edge).

    Node 3 (in line 3) is itself a final node, denoted by the vertical bar at the start of the line.
    Thus, "do" (coming in from the root) is a valid word, but so are "dog" and "dogs" (on the first edge)
    as well as "done" (on the second edge).

    Dictionary structure:

    Suppose the dictionary contains two words, 'word' and 'wolf'.
    This is represented by Python data structures as follows:

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
import sys
import codecs
import time

import binascii
import struct
import io

from dawgdictionary import DawgDictionary

# The DAWG builder uses the collation (sorting) given by Alphabet.sortkey
# This is by default the Icelandic sorting order
from languages import Alphabet


MAXLEN = 48  # Longest possible word to be processed
SCRABBLE_MAXLEN = 15  # Longest possible word in a Scrabble database
COMMON_MAXLEN = 12  # Longest words in common word list used by weakest robot


class _DawgNode:

    """ A _DawgNode is a node in a Directed Acyclic Word Graph (DAWG).
        It contains:
            * a node identifier (a simple unique sequence number);
            * a dictionary of edges (children) where each entry has a prefix
                (following letter(s)) together with its child _DawgNode;
            * and a Bool (final) indicating whether this node in the graph
                also marks the end of a legal word.

        A _DawgNode has a string representation which can be hashed to
        determine whether it is identical to a previously encountered node,
        i.e. whether it has the same final flag and the same edges with
        prefixes leading to the same child nodes. This assumes
        that the child nodes have already been subjected to the same
        test, i.e. whether they are identical to previously encountered
        nodes and, in that case, modified to point to the previous, identical
        subgraph. Each graph layer can thus depend on the (shallow) comparisons
        made in previous layers and deep comparisons are not necessary. This
        is an important optimization when building the graph.

    """

    # Running count of node identifiers
    # Zero is reserved for "None"
    _nextid = 1

    @staticmethod
    def sort_by_prefix(l):
        """ Return a list of (prefix, node) tuples sorted by prefix """
        return sorted(l, key=lambda x: Alphabet.sortkey(x[0]))

    @staticmethod
    def stringify_edges(edges):
        """ Utility function to create a compact descriptor string and hashable key for node edges """
        s = [
            prefix + ":" + ("0" if node is None else str(node.id))
            for prefix, node in _DawgNode.sort_by_prefix(edges.items())
        ]
        return "_".join(s)

    def __init__(self):
        self.id = _DawgNode._nextid
        _DawgNode._nextid += 1
        self.edges = dict()
        self.final = False
        self._strng = None  # Cached string representation of this node
        self._hash = None  # Hash of the final flag and a shallow traversal of the edges

    def __str__(self):
        """ Return a string representation of this node, cached if possible """
        if self._strng is None:
            # We don't have a cached string representation: create it
            edges = _DawgNode.stringify_edges(self.edges)
            self._strng = "|_" + edges if self.final else edges
        return self._strng

    def __hash__(self):
        """ Return a hash of this node, cached if possible """
        if self._hash is None:
            # We don't have a cached hash: create it
            self._hash = self.__str__().__hash__()
        return self._hash

    def __eq__(self, other):
        """ Use string equality based on the string representation of nodes """
        return self.__str__() == other.__str__()

    def reset_id(self, newid):
        """ Set a new id number for this node. This forces a reset of the cached data. """
        self.id = newid
        self._strng = None
        self._hash = None


class _Dawg:

    def __init__(self):
        self._lastword = ""
        self._lastlen = 0
        self._root = dict()
        # Initialize empty list of starting dictionaries
        self._dicts = [None for _ in range(MAXLEN)]
        self._dicts[0] = self._root
        # Initialize the result list of unique nodes

        # Keep a list of the values inserted too. Note that using
        # OrderedDict raises an exception while enumerating the values
        # (presumably because the dictionary has been altered).
        self._unique_nodes = dict()

    def _collapse_branch(self, parent, prefix, node):
        """ Attempt to collapse a single branch of the tree """

        di = node.edges
        assert di is not None

        # If the node has no outgoing edges, it must be a final node.
        # Optimize and reduce graph clutter by making the parent
        # point to None instead.

        if not di:
            assert node.final
            # We don't need to put a vertical bar (final marker) at the end of the prefix; it's implicit
            parent[prefix] = None
            return

        # Attempt to collapse simple chains of single-letter nodes
        # with single outgoing edges into a single edge with a multi-letter prefix.
        # If any of the chained nodes has a final marker, add a vertical bar '|' to
        # the prefix instead.

        if len(di) == 1:
            # Only one child: we can collapse
            lastd = None
            tail = None
            for ch, nx in di.items():
                # There will only be one iteration of this loop
                tail = ch
                lastd = nx
            # Delete the child node and put a string of prefix characters into the root instead
            del parent[prefix]
            if node.final:
                tail = "|" + tail
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

    def _collapse(self, edges):
        """ Collapse and optimize the edges in the parent dict """
        # Iterate through the letter position and
        # attempt to collapse all "simple" branches from it
        if edges:
            # NOTE! Be careful here, since the underlying dict may
            # be changing under our feet. The list() constructor is
            # thus required.
            for letter, node in list(edges.items()):
                if node:
                    self._collapse_branch(edges, letter, node)

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
            raise ValueError(
                "Word exceeds maximum length of {0} letters".format(MAXLEN)
            )
        # First see how many letters we have in common with the
        # last word we processed
        i = 0
        while i < lenword and i < self._lastlen and wrd[i] == self._lastword[i]:
            i += 1
        # Start from the point of last divergence in the tree
        # In the case of backtracking, collapse all previous outstanding branches
        self._collapse_to(i)
        # Add the (divergent) rest of the word
        d = self._dicts[i]  # Note that self._dicts[0] is self._root
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
        if nd is not None:
            nd.final = True
        # Save our position to optimize the handling of the next word
        self._lastword = wrd
        self._lastlen = lenword

    def finish(self):
        """ Complete the optimization of the tree """
        self._collapse_to(0)
        self._lastword = ""
        self._lastlen = 0
        self._collapse(self._root)
        # Renumber the nodes for a tidier graph and more compact output
        # 1 is the line number of the root in text output files, so we start with 2
        ix = 2
        for n in self._unique_nodes.values():
            if n is not None:
                n.reset_id(ix)
                ix += 1

    def _dump_level(self, level, d):
        """ Dump a level of the tree and continue into sublevels by recursion """
        for ch, nx in d.items():
            s = " " * level + ch
            if nx and nx.final:
                s += "|"
            s += " " * (50 - len(s))
            s += nx.__str__()
            print(s)
            if nx and nx.edges:
                self._dump_level(level + 1, nx.edges)

    def dump(self):
        """ Write a human-readable text representation of the DAWG to the standard output """
        self._dump_level(0, self._root)
        print(
            "Total of {0} nodes and {1} edges with {2} prefix characters".format(
                self.num_unique_nodes(), self.num_edges(), self.num_edge_chars()
            )
        )
        for n in self._unique_nodes.values():
            if n is not None:
                # We don't use ix for the time being
                print("Node {0}{1}".format(n.id, "|" if n.final else ""))
                for prefix, nd in n.edges.items():
                    print(
                        "   Edge {0} to node {1}".format(
                            prefix, 0 if nd is None else nd.id
                        )
                    )

    def num_unique_nodes(self):
        """ Count the total number of unique nodes in the graph """
        return len(self._unique_nodes)

    def num_edges(self):
        """ Count the total number of edges between unique nodes in the graph """
        edges = 0
        for n in self._unique_nodes.values():
            if n is not None:
                edges += len(n.edges)
        return edges

    def num_edge_chars(self):
        """ Count the total number of edge prefix letters in the graph """
        chars = 0
        for n in self._unique_nodes.values():
            if n is not None:
                for prefix in n.edges:
                    # Add the length of all prefixes to the edge, minus the vertical bar
                    # '|' which indicates a final character within the prefix
                    chars += len(prefix) - prefix.count("|")
        return chars

    def write_packed(self, packer):
        """ Write the optimized DAWG to a packer """
        packer.start(len(self._root))
        # Start with the root edges
        sortfunc = _DawgNode.sort_by_prefix
        for prefix, nd in sortfunc(self._root.items()):
            if nd is None:
                packer.edge(0, prefix)
            else:
                packer.edge(nd.id, prefix)
        for node in self._unique_nodes.values():
            if node is not None:
                packer.node_start(node.id, node.final, len(node.edges))
                for prefix, nd in sortfunc(node.edges.items()):
                    if nd is None:
                        packer.edge(0, prefix)
                    else:
                        packer.edge(nd.id, prefix)
                packer.node_end(node.id)
        packer.finish()

    def write_text(self, stream):
        """ Write the optimized DAWG to a text stream """
        # +1 to include the root in the node count
        print(
            "Output graph has {0} nodes"
            .format(len(self._unique_nodes))
        )
        # We don't have to write node ids since they correspond to line numbers.
        # The root is always in the first line and the first node after the root has id 2.
        # Start with the root edges
        stream.write(_DawgNode.stringify_edges(self._root) + "\n")
        for node in self._unique_nodes.values():
            if node is not None:
                stream.write(node.__str__() + "\n")


class _BinaryDawgPacker:

    """ _BinaryDawgPacker packs the DAWG data to a byte stream.

        !!! This is not fully implemented and not currently used by the
        !!! DawgDictionary class in dawgdictionary.py

        The stream format is as follows:

        For each node:
            BYTE Node header
                [feeeeeee]
                    f = final bit
                    eeee = number of edges
            For each edge out of a node:
                BYTE Prefix header
                    [ftnnnnnn]
                    If t == 1 then
                        f = final bit of single prefix character
                        nnnnnn = single prefix character,
                            coded as an index into AÁBDÐEÉFGHIÍJKLMNOÓPRSTUÚVXYÝÞÆÖ
                    else
                        00nnnnnn = number of prefix characters following
                        n * BYTE Prefix characters
                            [fccccccc]
                                f = final bit
                                ccccccc = prefix character,
                                    coded as an index into AÁBDÐEÉFGHIÍJKLMNOÓPRSTUÚVXYÝÞÆÖ
                DWORD Offset of child node

    """

    CODING_UCASE = Alphabet.upper
    CODING_LCASE = Alphabet.order

    def __init__(self, stream):
        self._stream = stream
        self._byte_struct = struct.Struct("<B")
        self._loc_struct = struct.Struct("<L")
        # _locs is a dict of already written nodes and their stream locations
        self._locs = dict()
        # _fixups is a dict of node ids and file positions where the
        # node id has been referenced without knowing where the node is
        # located
        self._fixups = dict()

    def start(self, num_root_edges):
        # The stream starts off with a single byte containing the
        # number of root edges
        self._stream.write(self._byte_struct.pack(num_root_edges))

    def node_start(self, ident, final, num_edges):
        pos = self._stream.tell()
        if ident in self._fixups:
            # We have previously output references to this node without
            # knowing its location: fix'em now
            for fix in self._fixups[ident]:
                self._stream.seek(fix)
                self._stream.write(self._loc_struct.pack(pos))
            self._stream.seek(pos)
            del self._fixups[ident]
        # Remember where we put this node
        self._locs[ident] = pos
        self._stream.write(
            self._byte_struct.pack((0x80 if final else 0x00) | (num_edges & 0x7F))
        )

    def node_end(self, ident):
        pass

    def edge(self, ident, prefix):
        b = []
        last = None
        for c in prefix:
            if c == u"|":
                last |= 0x80
            else:
                if last is not None:
                    b.append(last)
                try:
                    last = _BinaryDawgPacker.CODING_LCASE.index(c)
                except ValueError:
                    last = _BinaryDawgPacker.CODING_UCASE.index(c)
        b.append(last)

        if len(b) == 1:
            # Save space on single-letter prefixes
            self._stream.write(self._byte_struct.pack(b[0] | 0x40))
        else:
            self._stream.write(self._byte_struct.pack(len(b) & 0x3F))
            for by in b:
                self._stream.write(self._byte_struct.pack(by))
        if ident == 0:
            self._stream.write(self._loc_struct.pack(0))
        elif ident in self._locs:
            # We've already written the node and know where it is: write its location
            self._stream.write(self._loc_struct.pack(self._locs[ident]))
        else:
            # This is a forward reference to a node we haven't written yet:
            # reserve space for the node location and add a fixup
            pos = self._stream.tell()
            self._stream.write(
                self._loc_struct.pack(0xFFFFFFFF)
            )  # Temporary - will be overwritten
            if ident not in self._fixups:
                self._fixups[ident] = []
            self._fixups[ident].append(pos)

    def finish(self):
        # Clear the temporary fixup stuff from memory
        self._locs = dict()
        self._fixups = dict()

    def dump(self):
        buf = self._stream.getvalue()
        print("Total of {0} bytes".format(len(buf)))
        s = binascii.hexlify(buf)
        BYTES_PER_LINE = 16
        CHARS_PER_LINE = BYTES_PER_LINE * 2
        i = 0
        addr = 0
        lens = len(s)
        while i < lens:
            line = s[i : i + CHARS_PER_LINE]
            print(
                "{0:08x}: {1}".format(
                    addr,
                    " ".join([line[j : j + 2] for j in range(0, len(line) - 1, 2)]),
                )
            )
            i += CHARS_PER_LINE
            addr += BYTES_PER_LINE


class DawgBuilder:

    """ Creates a DAWG from word lists and writes the resulting
        graph to binary or text files.

        The word lists are assumed to be pre-sorted in ascending
        lexicographic order. They are automatically merged during
        processing to appear as one aggregated and sorted word list.
    """

    def __init__(self):
        self._dawg = None

    class _InFile(object):
        """ InFile represents a single sorted input file. """

        def __init__(self, relpath, fname):
            self._eof = False
            self._nxt = None
            self._key = None  # Sortkey for self._nxt
            fpath = os.path.abspath(os.path.join(relpath, fname))
            self._fin = codecs.open(fpath, mode="r", encoding="utf-8")
            print("Opened input file {0}".format(fpath))
            self._init()

        def _init(self):
            # Read the first word from the file to initialize the iteration
            self.read_word()

        def read_word(self):
            """ Read lines until we have a legal word or EOF """
            while True:
                try:
                    line = next(self._fin)
                except StopIteration:
                    # We're done with this file
                    self._eof = True
                    return False
                if line.endswith("\r\n"):
                    # Cut off trailing CRLF (Windows-style)
                    line = line[0:-2]
                elif line.endswith("\n"):
                    # Cut off trailing LF (Unix-style)
                    line = line[0:-1]
                if line and len(line) < MAXLEN:
                    # Valid word
                    self._nxt = line
                    self._key = Alphabet.sortkey(line)
                    return True

        def next_word(self):
            """ Returns the next available word from this input file """
            return None if self._eof else self._nxt

        def next_key(self):
            """ Returns the sort key of the next available word from this input file """
            return None if self._eof else self._key

        def has_word(self):
            """ True if a word is available, or False if EOF has been reached """
            return not self._eof

        def close(self):
            """ Close the associated file, if it is still open """
            if self._fin is not None:
                self._fin.close()
            self._fin = None


    class _InFileToBeSorted(_InFile):
        """ InFileToBeSorted represents an input file that should be pre-sorted in memory """

        def __init__(self, relpath, fname):
            # Call base class constructor
            super(DawgBuilder._InFileToBeSorted, self).__init__(relpath, fname)

        def _init(self):
            """ Read the entire file and pre-sort it """
            self._list = []
            self._index = 0
            try:
                for line in self._fin:
                    if line.endswith("\r\n"):
                        # Cut off trailing CRLF (Windows-style)
                        line = line[0:-2]
                    elif line.endswith("\n"):
                        # Cut off trailing LF (Unix-style)
                        line = line[0:-1]
                    if line and len(line) < MAXLEN:
                        # Valid word
                        self._list.append(line)
            except StopIteration:
                pass
            finally:
                self._fin.close()
                self._fin = None
            self._len = len(self._list)
            self._list.sort(key=Alphabet.sortkey)
            self.read_word()

        def read_word(self):
            if self._index >= self._len:
                self._eof = True
                return False
            self._nxt = self._list[self._index]
            self._key = Alphabet.sortkey(self._nxt)
            self._index += 1
            return True

        def close(self):
            """ Close the associated file, if it is still open """
            pass

    def _load(self, relpath, inputs, removals, word_filter):
        """ Load word lists into the DAWG from one or more static text files,
            assumed to be located in the relpath subdirectory.
            The text files should contain one word per line,
            encoded in UTF-8 format. Lines may end with CR/LF or LF only.
            Upper or lower case should be consistent throughout.
            All lower case is preferred. The words should appear in
            ascending sort order within each file. The input files will
            be merged in sorted order in the load process. Words found
            in the removals file will be removed from the output.
        """
        self._dawg = _Dawg()
        # Total number of words read from input files
        incount = 0
        # Total number of words written to output file
        # (may be less than incount because of filtering or duplicates)
        outcount = 0
        # Total number of duplicate words found in input files
        duplicates = 0
        # Count removed words due to the removed word list
        removed = 0
        # Enforce strict ascending lexicographic order
        lastword = None
        lastkey = None
        # Open the input files. The first (main) input file is assumed
        # to be pre-sorted. Other input files are sorted in memory before
        # being used.
        infiles = [
            DawgBuilder._InFile(relpath, f)
            if ix == 0
            else DawgBuilder._InFileToBeSorted(relpath, f)
            for ix, f in enumerate(inputs)
        ]
        # Open the removal file, if any
        if removals is None:
            removal = None
        else:
            removal = DawgBuilder._InFileToBeSorted(relpath, removals)
        remove_key = None if removal is None else removal.next_key()
        # Merge the inputs
        while True:
            smallest = None
            # Find the smallest next word among the input files
            for f in infiles:
                if f.has_word():
                    if smallest is None:
                        smallest = f
                        key_smallest = smallest.next_key()
                    else:
                        # Use the sort ordering of the current locale to compare words
                        key_f = f.next_key()
                        if key_f == key_smallest:
                            # We have the same word in two files: make sure we don't add it twice
                            f.read_word()
                            incount += 1
                            duplicates += 1
                        elif key_f < key_smallest:
                            # New smallest word
                            smallest = f
                            key_smallest = key_f
            if smallest is None:
                # All files exhausted: we're done
                break
            # We have the smallest word
            word = smallest.next_word()
            key = key_smallest
            incount += 1
            if lastkey and lastkey >= key:
                # Something appears to be wrong with the input sort order.
                # If it's a duplicate, we don't mind too much, but if it's out
                # of order, display a warning
                if lastkey > key:
                    print(
                        'Warning: input files should be in ascending order, but "{0}" > "{1}"'.format(
                            lastword, word
                        )
                    )
                else:
                    # Identical to previous word
                    duplicates += 1
            elif word_filter is None or word_filter(word):
                # This word passes the filter: check the removal list, if any
                while remove_key is not None and remove_key < key:
                    # Skip past words in the removal file as needed
                    removal.read_word()
                    remove_key = removal.next_key()
                if remove_key is not None and remove_key == key:
                    # Found a word to be removed
                    removal.read_word()
                    remove_key = removal.next_key()
                    removed += 1
                else:
                    # Not a word to be removed: add it to the graph
                    self._dawg.add_word(word)
                    outcount += 1
                lastword = word
                lastkey = key
            if incount % 10000 == 0:
                # Progress indicator
                print("{0}...".format(incount), end="\r")
                sys.stdout.flush()
            # Advance to the next word in the file we read from
            smallest.read_word()
        # Done merging: close all files
        for f in infiles:
            assert not f.has_word()
            f.close()
        # Complete and clean up
        self._dawg.finish()
        print(
            "Finished loading {0} words, output {1} words, {2} duplicates skipped, {3} removed"
            .format(incount, outcount, duplicates, removed)
        )

    def _output_binary(self, relpath, output):
        """ Write the DAWG to a flattened binary output file with extension '.dawg' """
        assert self._dawg is not None
        # !!! Experimental / debugging...
        f = io.BytesIO()
        # Create a packer to flatten the tree onto a binary stream
        p = _BinaryDawgPacker(f)
        # Write the tree using the packer
        self._dawg.write_packed(p)
        # Dump the packer contents to stdout for debugging
        p.dump()
        # Write packed DAWG to binary file
        with open(
            os.path.abspath(os.path.join(relpath, output + ".dawg")), "wb"
        ) as of:
            of.write(f.getvalue())
        f.close()

    def _output_text(self, relpath, output):
        """ Write the DAWG to a text output file with extension '.text.dawg' """
        assert self._dawg is not None
        fname = os.path.abspath(os.path.join(relpath, output + ".text.dawg"))
        with codecs.open(fname, mode="w", encoding="utf-8") as fout:
            self._dawg.write_text(fout)

    def build(
        self, inputs, output, relpath="resources", word_filter=None, removals=None
    ):
        """ Build a DAWG from input file(s) and write it to the output file(s) (potentially in multiple formats).
            The input files are assumed to be individually sorted in correct ascending alphabetical
            order. They will be merged in parallel into a single sorted stream and added to the DAWG.
        """
        # inputs is a list of input file names
        # output is an output file name without file type suffix (extension);
        # ".dawg" and ".text.dawg" will be appended depending on output formats
        # relpath is a relative path to the input and output files
        print("DawgBuilder starting...")
        if (not inputs) or (not output):
            # Nothing to do
            print("No inputs or no output: Nothing to do")
            return
        self._load(relpath, inputs, removals, word_filter)
        # print("Dumping...")
        # self._dawg.dump()
        print("Outputting...")
        # self._output_binary(relpath, output) # Not used for now
        self._output_text(relpath, output)
        print("DawgBuilder done")


# Filter functions
# The resulting DAWG will include all words for which filter() returns True, and exclude others.
# Useful for excluding long words or words containing "foreign" characters.

# noinspection PyUnusedLocal
def nofilter(word):
    """ No filtering - include all input words in output graph """
    return True


def filter_skrafl(word):
    """ Filtering for Icelandic Scrabble(tm)
        Exclude words longer than SCRABBLE_MAXLEN letters (won't fit on board)
        Exclude words with non-Icelandic letters, i.e. C, Q, W, Z
        Exclude two-letter words in the word database that are not
            allowed according to Icelandic Scrabble rules
    """
    return len(word) <= SCRABBLE_MAXLEN


def filter_common(word):
    """ For the list of common words used by the weakest robot,
        skip words longer than 12 characters (those would almost
        never be used anyway)
    """
    return len(word) <= COMMON_MAXLEN


def run_test():
    """ Build a DAWG from the files listed """
    # This creates a DAWG from a single file named testwords.txt
    print("Starting DAWG build for testwords.txt")
    db = DawgBuilder()
    t0 = time.time()
    db.build(
        ["testwords.txt"],  # Input files to be merged
        "testwords",  # Output file - full name will be testwords.text.dawg
        "resources",
    )  # Subfolder of input and output files
    t1 = time.time()
    print("Build took {0:.2f} seconds".format(t1 - t0))


def run_twl06():
    """ Build a DAWG from the files listed """
    # This creates a DAWG from a single file named TWL06.txt,
    # the Scrabble Tournament Word List version 6
    print("Starting DAWG build for TWL06.txt")
    db = DawgBuilder()
    t0 = time.time()
    db.build(
        ["TWL06.txt"],  # Input files to be merged
        "TWL06",  # Output file - full name will be TWL06.text.dawg
        "resources",  # Subfolder of input and output files
    )
    t1 = time.time()
    print("Build took {0:.2f} seconds".format(t1 - t0))


def run_skrafl():
    """ Build a DAWG from the files listed """
    # This creates a DAWG from the full database of Icelandic words in
    # 'Beygingarlýsing íslensks nútímamáls' (BIN), except abbreviations,
    # 'skammstafanir', and proper names, 'sérnöfn'.
    # The words in ordalisti.add.txt are added to BIN, and words in
    # ordalisti.remove.txt (known errors) are removed.
    # The result is about 2.3 million words, generating >100,000 graph nodes
    print("Starting DAWG build for skraflhjalp/netskrafl.appspot.com")
    db = DawgBuilder()
    t0 = time.time()
    db.build(
        ["ordalistimax15.sorted.txt", "ordalisti.add.txt"],  # Input files to be merged
        "ordalisti",  # Output file - full name will be ordalisti.text.dawg
        "resources",  # Subfolder of input and output files
        filter_skrafl,  # Word filter function to apply
        "ordalisti.remove.txt",  # Words to remove
    )
    t1 = time.time()
    print("Build took {0:.2f} seconds".format(t1 - t0))

    # Test loading of DAWG
    dawg = DawgDictionary()
    fpath = os.path.abspath(os.path.join("resources", "ordalisti.text.dawg"))
    t0 = time.time()
    dawg.load(fpath)
    t1 = time.time()

    print("DAWG loaded in {0:.2f} seconds".format(t1 - t0))

    # Store DAWG as a Python cPickle file
    t0 = time.time()
    dawg.store_pickle(
        os.path.abspath(os.path.join("resources", "ordalisti.dawg.pickle"))
    )
    t1 = time.time()

    print("DAWG pickle file stored in {0:.2f} seconds".format(t1 - t0))

    print("DAWG builder run complete")


if __name__ == "__main__":

    # Build the whole Icelandic Netskrafl word database by default
    run_skrafl()
