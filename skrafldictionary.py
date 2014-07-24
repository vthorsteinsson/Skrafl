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
        self._dicts = [None for i in range(0, MAXLEN)]
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
                if line:
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

    def _collapse(self, i, newd):
        """ Collapse and optimize the tree structure previously in
            place for character position i
        """
        d = self._dicts[i]
        if d:
        # Process d here
            tail = u''
            di = d
            while di and len(di) == 1:
                for ch, nx in di.iteritems():
                    tail += ch
                    if nx and nx.final:
                        tail += u'*'
                    if nx:
                        di = nx.next
                    else:
                        di = None
                    # We only want one iteration
                    break
            if di is None or len(di) == 0:
                # We found a contiguous sequence of 1-child dicts:
                # Clear the original dictionary and put a single compressed node
                # into it instead
                d.clear()
                d[tail] = None
        self._dicts[i] = newd

    def _addword(self, wrd):
        """ Add a word to the dictionary.
            For optimal results, words are expected to arrive in sorted order.
        """
        # First see how many letters we have in common with the
        # last word we processed
        i = 0
        while i < len(wrd) and i < self._lastlen and wrd[i] == self._lastword[i]:
            i += 1
        # Start from the point of last divergence in the tree
        d = self._dicts[i] # Note that self._dicts[0] is self._root
        nd = None
        # Add the (divergent) rest of the word
        while i < len(wrd):
            nd = _Node()
            # Add a new starting letter to the working dictionary,
            # with a fresh node containing an empty dictionary of subsequent letters
            d[wrd[i]] = nd
            d = nd.next
            i += 1
            # Now is the time to optimize the tree structure sitting
            # within the previous self._dicts[i], if any, because it
            # won't be modified after this (or indeed accessed in _addword)
            self._collapse(i, d)
        # We are at the node for the final letter
        if nd:
            nd.final = True
        # Save our position to optimize the handling of the next word
        self._lastword = wrd
        self._lastlen = len(wrd)

    def _dumplevel(self, level, d):
        for ch, nx in d.iteritems():
            print((u' ' * level).encode('cp861')),
            print(ch.encode('cp861')),
            if nx and nx.final:
                print ((u'*').encode('cp861')),
            print
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

