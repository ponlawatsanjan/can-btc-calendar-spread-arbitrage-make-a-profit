const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const root = __dirname;
const types = { '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.json':'application/json; charset=utf-8', '.svg':'image/svg+xml' };
http.createServer((req,res)=>{
  let pathname;
  try{pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400).end();return;}
  const file=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
  if(!file.startsWith(root+path.sep)||pathname.split('/').some(p=>p.startsWith('.'))||!types[path.extname(file)]){res.writeHead(404).end('Not found');return;}
  fs.stat(file,(err,stat)=>{
    if(err||!stat.isFile()){res.writeHead(404).end('Not found');return;}
    const headers={'Content-Type':types[path.extname(file)],'Cache-Control':'no-cache','Vary':'Accept-Encoding'};
    const gzip=stat.size>1024&&/\bgzip\b/.test(req.headers['accept-encoding']||'');
    if(gzip)headers['Content-Encoding']='gzip';
    res.writeHead(200,headers);const stream=fs.createReadStream(file);stream.on('error',()=>res.destroy());
    if(gzip)stream.pipe(zlib.createGzip()).pipe(res);else stream.pipe(res);
  });
}).listen(5180,'127.0.0.1',()=>console.log('Research presentation (static, no Python needed): http://127.0.0.1:5180'));
