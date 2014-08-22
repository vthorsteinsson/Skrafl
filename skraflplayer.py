# -*- coding: utf-8 -*-

""" Skraflplayer

Author: Vilhjalmur Thorsteinsson, 2014

This experimental module finds and ranks legal moves on
a Scrabble(tm)-like board.

"""

from languages import Alphabet

# A standard Scrabble board is 15 x 15 squares
BOARDSIZE = 15


class Skraflboard:

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

    def __init__(self):
        # Store letters on the board in list of strings
        self._letters = [u' ' * BOARDSIZE for _ in range(BOARDSIZE)]
        # Store tiles on the board in list of strings
        self._tiles = [u' ' * BOARDSIZE for _ in range(BOARDSIZE)]
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

    def has_adjacent(self, row, col):
        """ Check whether there are any tiles on the board adjacent to this square """
        if row > 0 and self.is_covered(row - 1, col):
            return True
        if row < BOARDSIZE and self.is_covered(row + 1, col):
            return True
        if col > 0 and self.is_covered(row, col - 1):
            return True
        if col < BOARDSIZE and self.is_covered(row, col + 1):
            return True
        return False

    def letter_at(self, row, col):
        """ Return the letter at the specified co-ordinate """
        return self._letters[row][col:col + 1]

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

    def tile_at(self, row, col):
        """ Return the tile at the specified co-ordinate (may be '?' for blank tile) """
        return self._tiles[row][col:col + 1]

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

    def __str__(self):
        l = []
        for row in self._letters:
            l.append(u' '.join([u'.' if c == u' ' else c for c in row]))
        return u'\n'.join(l)

    @staticmethod
    def wordscore(row, col):
        return int(Skraflboard._wordscore[row][col:col + 1])

    @staticmethod
    def letterscore(row, col):
        return int(Skraflboard._letterscore[row][col:col + 1])


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

    def set_above(self, wordpart):
        self._above = wordpart

    def set_below(self, wordpart):
        self._below = wordpart


class Skraflaxis:

    """ Represents an one-dimensional axis on the board, either
        horizontal or vertical.
    """

    def __init__(self, horizontal):
        self._axis = [Skraflsquare()] * BOARDSIZE
        self._horizontal = horizontal

    def is_horizontal(self):
        return self._horizontal

    def is_vertical(self):
        return not self._horizontal

    @staticmethod
    def from_row(board, row):
        """ Creates a Skraflaxis from a board row.
            Loads letters and tiles and initializes the cross-checks. """
        axis = Skraflaxis(True) # Horizontal
        for ix in range(BOARDSIZE):
            axis._axis[ix].load(board, row, ix)
            # Get the word part above the square, if any
            above = u''
            r = row
            while r > 0:
                r -= 1
                ltr = board.letter_at(r, ix)
                if ltr == u' ':
                    break
                above = ltr + above
            # Get the word part below the square, if any
            below = u''
            r = row + 1
            while r < BOARDSIZE:
                ltr = board.letter_at(r, ix)
                if ltr == u' ':
                    break
                below += ltr
                r += 1
            if above:
                axis._axis[ix].set_above(above)
            if below:
                axis._axis[ix].set_below(below)
        return axis

    @staticmethod
    def from_column(board, col):
        """ Creates a Skraflaxis from a board column.
            Loads letters and tiles and initializes the cross-checks. """
        axis = Skraflaxis(False) # Vertical
        for ix in range(BOARDSIZE):
            axis._axis[ix].load(board, ix, col)
            # Get the word part left of (above) the square, if any
            above = u''
            c = col
            while c > 0:
                c -= 1
                ltr = board.letter_at(ix, c)
                if ltr == u' ':
                    break
                above = ltr + above
            # Get the word part right of (below) the square, if any
            below = u''
            c = col + 1
            while c < BOARDSIZE:
                ltr = board.letter_at(ix, c)
                if ltr == u' ':
                    break
                below += ltr
                c += 1
            if above:
                axis._axis[ix].set_above(above)
            if below:
                axis._axis[ix].set_below(below)
        return axis

class Skraflstate:

    def __init__(self):
        self._board = Skraflboard()

    def load_board(self, board):
        """ Load a Skraflboard into this state """
        self._board = board

    def check_legality(self, play):
        """ Is the play legal in this state? """
        return play.check_legality(self._board)

    def apply_play(self, play):
        """ Apply the given Skraflplay to this state """
        play.apply(self._board)

    def score(self, play):
        """ Calculate the score of the play """
        return play.score(self._board)

    def __str__(self):
        return self._board.__str__()

class Cover:

    def __init__(self, row, col, tile, letter):
        self.row = row
        self.col = col
        self.tile = tile
        self.letter = letter

