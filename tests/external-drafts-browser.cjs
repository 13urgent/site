const{chromium}=require('playwright');const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{
 const source=fs.readFileSync(__dirname+'/../index.html','utf8');assert(!source.includes('externalImportForm'));assert(!source.includes('B2PWeb'));assert(!source.includes('Rubiwin'));assert(!source.includes('Budget d\'achat interne'));assert(!source.includes('src="imports.js"'));
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});const p=await b.newPage();await p.route('**/*',route=>route.abort());
 await p.setContent(source.replace(/<script\b[^>]*>[\s\S]*?<\/script>/g,''));assert.equal(await p.locator('#externalImportForm').count(),0);assert.equal(await p.locator('#externalDrafts').count(),0);
 let requests=0;p.on('request',()=>requests++);const before=requests;await p.addScriptTag({content:fs.readFileSync(__dirname+'/../imports.js','utf8')});assert.equal(requests,before);
 assert.equal(await p.locator('#adminDialog').count(),0);await b.close();console.log('PASS : formulaire/budgets/imports absents du HTML public, ancien module neutre, aucune requête externe, administration séparée du HTML public');
})().catch(e=>{console.error(e);process.exit(1)});
