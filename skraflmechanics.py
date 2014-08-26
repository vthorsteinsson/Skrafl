# -*- coding: utf-8 -*-

""" Skraflmechanics

    Author: Vilhjalmur Thorsteinsson, 2014

    This module contains classes that implement various
    mechanics for a Scrabble(tm)-like game, including the
    board itself, the players, their racks, moves,
    scoring, etc.

    Algorithms for automatic (computer) play are found
    in skraflplayer.py

"""

from random import randint
from languages import Alphabet
from skraflpermuter import WordDatabase


class Manager:

    # A singleton instance of the WordDatabase class, used by
    # all Manager instances throughout a server session
    _word_db = None

    def __init__(self):
        if Manager._word_db is None:
            # The word database will be lazily loaded from file upon first use
            Manager._word_db = WordDatabase()

    @staticmethod
    def word_db():
        if Manager._word_db is None:
            # The word database will be lazily loaded from file upon first use
            Manager._word_db = WordDatabase()
        return Manager._word_db


class Board:

    """ Represents the characteristics and the contents of a Scrabble board.
    """

    # A standard Scrabble board is 15 x 15 squares
    SIZE = 15

    # The rows are identified by letter
    ROWIDS = u"ABCDEFGHIJKLMNO"

    # Board squares with word scores (1=normal/single, 2=double, 3=triple word score)
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

    # Board squares with letter scores (1=normal/single, 2=double, 3=triple letter score)
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

    @staticmethod
    def short_coordinate(horiz, row, col):
        if horiz:
            # Row letter first, then column number (1-based)
            return Board.ROWIDS[row] + str(col + 1)
        else:
            # Column number first (1-based), then row letter
            return str(col + 1) + Board.ROWIDS[row]

    def __init__(self):
        # Store letters on the board in list of strings
        self._letters = [u' ' * Board.SIZE for _ in range(Board.SIZE)]
        # Store tiles on the board in list of strings
        self._tiles = [u' ' * Board.SIZE for _ in range(Board.SIZE)]
        # Keep track of which squares are closed (i.e. no tile can be
        # placed there because of cross-check limitations)
        self._open = [u' ' * Board.SIZE for _ in range(Board.SIZE)]
        # The two counts below should always stay in sync
        self._numletters = 0
        self._numtiles = 0

    def is_empty(self):
        """ Is the board empty, i.e. contains no tiles? """
        # One of those checks should actually be enough
        return self._numletters == 0 and self._numtiles == 0

    def is_covered(self, row, col):
        """ Is the specified square already covered (taken)? """
        return self.letter_at(row, col) != u' '

    def is_closed(self, row, col):
        """ Is the specified square unable to receive a tile? """
        return self._open[row][col] != u' '

    def mark_closed(self, row, col):
        """ Mark the specified square as unable to receive a tile """
        self._open[row] = self._open[row][0:col] + u'*' + self._open[row][col + 1:]

    def has_adjacent(self, row, col):
        """ Check whether there are any tiles on the board adjacent to this square """
        if row > 0 and self.is_covered(row - 1, col):
            return True
        if row < Board.SIZE - 1 and self.is_covered(row + 1, col):
            return True
        if col > 0 and self.is_covered(row, col - 1):
            return True
        if col < Board.SIZE - 1 and self.is_covered(row, col + 1):
            return True
        return False

    def letter_at(self, row, col):
        """ Return the letter at the specified co-ordinate """
        return self._letters[row][col]

    def tile_at(self, row, col):
        """ Return the tile at the specified co-ordinate (may be '?' for blank tile) """
        return self._tiles[row][col]

    def set_letter(self, row, col, letter):
        """ Set the letter at the specified co-ordinate """
        assert letter is not None
        assert len(letter) == 1
        prev = self.letter_at(row, col)
        if prev == letter:
            # Unchanged square: we're done
            return
        if prev == u' ' and letter != u' ':
            # Putting a letter into a previously empty square
            self._numletters += 1
        self._letters[row] = self._letters[row][0:col] + letter + self._letters[row][col + 1:]

    def set_tile(self, row, col, tile):
        """ Set the tile at the specified co-ordinate """
        assert tile is not None
        assert len(tile) == 1
        prev = self.tile_at(row, col)
        if prev == tile:
            # Unchanged square: we're done
            return
        if prev == u' ' and tile != u' ':
            # Putting a tile into a previously empty square
            self._numtiles += 1
        self._tiles[row] = self._tiles[row][0:col] + tile + self._tiles[row][col + 1:]

    def adjacent(self, row, col, xd, yd, getter):
        """ Return the letters or tiles adjacent to the given square, in the direction (xd, yd) """
        result = u''
        row += xd
        col += yd
        while row in range(Board.SIZE) and col in range(Board.SIZE):
            ltr = getter(row, col)
            if ltr == u' ':
                # Empty square: we're done
                break
            if xd + yd < 0:
                # Going up or to the left: add to the beginning
                result = ltr + result
            else:
                # Going down or to the right: add to the end
                result += ltr
            row += xd
            col += yd
        return result

    def letters_above(self, row, col):
        """ Return the letters immediately above the given square, if any """
        return self.adjacent(row, col, -1, 0, self.letter_at)

    def letters_below(self, row, col):
        """ Return the letters immediately below the given square, if any """
        return self.adjacent(row, col, 1, 0, self.letter_at)

    def letters_left(self, row, col):
        """ Return the letters immediately to the left of the given square, if any """
        return self.adjacent(row, col, 0, -1, self.letter_at)

    def letters_right(self, row, col):
        """ Return the letters immediately to the right of the given square, if any """
        return self.adjacent(row, col, 0, 1, self.letter_at)

    def tiles_above(self, row, col):
        """ Return the tiles immediately above the given square, if any """
        return self.adjacent(row, col, -1, 0, self.tile_at)

    def tiles_below(self, row, col):
        """ Return the tiles immediately below the given square, if any """
        return self.adjacent(row, col, 1, 0, self.tile_at)

    def tiles_left(self, row, col):
        """ Return the tiles immediately to the left of the given square, if any """
        return self.adjacent(row, col, 0, -1, self.tile_at)

    def tiles_right(self, row, col):
        """ Return the tiles immediately to the right of the given square, if any """
        return self.adjacent(row, col, 0, 1, self.tile_at)

    def __str__(self):
        """ Simple text dump of the contents of the board """
        l = []
        for row in self._letters:
            l.append(u' '.join([u'.' if c == u' ' else c for c in row]))
        return u'\n'.join(l)

    @staticmethod
    def wordscore(row, col):
        """ Returns the word score factor of the indicated square, 1, 2 or 3 """
        return int(Board._wordscore[row][col])

    @staticmethod
    def letterscore(row, col):
        """ Returns the letter score factor of the indicated square, 1, 2 or 3 """
        return int(Board._letterscore[row][col])

        
