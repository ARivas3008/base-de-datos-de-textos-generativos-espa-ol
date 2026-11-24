// Generación argumentativa controlada; Node.js 18+.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
function ensayo(docs,seed=41){
 const words=s=>s.normalize("NFC").toLowerCase().match(/\p{L}+/gu)||[];
 const src=docs.slice().sort((a,b)=>a.id.localeCompare(b.id)).map(d=>({id:d.id,normal:" "+words(d.text).join(" ")+" "}));
 let x=seed>>>0;const rnd=()=>{x=(Math.imul(1664525,x)+1013904223)>>>0;return x/4294967296};
 const banks={
 perspectiva:["la experiencia","la reflexión","el conocimiento"],
 capacidad:["el entendimiento","el juicio","la razón"],
 inicio1:["En primer lugar","Por una parte","Ante todo"],
 inicio2:["Por otra parte","En segundo lugar","Asimismo"],
 contraste:["Sin embargo","No obstante","Con todo"],
 cierre:["En conclusión","En suma","Por consiguiente"],
 valores:["la prudencia","la libertad","la verdad"],
 actividad:["la lectura","el estudio","la observación"],
 dialogo:["las palabras","las opiniones","las ideas"]
 };
 const cache=new Map();
 const evidence=v=>{if(!cache.has(v)){let p=" "+words(v).join(" ")+" ";let rows=[];for(const d of src){let i=0,n=0;while((i=d.normal.indexOf(p,i))>=0){n++;i+=p.length-1}if(n)rows.push({obra:d.id,frecuencia:n});}cache.set(v,rows)}return cache.get(v)};
 const total=e=>e.reduce((a,b)=>a+b.frecuencia,0);
 for(let attempt=0;attempt<32;attempt++){
  let trace=[];
  const pick=k=>{const opts=banks[k].map(v=>({v,e:evidence(v)})).filter(o=>o.e.length).map(o=>({...o,w:Math.sqrt(total(o.e))}));if(!opts.length)throw Error("Sin expresión atestiguada: "+k);let r=rnd()*opts.reduce((a,b)=>a+b.w,0);const o=opts.find(o=>(r-=o.w)<0)||opts.at(-1);trace.push({funcion:k,expresion:o.v,frecuencia:total(o.e),fuentes:o.e});return o.v};
  const perspectiva=pick("perspectiva"), capacidad=pick("capacidad"),a=pick("inicio1"),b=pick("inicio2"),c=pick("contraste"),d=pick("cierre"),valor=pick("valores"),actividad=pick("actividad"),dialogo=pick("dialogo");
  const parrafos=[
`Leer no consiste solamente en reconocer las palabras que otro ha escrito. Quien se acerca a un libro entra en contacto con una manera de comprender el mundo que puede ser distinta de la suya. De ese encuentro nace la posibilidad de examinar las propias convicciones y de descubrir los límites de ${perspectiva}. Por ello, la lectura constituye un medio de formación del juicio propio, siempre que el lector no se contente con aceptar cuanto encuentra en las páginas.`,
`${a}, los libros amplían el horizonte de quien los lee. La vida de una persona está circunscrita a determinadas circunstancias, mientras que una obra literaria permite contemplar conflictos, aspiraciones y costumbres de otras épocas. Al reconocer en esas vidas problemas que también le conciernen, el lector advierte que sus preocupaciones no son exclusivamente individuales. Tal descubrimiento favorece el ejercicio de ${capacidad}, pues obliga a considerar otras explicaciones antes de formular una opinión definitiva.`,
`${b}, la literatura enseña a distinguir entre la apariencia de una afirmación y aquello que le sirve de fundamento. Un personaje puede defender una causa justa mediante razones equivocadas, del mismo modo que una conducta aparentemente generosa puede ocultar un interés particular. Examinar estas contradicciones ayuda a apreciar los matices de ${dialogo} y a comprender que una expresión convincente no equivale necesariamente a un argumento verdadero. En este sentido, ${actividad} contribuye a que la persona juzgue con mayor independencia.`,
`${c}, sería excesivo atribuir a los libros una virtud que depende también de quien los lee. Una persona puede conocer muchas obras y conservar intactos sus prejuicios si nunca somete sus opiniones a examen. El valor formativo de la literatura no reside, por tanto, en la cantidad de páginas recorridas, sino en la disposición para confrontar lo leído con los hechos y admitir que una convicción propia puede resultar insuficiente.`,
`${d}, la lectura adquiere su mayor significado cuando se convierte en una práctica de deliberación. No se trata de renunciar a las propias ideas para adoptar las de un escritor, sino de adquirir los medios necesarios para examinarlas con rigor. Así entendida, la literatura fortalece ${valor} y permite participar en la vida común con un juicio menos dependiente de las certezas ajenas.`
  ];
  const texto=parrafos.join("\n\n");const tokens=words(texto);let hits=[];for(let i=0;i+8<=tokens.length;i++){const p=" "+tokens.slice(i,i+8).join(" ")+" ";for(const s of src)if(s.normal.includes(p))hits.push({obra:s.id,secuencia:p.trim()});}if(!hits.length)return {titulo:"La lectura y la formación del juicio propio",tipo:"ensayo argumentativo",tema:"lectura y pensamiento crítico",semilla:seed,obras_analizadas:src.length,palabras:tokens.length,estructura:["introducción y tesis","argumento 1","argumento 2","contraargumento y respuesta","conclusión"],texto,coincidencias_8_palabras:0,metodo:"estructura argumentativa y proposiciones redactadas manualmente; expresiones seleccionadas del corpus por raíz de frecuencia; no demuestra que las obras sostengan las tesis",evidencias:trace};
 }
 throw Error("No fue posible generar ensayo sin coincidencias de ocho palabras");
}
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const cat=JSON.parse(fs.readFileSync(path.join(root,'catalogo/resultado.json'),'utf8'));
const pilot=new Set(["conha-nh0002","conha-nh0011","conha-nh0017","conha-nh0027","oro-prosa-07","oro-prosa-12","oro-prosa-13","oro-prosa-16","oro-prosa-17","oro-teatro-04"]);
const args=process.argv.slice(2);const seed=Number(args.find(x=>!x.startsWith('--'))||41);if(!Number.isSafeInteger(seed))throw Error('Semilla inválida');
const docs=cat.obras.filter(a=>a.estado==='extraido'&&a.formato!=='gutenberg'&&(!args.includes('--piloto')||pilot.has(a.id))).map(a=>({id:a.id,text:fs.readFileSync(path.join(root,a.ruta_txt),'utf8')}));
console.log(JSON.stringify(ensayo(docs,seed),null,2));
