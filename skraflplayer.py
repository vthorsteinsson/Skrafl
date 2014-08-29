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
from skraflmechanics import Manager, Board, Cover, Move, ExchangeMove, PassMove
from languages import Alphabet


class Square:

    """ Represents a single square within an axis.
        A square knows about its cross-checks, i.e. which letters can be
        legally placed in the square while matching correctly with word
        parts above and/or below the square.
    """

    def __init__(self):
        # Cross checks, i.e. possible letters to be placed here,
        # represented as a bit pattern
        self._cc = 0
        # The tile located here, '?' if blank tile
        self._tile = None
        # The letter located here, including meaning of blank tile
        self._letter = None
        # Is this an anchor square?
        self._anchor = False

    def init(self, autoplayer, row, col, crosscheck):
        """ Initialize this square from the board """
        board = autoplayer.board()
        self._tile = board.tile_at(row, col)
        self._letter = board.letter_at(row, col)
        # Cross checks and anchors
        self._cc = crosscheck
        if self.is_open() and board.has_adjacent(row, col):
            # Empty square with adjacent covered squares and nonzero cross-checks:
            # mark as anchor
            self.mark_anchor()

    def is_empty(self):
        """ Is this square empty? """
        return self._letter == u' '

    def is_open(self):
        """ Can a new tile from the rack be placed here? """
        return self.is_empty() and bool(self._cc)

    def is_open_for(self, c):
        """ Can this letter be placed here? """
        return bool(self._cc & (1 << Alphabet.order.index(c)))

    def letter(self):
        """ Return the letter at this square """
        return self._letter

    def mark_anchor(self):
        """ Mark this square as an anchor """
        self._anchor = True

    def is_anchor(self):
        """ Is this an anchor square? """
        return self._anchor


class Axis:

    """ Represents a one-dimensional axis on the board, either
        horizontal or vertical. This is used to find legal moves
        for an AutoPlayer.
    """

    def __init__(self, autoplayer, index, horizontal):

        self._autoplayer = autoplayer
        self._sq = [None] * Board.SIZE
        for i in range(Board.SIZE):
            self._sq[i] = Square()
        self._index = index
        self._horizontal = horizontal
        self._rack = autoplayer.rack()
        # Bit pattern representing empty squares on this axis
        self._empty_bits = 0

    def is_horizontal(self):
        """ Is this a horizontal (row) axis? """
        return self._horizontal

    def is_vertical(self):
        """ Is this a vertical (column) axis? """
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

    def is_open_for(self, index, letter):
        """ Is the square at the index open for this letter? """
        return self._sq[index].is_open_for(letter)

    def is_empty(self, index):
        """ Is the square at the index empty? """
        return bool(self._empty_bits & (1 << index))

    def mark_anchor(self, index):
        """ Force the indicated square to be an anchor. Used in first move
            to mark the center square. """
        self._sq[index].mark_anchor()

    def init_crosschecks(self):
        """ Calculate and return a list of cross-check bit patterns for the indicated axis """

        # The cross-check set is the set of letters that can appear in a square
        # and make cross words (above/left and/or below/right of the square) valid
        board = self._autoplayer.board()
        # Prepare to visit all squares on the axis
        x, y = self.coordinate_of(0)
        xd, yd = self.coordinate_step()
        # Fetch the default cross-check bits, which depend on the rack.
        # If the rack contains a wildcard (blank tile), the default cc set
        # contains all letters in the Alphabet. Otherwise, it contains the
        # letters in the rack.
        all_cc = self._autoplayer.rack_bit_pattern()
        # Go through the open squares and calculate their cross-checks
        for ix in range(Board.SIZE):
            cc = all_cc # Start with the default cross-check set
            if not board.is_covered(x, y):
                if self.is_horizontal():
                    above = board.letters_above(x, y)
                    below = board.letters_below(x, y)
                else:
                    above = board.letters_left(x, y)
                    below = board.letters_right(x, y)
                query = u'' if not above else above
                query += u'?'
                if below:
                    query += below
                if len(query) > 1:
                    # Nontrivial cross-check: Query the word database for words that fit this pattern
                    matches = Manager.word_db().find_matches(query, False) # Don't need a sorted result
                    # print(u"Crosscheck query {0} yielded {1} matches".format(query, len(matches))) # !!! DEBUG
                    bits = 0
                    if matches:
                        cix = 0 if not above else len(above)
                        # Note the set of allowed letters here
                        bits = Alphabet.bit_pattern([wrd[cix] for wrd in matches])
                    # Reduce the cross-check set by intersecting it with the allowed set.
                    # If the cross-check set and the rack have nothing in common, this
                    # will lead to the square being marked as closed, which saves
                    # calculation later on
                    cc &= bits
            # Initialize the square
            self._sq[ix].init(self._autoplayer, x, y, cc)
            # Keep track of empty squares within the axis in a bit pattern for speed
            if self._sq[ix].is_empty():
                self._empty_bits |= (1 << ix)
            x += xd
            y += yd

    def _gen_moves_from_anchor(self, index, maxleft):
        """ Find valid moves emanating (on the left and right) from this anchor """

        if maxleft == 0 and index > 0 and not self.is_empty(index - 1):
            # We have a left part already on the board: try to complete it
            leftpart = u''
            ix = index
            while ix > 0 and not self.is_empty(ix - 1):
                leftpart = self._sq[ix - 1]._letter + leftpart
                ix -= 1
            # Use the ExtendRightNavigator to find valid words with this left part
            nav = ExtendRightNavigator(self, index, leftpart, self._rack, self._autoplayer)
            Manager.word_db().navigate(nav)
            return

        # We are not completing an existing left part
        # Begin by extending an empty prefix to the right, i.e. placing
        # tiles on the anchor square itself and to its right
        nav = ExtendRightNavigator(self, index, u'', self._rack, self._autoplayer)
        Manager.word_db().navigate(nav)

        if maxleft > 0:
            # Follow this by an effort to permute left prefixes into the open space
            # to the left of the anchor square
            nav = LeftPartNavigator(self, index, maxleft, self._rack, self._autoplayer)
            Manager.word_db().navigate(nav)

    def generate_moves(self):
        """ Find all valid moves on this axis by attempting to place tiles
            at and around all anchor squares """
        last_anchor = -1
        lenrack = len(self._rack)
        for i in range(Board.SIZE):
            if self._sq[i].is_anchor():
                # Count the consecutive open, non-anchor squares on the left of the anchor
                opensq = 0
                left = i
                while left > 0 and left > (last_anchor + 1) and self._sq[left - 1].is_open():
                    opensq += 1
                    left -= 1
                # We have a maximum left part length of min(opensq, lenrack-1) as the anchor
                # square itself must always be filled from the rack
                self._gen_moves_from_anchor(i, min(opensq, lenrack - 1))
                last_anchor = i

    