class Bag:

    """ Represents a bag of tiles """

    def __init__(self):
        # Get a full bag from the Alphabet; this varies between languages
        self._tiles = Alphabet.full_bag()

    def draw_tile(self):
        """ Draw a single tile from the bag """
        if self.is_empty():
            return None
        tile = self._tiles[randint(0, len(self._tiles) - 1)]
        self._tiles = self._tiles.replace(tile, u'', 1)
        return tile

    def return_tiles(self, tiles):
        """ Return one or more tiles to the bag """
        self._tiles += tiles

    def contents(self):
        """ Return the contents of the bag """
        return self._tiles

    def is_empty(self):
        """ Returns True if the bag is empty, i.e. all tiles have been drawn """
        return not self._tiles


class Rack:

    """ Represents a player's rack of tiles """

    MAX_TILES = 7

    def __init__(self):
        self._rack = u''

    def remove_tile(self, tile):
        """ Remove a tile from the rack """
        self._rack = self._rack.replace(tile, u'', 1)

    def replenish(self, bag):
        """ Draw tiles from the bag until we have 7 tiles or the bag is empty """
        while len(self._rack) < Rack.MAX_TILES and not bag.is_empty():
            self._rack += bag.draw_tile()

    def contents(self):
        """ Return the contents of the rack """
        return self._rack

    def contains(self, tiles):
        # Check whether the rack contains all tiles in the tiles string
        # (Quick and dirty, not time-critical)
        temp = self._rack
        for c in tiles:
            temp = temp.replace(c, u'', 1)
        return len(self._rack) - len(temp) == len(tiles)


