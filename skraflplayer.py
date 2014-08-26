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
from languages import Alphabet


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

    def letter(self):
        """ Return the letter at this square """
        return self._letter

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

    def filter_rack(self, rack):
        """ Return the rack letters that would be allowed here """
        if self._closed:
            return u''
        return u''.join([c for c in rack if self._allowed is None or c in self._allowed])


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
                if self._horizontal:
                    above = board.letters_above(x, y)
                    below = board.letters_below(x, y)
                else:
                    above = board.letters_left(x, y)
                    below = board.letters_right(x, y)
                sq.init_crosscheck(above, below)
                if not sq.is_open():
                    # We found crosschecks that close this square
                    # (i.e. make it impossible to place a tile on it):
                    # mark the board accordingly
                    # !!! BUG: A closed square might re-open when another tile is placed
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

    def coordinate_of(self, index):
        """ Return the co-ordinate on the board of a square within this axis """
        return (self._index, index) if self._horizontal else (index, self._index)

    def coordinate_step(self):
        """ How to move along this axis on the board, (row,col) """
        return (0, 1) if self._horizontal else (1, 0)

    def letter_at(self, index):
        """ Return the letter at the index """
        return self._sq[index].letter()

    def is_open(self, index):
        """ Is the square at the index open (i.e. can a tile be placed there?) """
        return self._sq[index].is_open()

    def is_empty(self, index):
        """ Is the square at the index empty? """
        return self._sq[index].is_empty()

    def filter_rack(self, index, rack):
        """ Return the rack letters that would be allowed at the index """
        return self._sq[index].filter_rack(rack)

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
            #print(u"Anchor {0}: Trying to complete left part '{1}' using rack '{2}'".format(
            #    coord, leftpart, rack))
            nav = ExtendRightNavigator(self, index, leftpart, rack, candidates)
            Manager.word_db().navigate(nav)
            return
        # We have some space to the left of the anchor square
        #print(u"Anchor {0}: Permuting back into {1} empty squares from rack '{2}'".format(
        #    coord, maxleft, rack))
        # Begin by extending an empty prefix to the right, i.e. placing
        # tiles on the anchor square itself and to its right
        nav = ExtendRightNavigator(self, index, u'', rack, candidates)
        Manager.word_db().navigate(nav)
        if maxleft > 0:
            # Follow this by an effort to permute left prefixes into the open space
            nav = LeftPartNavigator(self, index, rack, maxleft, candidates)
            Manager.word_db().navigate(nav)

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
        return self._find_best_move(board, rack, candidates)

    def _find_best_move(self, board, rack, candidates):
        """ Analyze the list of candidate moves and pick the best one """
        if not candidates:
            return None
        def keyfunc(x):
            return -x.score(board)
        # Sort the candidate moves in decreasing order by score
        candidates.sort(key=keyfunc)
        print(u"Rack '{0}' generated {1} candidate moves:".format(rack, len(candidates)))
        for m in candidates:
            print(u"Move {0} score {1}".format(m, m.score(board)))
        # Return the highest-scoring candidate
        return candidates[0]


class LeftPartNavigator:

    """ A navigation class to be used with DawgDictionary.navigate()
        to find all Appel & Jacobson LeftParts, i.e. permutations
        of the rack of length 0..limit that can be placed to the
        left of the anchor square and subsequently extended to the
        right using an ExtendRightNavigator.

        This function is independent of any particular board or
        axis configuration. It is only dependent on the limit,
        i.e. how many squares are available to be filled, and on
        the rack.

        The left part navigations can thus easily be precomputed at
        the start of move generation.

    """

    def __init__(self, axis, anchor, rack, limit, candidates):
        self._rack = rack
        self._stack = []
        self._index = 0
        self._limit = limit
        # We only store the axis and anchor to pass them on to ExtendRightNavigator
        self._axis = axis
        self._anchor = anchor
        self._candidates = candidates

    def push_edge(self, firstchar):
        """ Returns True if the edge should be entered or False if not """
        # Follow all edges that match a letter in the rack
        # (which can be '?', matching all edges)
        if not ((firstchar in self._rack) or (u'?' in self._rack)):
            return False
        # Fit: save our rack and move into the edge
        self._stack.append((self._rack, self._index))
        return True

    def accepting(self):
        """ Returns False if the navigator does not want more characters """
        # Continue as long as there is something left on the rack
        return bool(self._rack) and self._index <= self._limit

    def accepts(self, newchar):
        """ Returns True if the navigator will accept the new character """
        exactmatch = newchar in self._rack
        if (not exactmatch) and (u'?' not in self._rack):
            # Can't continue with this prefix - we no longer have rack letters matching it
            return False
        # We're fine with this: accept the character and remove from the rack
        self._index += 1
        if exactmatch:
            self._rack = self._rack.replace(newchar, u'', 1)
        else:
            self._rack = self._rack.replace(u'?', u'', 1)
        return True

    def accept(self, matched, final):
        """ Called to inform the navigator of a match and whether it is a final word """
        nav = ExtendRightNavigator(self._axis, self._anchor, matched, self._rack, self._candidates)
        Manager.word_db().navigate(nav)

    def pop_edge(self):
        """ Called when leaving an edge that has been navigated """
        self._rack, self._index = self._stack.pop()
        # We need to visit all outgoing edges, so return True
        return True

    def done(self):
        """ Called when the whole navigation is done """
        pass


