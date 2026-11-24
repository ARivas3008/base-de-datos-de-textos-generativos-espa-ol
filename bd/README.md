# Base de datos lingüística del español
## Objetivo
Construir un corpus documentado para generación textual, búsqueda de concordancias, aprendizaje de patrones lingüísticos, investigación de estilo y preparación de conjuntos de datos. No es una gramática prescriptiva ni un diccionario semántico completo. Las etiquetas de spaCy constituyen inferencias automáticas y requieren validación humana especialmente en textos antiguos.

## Reproducir
Python 3.11 recomendado.
```bash
python -m pip install -r requirements.txt
python -m pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl
python scripts/extraer_corpus.py
python scripts/construir_bd.py
```
Salida: salida/espanol.sqlite e informe.json. En GitHub Actions se publican como artefacto; el informe y los textos normalizados se guardan en main. Si se emplea --limit, el resultado es piloto, no corpus completo. No se debe comparar la cuenta anterior de palabras (regex) con la nueva sin considerar tokenización.

## Consultas
```sql
-- Formas exactas, conservando tildes y mayúsculas
SELECT * FROM v_lexico ORDER BY frecuencia DESC LIMIT 100;
-- Formas verbales y rasgos de conjugación
SELECT * FROM v_verbos WHERE lema='amar' ORDER BY frecuencia DESC;
-- Concordancias documentadas
SELECT autor,titulo,texto,superficie,rasgos,dep FROM v_concordancias WHERE lema='tierra' LIMIT 20;
-- Búsqueda de frase
SELECT o.texto FROM concordancia_fts f JOIN oracion o ON o.id=f.rowid WHERE concordancia_fts MATCH '"amor de"' LIMIT 30;
-- Construcciones gramaticales
SELECT c.tipo,o.texto,c.criterio FROM construccion c JOIN oracion o ON o.id=c.oracion_id WHERE c.tipo='acl:relcl' LIMIT 20;
-- Colocaciones por frecuencia (ventana de cinco tokens, no equivalen a locuciones normativas)
SELECT * FROM v_colocaciones WHERE lema_a='tierra' OR lema_b='tierra' ORDER BY frecuencia DESC LIMIT 30;
-- Secuencias para generación probabilística
SELECT secuencia,frecuencia FROM ngrama WHERE n=3 AND secuencia LIKE 'en la %' ORDER BY frecuencia DESC LIMIT 30;
-- Distribución por fuente
SELECT pais,genero,count(*) FROM obra GROUP BY pais,genero;
```

## Controles
- Fuente original fijada a un hash Git cuando está disponible; texto normalizado con SHA-256.
- Cuarentena de registros Gutenberg cuya cabecera no corresponde al título, autor o idioma del catálogo; no se aceptan por el solo ID.
- Índices y claves foráneas, quick_check, conciliación de frecuencias con las oraciones.
- Las posiciones son offsets Unicode del TXT normalizado (no bytes ni posiciones de una edición impresa).
- Etiquetas UD y rasgos morfológicos anotados automáticamente; no se inventan definiciones, sinónimos, etimologías, significados o reglas RAE. Se pueden agregar fuentes autorizadas y revisión experta posteriormente.
- Separación train/dev/test por hash de autor identificado; resolver alias y validar solapamientos entre obras y variantes antes de usar para evaluación formal.
- No eliminar arcaísmos ni dialectos del texto original; tratar discrepancias de concordancia como candidatos a revisar, no errores literarios.
- Fraseología, colocaciones y patrones recurrentes son candidatos estadísticos y no pruebas de corrección normativa.
- Los ngramas y estadísticas globales incluyen todos los subconjuntos; para evaluar un modelo, calcularlos solamente con train.
- El corpus histórico no representa todo el español contemporáneo ni todas las variedades.

## Estructura
- catalogo/obras-150.json: inventario de partida.
- corpus/original: ediciones digitales.
- corpus/txt: texto preparado.
- bd/esquema.sql: esquema y vistas.
- scripts/construir_bd.py: anotación, conteos, integridad.
- salida/: bases e informes locales (las bases grandes se distribuyen por artefacto).
