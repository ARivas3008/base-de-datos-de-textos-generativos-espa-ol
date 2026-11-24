#!/usr/bin/env python3
"""Materializa el catálogo fijado; no genera ni inventa texto."""
import csv, hashlib, json, re, sys, time, urllib.request, urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CAT = json.loads((ROOT / "catalogo/obras-150.json").read_text(encoding="utf-8"))
NS = {"t":"http://www.tei-c.org/ns/1.0"}
ORIG = ROOT / "corpus/original"
TXT = ROOT / "corpus/txt"
ORIG.mkdir(parents=True, exist_ok=True)
TXT.mkdir(parents=True, exist_ok=True)

def get(url):
    for i in range(3):
        try:
            req=urllib.request.Request(url, headers={"User-Agent":"Corpus-literario-es/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception:
            if i==2: raise
            time.sleep(2**i)

def gitsha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def atomic(path,data):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)

def tei_metadata(root):
    def val(p):
        e=root.find(p,NS)
        return " ".join("".join(e.itertext()).split()) if e is not None else ""
    return val(".//t:titleStmt/t:author"),val(".//t:titleStmt/t:title")

def tei_text(root):
    body=root.find(".//t:text/t:body",NS)
    if body is None: raise ValueError("TEI sin body")
    blocks={"p","head","l","speaker","stage","item","ab","quote","opener","closer","salute","signed"}
    def walk(node):
        tag=node.tag.rsplit("}",1)[-1]
        if tag in {"note","fw"}: return ""
        if tag=="lb": return "\n"
        s=node.text or ""
        for child in node:
            s+=walk(child)+(child.tail or "")
        if tag in blocks: s=s.strip()+"\n"+("" if tag=="l" else "\n")
        return s
    return walk(body).strip()

def pg_text(s):
    start=re.search(r"(?im)^\s*\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*",s)
    end=re.search(r"(?im)^\s*\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*",s)
    if not start or not end or start.end()>=end.start():
        raise ValueError("Marcadores Gutenberg ausentes; revisión manual")
    return s[start.end():end.start()].strip()

def process(a):
    record=dict(a)
    try:
        ext=".xml" if a["formato"]=="tei" else ".txt"
        orig=ORIG/(a["id"]+ext)
        if a["formato"]=="gutenberg":
            i=a["pg_id"]
            url=f"https://gutenberg.pglaf.org/cache/epub/{i}/pg{i}.txt"
        else: url=a["url_descarga"]
        b=orig.read_bytes() if orig.exists() else get(url)
        if a.get("sha_git_fuente") and gitsha(b)!=a["sha_git_fuente"]:
            b=get(url)
            if gitsha(b)!=a["sha_git_fuente"]: raise ValueError("SHA Git de origen no coincide")
        if not b or len(b)>10_000_000: raise ValueError("Tamaño inesperado")
        encoding="utf-8-sig"
        try: s=b.decode(encoding)
        except UnicodeDecodeError:
            if a.get("repositorio_fuente")!="Jero2760/estilometria": raise
            encoding="cp1252"
            s=b.decode(encoding)
        if "\x00" in s or "\ufffd" in s: raise ValueError("Caracteres inválidos")
        if a["formato"]=="tei":
            root=ET.fromstring(b)
            author,title=tei_metadata(root)
            record.update(autor=author or a["autor"],titulo=title or a["titulo"])
            s=tei_text(root)
        elif a["formato"]=="gutenberg":
            s=pg_text(s)
        elif a.get("tei_fuente"):
            try:
                path=urllib.parse.quote(a["tei_fuente"],safe="/")
                tei=get(f"https://raw.githubusercontent.com/{a['repositorio_fuente']}/{a['revision_fuente']}/{path}")
                au,ti=tei_metadata(ET.fromstring(tei))
                if au and ti: record.update(autor=au,titulo=ti,metadatos_abreviados=False)
            except Exception as exc: record["advertencia_metadatos"]=str(exc)
        elif s.lstrip().startswith("<"):
            raise ValueError("Posible HTML/XML en archivo TXT; requiere revisión")
        # Preservar palabras, acentos, puntuación y saltos de verso.
        clean=s.replace("\r\n","\n").replace("\r","\n").strip()+"\n"
        words=len(re.findall(r"[^\W\d_]+",clean,re.UNICODE))
        if words<500: raise ValueError("Texto demasiado breve para este catálogo")
        data=clean.encode("utf-8")
        dest=TXT/(a["id"]+".txt")
        atomic(orig,b)
        atomic(dest,data)
        record.update(estado="extraido",ruta_original=str(orig.relative_to(ROOT)),ruta_txt=str(dest.relative_to(ROOT)),sha256_original=hashlib.sha256(b).hexdigest(),sha256_txt=hashlib.sha256(data).hexdigest(),bytes_original=len(b),palabras=words,codificacion_origen=encoding,url_descarga_real=url)
    except Exception as exc:
        record.update(estado="error",error=str(exc))
    return record

def main():
    assert len(CAT["obras"])==150
    assert len({a["id"] for a in CAT["obras"]})==150
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows=list(pool.map(process,CAT["obras"]))
    ok=[a for a in rows if a["estado"]=="extraido"]
    hashes=[a["sha256_txt"] for a in ok]
    report={"objetivo":150,"extraidos":len(ok),"errores":150-len(ok),"duplicados_exactos":len(hashes)-len(set(hashes)),"palabras":sum(a["palabras"] for a in ok),"obras":rows,"limitaciones":"No equivale a cotejo página por página ni revisión legal global; comprobar los metadatos abreviados y elementos editoriales de cada edición."}
    (ROOT/"catalogo/resultado.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    columns=["id","autor","titulo","anio","pais","genero","idioma_original","derechos","estado","palabras","ruta_txt","sha256_txt","url_fuente","error"]
    with (ROOT/"catalogo/resultado.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore");w.writeheader();w.writerows(rows)
    print(json.dumps({k:v for k,v in report.items() if k!="obras"},ensure_ascii=False))
    for a in rows:
        if a["estado"]=="error": print(a["id"],a["error"],file=sys.stderr)
    return int(len(ok)!=150 or report["duplicados_exactos"]!=0)

if __name__=="__main__": sys.exit(main())
