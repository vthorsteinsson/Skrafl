# -*- coding: utf-8 -*-

""" Web server for netskrafl.appspot.com

    Author: Vilhjalmur Thorsteinsson, 2014

    This web server module uses the Flask framework to implement
    a crossword game similar to SCRABBLE(tm).

    The actual game logic is found in skraflplayer.py and
    skraflmechanics.py. The web client code is found in netskrafl.js

    The server is compatible with Python 2.7 and 3.x, CPython and PyPy.
    (To get it to run under PyPy 2.7.6 the author had to patch
    \pypy\lib-python\2.7\mimetypes.py to fix a bug that was not
    present in the CPython 2.7 distribution of the same file.)

    Note: SCRABBLE is a registered trademark. This software or its author
    are in no way affiliated with or endorsed by the owners or licensees
    of the SCRABBLE trademark.

"""

import logging
import time
from random import randint

from flask import Flask
from flask import render_template, redirect, jsonify
from flask import request, session, url_for

from google.appengine.api import users

from skraflmechanics import Manager, State, Board, Move, PassMove, ExchangeMove, ResignMove, Error
from skraflplayer import AutoPlayer
from languages import Alphabet
from skrafldb import UserModel, GameModel, MoveModel, CoverModel


# Standard Flask initialization

app = Flask(__name__)
app.config['DEBUG'] = True # !!! TODO: Change to False for production deployment
app.secret_key = '\x03\\_,i\xfc\xaf=:L\xce\x9b\xc8z\xf8l\x000\x84\x11\xe1\xe6\xb4M'

manager = Manager()


class User:

    """ Information about a human user including nickname and preferences """

    def __init__(self):
        u = users.get_current_user()
        if u is None:
            self._user_id = None
        else:
            self._user_id = u.user_id()
        self._nickname = u.nickname() # Default
        self._inactive = False
        self._preferences = { }

    # The users that have been authenticated in this session
    _cache = dict()

    def fetch(self):
        u = UserModel.fetch(self._user_id)
        if u is None:
            UserModel.create(self._user_id, self.nickname())
            # Use the default properties for a newly created user
            return
        self._nickname = u.nickname
        self._inactive = u.inactive
        self._preferences = u.prefs

    def update(self):
        UserModel.update(self._user_id, self._nickname, self._inactive, self._preferences)

    def id(self):
        return self._user_id

    def nickname(self):
        return self._nickname or self._user_id

    def set_nickname(self, nickname):
        self._nickname = nickname

    def logout_url(self):
        return users.create_logout_url("/")

    @classmethod
    def current(cls):
        user = users.get_current_user()
        if user is None:
            return None
        if user.user_id() in User._cache:
            return User._cache[user.user_id()]
        u = cls()
        u.fetch()
        User._cache[u.id()] = u
        return u

    @classmethod
    def current_nickname(cls):
        u = cls.current()
        if u is None:
            return None
        return u.nickname()


