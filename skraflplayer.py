# -*- coding: utf-8 -*-

""" Skraflplayer

Author: Vilhjalmur Thorsteinsson, 2014

This experimental module finds and ranks legal moves on
a Scrabble(tm)-like board.

"""

from languages import Alphabet

BOARDSIZE = 15


class Skraflboard:

    _wordscore = [
        "311111131111113",
        "121111111111121",
        "112111111111211",
        "111211111112111",
        "111121111121111",
        "111111111111111",
        "111111111111111",
        "311111121111113",
        "111111111111111",
        "111111111111111",
        "111121111121111",
        "111211111112111",
        "112111111111211",
        "121111111111121",
        "311111131111113"]
    _letterscore = [
        "111211111112111",
        "111113111311111",
        "111111212111111",
        "211111121111112",
        "111111111111111",
        "131111111111131",
        "112111111111211",
        "111211111112111",
        "112111111111211",
        "131111111111131",
        "111111111111111",
        "211111121111112",
        "111111212111111",
        "111113111311111",
        "111211111112111"]

    def __init__(self):
        self._letters = [u' ' * BOARDSIZE for _ in range(BOARDSIZE)]
        self._tiles = [u' ' * BOARDSIZE for _ in range(BOARDSIZE)]

    def letter_at(self, row, col):
        """ Return the letter at the specified co-ordinate """
        return self._letters[row][col]

    def tile_at(self, row, col):
        """ Return the tile at the specified co-ordinate (may be '?' for blank tile) """
        return self._tiles[row][col]

    @staticmethod
    def wordscore(row, col):
        return int(Skraflboard._wordscore[row][column])

    @staticmethod
    def letterscore(row, col):
        return int(Skraflboard._letterscore[row][column])


class Skraflsquare:

    def __init__(self):
        # Cross checks
        self._above = None
        self._below = None
        # The tile located here, '?' if blank tile
        self._tile = None
        # The letter located here, including meaning of blank tile
        self._letter = None
        # Set of letters that can legally be here
        self._legal = None
        # Is this an anchor square?
        self._anchor = False

    def load(self, board, row, col):
        """ Initialize this square from the board """
        self._tile = board.tile_at(row, col)
        self._letter = board.letter_at(row, col)


class Skraflaxis:

    """ Represents an one-dimensional axis on the board, either
        horizontal or vertical.
    """

    def __init__(self):
        self._axis = [Skraflsquare()] * BOARDSIZE

    @staticmethod
    def from_row(board, row):
        axis = Skraflaxis()
        for ix in range(BOARDSIZE):
            axis._axis[ix].load(board, row, ix)
        return axis

    @staticmethod
    def from_column(board, col):
        axis = Skraflaxis()
        for ix in range(BOARDSIZE):
            axis._axis[ix].load(board, ix, col)
        return axis

class Skraflstate:

    def __init__(self):
        self._board = None

    def load_board(self, board):
        """ Load a Skraflboard into this state """
        self._board = board

    def is_play_valid(self, play):
        """ Is the play valid in this state? """
        return True

    def apply_play(self, play):
        """ Apply the given Skraflplay to this state """
        pass

class Skraflplay:

    def __init__(self, start, word):
        self._start = start
        self._word = word

