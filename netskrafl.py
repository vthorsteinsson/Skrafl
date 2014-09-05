
""" Web server for netskrafl.appspot.com

    Author: Vilhjalmur Thorsteinsson, 2014

    This web server module uses the Flask framework to implement
    a crossword game similar to SCRABBLE(tm).

    The actual game logic is found in skraflplayer.py and
    skraflmechanics.py.

"""

from flask import Flask
from flask import render_template, redirect
from flask import request, session, url_for

import logging
import time

from skraflmechanics import Manager, State, Move, Error
from skraflplayer import AutoPlayer, AutoPlayer_MiniMax
from languages import Alphabet
import time
from random import randint

# Standard Flask initialization

app = Flask(__name__)
app.config['DEBUG'] = True # !!! TODO: Change to False for production deployment
app.secret_key = '\x03\\_,i\xfc\xaf=:L\xce\x9b\xc8z\xf8l\x000\x84\x11\xe1\xe6\xb4M'

manager = Manager()

# The current game state for different users
# !!! TODO: This will come from a database
games = dict()

class Game:
    """ A wrapper class for a particular game that is in process
        or completed. Contains inter alia a State instance.
    """

    def __init__(self):
        self.username = None
        self.state = None
        # Is the human player 0 or 1, where player 0 begins the game?
        self.player_index = 0
        # History of moves in this game so far
        self.moves = []

    def start_new(self, username):
        """ Start and initialize a new game """
        self.username = username
        self.state = State()
        self.player_index = randint(0, 1)
        self.state.set_player_name(self.player_index, username)
        self.state.set_player_name(1 - self.player_index, u"Netskrafl")
        # If AutoPlayer is first to move, generate the first move
        if self.player_index == 1:
            self.autoplayer_move()

    def autoplayer_move(self):
        """ Let the AutoPlayer make its move """
        apl = AutoPlayer(self.state)
        move = apl.generate_move()
        self.state.apply_move(move)
        self.moves.append(move)

    def human_move(self, move):
        self.state.apply_move(move)
        self.moves.append(move)

    def enum_tiles(self):
        """ Enumerate all tiles on the board in a convenient form """
        for x, y, t in self.state.board().enum_tiles():
            yield (u"ABCDEFGHIJKLMNO"[x] + str(y + 1), t, 0 if t == u' ' else Alphabet.scores[t])


def _process_move(movestring):
    """ Process a move from the client (the human player)
        Returns True if OK or False if the move was illegal
    """

    username = session['username']
    if not username or username not in games:
        return render_template("error.html")
    game = games[username]

    # Parse the move from the movestring we got back

    # Process the move string here
    if not game.state.check_legality(move):
        # Something was wrong with the rack
        # Show the user an error response page
        return render_template("error.html")

    game.human_move(move)

    # Respond immediately with an autoplayer move
    # (can be a bit time consuming if rack has one or two blank tiles)
    game.autoplayer_move()

    # Return a state update to the client (board, rack, score, movelist, etc.)
    return render_template("update.html", game = game)


@app.route("/submitmove", methods=['GET', 'POST'])
def submitmove():
    movestring = u''
    if request.method == 'POST':
        # A form POST, probably from the page itself
        try:
            movestring = unicode(request.form['moves'])
        except:
            movestring = u''
    else:
        # Presumably a GET: look at the URL parameters
        try:
            movestring = unicode(request.args.get('moves',''))
        except:
            movestring = u''
    # Process the movestring
    return _process_move(movestring)


@app.route("/login", methods=['GET', 'POST'])
def login():
    """ Handler for the user login page
    """
    login_error = False
    if request.method == 'POST':
        try:
            username = unicode(request.form['username']).strip()
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
    """ Handler for the user logout page
    """
    session.pop('username', None)
    return redirect(url_for("login"))


@app.route("/")
def main():
    """ Handler for the main (index) page
    """

    if 'username' not in session:
        # User hasn't logged in yet
        return redirect(url_for("login"))

    username = session['username']
    if username in games:
        game = games[username]
    else:
        # Create a fresh game for this user
        game = Game()
        game.start_new(username)
        games[username] = game

    return render_template("board.html", game = game)


@app.route("/help/")
def help():
    """ Show help page """
    return render_template("help.html")


# Run a default Flask web server for testing if invoked directly as a main program

if __name__ == "__main__":
    app.run(debug=True)
