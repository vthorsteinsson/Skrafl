# -*- coding: utf-8 -*-

""" Scrabble word dictionary

Author: Vilhjalmur Thorsteinsson, 2014

The dictionary is encapsulated within the class DawgDictionary.
The class can resolve whether a particular word is legal or not
by looking it up in a database of allowed Scrabble words.

DawgDictionary uses a Directed Acyclic Word Graph (DAWG) internally
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
import codecs

import binascii
import struct
import io


MAXLEN = 48 # Longest possible word to be processed


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
    _nextid = 1 # Zero is reserved for "None"

    @staticmethod
    def stringify_edges(edges, arr):
        """ Utility function to create a compact descriptor string and hashable key for node edges """
        for prefix, node in edges.items():
            arr.append(prefix + u':' + (u'0' if node is None else str(node.id)))
        return "_".join(arr)

    def __init__(self):
        self.id = _DawgNode._nextid
        _DawgNode._nextid += 1
        self.edges = dict()
        self.final = False
        self._strng = None # Cached string representation of this node
        self._hash = None # Hash of the final flag and a shallow traversal of the edges

    def __str__(self):
        """ Return a string representation of this node, cached if possible """
        if not self._strng:
            # We don't have a cached string representation: create it
            arr = []
            if self.final: 
                arr.append("*")
            self._strng = _DawgNode.stringify_edges(self.edges, arr)
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

        di = node.edges
        assert di is not None

        # If the node has no outgoing edges, it must be a final node.
        # Optimize by reducing graph clutter and making the parent
        # point to None instead.

        if len(di) == 0:
            assert node.final
            # We don't need to put an asterisk at the end of the prefix; it's implicit
            parent[prefix] = None
            return

        # Attempt to collapse simple chains of single-letter nodes
        # with single outgoing edges into a single node with a multi-letter prefix.
        # If any of the chained nodes has a final marker, add an asterisk '*' to
        # the prefix instead.

        # If the next level has more than one choice (child), we can't collapse it
        # into this one

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

    def _collapse(self, edges):
        """ Collapse and optimize the edges in the parent dict """
        # Iterate through the letter position and
        # attempt to collapse all "simple" branches from it
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
            raise ValueError("Word exceeds maximum length of {0} letters".format(MAXLEN))
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
        if nd is not None:
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
            if n is not None:
                # We don't use ix for the time being
                print(u"Node {0}{1}".format(n.id, u"*" if n.final else u""))
                for prefix, nd in n.edges.items():
                    print(u"   Edge {0} to node {1}".format(prefix, 0 if nd is None else nd.id))

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
                    # Add the length of all prefixes to the edge, minus the asterisk
                    # '*' which indicates a final character within the prefix
                    chars += len(prefix) - prefix.count(u'*')
        return chars

    def write_packed(self, packer):
        """ Write the optimized DAWG to a packer """
        packer.start(len(self._root))
        # Start with the root edges
        for prefix, nd in self._root.items():
            packer.edge(nd.id, prefix)
        for node in self._unique_nodes.values():
            if node is not None:
                packer.node_start(node.id, node.final, len(node.edges))
                for prefix, nd in node.edges.items():
                    if nd is None:
                        packer.edge(0, prefix)
                    else:
                        packer.edge(nd.id, prefix)
                packer.node_end(node.id)
        packer.finish()

    def write_text(self, stream):
        """ Write the optimized DAWG to a text stream """
        # Start with the root edges
        arr = []
        stream.write(u"Root " + _DawgNode.stringify_edges(self._root, arr) + u"\n")
        for node in self._unique_nodes.values():
            if node is not None:
                stream.write(str(node.id) + u" " + node.__str__() + u"\n")

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

    CODING_UCASE = u"AÁBDÐEÉFGHIÍJKLMNOÓPRSTUÚVXYÝÞÆÖ"
    CODING_LCASE = u"aábdðeéfghiíjklmnoóprstuúvxyýþæö"

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

    def node_start(self, id, final, num_edges):
        pos = self._stream.tell()
        if id in self._fixups:
            # We have previously output references to this node without
            # knowing its location: fix'em now
            for fix in self._fixups[id]:
                self._stream.seek(fix)
                self._stream.write(self._loc_struct.pack(pos))
            self._stream.seek(pos)
            del self._fixups[id]
        # Remember where we put this node
        self._locs[id] = pos
        self._stream.write(self._byte_struct.pack((0x80 if final else 0x00) | (num_edges & 0x7F)))

    def node_end(self, id):
        pass

    def edge(self, id, prefix):
        b = []
        last = None
        for c in prefix:
            if c == u'*':
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
        if id == 0:
            self._stream.write(self._loc_struct.pack(0))
        elif id in self._locs:
            # We've already written the node and know where it is: write its location
            self._stream.write(self._loc_struct.pack(self._locs[id]))
        else:
            # This is a forward reference to a node we haven't written yet:
            # reserve space for the node location and add a fixup
            pos = self._stream.tell()
            self._stream.write(self._loc_struct.pack(0xFFFFFFFF)) # Temporary - will be overwritten
            if id not in self._fixups:
                self._fixups[id] = []
            self._fixups[id].append(pos)

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
            print("{0:08x}: {1}".format(addr, u" ".join([line[j : j + 2] for j in range(0, len(line) - 1, 2)])))
            i += CHARS_PER_LINE
            addr += BYTES_PER_LINE


class DawgBuilder:

    """ Creates a DAWG from word lists and writes the resulting
        graph to binary or text files.
    """

    def __init__(self):
        self._dawg = None

    def _load_file(self, fname):
        """ Load a single word list file, assumed to contain one word per line """
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

    def _load(self, relpath, inputs):
        """ Load word lists into the DAWG from static text files,
            assumed to be located in the 'resources' subdirectory.
            The text files should contain one word per line,
            encoded in UTF-8 format. Lines may end with CR/LF or LF only.
            Upper or lower case should be consistent throughout.
            All lower case is preferred. The words should appear in
            ascending sort order.
        """
        self._dawg = _Dawg()
        for f in inputs:
            fpath = os.path.abspath(os.path.join(relpath, f))
            print("Loading word list " + fpath)
            self._load_file(fpath)
        self._dawg.finish()

    def _output_binary(self, relpath, output):
        """ Write the DAWG to a flattened binary stream """
        assert self._dawg is not None
        # Experimental / debugging...
        f = io.BytesIO()
        # Create a packer to flatten the tree onto a binary stream
        p = _BinaryDawgPacker(f)
        # Write the tree using the packer
        self._dawg.write_packed(p)
        # Dump the packer contents to stdout for debugging
        p.dump()
        # Write packed DAWG to binary file
        with open(os.path.abspath(os.path.join(relpath, output + u".dawg")), "wb") as of:
            of.write(f.getvalue())
        f.close()

    def _output_text(self, relpath, output):
        """ Write the DAWG to a text stream """
        assert self._dawg is not None
        fname = os.path.abspath(os.path.join(relpath, output + u".text.dawg"))
        with codecs.open(fname, mode='w', encoding='utf-8') as fout:
            self._dawg.write_text(fout)

    def build(self, inputs, output, relpath="resources"):
        """ Build a DAWG from input files and write it to output files """
        # inputs is a list of input file names
        # output is an output file name without file type suffix; ".dawg" and ".text.dawg" will be appended
        # relpath is a relative path to the input and output files
        print("DawgBuilder starting...")
        self._load(relpath, inputs)
        print("Dumping...")
        self._dawg.dump()
        print("Outputting...")
        self._output_binary(relpath, output)
        self._output_text(relpath, output)
        print("DawgBuilder done")


class BinaryDawgTester:

    def __init__(self):
        self._b = bytes()
        self._load_binary_dawg('testwords.dawg')
        self._byte_struct = struct.Struct("<B")
        self._loc_struct = struct.Struct("<L")

    def _load_binary_dawg(self, fname):
        with open(os.path.abspath(os.path.join('resources', fname)), "rb") as f:
            self._b = f.readall()

    def find(self, word):
        # !!! Incomplete code !!!
        node = 0
        for c in word:
            try:
                ci = _BinaryDawgPacker.CODING_LCASE.index(c)
            except ValueError:
                ci = _BinaryDawgPacker.CODING_UCASE.index(c)
            numedges = self._byte_struct.unpack_from(self._b, node)
            edge = node + 1
            for i in range(0, numedges):
                ehdr = self._byte_struct.unpack_from(self._b, edge)
                if ehdr & 0x40:
                    # Single-letter prefix
                    if ci == ehdr & 0x3F:
                        # We match this prefix: traverse the edge to the next node
                        node = self._loc_struct.unpack_from(self._b, edge + 1)
                        break
                    # Did not match: go to next edge
                    edge += 1 + self._loc_struct.size()
                else:
                    # Multi-letter prefix
                    numletters = ehdr & 0x3F


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
        if nodedata[0] == "Root":
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
                if line and len(line) < MAXLEN:
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
        self._test(u"abstraktmálarið")
        self._test(u"abstraktmálari")
        self._test(u"abstraktmálar")
        self._test(u"abstraktmála")
        self._test(u"prófun")
        self._test(u"")
        self._test(u"abo550")
        self._dawg = None


def test():
    # Build a DAWG from the file testwords.txt
    db = DawgBuilder()
    db.build(["testwords.txt"], "testwords", "resources")
    # Test navivation in the DAWG
    dt = DawgTester()
    dt.go("testwords", "resources")

