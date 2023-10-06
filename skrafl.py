"""

    Web server for SCRABBLE(tm) rack permutations

    Copyright (C) 2023 Miðeind ehf.
    Original author: Vilhjálmur Þorsteinsson

    This web server module uses the Flask framework to implement
    a simple form page where the user can enter a SCRABBLE(tm) rack
    and get a list of all legal word permutations from the rack,
    as well as combinations with a single additional letter.

    The actual permutation engine is found in skraflpermuter.py

    The server is compatible with 3.x, CPython and PyPy.

    Note: SCRABBLE is a registered trademark. This software or its author
    are in no way affiliated with or endorsed by the owners or licensees
    of the SCRABBLE trademark.

"""

from flask import Flask, render_template, request

import logging
import time

import skraflpermuter


# Standard Flask initialization

app = Flask(__name__)
app.config['DEBUG'] = False


def _process_rack(rack):
    """ Process a given input rack
        Returns True if OK or False if the rack was invalid, i.e. contains invalid letters
    """
    # Create a Tabulator to process the rack
    t = skraflpermuter.Tabulator()
    t0 = time.time()

    if not t.process(rack):
        # Something was wrong with the rack
        # Show the user an error response page
        return render_template("errorword.html", rack=rack)

    t1 = time.time()
    logging.info("Processed rack \"{0}\" in {1:.2f} seconds".format(rack, t1 - t0))

    # The rack was successfully processed and tabulated
    # Show the user a result page
    return render_template("result.html", result=t, rack="")


@app.route("/", methods=['GET', 'POST'])
def main():
    """ Handler for the main (index) page where the user enters a Scrabble rack.
    The page can be invoked via POST from itself, or by a GET, optionally with the
    rack parameter set, i.e. GET /?rack=xxx
    """
    rack = ""
    if request.method == 'POST':
        # A form POST, probably from the page itself
        try:
            rack = request.form['rack']
        except:
            rack = ""
    else:
        # Presumably a GET: look at the URL parameters
        try:
            rack = request.args.get('rack', '')
        except:
            rack = ""
    if rack:
        rack = rack[0:15]
        # We have something to do: process the entered rack
        # Currently we do not do anything useful with racks of more than 15 characters
        return _process_rack(rack)
    # If nothing to do, just show the main rack entry form
    return render_template("main.html", rack="")


@app.route("/help/")
def help():
    """ Show help page """
    return render_template("help.html", rack="")


# Run a default Flask web server for testing if invoked directly as a main program
if __name__ == "__main__":
    app.run(debug=True, port=3000, use_debugger=True, threaded=False, processes=1)
