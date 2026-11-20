import {marked} from 'marked';
import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const markdown=await readFile(path.join(root,'FINAL_REPORT.md'),'utf8');
const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><base href="${pathToFileURL(root+'/').href}"><title>PulseLite — Final Report</title><style>
@page{size:A4;margin:18mm 17mm 20mm}body{font:11px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#203538;margin:0}h1{font-size:36px;line-height:1.15;letter-spacing:-1px;color:#08776b;margin-top:30px}h2{font-size:22px;border-top:2px solid #08776b;padding-top:14px;margin-top:35px;break-after:avoid}h3{font-size:14px;margin-top:22px;break-after:avoid}p,li{orphans:3;widows:3}a{color:#08776b;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:10px;margin:16px 0}th{background:#e7f4ef;text-align:left}td,th{padding:8px;border:1px solid #d7e5df;vertical-align:top}tr{break-inside:avoid}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f6f5;padding:12px;font-size:9px}code{font-size:10px}img{max-width:100%;max-height:185mm;display:block;object-fit:contain;margin:12px auto 5px;border:1px solid #e0e8e7;border-radius:5px}p:has(img){break-inside:avoid;break-after:avoid}p:has(img)+p{font-size:9px;color:#536967;margin-top:5px;break-before:avoid}blockquote{padding:10px 16px;border-left:3px solid #08776b;background:#f0f7f4;margin:20px 0}hr{border:0;border-top:1px solid #d7e5df;margin:25px 0}.pagebreak,h2:last-of-type{break-before:page}
</style></head><body>${marked.parse(markdown)}</body></html>`;
const htmlPath=path.join(root,'reports/FINAL_REPORT.html');await writeFile(htmlPath,html);
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,env:{...process.env,TMPDIR:path.join(root,'tests/.tmp/chrome')}});
const page=await browser.newPage();await page.goto(pathToFileURL(htmlPath).href,{waitUntil:'networkidle'});
const broken=await page.locator('img').evaluateAll(images=>images.filter(i=>!i.complete||!i.naturalWidth).map(i=>i.getAttribute('src')));
if(broken.length)throw new Error('Report contains missing images: '+broken.join(', '));
await page.pdf({path:path.join(root,'FINAL_REPORT.pdf'),format:'A4',printBackground:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="font:8px Arial;width:100%;margin:0 17mm;color:#607175">PulseLite · Verified build report · 20 November 2026 <span style="float:right"><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',margin:{top:'18mm',bottom:'20mm',left:'17mm',right:'17mm'}});
console.log('PDF exported from the actual Markdown report; all referenced screenshots loaded.');await browser.close();