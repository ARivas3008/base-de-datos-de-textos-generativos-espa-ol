#!/usr/bin/env python3
"""Índice léxico observado; no atribuye etiquetas gramaticales sin modelo."""
import sqlite3,json,re,hashlib,unicodedata,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"salida";OUT.mkdir(exist_ok=True)
p=OUT/"lexico.sqlite";p.unlink(missing_ok=True)
db=sqlite3.connect(p)
db.executescript("""PRAGMA foreign_keys=ON;
CREATE TABLE obra(id TEXT PRIMARY KEY,autor TEXT,titulo TEXT,pais TEXT,genero TEXT,fuente TEXT,sha256 TEXT,palabras INTEGER);
CREATE TABLE palabra(forma TEXT PRIMARY KEY,frecuencia INTEGER,obras INTEGER);
CREATE TABLE palabra_obra(obra TEXT REFERENCES obra(id),forma TEXT REFERENCES palabra(forma),frecuencia INTEGER,PRIMARY KEY(obra,forma)) WITHOUT ROWID;
CREATE TABLE ejemplo(forma TEXT REFERENCES palabra(forma),obra TEXT REFERENCES obra(id),inicio INTEGER,fin INTEGER,fragmento TEXT,PRIMARY KEY(forma,obra)) WITHOUT ROWID;
CREATE TABLE bigrama(secuencia TEXT PRIMARY KEY,frecuencia INTEGER);
CREATE TABLE metadata(clave TEXT PRIMARY KEY,valor TEXT);
INSERT INTO metadata VALUES('metodo','Tokenización regex Unicode, NFC + casefold; sin etiquetas morfosintácticas');
""")
report=json.loads((ROOT/"catalogo/resultado.json").read_text())
word=re.compile(r"[^\W\d_]+(?:[’'-][^\W\d_]+)*",re.UNICODE)
normalize=lambda t:unicodedata.normalize("NFC",t).casefold()
for a in report["obras"]:
    if a["estado"]!="extraido" or a["formato"]=="gutenberg":continue
    b=(ROOT/a["ruta_txt"]).read_bytes()
    assert hashlib.sha256(b).hexdigest()==a["sha256_txt"]
    text=b.decode("utf-8");counts=collections.Counter();first={};bi=collections.Counter();prev=None;end=0
    for m in word.finditer(text):
        w=normalize(m.group());counts[w]+=1;first.setdefault(w,(m.start(),m.end()))
        if prev and not re.search(r"[^\s]",text[end:m.start()]):bi[prev+" "+w]+=1
        prev=w;end=m.end()
    oid=a["id"];db.execute("INSERT INTO obra VALUES(?,?,?,?,?,?,?,?)",(oid,a["autor"],a["titulo"],a.get("pais"),a.get("genero"),a["url_fuente"],a["sha256_txt"],sum(counts.values())))
    db.executemany("INSERT INTO palabra VALUES(?,?,1) ON CONFLICT(forma) DO UPDATE SET frecuencia=frecuencia+excluded.frecuencia,obras=obras+1",counts.items())
    db.executemany("INSERT INTO palabra_obra VALUES(?,?,?)",((oid,w,c) for w,c in counts.items()))
    db.executemany("INSERT INTO ejemplo VALUES(?,?,?,?,?)",((w,oid,max(0,i-75),min(len(text),j+75),text[max(0,i-75):min(len(text),j+75)]) for w,(i,j) in first.items() if counts[w]>=5))
    db.executemany("INSERT INTO bigrama VALUES(?,?) ON CONFLICT(secuencia) DO UPDATE SET frecuencia=frecuencia+excluded.frecuencia",bi.items())
    db.commit()
db.execute("DELETE FROM bigrama WHERE frecuencia<2");db.execute("CREATE INDEX palabra_obra_forma ON palabra_obra(forma)")
db.commit();assert db.execute("PRAGMA quick_check").fetchone()[0]=="ok";assert not db.execute("PRAGMA foreign_key_check").fetchone()
total=db.execute("SELECT sum(palabras) FROM obra").fetchone()[0];assert total==db.execute("SELECT sum(frecuencia) FROM palabra").fetchone()[0]
stats={"integridad":"ok","palabras":total,"obras":db.execute("SELECT count(*) FROM obra").fetchone()[0],"formas":db.execute("SELECT count(*) FROM palabra").fetchone()[0],"bigramas_recurrentes":db.execute("SELECT count(*) FROM bigrama").fetchone()[0],"ejemplos":db.execute("SELECT count(*) FROM ejemplo").fetchone()[0],"top":db.execute("SELECT forma,frecuencia FROM palabra ORDER BY frecuencia DESC LIMIT 30").fetchall(),"exclusion":"Gutenberg pendiente de comprobación bibliográfica; 140 obras fijadas por hash."}
db.close();stats["bytes_sqlite"]=p.stat().st_size
(OUT/"informe_lexico.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(stats,ensure_ascii=False),flush=True)