class Skraflplay:

    # Error return codes from Skraflplay.check_legality()
    LEGAL = 0
    NULL_MOVE = 1
    FIRST_MOVE_NOT_IN_CENTER = 2
    DISJOINT = 3
    NOT_ADJACENT = 4
    SQUARE_ALREADY_OCCUPIED = 5
    HAS_GAP = 6

    @staticmethod
    def errortext(errcode):
        return [u"LEGAL", 
            u"NULL_MOVE", 
            u"FIRST_MOVE_NOT_IN_CENTER", 
            u"DISJOINT", 
            u"NOT_ADJACENT", 
            u"SQUARE_ALREADY_OCCUPIED", 
            u"HAS_GAP"][errcode]

    def __init__(self):
        # A list of squares covered by the play, i.e. actual tiles
        # laid down on the board
        self._covers = []
        # Number of letters in word formed (this may be >= len(self._covers))
        self._numletters = 0
        # The word formed
        self._word = None
        # Starting row and column of word formed
        self._row = 0
        self._col = 0
        # Is the word horizontal or vertical?
        self._horizontal = True

    def short_coordinate(self):
        """ Return the coordinate of the move in 'Scrabble convention',
            i.e. row letter + column number for horizontal moves or
            column number + row letter for vertical ones """
        if self._horizontal:
            # Row letter first, then column number
            return u"ABCDEFGHIJKLMNO"[self._row:self._row + 1] + str(self._col)
        else:
            # Column number first, then row letter
            return str(self._col) + u"ABCDEFGHIJKLMNO"[self._row:self._row + 1]

    def __str__(self):
        return self.short_coordinate() + u" " + self._word

    def add_cover(self, row, col, tile, letter):
        self._covers.append(Cover(row, col, tile, letter))

    def check_legality(self, board):
        """ Performs basic formal checks on the play. Does not check
            whether the play connects correctly with words that are
            already on the board. """
        # Must cover at least one square
        if len(self._covers) < 1:
            return Skraflplay.NULL_MOVE
        row = 0
        col = 0
        horiz = True
        vert = True
        first = True
        # Play must be purely horizontal or purely vertical
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
            return Skraflplay.DISJOINT
        if horiz:
            self._covers.sort(key = lambda x: x.col) # Sort in ascending column order
            self._horizontal = True
        else:
            self._covers.sort(key = lambda x: x.row) # Sort in ascending row order
            self._horizontal = False
        # Check whether all missing squares in play sequence are already covered
        row = 0
        col = 0
        first = True
        for c in self._covers:
            if board.is_covered(c.row, c.col):
                # We already have a tile in the square: illegal play
                return Skraflplay.SQUARE_ALREADY_OCCUPIED
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
                            return Skraflplay.HAS_GAP
                else:
                    assert vert
                    # Vertical: check squares within column
                    for ix in range(row + 1, c.row):
                        if not board.is_covered(ix, c.col):
                            # Found gap: illegal play
                            return Skraflplay.HAS_GAP
            row = c.row
            col = c.col
        # Find the start and end of the word that is being formed, including
        # tiles aready on the board
        if horiz:
            # Look for the beginning
            while self._col > 0 and board.is_covered(self._row, self._col - 1):
                self._col -= 1
            # Look for the end
            while col + 1 < BOARDSIZE and board.is_covered(self._row, col + 1):
                col += 1
            self._numletters = col - self._col + 1
        else:
            # Look for the beginning
            while self._row > 0 and board.is_covered(self._row - 1, self._col):
                self._row -= 1
            # Look for the end
            while row + 1 < BOARDSIZE and board.is_covered(row + 1, self._col):
                row += 1
            self._numletters = row - self._row + 1
        # Assemble the resulting word
        self._word = u''
        for ix in range(self._numletters):
            # !!! BUG: need to mix in the covers of this play
            if horiz:
                self._word += board.letter_at(self._row, self._col + ix)
            else:
                self._word += board.letter_at(self._row + ix, self._col)
        # !!! TODO: Check here whether the word is found in the dictionary
        pass
        # Check that the play is adjacent to some previously placed tile
        # (unless this is the first move, i.e. the board is empty)
        if board.is_empty():
            # Must go through the center square
            center = False
            for c in self._covers:
                if c.row == BOARDSIZE / 2 and c.col == BOARDSIZE / 2:
                    center = True
                    break
            if not center:
                return Skraflplay.FIRST_MOVE_NOT_IN_CENTER
        else:
            # Must be adjacent to something already on the board
            if not any([board.has_adjacent(c.row, c.col) for c in self._covers]):
                return Skraflplay.NOT_ADJACENT
        # Create a succinct representation of the play
        pass
        # All checks pass: the play is legal
        return Skraflplay.LEGAL

    def score(self, board):
        """ Calculate the score of this play """
        # !!! BUG: Missing the letter scores of tiles already on the board
        sc = 0
        wsc = 1
        for c in self._covers:
            lscore = 0 if c.tile == u'?' else Alphabet.scores[c.tile]
            lscore *= Skraflboard.letterscore(c.row, c.col)
            sc += lscore
            wsc *= Skraflboard.wordscore(c.row, c.col)
        return sc * wsc

    def apply(self, board):
        """ Apply this play, assumed to have been checked for legality, to the board """
        for c in self._covers:
            board.set_letter(c.row, c.col, c.letter)
            board.set_tile(c.row, c.col, c.tile)

def test():

    state = Skraflstate()
    print unicode(state)

    # Test placing a simple play
    play = Skraflplay()
    play.add_cover(7, 7, u"þ", u"þ")
    play.add_cover(8, 7, u"ú", u"ú")
    legal = state.check_legality(play)
    if legal != Skraflplay.LEGAL:
        print(u"Play is not legal, code {0}".format(Skraflplay.errortext(legal)))
        return
    print(u"Play {0} is legal and scores {1} points".format(unicode(play), state.score(play)))

    state.apply_play(play)

    print(unicode(state))

    play = Skraflplay()
    play.add_cover(7, 8, u"e", u"e")
    play.add_cover(7, 9, u"s", u"s")
    play.add_cover(7, 10, u"s", u"s")
    play.add_cover(7, 11, u"i", u"i")
    legal = state.check_legality(play)
    if legal != Skraflplay.LEGAL:
        print(u"Play is not legal, code {0}".format(Skraflplay.errortext(legal)))
        return
    print(u"Play {0} is legal and scores {1} points".format(unicode(play), state.score(play)))

    state.apply_play(play)

    print(unicode(state))

