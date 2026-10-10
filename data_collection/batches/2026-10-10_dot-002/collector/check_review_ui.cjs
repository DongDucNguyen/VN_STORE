const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=__dirname, html=fs.readFileSync(path.join(root,'review.html'),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const decode=s=>s.replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#x27;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
const cards=[...html.matchAll(/<article data-site="([^"]+)" data-group="([^"]+)">([\s\S]*?)<\/article>/g)].map(m=>({dataset:{site:m[1],group:m[2]},textContent:decode(m[3].replace(/<[^>]*>/g,' ')),hidden:false}));
const elements=Object.fromEntries(['q','g','s','count'].map(k=>[k,{value:'',textContent:'',addEventListener(){}}]));
const context=vm.createContext({document:{querySelector:k=>elements[k.slice(1)],querySelectorAll:()=>cards}});
vm.runInContext(script,context);
const visible=()=>cards.filter(c=>!c.hidden).length;
assert.equal(visible(),300);
for(const g of ['det-may','gom-su','may-tre-coi','go-son-mai','thuc-pham']){elements.g.value=g;vm.runInContext('filter()',context);assert.equal(visible(),60);}
elements.g.value='';elements.s.value='minhlong';vm.runInContext('filter()',context);assert.equal(visible(),60);
elements.s.value='';elements.q.value='binh hoa';vm.runInContext('filter()',context);assert.ok(visible()>0);
elements.q.value='ZZZZ_NON_EXISTENT_8293';vm.runInContext('filter()',context);assert.equal(visible(),0);
elements.q.value='';vm.runInContext('filter()',context);assert.equal(visible(),300);
const result={passed:true,cards:cards.length,checks:['all cards','five group filters','source filter','Vietnamese accent-insensitive search','empty result','reset'],limitation:'Tests embedded filter logic using DOM stubs; does not claim browser visual QA.'};
fs.writeFileSync(path.join(root,'review_ui_checks.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
