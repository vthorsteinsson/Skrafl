""" Small word processor for the Skrafl application """

import locale
import encodings.iso8859_1

#locale.setlocale(locale.LC_ALL, 'Icelandic_Iceland') # Use Icelandic locale for string operations

infile_name = 'c:\\users\\user\\dropbox\\BIN\\smaord.txt'
outfile_name = 'c:\\users\\user\\dropbox\\BIN\\smaordalisti.txt'
#encoder = encodings.iso8859_1.Codec();
#banned = encoder.encode('.-/ABCDEFGHIJKLMNOPQRSTUVWXYZÞÆÖÐÁÉÍÓÚÝ')

print ("Beygingarlýsing íslensks nútímamáls, smáorð -> skraflgrunnur")

with open(infile_name, mode='r', encoding='iso8859-1') as fin :
    with open(outfile_name, mode='w', encoding='iso8859-1') as fout :
        for line in fin :
            # The lines end with a newline character
            if len(line) > 1 :
                fout.write(line.split(None, 1)[0] + '\n')

                
