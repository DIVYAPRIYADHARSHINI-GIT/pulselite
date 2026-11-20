import { useEffect, useState, type ReactNode } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { api, number, type Point, type Row } from './lib';

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    chart: <><path d="M3 3v18h18M6 15l5-6 4 3 6-8"/></>,
    shield: <><path d="M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/></>,
    globe: <><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></>,
    sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/></>,
    moon: <path d="M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10Z"/>,
    arrow: <path d="M5 12h14m-6-6 6 6-6 6"/>,
    down: <path d="M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4"/>,
    code: <path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/>,
    copy: <><rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    check: <path d="m5 12 4 4L19 6"/>,
    pulse: <path d="M2 12h5l3-8 5 16 3-8h4"/>,
    users: <><circle cx="9" cy="7" r="3"/><path d="M3 21v-4a6 6 0 0 1 12 0v4M16 4a3 3 0 0 1 0 6m2 4c3 1 3 3 3 7"/></>,
    page: <><path d="M5 2h9l5 5v15H5zM14 2v6h5M8 12h8m-8 4h6"/></>,
    logout: <><path d="M9 4H3v16h6m4-12 4 4-4 4m-6-4h14"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.chart}</svg>;
}
export function Logo() { return <Link className="logo" to="/" aria-label="PulseLite home"><span className="logo-mark"><Icon name="pulse" size={23}/></span>Pulse<span className="logo-lite">Lite</span></Link>; }
export function ThemeToggle() {
  const [dark, setDark] = useState(document.documentElement.dataset.theme === 'dark');
  function toggle() { const next = !dark; setDark(next); document.documentElement.dataset.theme = next ? 'dark' : 'light'; try { localStorage.setItem('pulselite-theme', next ? 'dark' : 'light'); } catch {} }
  return <button className="icon-button" onClick={toggle} aria-label={`Switch to ${dark ? 'light' : 'dark'} theme`}><Icon name={dark ? 'sun' : 'moon'}/></button>;
}
export function Header() { return <header className="public-header"><Logo/><nav aria-label="Main navigation"><Link to="/demo">Live demo</Link><Link to="/privacy" className="privacy-link">Our privacy promise</Link><ThemeToggle/><Link className="button secondary" to="/signin">Sign in</Link><Link className="button primary nav-cta" to="/signup">Get started <Icon name="arrow" size={16}/></Link></nav></header>; }
export function Shell({ children, demo = false }: { children: ReactNode; demo?: boolean }) {
  const location = useLocation();
  const [error, setError] = useState('');
  async function signout() { try { await api('/auth/signout', { method: 'POST' }); window.location.assign('/signin'); } catch(e) { setError((e as Error).message); } }
  return <div className="app-shell"><a href="#main" className="skip-link">Skip to main content</a><aside className="sidebar"><Logo/><div className="workspace-label">YOUR WORKSPACE</div><nav aria-label="Workspace"><NavLink to="/sites"><Icon name="grid"/> My websites</NavLink><NavLink to="/demo"><Icon name="chart"/> Demo analytics <span className="tiny-badge">DEMO</span></NavLink><NavLink to="/privacy"><Icon name="shield"/> Privacy</NavLink></nav><div className="sidebar-bottom"><div className="privacy-note"><Icon name="shield"/><strong>Small footprint.<br/>Clearer picture.</strong><p>No cookies. No cross-day tracking.</p></div>{!demo && <button onClick={signout} className="text-button"><Icon name="logout"/>Sign out</button>}<div className="version">PULSELITE <span>v1.0</span></div></div></aside><div className="app-content"><header className="app-top"><div className="breadcrumb">Workspace <span>/</span> <strong>{location.pathname.includes('install') ? 'Installation' : location.pathname === '/sites' ? 'My websites' : 'Analytics'}</strong></div><div className="top-actions"><span className="secure-label"><Icon name="shield" size={15}/> Privacy by design</span><ThemeToggle/><span className="avatar" aria-label="Workspace">P</span></div></header><main id="main" className="workspace-main">{error && <ErrorState message={error}/>} {children}</main><footer className="app-footer"><span>Less tracking. More understanding.</span><Link to="/privacy">How PulseLite handles data <span aria-hidden="true">↗</span></Link></footer></div></div>;
}
export function Loading() { return <div className="loading" role="status"><span className="spinner"/><h2>Finding your pulse…</h2><p>Bringing your latest analytics together.</p></div>; }
export function ErrorState({ message, retry }: { message: string; retry?: () => void }) { return <div className="error-state" role="alert"><strong>Let’s try that again.</strong><p>{message}</p>{retry && <button className="button secondary" onClick={retry}>Try again</button>}{message.includes('sign in') && <Link className="button primary" to="/signin">Sign in</Link>}</div>; }
export function useResource<T>(path: string, refresh = 0) {
  const [data, setData] = useState<T | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(true), [nonce, setNonce] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    async function load() { try { const result = await api<T>(path); if (active) { setData(result); setError(''); } } catch(e) { if(active) setError((e as Error).message); } finally { if(active) setLoading(false); } }
    load(); const interval = refresh ? window.setInterval(() => { if(!document.hidden) load(); }, refresh) : null;
    return () => { active = false; if(interval) clearInterval(interval); };
  }, [path, nonce, refresh]);
  return { data, error, loading, reload: () => setNonce(n => n + 1) };
}
export function Chart({ series }: { series: Point[] }) {
  const max = Math.max(...series.map(s => s.pageviews), 4);
  const W = 900, H = 215;
  const x = (i: number) => 48 + i * (W - 72) / Math.max(series.length - 1, 1);
  const y = (v: number) => H - 16 - v / max * (H - 40);
  const path = (key: 'visitors'|'pageviews') => series.map((s, i) => `${i ? 'L' : 'M'}${x(i)},${y(s[key])}`).join(' ');
  const visitorPath = path('visitors');
  return <div className="chart-wrap"><svg role="img" aria-label="Daily visitors and pageviews over the selected UTC date range" viewBox={`0 0 ${W} 255`} className="line-chart"><defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--accent)" stopOpacity=".16"/><stop offset="100%" stopColor="var(--accent)" stopOpacity="0"/></linearGradient></defs>{[0,1,2,3,4].map(i => <g key={i}><line x1="48" x2="878" y1={y(max*i/4)} y2={y(max*i/4)} stroke="var(--border)" strokeDasharray="3 5"/><text x="35" y={y(max*i/4)+4} textAnchor="end">{Math.round(max*i/4)}</text></g>)}{series.length > 0 && <><path d={`${visitorPath} L${x(series.length-1)},${H-16} L48,${H-16} Z`} fill="url(#chart-fill)"/><path d={path('pageviews')} stroke="var(--chart-secondary)" strokeDasharray="5 5" strokeWidth="2" fill="none"/><path d={visitorPath} stroke="var(--accent)" strokeWidth="3" fill="none" strokeLinejoin="round"/>{series.map((s,i) => <circle key={s.date} cx={x(i)} cy={y(s.visitors)} r={series.length < 9 ? 4 : 2.5} fill="var(--accent)"><title>{`${s.date}: ${s.visitors} daily visitors, ${s.pageviews} pageviews`}</title></circle>)}</>}{series.filter((_,i) => i === 0 || i === series.length-1 || i % Math.ceil(series.length/6) === 0).map(s => <text key={s.date} x={x(series.indexOf(s))} y="240" textAnchor={s === series[0] ? 'start' : s === series[series.length-1] ? 'end' : 'middle'}>{new Date(s.date+'T12:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'UTC'})}</text>)}</svg><details className="chart-data"><summary>View chart data as a table</summary><div className="table-scroll"><table><thead><tr><th>Date (UTC)</th><th>Daily visitors</th><th>Pageviews</th></tr></thead><tbody>{series.map(s => <tr key={s.date}><td>{s.date}</td><td>{s.visitors}</td><td>{s.pageviews}</td></tr>)}</tbody></table></div></details></div>;
}
export function Breakdown({ title, rows, total, onFilter, format = x => x, icon = 'chart' }: { title: string; rows: Row[]; total: number; onFilter?: (name: string) => void; format?: (name: string) => string; icon?: string }) {
  return <section className="panel breakdown"><div className="panel-title"><h2>{title}</h2><Icon name={icon} size={18}/></div><div className="table-heading"><span>{title === 'Top pages' ? 'PAGE PATH' : 'NAME'}</span><span>PAGEVIEWS</span></div>{rows.length ? rows.slice(0,7).map((row,i) => <div className="bar-row" key={row.name}><span className="bar-bg" style={{width: `${Math.max(2, row.pageviews / Math.max(total,1) * 100)}%`}}/><button className="row-name" title={`Filter by ${format(row.name)}`} onClick={() => onFilter?.(row.name)} disabled={!onFilter}><span className="row-index">{String(i+1).padStart(2,'0')}</span>{format(row.name)}</button><span className="row-number">{number(row.pageviews)}<small>{Math.round(row.pageviews / Math.max(total,1) * 100)}%</small></span></div>) : <p className="muted small">No pageviews in this selection.</p>}<div className="table-foot">{rows.length ? 'Select a row to filter your analytics' : 'Data will appear after your first visit'}</div></section>;
}