#!/usr/bin/env python3
"""Exporta texto y anotaciones en JSONL separados por autor para preparación de modelos."""
import argparse, json, sqlite3
from pathlib import Path
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="salida/espanol.sqlite");p.add_argument("--out",default="salida/dataset");p.add_argument("--max-chars",type=int,default=3000);a=p.parse_args()
    if a.max_chars<200:raise ValueError("max-chars debe ser >=200")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(a.db);db.row_factory=sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    files={k:(out/(k+".jsonl")).open("w",encoding="utf-8") for k in ("train","dev","test")}
    counts={k:0 for k in files}
    current=None;parts=[];size=0
    def flush():
        nonlocal parts,size
        if not parts:return
        first=parts[0];last=parts[-1];sp=first["particion"]
        obj={"obra_id":first["obra_id"],"autor":first["autor"],"titulo":first["titulo"],"pais":first["pais"],"genero":first["genero"],"fuente":first["fuente"],"sha256":first["sha256"],"inicio":first["inicio"],"fin":last["fin"],"oraciones":[x["id"] for x in parts],"texto":"\n".join(x["texto"] for x in parts),"patrones_pos":[x["patron_pos"] for x in parts],"patrones_dep":[x["patron_dep"] for x in parts]}
        files[sp].write(json.dumps(obj,ensure_ascii=False)+"\n");counts[sp]+=1
        parts=[];size=0
    q="""SELECT o.id obra_id,o.autor,o.titulo,o.pais,o.genero,o.fuente,o.sha256,o.particion,s.id,s.inicio,s.fin,s.texto,s.patron_pos,s.patron_dep FROM obra o JOIN parrafo p ON p.obra_id=o.id JOIN oracion s ON s.parrafo_id=p.id ORDER BY o.id,p.orden,s.orden"""
    try:
        for r in db.execute(q):
            if current!=r["obra_id"] or size+len(r["texto"])+1>a.max_chars:flush()
            current=r["obra_id"];parts.append(r);size+=len(r["texto"])+1
        flush()
    finally:
        for f in files.values():f.close()
        db.close()
    (out/"manifest.json").write_text(json.dumps({"fragmentos":counts,"limites":"Las oraciones individuales largas se conservan; los separadores son de exportación. Alias y obras duplicadas deben revisarse antes de evaluar."},indent=2,ensure_ascii=False)+"\n")
    print(counts)
if __name__=="__main__":main()
