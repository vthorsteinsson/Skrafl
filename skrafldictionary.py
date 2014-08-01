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

class _Node:

    def __init__(self):
        self.next = dict()
        self.final = False

    def __str__(self):
        return u'_Node ({0}) with dict {1}'.format(self.final, self.next)

    def __repr__(self):
        return u'_Node ({0}) with dict {1}'.format(self.final, self.next)

class Skrafldictionary:

    def __init__(self):
        self._lastword = u''
        self._lastlen = 0
        self._root = dict()
        # Initialize empty list of starting dictionaries
        self._dicts = [None] * MAXLEN
        self._dicts[0] = self._root

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
                    self._addword(line)

    def _load(self):
        """ Load word lists into memory from static preprocessed text files """
        # Load lists of legal words
        # The lists are divided into smaller files to circumvent the
        # file size limits (~32 MB per file) imposed by App Engine
        files = ['testwords.txt']
        for f in files:
            fpath = os.path.abspath(os.path.join('resources', f))
            print("Loading word list " + fpath)
            self._load_file(fpath)
        # Complete the optimization of the tree
        j = self._lastlen
        while j > 0:
            if self._dicts[j]:
                self._collapse(self._dicts[j])
                self._dicts[j] = None
            j -= 1
        self._lastword = u''
        self._lastlen = 0

    def _collapse_branch(self, root_d, root_ch, root_nd):
        """ Attempt to collapse a single branch of the tree """
        # If the next level has more than one choice (child), we can't collapse it
        # into this one
        di = root_nd.next
        if not(di) or len(di) > 1:
            # Nothing to do
            return
        # Only one child: we can collapse
        lastd = None
        tail = None
        for ch, nx in di.items():
            # There will only be one iteration of this loop
            tail = ch
            lastd = nx
        # Delete the child node and put a string of characters into the root instead
        del root_d[root_ch]
        if root_nd.final:
            tail = u'*' + tail
        root_d[root_ch + tail] = lastd

    def _collapse(self, d):
        """ Collapse and optimize the tree structure with a root in dict d
        """
        # Iterate through the letter position and
        # attempt to collapse all "simple" branches from it
        for ch, nx in list(d.items()):
            if nx:
                self._collapse_branch(d, ch, nx)

    def _addword(self, wrd):
        """ Add a word to the dictionary.
            For optimal results, words are expected to arrive in sorted order.

            As an example, we may have these three words arriving in sequence:

            abbadísar
            abbadísarinnar  [extends last word by 5 letters]
            abbadísarstofa  [backtracks from last word by 5 letters]

        """
        # First see how many letters we have in common with the
        # last word we processed
        i = 0
        while i < len(wrd) and i < self._lastlen and wrd[i] == self._lastword[i]:
            i += 1
        # Start from the point of last divergence in the tree
        # In the case of backtracking, collapse all previous outstanding branches
        j = self._lastlen
        while j > i:
            if self._dicts[j]:
                self._collapse(self._dicts[j])
                self._dicts[j] = None
            j -= 1
        # Add the (divergent) rest of the word
        d = self._dicts[i] # Note that self._dicts[0] is self._root
        nd = None
        while i < len(wrd):
            nd = _Node()
            # Add a new starting letter to the working dictionary,
            # with a fresh node containing an empty dictionary of subsequent letters
            d[wrd[i]] = nd
            d = nd.next
            i += 1
            self._dicts[i] = d
        # We are at the node for the final letter in the word: mark it as such
        if nd:
            nd.final = True
        # Save our position to optimize the handling of the next word
        self._lastword = wrd
        self._lastlen = len(wrd)

    def _dumplevel(self, level, d):
        for ch, nx in d.items():
            s = u' ' * level + ch
            if nx and nx.final:
                s = s + u'*'
            print(s.encode('cp861'))
            if nx and nx.next:
                self._dumplevel(level + 1, nx.next)

    def go(self):
        """ Start the dictionary loading """
        print("Here we go...")
        self._load()
        print("Dumping...")
        self._dumplevel(0, self._root)

def test():
   sd = Skrafldictionary()
   sd.go()