class State:

    """ Represents the state of a game at a particular point.
        Contains the current board, the racks, scores, etc.
    """

    def __init__(self):
        self._board = Board()
        self._player_to_move = 0
        self._scores = [0, 0]
        self._racks = [Rack(), Rack()]
        # Initialize a fresh, full bag of tiles
        self._bag = Bag()
        # Draw the racks from the bag
        for rack in self._racks:
            rack.replenish(self._bag)

    def load_board(self, board):
        """ Load a Board into this state """
        self._board = board

    def check_legality(self, move):
        """ Is the move legal in this state? """
        if move is None:
            return Move.NULL_MOVE
        return move.check_legality(self._board, self.player_rack())

    def apply_move(self, move):
        """ Apply the given move to this state """
        # Update the player's score
        self._scores[self._player_to_move] += self.score(move)
        # Update the board and the rack
        rack = self.player_rack()
        move.apply(self._board, rack)
        # Draw new tiles
        rack.replenish(self._bag)
        # It's the other player's move
        self._player_to_move = 1 - self._player_to_move

    def score(self, move):
        """ Calculate the score of the move """
        return move.score(self._board)

    def player_rack(self):
        """ Return the Rack object for the player whose turn it is """
        return self._racks[self._player_to_move]

    def board(self):
        """ Return the Board object of this state """
        return self._board

    def __str__(self):
        return self._board.__str__() + u"\n{0} vs {1}".format(self._scores[0], self._scores[1])


class Cover:

    """ Represents a covering of a square by a tile """

    def __init__(self, row, col, tile, letter):
        self.row = row
        self.col = col
        self.tile = tile
        self.letter = letter


