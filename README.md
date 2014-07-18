## Skraflhjálp (Scrabble Helper)

Vefur sem hjálpar skröflurum að finna orð í rekkanum og tengja þau við stafi sem fyrir eru.

Vefurinn er byggður á Python 2.7 og notar [Flask](http://flask.pocoo.org/)
undirforritasafnið, þar með talið [Jinja2](http://jinja.pocoo.org/) sniðmátakerfið (templates).

Hann notar [Bootstrap](http://getbootstrap.com/) CSS-safnið fyrir viðmót og þægilega aðlögun að
mismunandi skjám, þ.e. síma, spjaldtölvu eða borðtölvu.

Vefinn má nálgast á [http://skraflhjalp.appspot.com](http://skraflhjalp.appspot.com)

## Notkun vefsins
Ef farið er inn á vefslóðina / kemur upp aðalsíða Skraflhjálpar.
Slóðin /help gefur hjálparsíðu.

## Til að keyra á eigin tölvu
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

## Höfundur
Vilhjálmur Þorsteinsson
