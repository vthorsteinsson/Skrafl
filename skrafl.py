
""" Web server for Scrabble rack permutations

    Original author: Vilhjalmur Thorsteinsson, 2014

    This web server module uses the Flask framework to implement
    a simple form page where the user can enter a Scrabble rack
    and get a list of all legal word permutations from the rack,
    as well as combinations with a single additional letter.

    The actual permutation engine is found in skraflpermuter.py

"""

from flask import Flask
from flask import render_template
from flask import request

import logging

import skraflpermuter

# Standard Flask initialization

app = Flask(__name__)
app.config['DEBUG'] = True # !!! Remove this before public deployment

logging.info("Starting initialization of Referee")
_referee = skraflpermuter.Referee()
_referee.initialize()
logging.info("Completed initialization of Referee")

def _process_rack(rack):
    """ Process a given input rack
        Returns True if OK or False if the rack was invalid, i.e. contains invalid letters
    """
    # Create a Tabulator to process the rack
    t = skraflpermuter.Tabulator(_referee)
    if not t.process(rack):
       # Something was wrong with the rack
       # Show the user an error response page
       return render_template("errorword.html")
    # The rack was successfully processed and tabulated
    # Show the user a result page
    return render_template("result.html", result=t)

@app.route("/", methods=['GET', 'POST'])
def main():
    """ Handler for the main (index) page where the user enters a Scrabble rack.
    The page can be invoked via POST from itself, or by a GET, optionally with the
    rack parameter set, i.e. GET /?rack=xxx
    """
    rack = u''
    if request.method == 'POST':
        # A form POST, probably from the page itself
        try:
            rack = unicode(request.form['rack'])
        except:
            rack = u''
    else:
        # Presumably a GET: look at the URL parameters
        try:
            rack = unicode(request.args.get('rack',''))
        except:
            rack = u''
    if rack:
        # We have something to do: process the entered rack
        # Currently we do not do anything useful with racks of more than 7 characters
        rack = rack[0:7]
        return _process_rack(rack)
    # If nothing to do, just show the main rack entry form
    return render_template("main.html")

@app.route("/help/")
def help():
    """ Show help page """
    return render_template("help.html")

# Run a default Flask web server for testing if invoked directly as a main program

"""
if __name__ == "__main__":
    app.run(debug=True)
    
"""