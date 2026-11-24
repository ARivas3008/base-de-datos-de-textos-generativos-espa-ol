// Motor experimental: no requiere dependencias externas (Node.js 18+).
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
function generar(docs,seed=27,modo="narrativo"){
 const words=s=>s.normalize("NFC").toLowerCase().match(/\p{L}+/gu)||[];
 const sources=docs.map(d=>({id:d.id,normal:" "+words(d.text).join(" ")+" "}));
 let state=seed>>>0;
 const random=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296};
 const bank={momento:["Al caer la tarde","Al amanecer","A la mañana siguiente","Al anochecer"],viajero:["el viajero","el forastero","el caminante"],llegada:["llegó al pueblo","entró en la aldea","volvió a la ciudad","llegó a la ciudad","llegó a la plaza"],sitio:["la calle","la plaza","el camino"],sonido:["el rumor del viento","el ruido de los pasos","el canto de los pájaros","el murmullo del agua","el ruido del agua"],objeto:["una carta","un recuerdo","una promesa"],sustantivo:["el silencio","la soledad","la esperanza","la memoria"],paisaje:["los árboles","las montañas","los campos","las casas"],luz:["la luz del día","la luz del sol","la claridad del día"],verbo:["recordó","comprendió","pensó"],cierre:["volver a empezar","seguir adelante","esperar un poco más"],reflexion:["la memoria","la experiencia","el tiempo"],virtud:["la paciencia","la prudencia","la esperanza"]};
 const counts=new Map();
 const evidence=v=>{if(!counts.has(v)){const p=" "+words(v).join(" ")+" ";const list=[];for(const d of sources){let from=0,c=0;while((from=d.normal.indexOf(p,from))!==-1){c++;from+=Math.max(1,p.length-1)}if(c)list.push({obra:d.id,frecuencia:c})}counts.set(v,list)}return counts.get(v)};
 const freq=e=>e.reduce((s,y)=>s+y.frecuencia,0);
 const choose=(key,trace)=>{let a=bank[key].map(v=>({v,e:evidence(v)})).filter(x=>x.e.length).map(x=>({...x,tipo:"expresión contigua",w:Math.sqrt(freq(x.e))}));if(!a.length){a=bank[key].map(v=>({v,e:words(v).map(p=>({palabra:p,fuentes:evidence(p)}))})).filter(x=>x.e.every(y=>y.fuentes.length)).map(x=>({...x,tipo:"combinación de palabras observadas",w:Math.sqrt(Math.min(...x.e.map(y=>freq(y.fuentes))))}));}if(!a.length)throw Error("Sin candidatos observados: "+key);let r=random()*a.reduce((s,x)=>s+x.w,0);let x=a.find(x=>(r-=x.w)<0)||a.at(-1);trace.push({slot:key,expresion:x.v,tipo:x.tipo,evidencia:x.e});return x.v};
 const cap=s=>s[0].toUpperCase()+s.slice(1);
 const frames={
 narrativo:p=>{const m=p("momento"),v=p("viajero"),l=p("llegada"),s=p("sitio"),a=p("sonido"),o=p("objeto"),verb=p("verbo"),c=p("cierre");return `${m}, ${v} ${l}. Se detuvo un instante para mirar ${s} y escuchó ${a}. Llevaba consigo ${o} que le impedía olvidar lo sucedido. Mientras buscaba un lugar donde descansar, ${verb} que aún estaba a tiempo de ${c}.`;},
 descriptivo:p=>{const l=p("luz"),a=p("paisaje"),s=p("sonido"),v=p("sustantivo");return `${cap(l)} se extendía sobre ${a}. Apenas se distinguía ${s} entre los demás sonidos del lugar. Todo parecía inmóvil, como si ${v} hubiera ocupado hasta el último rincón. Poco a poco, el paisaje fue adquiriendo una expresión distinta.`;},
 reflexivo:p=>{const v=p("reflexion"),a=p("virtud"),c=p("cierre");return `${cap(v)} no nos devuelve aquello que hemos perdido, pero nos enseña a mirar de otro modo lo que todavía poseemos. Hay momentos en que ${a} vale más que cualquier certeza. No siempre es posible cambiar lo sucedido; lo que sí podemos hacer es aprender a ${c}.`;}
 };
 if(!frames[modo])throw Error("Modo desconocido");
 for(let attempt=0;attempt<100;attempt++){const trace=[];const texto=frames[modo](key=>choose(key,trace));const t=words(texto);let overlap=false;for(let i=0;i+8<=t.length&&!overlap;i++){const p=" "+t.slice(i,i+8).join(" ")+" ";overlap=sources.some(d=>d.normal.includes(p));}if(!overlap)return {texto,modo,semilla:seed,metodo:"plantillas redactadas + expresiones o palabras atestiguadas, selección ponderada por raíz de frecuencia; no es un LLM",obras_analizadas:docs.length,coincidencia_8_palabras:false,evidencias:trace};}
 throw Error("No se encontró una salida sin coincidencias de 8 palabras");
}
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const cat=JSON.parse(fs.readFileSync(path.join(root,'catalogo/resultado.json'),'utf8'));
const args=process.argv.slice(2);const modo=args[0]||'narrativo';const seed=Number(args[1]||27);if(!Number.isSafeInteger(seed))throw Error('Semilla entera requerida');
const only=args.includes('--piloto')?new Set(["conha-nh0001","conha-nh0002","conha-nh0011","conha-nh0017","conha-nh0027","conha-nh0035","conha-nh0005","oro-prosa-07"]):null;
const docs=cat.obras.filter(a=>a.estado==='extraido'&&a.formato!=='gutenberg'&&(!only||only.has(a.id))).map(a=>({id:a.id,text:fs.readFileSync(path.join(root,a.ruta_txt),'utf8')}));
console.log(JSON.stringify(generar(docs,seed,modo),null,2));
