# -*- coding: utf-8 -*-

""" Skraflplayer

    Author: Vilhjalmur Thorsteinsson, 2014

    This experimental module finds and ranks legal moves on
    a Scrabble(tm)-like board.

    The algorithm is based on the classic paper by Appel & Jacobson,
    "The World's Fastest Scrabble Program",
    http://www.cs.cmu.edu/afs/cs/academic/class/15451-s06/www/lectures/scrabble.pdf

"""

from dawgdictionary import DawgDictionary
from skraflmechanics import Manager, Board, Cover, Move


class Square:

    """ Represents a single square within an axis. This includes
        the cross-checks, i.e. word parts above/left and below/right
        of the square.
    """

    def __init__(self):
        # Cross checks
        self._above = None
        self._below = None
        # The tile located here, '?' if blank tile
        self._tile = None
        # The letter located here, including meaning of blank tile
        self._letter = None
        # Set of letters that can be here
        self._allowed = None
        # Is this an anchor square?
        self._anchor = False
        # Can a new tile be placed here?
        self._closed = False

    def init(self, board, row, col):
        """ Initialize this square from the board """
        self._tile = board.tile_at(row, col)
        self._letter = board.letter_at(row, col)
        self._closed = board.is_closed(row, col)

    def is_empty(self):
        return self._letter == u' '

    def is_open(self):
        """ Can a new tile be placed here? """
        return self.is_empty() and not self._closed

    def mark_anchor(self):
        """ Mark this square as an anchor """
        self._anchor = True

    def set_above(self, wordpart):
        """ Cross-check word or partial word above this square """
        self._above = wordpart
        if wordpart:
            self._anchor = True

    def set_below(self, wordpart):
        """ Cross-check word or partial word below this square """
        self._below = wordpart
        if wordpart:
            self._anchor = True

    def init_crosscheck(self, above, below):
        """ Initialize cross-check information for this square """
        if above:
            self.set_above(above)
        if below:
            self.set_below(below)
        if above or below:
            # We have a cross-check here, i.e. a connection
            # with words or word parts above and/or below:
            # Check what that implies for this square
            query = u'' if not above else above
            query += u'?'
            if below:
                query += below
            # Query the word database for words that fit this pattern
            matches = Manager.word_db().find_matches(query)
            # print(u"Crosscheck query {0} yielded {1} matches".format(query, len(matches))) # !!! DEBUG
            if not matches:
                # No tile fits this square; it must remain empty
                self._closed = True
                self._anchor = False
            else:
                ix = 0 if not above else len(above)
                # Note the set of allowed letters here
                self._allowed = set([wrd[ix] for wrd in matches])


class Axis:

    """ Represents a one-dimensional axis on the board, either
        horizontal or vertical. This is used to find legal moves
        for an AutoPlayer.
    """

    def __init__(self, index, horizontal):
        self._sq = [None] * Board.SIZE
        for i in range(Board.SIZE):
            self._sq[i] = Square()
        self._index = index
        self._horizontal = horizontal

    def _init(self, board, x, y, xd, yd):
        """ Initialize axis data from the board """
        for ix in range(Board.SIZE):
            sq = self._sq[ix]
            sq.init(board, x, y)
            if sq.is_open():
                # For open squares, initialize the cross-checks
                above = board.letters_above(x, y)
                below = board.letters_below(x, y)
                sq.init_crosscheck(above, below)
                if not sq.is_open():
                    # We found crosschecks that close this square
                    # (i.e. make it impossible to place a tile on it):
                    # mark the board accordingly
                    board.mark_closed(x, y)
            x += xd
            y += yd
        for ix in range(Board.SIZE):
            # Make sure that open squares around occupied tiles
            # are marked as anchors
            if not self._sq[ix].is_empty():
                if ix > 0 and self._sq[ix - 1].is_open():
                    self._sq[ix - 1].mark_anchor()
                if ix < Board.SIZE - 1 and self._sq[ix + 1].is_open():
                    # print(u"Marking {0} as anchor".format(Board.short_coordinate(True, x + xd, y + yd)))
                    self._sq[ix + 1].mark_anchor()

    def is_horizontal(self):
        return self._horizontal

    def is_vertical(self):
        return not self._horizontal

    def _add_moves_from_anchor(self, index, maxleft, rack, candidates):
        """ Find valid moves emanating (on the left and right) from this anchor """
        if self._horizontal:
            coord = Board.short_coordinate(True, self._index, index)
        else:
            coord = Board.short_coordinate(False, index, self._index)
        if index > 0 and not self._sq[index - 1].is_empty():
            # We have a left part already on the board: try to complete it
            leftpart = u''
            ix = index
            while ix > 0 and not self._sq[ix - 1].is_empty():
                leftpart = self._sq[ix - 1]._letter + leftpart
                ix -= 1
            print(u"Anchor {0}: Trying to complete left part '{1}' using rack '{2}'".format(
                coord, leftpart, rack))
            return
        # We have open space to the left of the anchor square:
        # permute the rack into it
        print(u"Anchor {0}: Permuting back into {1} empty squares from rack '{2}'".format(
            coord, maxleft, rack))
        pass

    def add_valid_moves(self, rack, candidates):
        """ Find all valid moves on this axis, given a rack,
            and add them to the candidates list """
        last_open = -1
        for i in range(Board.SIZE):
            if self._sq[i]._anchor:
                self._add_moves_from_anchor(i, min(i - last_open - 1, len(rack) - 1), rack, candidates)
                last_open = i
            elif not self._sq[i].is_open():
                last_open = i

    @staticmethod
    def from_row(board, row):
        """ Creates an Axis from a board row.
            Loads letters and tiles and initializes the cross-checks. """
        axis = Axis(row, True) # Horizontal
        axis._init(board, row, 0, 0, 1)
        return axis

    @staticmethod
    def from_column(board, col):
        """ Creates an Axis from a board column.
            Loads letters and tiles and initializes the cross-checks. """
        axis = Axis(col, False) # Vertical
        axis._init(board, 0, col, 1, 0)
        return axis


