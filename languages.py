# -*- coding: utf-8 -*-

""" The classes in this module encapsulate particulars of supported
    languages.

    Currently the only supported language is Icelandic.

"""

class Icelandic:

    """ Class Icelandic encapsulates particulars of the Icelandic language
        and Scrabble rules. Add similar data and functions for
        other languages.
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
        return Icelandic.order[Icelandic.upper.index(ch)]

    @staticmethod
    def sortkey(word):
        return [Icelandic.order.index(ch) for ch in word]

    @staticmethod
    def sort(l):
        l.sort(key = Icelandic.sortkey)

    @staticmethod
    def sorted(l):
        return sorted(l, key = Icelandic.sortkey)

