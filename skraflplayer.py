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

    def letter_at(self, row, col):
        """ Return the letter at the specified co-ordinate """
        return self._letters[row][col:col + 1]

    def set_letter(self, letter, row, col):
        """ Set the letter at the specified co-ordinate """
        assert letter is not None
        assert len(letter) == 1
        prev = self._letter_at(row, col)
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

    def set_tile(self, tile, row, col):
        """ Set the tile at the specified co-ordinate """
        assert tile is not None
        assert len(tile) == 1
        prev = self._tile_at(row, col)
        if prev == tile:
            # Unchanged square: we're done
            return
        if prev == u' ' and tile != u' ':
            # Putting a tile into a previously empty square
            self._numtiles += 1
        self._tiles[row] = self._tiles[row][0:col] + tile + self._tiles[row][col + 1:]

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

    def is_play_legal(self, play):
        """ Is the play legal in this state? """
        return play.is_legal(self._board)

    def apply_play(self, play):
        """ Apply the given Skraflplay to this state """
        pass

class Skraflplay:

    def __init__(self):
        # Store a list of tuples where each tuple
        # denotes a square covered by the play.
        # The tuples are (row, col, tile, letter)
        self._covers = []

    def add_cover(self, row, col, tile, letter):
        self._covers.append((row, col, tile, letter))

    def is_legal(self, board):
        """ Performs basic formal checks on the play. Does not check
            whether the play connects correctly with words that are
            already on the board. """
        # Must cover at least one square
        if len(self._covers) < 1:
            return False
        row = 0
        col = 0
        horiz = True
        vert = True
        first = True
        # Play must be purely horizontal or purely vertical
        for c in self._covers:
            nrow, ncol, ntile, nletter = c
            if first:
                row = nrow
                col = ncol
                first = False
            else:
                if nrow != row:
                    horiz = False
                if ncol != col:
                    vert = False
        if (not horiz) and (not vert):
            # Spread all over: not legal
            return False
        if horiz:
            self._covers.sort(key = lambda x: x[1]) # Sort in ascending column order
        else:
            self._covers.sort(key = lambda x: x[0]) # Sort in ascending row order
        # Check whether all missing squares in sequence are already covered
        for c in self._covers:
            nrow, ncol, ntile, nletter = c
            if board.is_covered(nrow, ncol):
                # We already have a tile in the square
                return False
            pass
        # Find the start and end of the word that is being formed, including
        # tiles aready on the board
        pass
        # Check that the play is adjacent to some previously placed tile
        # (unless this is the first move, i.e. the board is empty)
        pass
        # Create a succinct representation of the play
        pass
        # All checks pass: the play is legal
        return True


def test():

    state = Skraflstate()
    play = Skraflplay()
    play.add_cover(6, 7, u'þ', u'þ')
    play.add_cover(7, 7, u'ú', u'ú')
    if not state.is_play_legal(play):
        print("Play is not legal")
        return
    print("Play is legal")