class AutoPlayer:

    """ Implements an automatic, computer-controlled player
    """

    def __init__(self):
        pass

    def find_move(self, state):
        """ Finds and returns a Move object to be played """
        candidates = []
        board = state.board()
        rack = state.player_rack().contents()
        # Analyze rows for legal moves
        for r in range(Board.SIZE):
            Axis.from_row(board, r).add_valid_moves(rack, candidates)
        # Analyze columns for legal moves
        for c in range(Board.SIZE):
            Axis.from_column(board, c).add_valid_moves(rack, candidates)
        # Look at the candidates and pick the best one
        return self._find_best_move(board, candidates)

    def _find_best_move(self, board, candidates):
        """ Analyze the list of candidate moves and pick the best one """
        if not candidates:
            return None
        # Sort the candidate moves in decreasing order by score
        candidates.sort(lambda x: - x.score(board))
        # Return the highest-scoring candidate
        return candidates[0]


class MoveGenerator:

    """ A navigation class to be used with DawgDictionary.navigate()
        to find the possible moves emanating from an anchor square
    """

    def __init__(self, rack, axis, anchor, leftlimit):
        self._rack = rack
        self._axis = axis
        self._anchor = anchor
        self._index = anchor # Moves as we go right from the anchor
        self._left = 0 # How many tiles are currently to the left of the anchor?
        self._leftlimit = leftlimit # Max number of tiles to the left of the anchor
        self._stack = []
        self._result = []

    def push_edge(self, firstchar):
        """ Returns True if the edge should be entered or False if not """
        # Follow all edges that match a letter in the rack
        # (which can be '?', matching all edges)
        if not ((firstchar in self._rack) or (u'?' in self._rack)):
            return False
        # Fit: save our rack and move into the edge
        self._stack.append(self._rack)
        return True

    def accepting(self):
        """ Returns False if the navigator does not want more characters """
        # Continue as long as there is something left on the rack
        return bool(self._rack)

    def accepts(self, newchar):
        """ Returns True if the navigator will accept the new character """
        exactmatch = newchar in self._rack
        if (not exactmatch) and (u'?' not in self._rack):
            # Can't continue with this prefix - we no longer have rack letters matching it
            return False
        if self._left < self._leftlimit:
            # Still in the left part: no further constraints to check
            self._left += 1
        else:
            # Do the cross-check with the anchor square
            # and then venture into the right part
            pass
        # We're fine with this: accept the character and remove from the rack
        if exactmatch:
            self._rack = self._rack.replace(newchar, u'', 1)
        else:
            self._rack = self._rack.replace(u'?', u'', 1)
        return True

    def accept(self, matched, final):
        """ Called to inform the navigator of a match and whether it is a final word """
        if final and len(matched) >= self._minlen:
            self._result.append(matched)

    def pop_edge(self):
        """ Called when leaving an edge that has been navigated """
        self._rack = self._stack.pop()
        # We need to visit all outgoing edges, so return True
        return True

    def done(self):
        """ Called when the whole navigation is done """
        pass

    def result(self):
        return None



