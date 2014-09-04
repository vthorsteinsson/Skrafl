# -*- coding: utf-8 -*-

""" Skrafltester

    Author: Vilhjalmur Thorsteinsson, 2014

    This module implements a testing function for the
    functionality in skraflmechanics.py and skraflplayer.py

"""

from skraflmechanics import Manager, State, Move, ExchangeMove, Error
from skraflplayer import AutoPlayer, AutoPlayer_MiniMax
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
    state.set_player_name(0, u"AutoPlayer")
    state.set_player_name(1, u"MiniMax")

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

        apl = None
        if state.player_to_move() == 0:
            # Simplistic player
            apl = AutoPlayer(state)
        else:
            # MiniMax player
            apl = AutoPlayer_MiniMax(state)
        g0 = time.time()
        move = apl.generate_move()
        g1 = time.time()

        # legal = state.check_legality(move)
        # if legal != Error.LEGAL:
        #     # Oops: the autoplayer generated an illegal move
        #     print(u"Play is not legal, code {0}".format(Error.errortext(legal)))
        #     return
        print(u"Play {0} scores {1} points ({2:.2f} seconds)".format(unicode(move), state.score(move), g1 - g0))

        state.apply_move(move)

        print(unicode(state))

    state.finalize_score()
    p0, p1 = state.scores()
    t1 = time.time()

    print(u"Game over, final score {4} {0} : {5} {1} after {2} moves ({3:.2f} seconds)".format(p0, p1,
        state.num_moves(), t1 - t0, state.player_name(0), state.player_name(1)))

    return state.scores()


def test():

    print(u"Welcome to the skrafl game tester")

    manager = Manager()

    gameswon = [0, 0]
    totalpoints = [0, 0]
    sumofmargin = [0, 0]
    num_games = 0

    # Run games
    for _ in range(100):
        p0, p1 = test_game()
        if p0 > p1:
            gameswon[0] += 1
            sumofmargin[0] += (p0 - p1)
        elif p1 > p0:
            gameswon[1] += 1
            sumofmargin[1] += (p1 - p0)
        totalpoints[0] += p0
        totalpoints[1] += p1
        num_games += 1

    print(u"Test completed, {0} games played".format(num_games))
    if gameswon[0] == 0:
        print(u"AutoPlayer won {0} games and scored an average of {1:.1f} points per game".format(gameswon[0],
            float(totalpoints[0]) / num_games))
    else:
        print(u"AutoPlayer won {0} games with an average margin of {2:.1f} and scored an average of {1:.1f} points per game".format(gameswon[0],
            float(totalpoints[0]) / num_games, float(sumofmargin[0]) / gameswon[0]))
    if gameswon[1] == 0:
        print(u"MiniMax won {0} games and scored an average of {1:.1f} points per game".format(gameswon[1],
            float(totalpoints[1]) / num_games))
    else:
        print(u"MiniMax won {0} games with an average margin of {2:.1f} and scored an average of {1:.1f} points per game".format(gameswon[1],
            float(totalpoints[1]) / num_games, float(sumofmargin[1]) / gameswon[1]))

