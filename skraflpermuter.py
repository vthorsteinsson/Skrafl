# -*- coding: utf-8 -*-

""" Scrabble rack permutations

Author: Vilhjalmur Thorsteinsson, 2014

This module implements a main class named Tabulator and
a helper class named WordDatabase.

Tabulator takes a Scrabble rack and processes it to find
all valid word permutations within the rack. It can then
be queried for the number of such permutations, the list
of permutations, the highest "plain" score in the list,
and the list of the permutations having the highest such score.
It also generates valid combinations of the
rack with a single additional letter.

WordDatabase can judge whether a particular word is valid
in (Icelandic) Scrabble. It uses a preprocessed word graph
loaded from text files.

"""

import os
import itertools
import codecs
import logging
import time

import dawgdictionary

# Dictionary of Icelandic scrabble letter scores

_scores = {
    u'a': 1,
    u'á': 4,
    u'b': 6,
    u'd': 4,
    u'ð': 2,
    u'e': 1,
    u'é': 6,
    u'f': 3,
    u'g': 2,
    u'h': 3,
    u'i': 1,
    u'í': 4,
    u'j': 5,
    u'k': 2,
    u'l': 2,
    u'm': 2,
    u'n': 1,
    u'o': 3,
    u'ó': 6,
    u'p': 8,
    u'r': 1,
    u's': 1,
    u't': 1,
    u'u': 1,
    u'ú': 8,
    u'v': 3,
    u'x': 10,
    u'y': 7,
    u'ý': 9,
    u'þ': 4,
    u'æ': 5,
    u'ö': 7
}

# Sort ordering of Icelandic letters
_order = u'aábdðeéfghiíjklmnoóprstuúvxyýþæö'
_upper = u'AÁBDÐEÉFGHIÍJKLMNOÓPRSTUÚVXYÝÞÆÖ'

# Singleton instance of Referee class that manages the list of legal words

class WordDatabase:

    """ Maintains the set of permitted words and judges whether a word is acceptable.
    
    This class loads and maintains a Directed Acyclic Word Graph (DAWG) of valid words.
    The DAWG is used to check racks for validity and to find all valid words embedded
    within a rack.

    The word database is fairly big (several megabytes) so it is important to avoid multiple
    instances of it. The Tabulator implementation below makes sure to use a singleton
    instance of this class, in the class variable _word_db, across all invocations.

    The word graph is loaded from a text file, 'ordalisti.text.dawg', assumed to be in
    the 'resources' folder. The file is generated using DawgBuilder.build() in dawgbuilder.py.

    The graph contains a cleaned-up version of a database originally from bin.arnastofnun.is,
    used under license conditions from "Stofnun Árna Magnússonar í íslenskum fræðum".

    """

    def __init__(self):
        # We maintain the list of permitted words in a DAWG dictionary
        # The DAWG is lazily loaded into memory upon first use
        self._dawg = None

    def _load(self):
        """ Load word lists into memory from static preprocessed text files """
        if self._dawg is not None:
            # Already loaded, nothing to do
            return
        fname = os.path.abspath(os.path.join("resources", "ordalisti.text.dawg"))
        logging.info("Loading graph from file {0}".format(fname))
        t0 = time.time()
        self._dawg = dawgdictionary.DawgDictionary()
        self._dawg.load(fname)
        t1 = time.time()
        logging.info("Loaded {0} graph nodes in {1:.2f} seconds".format(self._dawg.num_nodes(), t1 - t0))

    def initialize(self):
        """ Force preloading of word lists into memory """
        if self._dawg is None:
            self._load()

    def is_valid_word(self, word):
        """ Checks whether a word is found in the list of legal words """
        if not word:
            return False
        if self._dawg is None:
            self._load()
        assert self._dawg is not None
        return self._dawg.find(word)

    def find_permutations(self, rack):
        """ Find all embedded words within a rack """
        if not rack:
            return None
        if self._dawg is None:
            self._load()
        assert self._dawg is not None
        return self._dawg.find_permutations(rack)


