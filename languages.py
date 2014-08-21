# -*- coding: utf-8 -*-

""" Language and alphabet encapsulation module

    Author: Vilhjalmur Thorsteinsson, 2014

    The classes in this module encapsulate particulars of supported
    languages.

    Currently the only supported language is Icelandic.

"""

class Alphabet:

    """ This implementation of the Alphabet class encapsulates particulars of the Icelandic
        language and Scrabble rules. Other languages can be supported by modifying
        or subclassing this class.
    """

    # Dictionary of Scrabble letter scores

    scores = {
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
    order = u'aábdðeéfghiíjklmnoóprstuúvxyýþæö'
    # Upper case version of the order string
    upper = u'AÁBDÐEÉFGHIÍJKLMNOÓPRSTUÚVXYÝÞÆÖ'

    @staticmethod
    def lowercase(ch):
        """ Convert an uppercase character to lowercase """
        return Alphabet.order[Alphabet.upper.index(ch)]

    @staticmethod
    def sortkey(word):
        """ Return a sort key with the proper lexicographic ordering
            for the given word. """
        # This assumes that Alphabet.order is correctly ordered in ascending order.
        return [Alphabet.order.index(ch) for ch in word]

    @staticmethod
    def sort(l):
        """ Sort a list in-place by lexicographic ordering according to this Alphabet """
        l.sort(key = Alphabet.sortkey)

    @staticmethod
    def sorted(l):
        """ Return a list sorted by lexicographic ordering according to this Alphabet """
        return sorted(l, key = Alphabet.sortkey)

    @staticmethod
    def string_subtract(a, b):
        """ Subtract all letters in b from a, counting each instance separately """
        # Note that this cannot be done with sets, as they fold multiple letter instances into one
        lcount = [a.count(c) - b.count(c) for c in Alphabet.order]
        return u''.join([Alphabet.order[ix] * lcount[ix] for ix in range(len(lcount)) if lcount > 0])
