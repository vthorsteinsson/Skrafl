# -*- coding: utf-8 -*-

""" Skrafltester

    Author: Vilhjalmur Thorsteinsson, 2014

    This module implements a testing function for the
    functionality in skraflmechanics.py and skraflplayer.py

"""

from skraflmechanics import Manager, State, Move, ExchangeMove, Error
from skraflplayer import AutoPlayer
import time

def test_move(state, movestring):
    # Test placing a simple move
    coord, word = movestring.split(u' ')
    rowid = u"ABCDEFGHIJKLMNO"
    row, col = 0, 0
    xd, yd = 0, 0
    horiz = True
    if coord[0] in rowid:
        row = rowid.index(coord[0])
        col = int(coord[1:]) - 1
        yd = 1
    else:
        row = rowid.index(coord[-1])
        col = int(coord[0:-1]) - 1
        xd = 1
        horiz = False
    move = Move(word, row, col, horiz)
    next_is_blank = False
    for c in word:
        if c == u'?':
            next_is_blank = True
            continue
        if not state.board().is_covered(row, col):
            move.add_cover(row, col, u'?' if next_is_blank else c, c)
            next_is_blank = False
        row += xd
        col += yd
    legal = state.check_legality(move)
    if legal != Error.LEGAL:
        print(u"Play is not legal, code {0}".format(Error.errortext(legal)))
        return False
    print(u"Play {0} is legal and scores {1} points".format(unicode(move), state.score(move)))
    state.apply_move(move)
    print(unicode(state))
    return True

def test_exchange(state, numtiles):
    exch = state.player_rack().contents()[0:numtiles]
    move = ExchangeMove(exch)
    legal = state.check_legality(move)
    if legal != Error.LEGAL:
        print(u"Play is not legal, code {0}".format(Error.errortext(legal)))
        return False
    print(u"Play {0} is legal and scores {1} points".format(unicode(move), state.score(move)))
    state.apply_move(move)
    print(unicode(state))
    return True

def test_game():
    """ Go through a whole game by pitting two AutoPlayers against each other """

    state = State()
    print unicode(state)

    # test_move(state, u"H4 stuði")
    # test_move(state, u"5E detts")
    # test_exchange(state, 3)
    # test_move(state, u"I3 dýs")
    # test_move(state, u"6E ?óx") # The question mark indicates a blank tile for the subsequent cover
    # state.player_rack().set_tiles(u"ðhknnmn")

    # Generate a sequence of moves, switching player sides automatically

    t0 = time.time()

    while not state.is_game_over():

        apl = AutoPlayer(state)
        move = apl.generate_move()

        legal = state.check_legality(move)
        if legal != Error.LEGAL:
            # Oops: the autoplayer generated an illegal move
            print(u"Play is not legal, code {0}".format(Error.errortext(legal)))
            return
        print(u"Play {0} scores {1} points".format(unicode(move), state.score(move)))

        state.apply_move(move)

        print(unicode(state))

    state.finalize_score()
    p0, p1 = state.scores()
    t1 = time.time()

    print(u"Game over, final score {0} : {1} after {2} moves ({3:.2f} seconds)".format(p0, p1, state.num_moves(), t1 - t0))


def test():

    print(u"Welcome to the skrafl game tester")

    manager = Manager()

    # Loop forever
    while True:
        test_game()

