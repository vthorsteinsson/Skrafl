# -*- coding: utf-8 -*-

""" Scrabble rack permutations

Copyright (C) 2014 by Vilhjalmur Thorsteinsson

This module implements a main class named Tabulator and
a helper class named Referee.

Tabulator takes a Scrabble rack and processes it to find
all valid word permutations within the rack. It can then
be queried for the number of such permutations, the list
of permutations, the highest "plain" score in the list,
and the list of the permutations having the highest such score.

Referee can judge whether a particular word is valid
in (Icelandic) Scrabble. It uses a word database loaded
from text files.

"""

import os
import itertools
import codecs
import logging

# Dictionary of Icelandic scrabble letter scores

_scores = {
    u'a': 1,
    u'b': 6,
    u'd': 4,
    u'e': 1,
    u'f': 3,
    u'g': 2,
    u'h': 3,
    u'i': 1,
    u'j': 5,
    u'k': 2,
    u'l': 2,
    u'm': 2,
    u'n': 1,
    u'o': 3,
    u'p': 8,
    u'r': 1,
    u's': 1,
    u't': 1,
    u'u': 1,
    u'v': 3,
    u'x': 10,
    u'y': 7,
    u'þ': 4,
    u'æ': 5,
    u'ö': 7,
    u'ð': 2,
    u'á': 4,
    u'é': 6,
    u'í': 4,
    u'ó': 6,
    u'ú': 8,
    u'ý': 9
}

# Singleton instance of Referee class that manages the list of legal words

_referee = None


class Referee:

    """ Maintains the set of permitted words and judges whether a word is acceptable
    
    This class loads and maintains the list of valid words, and is used to judge
    whether a given word is valid.

    The list is fairly big (several megabytes) so it is important to avoid multiple
    instances of it. The Tabulator implementation below makes sure to use a singleton
    instance of this class, in the variable _referee, across all invocations.

    The word list is loaded from text files assumed to sit in the resources
    folder. These files are presently ordalisti.txt and smaordalisti.txt,
    a list of longer (/declined) and shorter (/undeclined) words, respectively.
    
    Note that for optimization purposes, only words from 2..8 letters in length
    are loaded into memory. The class will thus not recognize valid words longer than
    8 letters, nor single-letter words. This restriction is fine for Scrabble.

    """

    def __init__(self):
        # We maintain the list of permitted words in a (pretty big!) set
        self._permitted = set()
        # The set is lazily loaded into memory upon first use
        self._loaded = False

    def _load_file(self, fname):
        """Load a word list file, assumed to contain one word per line"""
#        with open(fname, mode='r', encoding='iso8859-1') as fin:
        with codecs.open(fname, mode='r', encoding='utf-8') as fin:
            for line in fin:
                if line.endswith(u'\n'):
                    # Cut off trailing newline
                    line = line[0:-1]
                if line and len(line) < 9: # No need to load longer words than 8 letters (rack + 1 letter combinations)
                    self._permitted.add(line)

    def _load(self):
        """ Load word lists into memory from static preprocessed text files """
        if self._loaded:
            # Already loaded, nothing to do
            return
        logging.info("Loading word list 1")
        self._load_file(os.path.abspath('resources\\ordalisti.txt'))
        logging.info("Loading word list 2")
        self._load_file(os.path.abspath('resources\\smaordalisti.txt'))
        logging.info("Total number of words in permitted set is " + str(len(self._permitted)))
        self._loaded = True

    def is_valid_word(self, word):
        """ Checks whether a word is found in the list of legal words """
        if not word:
            return False;
        if not self._loaded:
            self._load()
        return word in self._permitted

        
class Tabulator:

    """ Processes and tabulates the possibilities within a given rack that is passed to the constructor.

    The rack should normally be 1..7 letters in length.

    """

    def __init__(self):
        self._counter = 0
        self._allwords = []
        self._highscore = 0
        self._highwords = []
        self._combinations = { }
        self._rack = u''
        self._rack_is_valid = False # True if the rack is itself a valid word

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
        try:
            for c in rack:
                score += _scores[c]
        except KeyError:
            return False
        # The rack contains only valid letters
        self._rack = rack
        # Check combinations with one additional letter
        for i in _scores:
            # Permute the rack with the additional letter
            resultset = set(itertools.permutations(rack + i))
            # Check the permutations to find valid words and their scores
            comblist = []
            for p in resultset:
                word, score = self._check_permutation(p)
                if score > 0:
                    # Found a legal combination
                    comblist.append(word)
            if len(comblist) > 0:
                # We found at least one legal word from the combinations with this letter
                self._add_combination(i, comblist)
        # Check permutations
        # The shortest possible rack to check for permutations is 2 letters
        if len(rack) < 2:
            return True
        for i in range(1, len(rack)):
            # Calculate the permutations of length i+1 and fold them into a set,
            # causing duplicates to be dropped
            resultset = set(itertools.permutations(rack, i + 1))
            for r in resultset:
                word, score = self._check_permutation(r)
                if score > 0:
                    self._add_permutation(word, score)
        # Successful
        return True

    def _check_permutation(self, p):
        """ Check a single candidate permutation for validity, and, if valid, add it to the tabulated results """
        word = u''
        score = 0
        # The permutation p comes in as a set of characters. Assemble a word and calculate its score
        for c in p:
            word += c
            score += _scores[c]
        if not self.is_valid_word(word):
            # Not a valid word: we're done
            return (word, 0)
        # Valid word: return its score
        return (word, score)

    def _add_permutation(self, word, score):
        # The word is found in the word list and is thus valid
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
        # Add a list of legal combinations that are possible if the letter ch is added to the rack
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
        """ Returns a dict of the combinations possible with additional letters.
        The dict contains {ch: wordlist} tuples where ch is the additional letter
        and wordlist is a list of legal words that can be formed with that letter. """
        return self._combinations
      
    def is_valid_word(self, word):
        """ Checks whether a particular word is present on the list of valid words """
        global _referee
        # We use only one instance of Referee (singleton) for multiple instances of Tabulator
        if _referee is None:
            _referee = Referee()
        return _referee.is_valid_word(word)