class Game:

    """ A wrapper class for a particular game that is in process
        or completed. Contains inter alia a State instance.
    """

    def __init__(self):
        self.username = None
        self.state = None
        # Is the human player 0 or 1, where player 0 begins the game?
        self.player_index = 0
        # The last move made by the autoplayer
        self.last_move = None
        # Was the game finished by resigning?
        self.resigned = False
        # History of moves in this game so far
        self.moves = []

    # The current game state for different users
    # !!! TODO: This will be stored persistently in the App Engine datastore
    _cache = dict()

    @classmethod
    def current(cls):
        """ Obtain the current game state """
        user = User.current()
        user_id = None if user is None else user.id()
        if not user_id or user_id not in Game._cache:
            # No game state found
            return None
        # Fetch the game state
        # !!! TODO: Will fetch from persistent state
        return Game._cache[user_id]

    @classmethod
    def new(cls, username):
        """ Start and initialize a new game """
        game = cls()
        game.username = username
        game.state = State()
        game.player_index = randint(0, 1)
        game.state.set_player_name(game.player_index, username)
        game.state.set_player_name(1 - game.player_index, u"Netskrafl")
        # Cache the game so it can be looked up by user id
        user = User.current()
        if user is not None:
            Game._cache[user.id()] = game
        # If AutoPlayer is first to move, generate the first move
        if game.player_index == 1:
            game.autoplayer_move()
        # Store the new game in persistent storage
        game._store_db(user.id())
        return game

    def _store_db(self, user_id):
        """ Store the game state in persistent storage """
        gm = GameModel()
        gm.set_player(self.player_index, user_id)
        gm.set_player(1 - self.player_index, None)
        gm.rack0 = self.state._racks[0].contents()
        gm.rack1 = self.state._racks[1].contents()
        gm.score0 = self.state._scores[0]
        gm.score1 = self.state._scores[1]
        gm.to_move = len(self.moves) % 2
        gm.over = self.state.is_game_over()
        movelist = []
        for player, m in self.moves:
            mm = MoveModel()
            coord, word, score = m.summary(self.state.board())
            mm.coord = coord
            mm.word = word
            mm.score = score
            covlist = []
            for coord, tile, letter, score in m.details():
                cm = CoverModel()
                cm.coord = coord
                cm.tile = tile
                cm.letter = letter
                cm.score = score
                covlist.append(cm)
            mm.covers = covlist
            movelist.append(mm)
        gm.moves = movelist
        gm.put()

    def set_human_name(self, nickname):
        """ Set the nickname of the human player """
        self.state.set_player_name(self.player_index, nickname)

    def resign(self):
        """ The human player is resigning the game """
        self.resigned = True

    def autoplayer_move(self):
        """ Let the AutoPlayer make its move """
        # !!! DEBUG for testing various move types
        # rnd = randint(0,3)
        # if rnd == 0:
        #     print(u"Generating ExchangeMove")
        #     move = ExchangeMove(self.state.player_rack().contents()[0:randint(1,7)])
        # else:
        apl = AutoPlayer(self.state)
        move = apl.generate_move()
        self.state.apply_move(move)
        self.moves.append((1 - self.player_index, move))
        self.last_move = move

    def human_move(self, move):
        """ Register the human move, update the score and move list """
        self.state.apply_move(move)
        self.moves.append((self.player_index, move))
        self.last_move = None # No autoplayer move yet

    def enum_tiles(self):
        """ Enumerate all tiles on the board in a convenient form """
        for x, y, tile, letter in self.state.board().enum_tiles():
            yield (Board.ROWIDS[x] + str(y + 1), tile, letter,
                0 if tile == u'?' else Alphabet.scores[tile])

    BAG_SORT_ORDER = Alphabet.order + u'?'

    def display_bag(self):
        """ Returns the bag as it should be displayed, i.e. including the autoplayer's rack """
        displaybag = self.state.bag().contents() + self.state._racks[1 - self.player_index].contents()
        return u''.join(sorted(displaybag, key=lambda ch: Game.BAG_SORT_ORDER.index(ch)))

    def client_state(self):
        """ Create a package of information for the client about the current state """
        reply = dict()
        if self.state.is_game_over():
            # The game is now over - one of the players finished it
            reply["result"] = Error.GAME_OVER # Not really an error
            num_moves = 1
            if self.last_move is not None:
                # Show the autoplayer move if it was the last move in the game
                reply["lastmove"] = self.last_move.details()
                num_moves = 2 # One new move to be added to move list
            newmoves = [(player, m.summary(self.state.board())) for player, m in self.moves[-num_moves:]]
            # Lastplayer is the player who finished the game
            lastplayer = self.moves[-1][0]
            if not self.resigned:
                # If the game did not end by resignation,
                # account for the losing rack
                rack = self.state._racks[1 - lastplayer].contents()
                # Subtract the score of the losing rack from the losing player
                newmoves.append((1 - lastplayer, (u"", rack, -1 * Alphabet.score(rack))))
                # Add the score of the losing rack to the winning player
                newmoves.append((lastplayer, (u"", rack, 1 * Alphabet.score(rack))))
            # Add a synthetic "game over" move
            newmoves.append((1 - lastplayer, (u"", u"OVER", 0)))
            reply["newmoves"] = newmoves
            reply["bag"] = "" # Bag is now empty, by definition
            reply["xchg"] = False # Exchange move not allowed
        else:
            reply["result"] = 0 # Indicate no error
            reply["rack"] = self.state.player_rack().details()
            reply["lastmove"] = self.last_move.details()
            reply["newmoves"] = [(player, m.summary(self.state.board())) for player, m in self.moves[-2:]]
            reply["bag"] = self.display_bag()
            reply["xchg"] = self.state.is_exchange_allowed()
        reply["scores"] = self.state.scores()
        return reply