class AutoPlayer:

    """ Implements an automatic, computer-controlled player
    """

    def __init__(self, state):

        # List of valid, candidate moves
        self._candidates = []
        self._state = state
        self._board = state.board()
        # The rack that the autoplayer has to work with
        self._rack = state.player_rack().contents()

        # Calculate a bit pattern representation of the rack
        if u'?' in self._rack:
            # Wildcard in rack: all letters allowed
            self._rack_bit_pattern = Alphabet.all_bits_set()
        else:
            # No wildcard: limits the possibilities of covering squares
            self._rack_bit_pattern = Alphabet.bit_pattern(self._rack)

    def board(self):
        """ Return the board """
        return self._board

    def rack(self):
        """ Return the rack, as a string of tiles """
        return self._rack

    def rack_bit_pattern(self):
        """ Return the bit pattern corresponding to the rack """
        return self._rack_bit_pattern

    def candidates(self):
        """ The list of valid, candidate moves """
        return self._candidates

    def add_candidate(self, move):
        """ Add a candidate move to the AutoPlayer's list """
        self._candidates.append(move)

    def _axis_from_row(self, row):
        """ Create and initialize an Axis from a board row """
        return Axis(self, row, True) # Horizontal

    def _axis_from_column(self, col):
        """ Create and initialize an Axis from a board column """
        return Axis(self, col, False) # Vertical

    def generate_move(self):
        """ Finds and returns a Move object to be played """

        # Generate moves in one-dimensional space by looking at each axis
        # (row or column) on the board separately

        if self._board.is_empty():
            # Special case for first move: only consider the vertical
            # central axis (any move played there can identically be
            # played horizontally), and with only one anchor in the
            # middle square
            axis = self._axis_from_column(Board.SIZE / 2)
            axis.init_crosschecks()
            # Mark the center anchor
            axis.mark_anchor(Board.SIZE / 2)
            axis.generate_moves()
        else:
            # Normal move: go through all 15 (row) + 15 (column) axes and generate
            # valid moves within each of them
            for r in range(Board.SIZE):
                axis = self._axis_from_row(r)
                axis.init_crosschecks()
                axis.generate_moves()
            for c in range(Board.SIZE):
                axis = self._axis_from_column(c)
                axis.init_crosschecks()
                axis.generate_moves()
        # We now have a list of valid candidate moves; pick the best one
        move = self._find_best_move()
        if move is not None:
            return move
        # Can't do anything: try exchanging all tiles
        if self._state.allows_exchange():
            return ExchangeMove(self.rack())
        # If we can't exchange tiles, we have to pass
        return PassMove()

    def _find_best_move(self):
        """ Analyze the list of candidate moves and pick the best one """

        if not self._candidates:
            return None

        def keyfunc(x):
            # Sort moves first by descending score;
            # in case of ties prefer longer words
            return (-x.score(self._board), - x.num_covers())

        def keyfunc_firstmove(x):
            # Special case for first move:
            # Sort moves first by descending score, and in case of ties,
            # try to go to the upper half of the board for a more open game
            return (-x.score(self._board), x._row)

        # Sort the candidate moves using the appropriate key function
        if self._board.is_empty():
            # First move
            self._candidates.sort(key=keyfunc_firstmove)
        else:
            # Subsequent moves
            self._candidates.sort(key=keyfunc)
        print(u"Rack '{0}' generated {1} candidate moves:".format(self._rack, len(self._candidates)))
        # Show top 20 candidates
        for m in self._candidates[0:20]:
            print(u"Move {0} score {1}".format(m, m.score(self._board)))
        # Return the highest-scoring candidate
        return self._candidates[0]


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

        The left part navigations can thus potentially be precomputed at
        the start of move generation.

    """

    def __init__(self, axis, anchor, limit, rack, autoplayer):
        self._rack = rack
        self._stack = []
        self._index = 0
        self._limit = limit
        # We only store the axis, anchor and autoplayer to pass them on to ExtendRightNavigator
        self._axis = axis
        self._anchor = anchor
        # The autoplayer that invoked the navigator
        self._autoplayer = autoplayer

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
        return bool(self._rack) and self._index < self._limit

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
        nav = ExtendRightNavigator(self._axis, self._anchor, matched, self._rack, self._autoplayer)
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

    def __init__(self, axis, anchor, prefix, rack, autoplayer):
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
        # The autoplayer that invokes the navigator
        self._autoplayer = autoplayer
        # Cache the initial check we do when pushing into an edge
        self._last_check = None

    def _check(self, ch):
        """ Check whether the letter ch could be placed at the
            current square, given the cross-checks and the rack """
        if not self._axis.is_empty(self._index):
            # There is a tile already in the square: we must match it exactly
            return Match.BOARD_TILE if (ch == self._axis.letter_at(self._index)) else Match.NO
        # Open square: apply cross-check constraints to the rack
        # Would this character pass the cross-checks?
        if not self._axis.is_open_for(self._index, ch):
            return Match.NO
        if u'?' in self._rack:
            # We could always use the wildcard in the rack to cover this, so OK
            return Match.RACK_TILE
        # Filter the rack by the applicable cross checks, and see whether
        # the candidate edge prefix matches that
        return Match.RACK_TILE if ch in self._rack else Match.NO

    def push_edge(self, firstchar):
        """ Returns True if the edge should be entered or False if not """
        # If we are still navigating through the prefix, do a simple compare
        if self._pix < self._lenp:
            return firstchar == self._prefix[self._pix]
        # We are in the right part: check whether we have a potential match
        self._last_check = self._check(firstchar)
        if self._last_check == Match.NO:
            return False
        # Match: save our rack and our index and move into the edge
        self._stack.append((self._rack, self._index, self._pix))
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
                print(u"Prefix is '{0}' but newchar is '{1}'".format(self._prefix[self._pix], newchar))
                assert False
                return False # Should not happen - all prefixes should exist in the graph
            # So far, so good: move on
            self._pix += 1
            return True
        # We are on the anchor square or to its right
        # Use the cached check from push_edge if we have one
        match = self._check(newchar) if self._last_check is None else self._last_check
        self._last_check = None
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
        if final and (self._pix > self._lenp) and len(matched) > 1 and (self._index >= Board.SIZE or
            self._axis.is_empty(self._index)):

            # print(u"Found solution {0} with {1} tiles to the left of the anchor".format(matched, self._lenp))

            # Solution found - make a Move object for it and add it to the AutoPlayer's list
            ix = self._anchor - self._lenp # The word's starting index within the axis
            row, col = self._axis.coordinate_of(ix)
            xd, yd = self._axis.coordinate_step()
            move = Move(matched, row, col, self._axis.is_horizontal())
            # Fetch the rack as it was at the beginning of move generation
            rack = self._autoplayer.rack()
            for c in matched:
                if self._axis.is_empty(ix):
                    # Empty square that is being covered by this move
                    # Find out whether it is a blank or normal letter tile
                    if c in rack:
                        rack = rack.replace(c, u'', 1)
                        tile = c
                    else:
                        # Must be a wildcard match
                        rack = rack.replace(u'?', u'', 1)
                        tile = u'?'
                    assert row in range(Board.SIZE)
                    assert col in range(Board.SIZE)
                    # Add this cover to the Move object
                    move.add_validated_cover(Cover(row, col, tile, c))
                ix += 1
                row += xd
                col += yd
            # Check that we've picked off the correct number of tiles
            assert len(rack) == len(self._rack)
            self._autoplayer.add_candidate(move)

    def pop_edge(self):
        """ Called when leaving an edge that has been navigated """
        if not self._stack:
            # We are still navigating through the prefix: short-circuit
            return False
        self._rack, self._index, self._pix = self._stack.pop()
        # Once past the prefix, we need to visit all outgoing edges, so return True
        return True

    def done(self):
        """ Called when the whole navigation is done """
        pass



