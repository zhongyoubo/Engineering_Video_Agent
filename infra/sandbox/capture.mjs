import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {chromium} from 'playwright';

const [mode,entry]=process.argv.slice(2);
if(!entry||path.isAbsolute(entry)||entry.split(/[\\/]/).includes('..'))throw Error('Invalid entry');
const source=path.resolve('/source'),target=path.resolve(source,entry);
if(!target.startsWith(source+'/')||!fs.statSync(target).isFile())throw Error('Missing entry');
if(mode==='python-cli'){
  const proc=spawn('python3',['-I',target],{cwd:source,env:{PATH:'/usr/bin:/bin',HOME:'/tmp'},stdio:['ignore','pipe','pipe']});
  let text='',length=0;
  for(const stream of [proc.stdout,proc.stderr])stream.on('data',chunk=>{length+=chunk.length;
    if(length>1048576)proc.kill('SIGKILL');else text+=chunk.toString('utf8')});
  const code=await new Promise(r=>proc.on('exit',r));
  fs.writeFileSync('/output/result.json',JSON.stringify({exit_code:code,stdout:text.slice(-12000),entry,kind:'python-cli'}));
}else if(mode==='static-web'){
  const server=http.createServer((req,res)=>{
    let file;try{file=path.resolve(source,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname))}catch{res.writeHead(400).end();return}
    if(!file.startsWith(source+'/')){res.writeHead(403).end();return}
    const ext=path.extname(file),mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml'}[ext]||'application/octet-stream';
    try{res.setHeader('Content-Type',mime);res.end(fs.readFileSync(file))}catch{res.writeHead(404).end()}
  });
  await new Promise(r=>server.listen(8765,'127.0.0.1',r));
  const browser=await chromium.launch({args:['--no-sandbox','--disable-dev-shm-usage']});
  try{
    const ctx=await browser.newContext({viewport:{width:1720,height:900},recordVideo:{dir:'/output/raw',size:{width:1720,height:900}}});
    await ctx.route('**/*',route=>{const u=new URL(route.request().url());
      return u.hostname==='127.0.0.1'&&u.port==='8765'?route.continue():route.abort()});
    const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8765/'+entry,{waitUntil:'networkidle',timeout:30000});
    await page.screenshot({path:'/output/page.png'});
    // Conservative, explicit convention: only user-marked demo actions are automatically clicked.
    const actions=page.locator('[data-demo-action="click"]');let clicked=0;
    for(let i=0;i<Math.min(await actions.count(),3);i++){
      const action=actions.nth(i);if(await action.isVisible()){await action.click();clicked++;await page.waitForTimeout(600)}}
    await page.waitForTimeout(1500);await page.screenshot({path:'/output/page.png'});
    const video=page.video();await ctx.close();fs.copyFileSync(await video.path(),'/output/capture.webm');
    fs.writeFileSync('/output/result.json',JSON.stringify({exit_code:errors.length?1:0,kind:'static-web',entry,clicked,page_errors:errors}));
  }finally{await browser.close();server.close()}
}else throw Error('Unsupported runtime');