def _process_move(movelist):
    """ Process a move from the client (the human player)
        Returns True if OK or False if the move was illegal
    """

    game = Game.current()

    if game is None:
        # !!! TODO: more informative error message about relogging in
        return jsonify(result=Error.NULL_MOVE)

    # Parse the move from the movestring we got back
    m = Move(u'', 0, 0)
    try:
        for mstr in movelist:
            if mstr == u"pass":
                # Pass move
                m = PassMove()
                break
            if mstr[0:5] == u"exch=":
                # Exchange move
                m = ExchangeMove(mstr[5:])
                break
            if mstr == u"rsgn":
                # Resign from game, forfeiting all points
                m = ResignMove(game.state.scores()[game.player_index])
                game.resign()
                break
            sq, tile = mstr.split(u'=')
            row = u"ABCDEFGHIJKLMNO".index(sq[0])
            col = int(sq[1:]) - 1
            if tile[0] == u'?':
                # If the blank tile is played, the next character contains
                # its meaning, i.e. the letter it stands for
                letter = tile[1]
                tile = tile[0]
            else:
                letter = tile
            # print(u"Cover: row {0} col {1}".format(row, col))
            m.add_cover(row, col, tile, letter)
    except Exception as e:
        logging.info(u"Exception in _process_move(): {0}".format(e).encode("latin-1"))
        m = None

    # Process the move string here
    err = game.state.check_legality(m)

    if err != Error.LEGAL:
        # Something was wrong with the move:
        # show the user a corresponding error message
        return jsonify(result=err)

    # Move is OK: register it and update the state
    game.human_move(m)

    # Respond immediately with an autoplayer move
    # (can be a bit time consuming if rack has one or two blank tiles)
    if not game.state.is_game_over():
        game.autoplayer_move()

    if game.state.is_game_over():
        # If the game is now over, tally the final score
        game.state.finalize_score()

    # Return a state update to the client (board, rack, score, movelist, etc.)
    return jsonify(game.client_state())


@app.route("/submitmove", methods=['POST'])
def submitmove():
    """ Handle a move that is being submitted from the client """
    movelist = []
    if request.method == 'POST':
        # This URL should only receive Ajax POSTs from the client
        try:
            movelist = request.form.getlist('moves[]')
        except:
            pass
    # Process the movestring
    return _process_move(movelist)


@app.route("/userprefs", methods=['GET', 'POST'])
def userprefs():
    """ Handler for the user preferences page """

    user = User.current()
    if user is None:
        # User hasn't logged in yet: redirect to login page
        return redirect(users.create_login_url("/userprefs"))

    if request.method == 'POST':
        try:
            # Funny string addition below ensures that username is
            # a Unicode string under both Python 2 and 3
            nickname = u'' + request.form['nickname'].strip()
        except:
            nickname = u''
        if nickname:
            user.set_nickname(nickname)
            user.update()
            game = Game.current()
            if game is not None:
                game.set_human_name(nickname)
            return redirect(url_for("main"))
    return render_template("userprefs.html", user = user)


@app.route("/login", methods=['GET', 'POST'])
def login():
    """ Handler for the user login page """
    login_error = False
    if request.method == 'POST':
        try:
            # Funny string addition below ensures that username is
            # a Unicode string under both Python 2 and 3
            username = u'' + request.form['username'].strip()
        except:
            username = u''
        if username:
            # !!! TODO: Add validation of username here
            session['username'] = username
            return redirect(url_for("main"))
        login_error = True
    return render_template("login.html", err = login_error)


@app.route("/logout")
def logout():
    """ Handler for the user logout page """
    session.pop('username', None)
    return redirect(url_for("login"))


@app.route("/")
def main():
    """ Handler for the main (index) page """

    user = User.current()
    # if 'username' not in session:
    #    return redirect(url_for("login"))
    if user is None:
        # User hasn't logged in yet: redirect to login page
        return redirect(users.create_login_url("/"))

    game = Game.current()
    if game is not None and game.state.is_game_over():
        # Trigger creation of a new game if the previous one was finished
        game = None

    if game is None:
        # Create a fresh game for this user
        game = Game.new(user.nickname())

    return render_template("board.html", game = game, user = user)


@app.route("/help/")
def help():
    """ Show help page """
    return render_template("help.html")


@app.errorhandler(404)
def page_not_found(e):
    """ Return a custom 404 error """
    return u'Sorry, nothing at this URL', 404


@app.errorhandler(500)
def server_error(e):
    """ Return a custom 500 error """
    return u'Sorry, unexpected error: {}'.format(e), 500


# Run a default Flask web server for testing if invoked directly as a main program

if __name__ == "__main__":
    app.run(debug=True)
