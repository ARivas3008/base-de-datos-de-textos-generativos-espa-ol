#!/usr/bin/env python3
"""Construye SQLite de corpus real. Las etiquetas son inferencias de spaCy, no reglas normativas."""
import argparse, collections as C, hashlib, json, math, re, sqlite3, unicodedata
from pathlib import Path
import spacy

ROOT=Path(__file__).resolve().parents[1]
CONTENT={"NOUN","PROPN","VERB","ADJ","ADV"}
WORD=re.compile(r"[^\W\d_]",re.UNICODE)
def norm(s): return unicodedata.normalize("NFC",s).casefold()
def fold(s): return "".join(c for c in unicodedata.normalize("NFD",s.casefold()) if not unicodedata.combining(c))
def ident(s): return hashlib.sha256(s.encode()).hexdigest()
def paragraphs(s):
    for m in re.finditer(r"\S[\s\S]*?(?=\n[ \t]*\n|\Z)",s):
        a,b=m.start(),m.end()
        while b-a>40000:
            end=s.rfind(" ",a+20000,a+40000)
            if end<0:end=a+40000
            yield a,s[a:end];a=end
        if s[a:b].strip():yield a,s[a:b]
def pg_check(a):
    p=ROOT/a["ruta_original"];h=p.read_text(encoding=a.get("codificacion_origen","utf-8-sig"))[:15000]
    h=re.split(r"\*\*\*\s*START",h,flags=re.I)[0]
    def field(k):
        m=re.search(r"(?im)^"+k+r":\s*(.+)",h);return fold(m.group(1)) if m else ""
    title,author,lang=field("Title"),field("Author"),field("Language")
    expected=set(re.findall(r"[a-z]{4,}",fold(a["titulo"])))-{"otros","obras","completas","mejores"}
    actual=set(re.findall(r"[a-z]{4,}",title))
    surname=fold(a["autor"]).split()[-1]
    if not title or surname not in author or "spanish" not in lang or (expected and len(expected&actual)/len(expected)<0.6):
        return False,f"Cabecera Gutenberg no coincide: {title} | {author} | {lang}"
    return True,"cabecera coincidente; comprobar edición"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--model",default="es_core_news_sm");ap.add_argument("--output",default="salida/espanol.sqlite");ap.add_argument("--limit",type=int);ap.add_argument("--batch-size",type=int,default=16);args=ap.parse_args()
    out=ROOT/args.output;out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    db=sqlite3.connect(tmp);db.executescript((ROOT/"bd/esquema.sql").read_text());db.execute("PRAGMA journal_mode=DELETE");db.execute("PRAGMA synchronous=NORMAL");db.execute("PRAGMA temp_store=FILE");db.execute("PRAGMA cache_size=-131072")
    nlp=spacy.load(args.model);nlp.max_length=100000
    assert all(x in nlp.pipe_names for x in ("parser","lemmatizer","morphologizer")),nlp.pipe_names
    report=json.loads((ROOT/"catalogo/resultado.json").read_text())
    rows=report["obras"]
    if args.limit:rows=rows[:args.limit]
    db.executemany("INSERT INTO metadata VALUES(?,?)",[("version","1"),("spacy",spacy.__version__),("modelo",args.model),("modelo_version",nlp.meta.get("version","")),("anotacion","automática; no normativa; susceptible a errores en español histórico"),("colocacion","lemas de contenido, ventana de cinco tokens hacia delante, sin cruzar oración"),("ngramas","formas normalizadas; no cruzan oración ni puntuación"),("particion","hash de autor normalizado; no dividir un mismo autor identificado entre particiones; alias requieren revisión")])
    caches={k:{} for k in ("forma","lema","morfologia")}
    def lookup(table,key):
        d=caches[table]
        if key in d:return d[key]
        i=len(d)+1;d[key]=i
        if table=="forma":db.execute("INSERT INTO forma VALUES(?,?,?)",(i,key,norm(key)))
        elif table=="lema":db.execute("INSERT INTO lema VALUES(?,?,?)",(i,*key))
        else:db.execute("INSERT INTO morfologia VALUES(?,?)",(i,key))
        return i
    def count_up(table,cols,key,frequency):
        marks=",".join("?" for _ in range(len(cols)+1));names=",".join(cols+["frecuencia"])
        db.executemany(f"INSERT INTO {table}({names}) VALUES({marks}) ON CONFLICT({','.join(cols)}) DO UPDATE SET frecuencia=frecuencia+excluded.frecuencia",((*k,v) for k,v in key.items() if v>=frequency))
    total=0
    for a in rows:
        if a["estado"]!="extraido":
            db.execute("INSERT INTO cuarentena VALUES(?,?)",(a["id"],a.get("error","No extraído")));continue
        status="fuente fijada por hash; revisión bibliográfica pendiente"
        if a["formato"]=="gutenberg":
            ok,status=pg_check(a)
            if not ok:
                db.execute("INSERT INTO cuarentena VALUES(?,?)",(a["id"],status));continue
        raw=(ROOT/a["ruta_txt"]).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=a["sha256_txt"]:raise ValueError("Hash no coincide "+a["id"])
        s=raw.decode("utf-8");oid=a["id"];author=a["autor"];bucket=int(ident(fold(author))[:8],16)%100
        split="train" if bucket<80 else "dev" if bucket<90 else "test"
        db.execute("INSERT INTO obra VALUES(?,?,?,?,?,?,?,?,?,?,?)",(oid,author,a["titulo"],a.get("pais"),a.get("genero"),a.get("anio"),a["url_fuente"],a["sha256_txt"],len(s),split,status))
        fc,lc,flex,ng,relations,coll,dist=C.Counter(),C.Counter(),C.Counter(),C.Counter(),C.Counter(),C.Counter(),C.Counter()
        sc=0;pun=C.Counter();dialog=0;patterns=C.Counter();examples={}
        pars=paragraphs(s)
        def inputs():
            for pi,(start,p) in enumerate(pars):
                pid=db.execute("INSERT INTO parrafo(obra_id,orden,inicio,fin,texto) VALUES(?,?,?,?,?)",(oid,pi,start,start+len(p),p)).lastrowid
                yield p,(pid,start)
        for doc,(pid,start) in nlp.pipe(inputs(),as_tuples=True,batch_size=args.batch_size):
            for si,sent in enumerate(doc.sents):
                toks=list(sent);nw=sum(bool(WORD.search(t.text)) and not t.is_punct and not t.is_space for t in toks)
                if not toks:continue
                pospat=" ".join(t.pos_ for t in toks if not t.is_space)
                deppat=" ".join(t.dep_ for t in toks if not t.is_space)
                sid=db.execute("INSERT INTO oracion(parrafo_id,orden,inicio,fin,texto,patron_pos,patron_dep,n_palabras) VALUES(?,?,?,?,?,?,?,?)",(pid,si,start+sent.start_char,start+sent.end_char,sent.text,pospat,deppat,nw)).lastrowid
                sc+=1;dialog+=int(sent.text.lstrip().startswith(("—","–","-")))
                for k in (("POS",pospat),("DEP",deppat)):
                    if 2<=len(toks)<=40:patterns[k]+=1;examples.setdefault(k,sid)
                infos=[];data=[];construct=[]
                for i,t in enumerate(toks):
                    f=lookup("forma",t.text);l=lookup("lema",(norm(t.lemma_ or t.text),t.pos_));m=lookup("morfologia",str(t.morph))
                    word=int(bool(WORD.search(t.text)) and not t.is_punct and not t.is_space);h=t.head.i-sent.start
                    if not 0<=h<len(toks):raise ValueError("Dependencia fuera de oración")
                    data.append((sid,i,f,l,m,t.tag_,t.dep_,h,start+t.idx,start+t.idx+len(t.text),word,t.whitespace_))
                    infos.append((t,l,word))
                    if word:fc[f]+=1;lc[l]+=1;flex[l,f,m]+=1
                    else:pun[t.text]+=1
                    if t.dep_ in ("nsubj","obj","iobj","ccomp","xcomp","advcl","acl","acl:relcl","obl","aux:pass","expl:pass"):
                        construct.append((t.dep_,sid,min(i,h),max(i,h),"dependencia UD inferida"))
                    if t.pos_ in ("VERB","AUX") and t.morph.get("VerbForm")==["Fin"]:
                        construct.append(("verbo_finito",sid,i,i,"VerbForm=Fin"))
                    if t.dep_ in ("amod","det") and t.head.pos_ in ("NOUN","PROPN"):
                        for feature in ("Gender","Number"):
                            x,y=t.morph.get(feature),t.head.morph.get(feature)
                            if x and y:
                                label="concordancia_"+feature+("_coincide" if set(x)&set(y) else "_discrepa")
                                construct.append((label,sid,min(i,h),max(i,h),"comparación de rasgos inferidos; no diagnóstico normativo"))
                db.executemany("INSERT INTO token VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",data)
                db.executemany("INSERT OR IGNORE INTO construccion VALUES(?,?,?,?,?)",construct)
                db.executemany("INSERT OR IGNORE INTO entidad VALUES(?,?,?,?,?)",((sid,start+e.start_char,start+e.end_char,e.label_,e.text) for e in sent.ents))
                run=[]
                for i,(t,l,word) in enumerate(infos):
                    if word:
                        run.append(norm(t.text))
                        for k in (2,3):
                            if len(run)>=k:ng[k," ".join(run[-k:])]+=1
                        h=t.head.i-sent.start
                        if h!=i and infos[h][2]:relations[infos[h][1],l,t.dep_]+=1
                        if t.pos_ in CONTENT:
                            for j in range(i+1,min(i+6,len(infos))):
                                u,r,w=infos[j]
                                if w and u.pos_ in CONTENT:
                                    pair=tuple(sorted((l,r)));coll[pair]+=1;dist[pair]+=j-i
                    elif not t.is_space:run=[]
        db.executemany("INSERT INTO frecuencia_forma VALUES(?,?,1) ON CONFLICT(forma_id) DO UPDATE SET frecuencia=frecuencia+excluded.frecuencia,obras=obras+1",fc.items())
        db.executemany("INSERT INTO frecuencia_lema VALUES(?,?,1) ON CONFLICT(lema_id) DO UPDATE SET frecuencia=frecuencia+excluded.frecuencia,obras=obras+1",lc.items())
        db.executemany("INSERT INTO frecuencia_obra VALUES(?,?,?)",((oid,l,v) for l,v in lc.items()))
        count_up("flexion",["lema_id","forma_id","morfologia_id"],flex,1)
        count_up("ngrama",["n","secuencia"],ng,1)
        count_up("relacion",["cabeza_lema","dependiente_lema","dep"],relations,1)
        db.executemany("INSERT INTO colocacion VALUES(?,?,?,?) ON CONFLICT(lema_a,lema_b) DO UPDATE SET distancia_media=(distancia_media*frecuencia+excluded.distancia_media*excluded.frecuencia)/(frecuencia+excluded.frecuencia),frecuencia=frecuencia+excluded.frecuencia",((*k,v,dist[k]/v) for k,v in coll.items()))
        db.executemany("INSERT INTO patron VALUES(?,?,?,?) ON CONFLICT(tipo,secuencia) DO UPDATE SET frecuencia=frecuencia+excluded.frecuencia",((*k,v,examples[k]) for k,v in patterns.items()))
        w=sum(fc.values());db.execute("INSERT INTO estilo_obra VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(oid,w,len(fc),len(lc),sc,w/max(sc,1),len(fc)/max(w,1),pun[","],pun["."],pun["?"]+pun["¿"],pun["!"]+pun["¡"],pun["—"]+pun["–"],dialog/max(sc,1)))
        total+=w;db.commit();print(json.dumps({"obra":oid,"palabras":w,"acumuladas":total},ensure_ascii=False),flush=True)
    db.execute("DELETE FROM ngrama WHERE frecuencia<2");db.execute("DELETE FROM colocacion WHERE frecuencia<2");db.execute("DELETE FROM relacion WHERE frecuencia<2");db.execute("DELETE FROM patron WHERE frecuencia<2")
    db.executescript("CREATE INDEX idx_token_lema ON token(lema_id,oracion_id); CREATE INDEX idx_token_forma ON token(forma_id,oracion_id); CREATE INDEX idx_forma_normalizada ON forma(normalizada); CREATE INDEX idx_lema_texto ON lema(lema); CREATE INDEX idx_ng_freq ON ngrama(n,frecuencia DESC); CREATE INDEX idx_construccion_tipo ON construccion(tipo,oracion_id); CREATE INDEX idx_parrafo_obra ON parrafo(obra_id); CREATE INDEX idx_oracion_parrafo ON oracion(parrafo_id);")
    db.execute("CREATE VIRTUAL TABLE concordancia_fts USING fts5(texto,content='oracion',content_rowid='id',tokenize='unicode61 remove_diacritics 0')")
    db.execute("INSERT INTO concordancia_fts(concordancia_fts) VALUES('rebuild')")
    db.commit()
    assert db.execute("PRAGMA quick_check").fetchone()[0]=="ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchone()
    assert total==db.execute("SELECT coalesce(sum(frecuencia),0) FROM frecuencia_forma").fetchone()[0]
    assert total==db.execute("SELECT coalesce(sum(n_palabras),0) FROM oracion").fetchone()[0]
    counts={t:db.execute("SELECT count(*) FROM "+t).fetchone()[0] for t in ("obra","parrafo","oracion","token","forma","lema","morfologia","flexion","entidad","ngrama","colocacion","relacion","patron","construccion","cuarentena")}
    stats={"integridad":"ok","modelo":nlp.meta.get("version"),"palabras":total,"tablas":counts,"cuarentena":db.execute("SELECT * FROM cuarentena").fetchall(),"particiones":db.execute("SELECT particion,count(*) FROM obra GROUP BY particion").fetchall(),"formas_mas_frecuentes":db.execute("SELECT superficie,frecuencia FROM v_lexico ORDER BY frecuencia DESC LIMIT 30").fetchall(),"lemas_mas_frecuentes":db.execute("SELECT lema,pos,frecuencia FROM v_lemas ORDER BY frecuencia DESC LIMIT 30").fetchall()}
    db.close();tmp.replace(out);stats["bytes_sqlite"]=out.stat().st_size
    (out.parent/"informe.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(stats,ensure_ascii=False),flush=True)
    if not counts["obra"]:raise ValueError("Sin obras válidas")
if __name__=="__main__":main()