class Match:

    """ Return codes for the _check() function in ExtendRightNavigator """

    NO = 0
    BOARD_TILE = 1
    RACK_TILE = 2


class ExtendRightNavigator:

    """ A navigation class to be used with DawgDictionary.navigate()
        to perform the Appel & Jacobson ExtendRight function. This
        places rack tiles on and to the right of an anchor square, in
        conformance with the cross-checks and the tiles already on
        the board.
    """

    def __init__(self, axis, anchor, prefix, rack, candidates):
        self._axis = axis
        self._rack = rack
        # The prefix to the left of the anchor
        self._prefix = prefix
        self._lenp = len(prefix)
        # Prefix index
        self._pix = 0
        self._anchor = anchor
        # The tile we are placing next
        self._index = anchor
        self._stack = []
        # The list of candidate moves
        self._candidates = candidates

    def _check(self, ch):
        """ Check whether the letter ch could be placed at the
            current square, given the cross-checks and the rack """
        if not self._axis.is_empty(self._index):
            # There is a tile already in the square: we must match it exactly
            return Match.BOARD_TILE if (ch == self._axis.letter_at(self._index)) else Match.NO
        # Open square: apply cross-check constraints to the rack
        if u'?' in self._rack:
            r = Alphabet.order # All letters possible
        else:
            r = self._rack
        # Filter the rack by the applicable cross checks, and see whether
        # the candidate edge prefix matches that
        return Match.RACK_TILE if (ch in self._axis.filter_rack(self._index, r)) else Match.NO

    def push_edge(self, firstchar):
        """ Returns True if the edge should be entered or False if not """
        # If we are still navigating through the prefix, do a simple compare
        if self._pix < self._lenp:
            return firstchar == self._prefix[self._pix]
        # We are in the right part: check whether we have a potential match
        if self._check(firstchar) == Match.NO:
            return False
        # Match: save our rack and our index and move into the edge
        self._stack.append((self._rack, self._index))
        return True

    def accepting(self):
        """ Returns False if the navigator does not want more characters """
        if self._pix < self._lenp:
            # Still navigating the prefix: continue
            return True
        # Continue as long as there is something left to check
        if self._index >= Board.SIZE:
            # Gone off the board edge
            return False
        # Otherwise, continue while we have something on the rack
        # or we're at an occupied square
        return self._rack or (not self._axis.is_empty(self._index))

    def accepts(self, newchar):
        """ Returns True if the navigator will accept the new character """
        if self._pix < self._lenp:
            # Still going through the prefix
            if self._prefix[self._pix] != newchar:
                assert False
                return False # Should not happen - all prefixes should exist in the graph
            # So far, so good: move on
            self._pix += 1
            return True
        # We are on the anchor square or to its right
        match = self._check(newchar)
        if match == Match.NO:
            # Something doesn't fit anymore, so we're done with this edge
            return False
        # We're fine with this: accept the character and remove from the rack
        self._index += 1
        self._pix += 1
        if match == Match.RACK_TILE:
            # We used a rack tile: remove it from the rack before continuing
            if newchar in self._rack:
                self._rack = self._rack.replace(newchar, u'', 1)
            else:
                # Must be wildcard: remove it
                assert u'?' in self._rack
                self._rack = self._rack.replace(u'?', u'', 1)
        return True

    def accept(self, matched, final):
        """ Called to inform the navigator of a match and whether it is a final word """
        if final and (self._pix > self._lenp) and (self._index >= Board.SIZE or
            self._axis.is_empty(self._index)):

            # print(u"Found solution {0} with {1} tiles to the left of the anchor".format(matched, self._lenp))

            # Make a Move object for this solution and add it to the candidates list
            ix = self._anchor - self._lenp # The word's starting index within the axis
            row, col = self._axis.coordinate_of(ix)
            xd, yd = self._axis.coordinate_step()
            move = Move(matched, row, col)
            for c in matched:
                if self._axis.is_empty(ix):
                    # Empty square that is being covered by this move
                    # !!! Add logic for wildcard tile '?' if used
                    move.add_validated_cover(Cover(row, col, c, c))
                ix += 1
                row += xd
                col += yd
            self._candidates.append(move)

    def pop_edge(self):
        """ Called when leaving an edge that has been navigated """
        if not self._stack:
            # We are still navigating through the prefix: short-circuit
            return False
        self._rack, self._index = self._stack.pop()
        # Once past the prefix, we need to visit all outgoing edges, so return True
        return True

    def done(self):
        """ Called when the whole navigation is done """
        pass



