## Skraflhjálp (Scrabble Helper)

### English summary

This set of pure Python 2.7 programs and modules implements a word permutation
engine that is the core of an [Icelandic Scrabble Helper website](http://skraflhjalp.appspot.com).

The web and its engine are helpful for Scrabble players, crossword
enthusiasts and others - including programmers - who are interested in fast and
flexible dictionary lookup, for Icelandic and other languages.

The software uses a *DAWG* (*Directed Acyclic Word Graph*, also called
*Minimal Acyclic Finite State Automaton*, *MA-FSA*) to store the dictionary in a
compact - yet Pythonistic - text-based form for very fast lookup and permutation,
even of long letter sequences.

The algorithm for building an optimal DAWG from lists of valid words is based on the theory
of [Daciuk et al](http://www.aclweb.org/anthology/J00-1002.pdf), with reference
to [Steve Hanov's implementation](http://stevehanov.ca/blog/index.php?id=115)
(and a nod to [ftbe's Go code on GitHub](https://github.com/ftbe/dawg)).
However it optimizes further than Hanov does by collapsing chains of nodes connected by single
edges into multi-letter edges, reducing the node count significantly.

At run time, permutations are found in an efficient way, even in the presence of
wildcards (blank tiles), by direct traversal of the graph.
For details see the ```dawgbuilder.py``` and ```dawgdictionary.py``` files.

The code builds a 103,000 node DAWG for the Icelandic language, 2.6 million words, in about
160 seconds on a medium-powered Windows desktop PC. The resulting graph structure is stored
in a 3,466 KB file and takes under 4 seconds to load into memory.

For English, it converts the 178,691 words of the Scrabble Tournament World List v6 (TWL06)
into a graph of 29,691 nodes in under 10 seconds. The resulting .dawg.text file is 772 KB.

Generation of all permutations of a 7-letter Scrabble rack, as well as combinations of the
rack with one additional letter, typically takes 30-70 milliseconds.

### Íslenskt yfirlit

Vefur sem hjálpar skröflurum að finna orð í rekkanum og tengja þau við stafi sem fyrir eru.

Vefurinn er byggður á Python 2.7 og notar [Flask](http://flask.pocoo.org/)
undirforritasafnið, þar með talið [Jinja2](http://jinja.pocoo.org/) sniðmátakerfið (templates).

Hann notar [Bootstrap](http://getbootstrap.com/) CSS-safnið fyrir viðmót og þægilega aðlögun að
mismunandi skjám, þ.e. síma, spjaldtölvu eða borðtölvu.

Vefinn má nálgast á [http://skraflhjalp.appspot.com](http://skraflhjalp.appspot.com)

### Notkun vefsins
Ef farið er inn á vefslóðina / kemur upp aðalsíða Skraflhjálpar.
Slóðin /help gefur hjálparsíðu.

### Til að keyra á eigin tölvu
1. Settu upp [Python 2.7](https://www.python.org/download/releases/2.7.8/).

2. Sæktu þetta Git safn:

   ```
   git clone https://github.com/vthorsteinsson/skrafl.git
   ```

3. Sæktu undirforritasöfn inn á lib skráasafnið undir aðalmöppu Skraflhjálpar.
   Google App Engine getur aðeins notað undirforritasöfn sem geymd eru beint undir
   möppu viðkomandi verkefnis.

   ```
   cd skrafl
   pip install -r requirements.txt -t lib
   ```
4. Keyra má vefþjón Skraflhjálpar beint frá skipanalínu.
   Google App Engine:

   ```
   dev_appserver.py .
   ```

   Venjuleg Python 2.7 uppsetning:

   ```
   python skrafl.py
   ```

5. Nálgast má vefinn á vefrápara:

   Í skýinu á appspot.com [http://skraflhjalp.appspot.com](http://skraflhjalp.appspot.com)

   Á Google App Engine/Cloud SDK á eigin tölvu [http://localhost:8080](http://localhost:8080)
   
   Venjuleg Python 2.7 uppsetning með Flask/Werkzeug [http://localhost:5000](http://localhost:5000)

### Höfundur
Vilhjálmur Þorsteinsson

