# -*- coding: utf-8 -*-
""" Small word processor for the Skrafl application

    This code is written for Python 3

"""

import codecs
import locale
import functools
import os.path

def run():
    """ Read input file in iso8859-1, sort it using Icelandic sort order and output it in utf-8 """

    print("Beygingarlýsing íslensks nútímamáls, smáorð -> skraflgrunnur")

    locale.setlocale(locale.LC_ALL, 'isl') # Use Icelandic locale for string operations

    relpath = "resources"
    fname = "smaord"

    infile_name = os.path.abspath(os.path.join(relpath, fname + ".txt"))
    outfile_name = os.path.abspath(os.path.join(relpath, fname + ".sorted.txt"))

    print("Inntak úr {0}".format(infile_name))
    print("Úttak í {0}".format(outfile_name))

    keyfunc = functools.cmp_to_key(locale.strcoll)
    wordlist = []

    with codecs.open(infile_name, mode='r', encoding='iso8859-1') as fin:
        for line in fin:
            if not line:
                continue
            if line[:-1] == '\n':
                line = line[0:-1]
            elif line[:-2] == '\r\n':
                line = line[0:-2]
            if not line:
                continue
            wordlist.append(line.split(' ')[0])

    print("Raða {0} orðum".format(len(wordlist)))
    wordlist.sort(key=keyfunc)

    print("Skrifa úttak")
    with codecs.open(outfile_name, mode='w', encoding='utf-8') as fout :
        for word in wordlist:
            fout.write(word + '\n')

    print("Vinnslu lokið")
