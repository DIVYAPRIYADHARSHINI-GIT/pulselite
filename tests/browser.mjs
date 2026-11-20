import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { randomBytes } from 'node:crypto';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = process.env.TEST_FRONTEND || 'http://localhost:5173';
const collector = process.env.TEST_BACKEND || 'http://localhost:8000';
const demo = process.env.TEST_DEMO || 'http://localhost:4174';
const label = process.env.TEST_LABEL || 'local';
const run = new Date().toISOString().replaceAll(/[:.]/g,'-');
const results = [], consoleErrors = [], failedRequests = [], audits = [];
const email = `chrome-test-${Date.now()}@pulselite.test`;
const password = randomBytes(24).toString('base64url');
await mkdir(path.join(root,'screenshots'),{recursive:true});
await mkdir(path.join(root,'bugs'),{recursive:true});
await mkdir(path.join(root,'tests/.tmp/chrome'),{recursive:true});
const browser = await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,env:{...process.env,TMPDIR:path.join(root,'tests/.tmp/chrome')}});
const context = await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'light',permissions:['clipboard-read','clipboard-write'],acceptDownloads:true});
context.setDefaultTimeout(15000);
context.setDefaultNavigationTimeout(20000);
const page = await context.newPage();
let siteId;
function observe(p) {
  p.on('pageerror', e=>consoleErrors.push(e.message));
  p.on('console', m=>{if(m.type()==='error')consoleErrors.push(m.text());});
  p.on('requestfailed', r=>{if(!r.failure()?.errorText.includes('ERR_ABORTED'))failedRequests.push({url:r.url().split('?')[0],error:r.failure()?.errorText});});
}
observe(page);
async function screenshot(name,p=page){const prefix=label==='local'?'':label+'-';await p.screenshot({path:path.join(root,'screenshots',`${prefix}${name}.png`),fullPage:true,animations:'disabled'});if(/dashboard|mobile|live-view/.test(name))await p.screenshot({path:path.join(root,'screenshots',`${prefix}${name}-viewport.png`),fullPage:false,animations:'disabled'});}
async function check(name,fn){let timer;try{await Promise.race([fn(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('45-second check watchdog elapsed')),45000);})]);results.push({name,pass:true});console.log(`PASS ${name}`);}catch(e){results.push({name,pass:false,error:String(e.message)});await page.screenshot({path:path.join(root,'bugs',`${run}-${results.length}-failure.png`),fullPage:true,timeout:5000}).catch(()=>{});await writeFile(path.join(root,'bugs',`${run}-${results.length}-failure.txt`),`${name}\n${e.stack}\n`);console.log(`FAIL ${name}: ${e.message}`);throw e;}finally{clearTimeout(timer);}}
function assert(value,message){if(!value)throw new Error(message);}
async function metric(name,value){await page.getByTestId(name).filter({hasText:new RegExp(`^${value}$`)}).waitFor({state:'visible'});}
async function settle(p=page){await p.waitForLoadState('networkidle');await p.locator('.loading').waitFor({state:'hidden'}).catch(()=>{});}
async function audit(label,p=page){const a=await new AxeBuilder({page:p}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();audits.push({label,violations:a.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({html:n.html,summary:n.failureSummary}))}))});assert(a.violations.length===0,`${label}: ${a.violations.length} accessibility violations: ${a.violations.map(v=>v.id).join(', ')}`);}
async function noOverflow(p=page){assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), 'Horizontal overflow detected');}
try{
 await check('Home renders original identity and illustrative preview',async()=>{await page.goto(base);await settle();assert(await page.getByRole('heading',{name:/Your traffic/}).isVisible(),'Home heading missing');await screenshot('01-home');await audit('home-desktop-light');await noOverflow();});
 await check('Keyboard skip link reaches main content',async()=>{await page.keyboard.press('Tab');assert(await page.getByRole('link',{name:'Skip to main content'}).evaluate(el=>el===document.activeElement),'Skip link not first focus target');await page.keyboard.press('Enter');assert(await page.evaluate(()=>location.hash==='#main'),'Skip navigation did not target main');});
 await check('Signup page and accessibility',async()=>{await page.goto(base+'/signup');await settle();await screenshot('02-signup');await audit('signup-desktop-light');});
 await check('Real signup establishes HTTP-only owner session',async()=>{await page.getByLabel('Email address').fill(email);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Create your account'}).click();await page.waitForURL('**/sites');await settle();const cookies=await context.cookies();const session=cookies.find(c=>c.name==='pulselite_session');assert(session?.httpOnly,'No HTTP-only session');assert(session.secure===base.startsWith('https:'),'Cookie Secure flag does not match deployment mode');await page.getByLabel('Website name').waitFor({state:'visible'});assert(!await page.evaluate(()=>document.cookie.includes('pulselite_session')),'Cookie accessible to JS');await screenshot('03-sites-empty');await audit('sites-empty');});
 await check('Owner adds exact-origin test website',async()=>{await page.getByLabel('Website name').fill('CHROME TEST · Form & Field');await page.getByLabel('Website origin').fill(demo);await page.getByRole('button',{name:'Add website',exact:true}).click();await page.waitForURL('**/install');await settle();siteId=Number(page.url().match(/sites\/(\d+)/)[1]);await page.getByRole('button',{name:'Copy snippet'}).waitFor({state:'visible'});await screenshot('04-snippet');await audit('snippet');});
 let key;
 await check('Snippet copy button copies real public key',async()=>{await page.getByRole('button',{name:'Copy snippet'}).click();const copied=await page.evaluate(()=>navigator.clipboard.readText());assert(copied.includes('/api/tracker.js')&&copied.includes('defer'),'Incorrect copied snippet');key=copied.match(/data-site="([^"]+)"/)[1];assert(key.length>=20,'Invalid public key');});
 await check('Unvisited website has install-oriented empty state',async()=>{await page.getByRole('link',{name:'Open dashboard',exact:true}).click();await settle();await page.getByRole('heading',{name:'Ready when your visitors are.'}).waitFor({state:'visible'});await screenshot('05-empty-dashboard');await audit('empty-dashboard');});
 await check('Real demo installation sends no cookies and strips URL secrets',async()=>{
   console.log('Demo diagnostic: creating visitor browser context');
   const visitor=await browser.newContext({viewport:{width:1440,height:1000},userAgent:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'});
   console.log('Demo diagnostic: context created; setting test-only cookie');
   // Explicit test-only marker proves omission even when a cookie exists for the collector host.
   await visitor.addCookies([{name:'pulselite_cookie_probe',value:'test-marker-not-a-secret',url:collector}]);
   visitor.setDefaultTimeout(15000);
   console.log('Demo diagnostic: cookie set; opening sample website');
   const sample=await visitor.newPage();observe(sample);await sample.goto(demo);await sample.getByLabel('Public site key').fill(key);await sample.getByLabel('Collector address').fill(collector);
   console.log('Demo diagnostic: form filled; connecting tracker');
   const networkPromise=Promise.all([sample.waitForRequest(r=>r.url().includes('/api/event/')&&r.method()==='POST'),sample.waitForResponse(r=>r.url().includes('/api/event/')&&r.request().method()==='POST')]);
   await sample.getByRole('button',{name:'Connect tracker'}).click();const [request,response]=await networkPromise;
   console.log('Demo diagnostic: collector request and response received');
   console.log('Demo diagnostic: reading complete network headers');
   const headers=await request.allHeaders();
   console.log('Demo diagnostic: complete headers returned; no Cookie or Referer');
   assert(!headers.cookie,'Collector received a cookie');assert(!headers.referer,'Collector received full Referer header');assert(response.status()===202,'Collector rejected real demo request');
   // Chrome keepalive response-body inspection stalls in this harness. Actual
   // acceptance is proven by the subsequent owner dashboard's SQL-backed counts,
   // rather than weakening the test to accept HTTP 202 alone (bots also get 202).
   console.log('Demo diagnostic: checking payload/storage; acceptance verified in dashboard next');
   const payload=request.postDataJSON();assert(payload.path==='/'&&!JSON.stringify(payload).includes('site='),'Tracker leaked URL query');assert(await sample.evaluate(()=>localStorage.length===0&&sessionStorage.length===0),'Tracker wrote browser storage');
   console.log('Demo diagnostic: privacy assertions passed; screenshot/navigation next');
   await screenshot('06-demo-site-connected',sample);await sample.getByRole('link',{name:'Journal',exact:true}).click();await sample.waitForLoadState('networkidle');await visitor.close();
 });
 await check('Dashboard receives real views and approximate visitor count',async()=>{await page.getByRole('button',{name:'Refresh analytics'}).click();await metric('pageviews',2);await metric('visitors',1);await screenshot('07-real-dashboard');await audit('real-dashboard');});
 await check('Live view displays actual last-five-minute visitor',async()=>{await page.getByRole('button',{name:'Open live view'}).click();assert(await page.getByText('1 active visitor',{exact:true}).isVisible(),'Live visitor missing');await screenshot('08-live-view');});
 await check('CSV export downloads real aggregated data',async()=>{const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export CSV'}).click();const download=await downloadPromise;const dest=path.join(root,'reports',`test-export-${run}.csv`);await download.saveAs(dest);const csv=await readFile(dest,'utf8');assert(csv.includes('daily_unique_visitors')&&csv.includes('/journal'),'Export lacks actual data');assert(!csv.includes('visitor_hash')&&!csv.includes('user_agent'),'Export leaked identifiers');await screenshot('09-export');});
 await check('Page filter and preset date ranges update actual query results',async()=>{await page.getByLabel('Filter by page').fill('/journal');await page.getByRole('button',{name:'Apply',exact:true}).click();await metric('pageviews',1);await page.getByRole('button',{name:'Clear filters',exact:true}).click();for(const n of ['1','7','30']){await page.getByLabel('Date range',{exact:true}).selectOption(n);await metric('pageviews',2);}});
 await check('Populated sites list and sign-out/sign-in journey',async()=>{await page.getByRole('link',{name:'My websites',exact:true}).click();await page.getByRole('heading',{name:'CHROME TEST · Form & Field'}).waitFor({state:'visible'});await screenshot('10-sites-populated');await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.waitForURL('**/signin');await page.getByLabel('Email address').fill(email);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL('**/sites');await settle();});
 await check('Synthetic demo is clearly labelled and SQL-backed',async()=>{await page.goto(base+'/demo');await settle();assert(await page.getByText('DEMO DATA',{exact:true}).isVisible(),'Demo label missing');assert(Number((await page.getByTestId('pageviews').textContent()).replaceAll(',',''))>0,'Seed data absent');await screenshot('11-dashboard-light');await audit('demo-desktop-light');});
 await check('Direct referrer filter works after regression fix',async()=>{const ref=page.locator('section.breakdown').filter({has:page.getByRole('heading',{name:'Top referrers',exact:true})});await ref.getByRole('button',{name:/Direct/}).click();await settle();assert(new URL(page.url()).searchParams.get('referrer')==='Direct','Direct filter not set');assert(Number((await page.getByTestId('pageviews').textContent()).replaceAll(',',''))>0,'Direct filter returned no data');await page.getByRole('button',{name:'Clear filters',exact:true}).click();await settle();});
 await check('Desktop dark theme is persistent and accessible',async()=>{await page.getByRole('button',{name:'Switch to dark theme'}).click();await page.reload();await settle();assert(await page.locator('html').getAttribute('data-theme')==='dark','Theme did not persist');await screenshot('12-dashboard-dark');await audit('demo-desktop-dark');await noOverflow();});
 await check('Mobile dashboard layout and dark accessibility',async()=>{await page.setViewportSize({width:390,height:844});await noOverflow();await screenshot('13-mobile-dark');await audit('demo-mobile-dark');});
 await check('Mobile light dashboard and keyboard filters',async()=>{await page.getByRole('button',{name:'Switch to light theme'}).click();await noOverflow();await screenshot('14-mobile-light');await audit('demo-mobile-light');await page.getByLabel('Filter by page').focus();await page.keyboard.type('/work');await page.keyboard.press('Enter');await settle();assert(new URL(page.url()).searchParams.get('page')==='/work','Keyboard filtering failed');});
 await check('Mobile home and privacy content are accessible',async()=>{await page.goto(base);await settle();await screenshot('15-home-mobile');await noOverflow();await audit('home-mobile-light');await page.goto(base+'/privacy');await settle();await screenshot('16-privacy-mobile');await noOverflow();await audit('privacy-mobile-light');});
 await check('No unexpected console errors or network failures',async()=>{assert(consoleErrors.length===0,`Console errors: ${consoleErrors.join('; ')}`);assert(failedRequests.length===0,`Failed requests: ${JSON.stringify(failedRequests)}`);});
}catch{}
finally{
 const report={run,browser:'Installed Google Chrome, headless',base,account:email,siteId,siteName:'CHROME TEST · Form & Field',passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length,results,audits,consoleErrors,failedRequests};
 await writeFile(path.join(root,'reports',`browser-${run}.json`),JSON.stringify(report,null,2));
 if(report.failed||consoleErrors.length||failedRequests.length)await writeFile(path.join(root,'bugs',`${run}-browser-diagnostic.json`),JSON.stringify(report,null,2));
 console.log(`Browser checks: ${report.passed} passed, ${report.failed} failed. ${audits.length} axe audits attempted. Test account: ${email}; site id: ${siteId || 'not created'}.`);
 await browser.close();
 process.exitCode=report.failed||consoleErrors.length||failedRequests.length?1:0;
}