class Tabulator:

    """ Processes and tabulates the possibilities within a given rack that is passed to the constructor.

    The rack should normally be 1..7 letters in length.

    """

    _word_db = None

    def __init__(self):
        self._counter = 0
        self._allwords = []
        self._highscore = 0
        self._highwords = []
        self._combinations = { }
        self._rack = u''
        self._rack_is_valid = False # True if the rack is itself a valid word
        if Tabulator._word_db is None:
            # The Referee word graph will be lazily loaded from file upon first use
            Tabulator._word_db = WordDatabase()

    def process(self, rack):
        """ Iterate over all permutations of the rack, i.e. with length from 2 to the rack length """
        # Make sure we reset all state in case we're called multiple times
        self._counter = 0
        self._allwords = []
        self._highscore = 0
        self._highwords = []
        self._combinations = { }
        self._rack = u''
        # Do a sanity check on the input by calculating its raw score, thereby
        # checking whether all the letters are valid
        score = 0
        rack_lower = u'' # Rack converted to lowercase
        try:
            for c in rack:
                ch = c
                if ch in _upper:
                    # Uppercase: find corresponding lowercase letter
                    ch = _order[_upper.index(ch)]
                score += _scores[ch]
                rack_lower += ch
        except KeyError:
            # A letter in the rack is not valid, even after conversion to lower case
            return False
        # The rack contains only valid letters
        self._rack = rack_lower
        # Check combinations with one additional letter
        # !!! TBD !!!: leftover from older code; will be optimized to one graph traversal
        for i in _order:
            # Permute the rack with the additional letter
            p = self._word_db.find_permutations(self._rack + i)
            # Check the permutations to find valid words and their scores
            if p is not None:
                result = [word for word in p if len(word) == len(self._rack) + 1]
                if result:
                    # We found at least one legal word from the combinations with this letter
                    self._add_combination(i, result)
        # Check permutations
        # The shortest possible rack to check for permutations is 2 letters
        if len(self._rack) < 2:
            return True
        p = self._word_db.find_permutations(self._rack)
        if p is not None:
            for word in p:
                self._add_permutation(word, self.score(word))
        # Successful
        return True

    def score(self, word):
        """ Calculate the score for a word """
        if word is None:
            return 0
        try:
            s = reduce(lambda x, y: x + _scores[y], word, 0)
        except KeyError:
            # Word contains an unrecognized letter: return a zero score
            s = 0
        return s

    def _add_permutation(self, word, score):
        """ Add a valid permulation to the tabulation result """
        self._counter += 1
        self._allwords.append(word)
        if score > self._highscore:
            # New high scoring word: note it and start a new list
            self._highscore = score
            self._highwords = [word]
        elif score == self._highscore:
            # Equal score to the previous high scorer: append to the list
            self._highwords.append(word)

    def _add_combination(self, ch, wordlist):
        """ Add to a list of legal combinations that are possible if the letter ch is added to the rack """
        self._combinations[ch] = wordlist

    def rack(self):
        """ Returns the rack that has been tabulated """
        return self._rack

    def count(self):
        """ Returns a count of all valid letter permutations in the rack """
        return self._counter

    def allwords(self):
        """ Returns a list of all the valid letter permulations in the rack """
        return self._allwords
        
    def highscore(self):
        """Returns the highest scoring letter permutation (by plain summation) in the rack"""
        return self._highscore

    def highwords(self):
        """ Returns a list of all letter permutations in the rack having the highest score """
        return self._highwords

    def combinations(self):
        """ Returns a list of the combinations possible with additional letters.
        The list contains (ch, wordlist) tuples where ch is the additional letter
        and wordlist is a list of legal words that can be formed with that letter. """
        lc = list(self._combinations.items())
        if lc:
            # Sort the combinations properly in alphabetical order before returning them
           lc.sort(key = lambda x: _order.index(x[0]))
           return lc
        # No combinations
        return None

    def is_valid_word(self, word):
        """ Checks whether a word is valid """
        return Tabulator._word_db.is_valid_word(word)
