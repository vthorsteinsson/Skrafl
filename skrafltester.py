# -*- coding: utf-8 -*-

""" Skrafltester

    Author: Vilhjalmur Thorsteinsson, 2014

    This module implements a testing function for the
    functionality in skraflmechanics.py and skraflplayer.py

"""

from skraflmechanics import Manager, State, Move
from skraflplayer import AutoPlayer

def test_move(state, movestring):
    # Test placing a simple move
    coord, word = movestring.split(u' ')
    rowid = u"ABCDEFGHIJKLMNO"
    row, col = 0, 0
    xd, yd = 0, 0
    if coord[0] in rowid:
        row = rowid.index(coord[0])
        col = int(coord[1:]) - 1
        yd = 1
    else:
        row = rowid.index(coord[-1])
        col = int(coord[0:-1]) - 1
        xd = 1
    move = Move(word, row, col)
    for c in word:
        if not state.board().is_covered(row, col):
            move.add_cover(row, col, c, c)
        row += xd
        col += yd
    legal = state.check_legality(move)
    if legal != Move.LEGAL:
        print(u"Play is not legal, code {0}".format(Move.errortext(legal)))
        return False
    print(u"Play {0} is legal and scores {1} points".format(unicode(move), state.score(move)))
    state.apply_move(move)
    print(unicode(state))
    return True

def test_exchange(state, numtiles):
    print(u"Exchanging {0} tiles".format(numtiles))
    state.exchange(state.player_rack().contents()[0:numtiles])

def test():

    manager = Manager()

    state = State()
    print unicode(state)

    test_move(state, u"H4 stuði")
    test_move(state, u"5E detts")
    test_exchange(state, 3)
    test_move(state, u"I3 dýs")
    test_move(state, u"6E óx")
    state.player_rack().set_tiles(u"ðhknnmn")

    # Generate a sequence of moves, switching player sides automatically

    for _ in range(8):

        apl = AutoPlayer(state)
        move = apl.generate_move()

        legal = state.check_legality(move)
        if legal != Move.LEGAL:
            # Oops: the autoplayer generated an illegal move
            print(u"Play is not legal, code {0}".format(Move.errortext(legal)))
            return
        print(u"Play {0} is legal and scores {1} points".format(unicode(move), state.score(move)))

        state.apply_move(move)

        print(unicode(state))