class Move:

    """ Represents a move by a player """

    # Error return codes from Move.check_legality()
    LEGAL = 0
    NULL_MOVE = 1
    FIRST_MOVE_NOT_IN_CENTER = 2
    DISJOINT = 3
    NOT_ADJACENT = 4
    SQUARE_ALREADY_OCCUPIED = 5
    HAS_GAP = 6
    WORD_NOT_IN_DICTIONARY = 7
    CROSS_WORD_NOT_IN_DICTIONARY = 8
    TOO_MANY_TILES_PLAYED = 9
    TILE_NOT_IN_RACK = 10

    # Bonus score for playing all 7 tiles in one move
    BINGO_BONUS = 50

    @staticmethod
    def errortext(errcode):
        return [u"LEGAL", 
            u"NULL_MOVE", 
            u"FIRST_MOVE_NOT_IN_CENTER", 
            u"DISJOINT", 
            u"NOT_ADJACENT", 
            u"SQUARE_ALREADY_OCCUPIED", 
            u"HAS_GAP",
            u"WORD_NOT_IN_DICTIONARY",
            u"CROSS_WORD_NOT_IN_DICTIONARY",
            u"TOO_MANY_TILES_PLAYED",
            u"TILE_NOT_IN_RACK"][errcode]

    def __init__(self, word, row, col):
        # A list of squares covered by the play, i.e. actual tiles
        # laid down on the board
        self._covers = []
        # Number of letters in word formed (this may be >= len(self._covers))
        self._numletters = 0 if word is None else len(word)
        # The word formed
        self._word = word
        # Starting row and column of word formed
        self._row = row
        self._col = col
        # Is the word horizontal or vertical?
        self._horizontal = True

    def short_coordinate(self):
        """ Return the coordinate of the move in 'Scrabble notation',
            i.e. row letter + column number for horizontal moves or
            column number + row letter for vertical ones """
        return Board.short_coordinate(self._horizontal, self._row, self._col)

    def __str__(self):
        """ Return the standard move notation of a coordinate followed by the word formed """
        return self.short_coordinate() + u":'" + self._word + u"'"

    def add_cover(self, row, col, tile, letter):
        """ Add a placement of a tile on a board square to this move """
        # Sanity check the input
        if row < 0 or row >= Board.SIZE:
            return False
        if col < 0 or col >= Board.SIZE:
            return False
        if (tile is None) or len(tile) != 1:
            return False
        if (letter is None) or len(letter) != 1 or (letter not in Alphabet.order):
            return False
        if tile != u'?' and tile != letter:
            return False
        if len(self._covers) >= Rack.MAX_TILES:
            # Already have 7 tiles being played
            return False
        self._covers.append(Cover(row, col, tile, letter))
        return True

    def add_validated_cover(self, cover):
        """ Add an already validated Cover object to this move """
        self._covers.append(cover)
        # Find out automatically whether this is a horizontal or vertical move
        if len(self._covers) == 2:
            self._horizontal = self._covers[0].row == cover.row

    def check_legality(self, board, rack):
        """ Check whether this move is legal on the board """
        # Must cover at least one square
        if len(self._covers) < 1:
            return Move.NULL_MOVE
        if len(self._covers) > Rack.MAX_TILES:
            return Move.TOO_MANY_TILES_PLAYED
        row = 0
        col = 0
        horiz = True
        vert = True
        first = True
        # All tiles played must be in the rack
        played = u''.join([c.tile for c in self._covers])
        if not rack.contains(played):
            # !!! TODO: Debugging aid; change this
            # return Move.TILE_NOT_IN_RACK
            pass
        # The tiles covered by the move must be purely horizontal or purely vertical
        for c in self._covers:
            if first:
                row = c.row
                col = c.col
                first = False
            else:
                if c.row != row:
                    horiz = False
                if c.col != col:
                    vert = False
        if (not horiz) and (not vert):
            # Spread all over: not legal
            return Move.DISJOINT
        # The move is purely horizontal or vertical
        if horiz:
            self._covers.sort(key = lambda x: x.col) # Sort in ascending column order
            self._horizontal = True
        else:
            self._covers.sort(key = lambda x: x.row) # Sort in ascending row order
            self._horizontal = False
        # Check whether eventual missing squares in the move sequence are already covered
        row = 0
        col = 0
        first = True
        for c in self._covers:
            if board.is_covered(c.row, c.col):
                # We already have a tile in the square: illegal play
                return Move.SQUARE_ALREADY_OCCUPIED
            # If there is a gap between this cover and the last one,
            # make sure all intermediate squares are covered
            if first:
                self._row = c.row
                self._col = c.col
                first = False
            else:
                if horiz:
                    # Horizontal: check squares within row
                    for ix in range(col + 1, c.col):
                        if not board.is_covered(c.row, ix):
                            # Found gap: illegal play
                            return Move.HAS_GAP
                else:
                    assert vert
                    # Vertical: check squares within column
                    for ix in range(row + 1, c.row):
                        if not board.is_covered(ix, c.col):
                            # Found gap: illegal play
                            return Move.HAS_GAP
            row = c.row
            col = c.col
        # Find the start and end of the word that is being formed, including
        # tiles aready on the board
        if horiz:
            # Look for the beginning
            while self._col > 0 and board.is_covered(self._row, self._col - 1):
                self._col -= 1
            # Look for the end
            while col + 1 < Board.SIZE and board.is_covered(self._row, col + 1):
                col += 1
            # Now we know the length
            self._numletters = col - self._col + 1
        else:
            # Look for the beginning
            while self._row > 0 and board.is_covered(self._row - 1, self._col):
                self._row -= 1
            # Look for the end
            while row + 1 < Board.SIZE and board.is_covered(row + 1, self._col):
                row += 1
            # Now we know the length
            self._numletters = row - self._row + 1
        # !!! For cosmetic purposes, we may want to see if a single cover
        # !!! creates a longer word vertically than horizontally and switch
        # !!! orientation in that case
        # Assemble the resulting word
        self._word = u''
        cix = 0
        for ix in range(self._numletters):
            if horiz:
                if cix < len(self._covers) and self._col + ix == self._covers[cix].col:
                    # This is one of the new letters
                    self._word += self._covers[cix].letter
                    cix += 1
                else:
                    # This is a letter that was already on the board
                    self._word += board.letter_at(self._row, self._col + ix)
            else:
                if cix < len(self._covers) and self._row + ix == self._covers[cix].row:
                    # This is one of the new letters
                    self._word += self._covers[cix].letter
                    cix += 1
                else:
                    # This is a letter that was already on the board
                    self._word += board.letter_at(self._row + ix, self._col)
        # Check whether the word is in the dictionary
        if self._word not in Manager.word_db():
            return Move.WORD_NOT_IN_DICTIONARY
        # Check that the play is adjacent to some previously placed tile
        # (unless this is the first move, i.e. the board is empty)
        if board.is_empty():
            # Must go through the center square
            center = False
            for c in self._covers:
                if c.row == Board.SIZE / 2 and c.col == Board.SIZE / 2:
                    center = True
                    break
            if not center:
                return Move.FIRST_MOVE_NOT_IN_CENTER
        else:
            # Must be adjacent to something already on the board
            if not any([board.has_adjacent(c.row, c.col) for c in self._covers]):
                return Move.NOT_ADJACENT
            # Check all cross words formed by the new tiles
            for c in self._covers:
                if board.is_closed(c.row, c.col):
                    # We don't need to check further: no tile can be placed in this square
                    return Move.CROSS_WORD_NOT_IN_DICTIONARY
                if self._horizontal:
                    cross = board.letters_above(c.row, c.col) + c.letter + board.letters_below(c.row, c.col)
                else:
                    cross = board.letters_left(c.row, c.col) + c.letter + board.letters_right(c.row, c.col)
                if len(cross) > 1 and cross not in Manager.word_db():
                    # print(u"Cross check fails for {0}".format(cross)) # !!! DEBUG
                    return Move.CROSS_WORD_NOT_IN_DICTIONARY
        # All checks pass: the play is legal
        return Move.LEGAL

    def score(self, board):
        """ Calculate the score of this move, which is assumed to be legal """
        # Sum of letter scores
        total = 0
        sc = 0
        # Word score multiplier
        wsc = 1
        # Cover index
        cix = 0
        # Number of tiles freshly covered
        numcovers = len(self._covers)
        # Tally the score of the primary word
        for ix in range(self._numletters):
            if self._horizontal:
                this_ix = self._col + ix
                cover_ix = 0 if cix >= numcovers else self._covers[cix].col
            else:
                this_ix = self._row + ix
                cover_ix = 0 if cix >= numcovers else self._covers[cix].row
            if cix < numcovers and this_ix == cover_ix:
                # This is one of the new tiles
                c = self._covers[cix]
                lscore = 0 if c.tile == u'?' else Alphabet.scores[c.tile]
                lscore *= Board.letterscore(c.row, c.col)
                wsc *= Board.wordscore(c.row, c.col)
                cix += 1
            else:
                # This is a letter that was already on the board
                lscore = Alphabet.scores[self._word[ix]]
            sc += lscore
        total = sc * wsc
        # Tally the scores of words formed across the primary word
        for c in self._covers:
            if self._horizontal:
                cross = board.tiles_above(c.row, c.col) + board.tiles_below(c.row, c.col)
            else:
                cross = board.tiles_left(c.row, c.col) + board.tiles_right(c.row, c.col)
            if cross:
                sc = 0 if c.tile == u'?' else Alphabet.scores[c.tile]
                sc *= Board.letterscore(c.row, c.col)
                wsc = Board.wordscore(c.row, c.col)
                for tile in cross:
                    sc += 0 if tile == u'?' else Alphabet.scores[tile]
                # print(u"Cross {0} scores {1}".format(cross, sc * wsc)) # !!! DEBUG
                total += sc * wsc
        # Add the bingo bonus of 50 points for playing all (seven) tiles
        if numcovers == Rack.MAX_TILES:
            total += Move.BINGO_BONUS
        return total

    def apply(self, board, rack):
        """ Apply this move, assumed to be legal, to the board """
        for c in self._covers:
            board.set_letter(c.row, c.col, c.letter)
            board.set_tile(c.row, c.col, c.tile)
            rack.remove_tile(c.tile)
