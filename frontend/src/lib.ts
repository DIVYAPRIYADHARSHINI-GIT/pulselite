export const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
export const COLLECTOR = (import.meta.env.VITE_COLLECTOR_URL || 'http://localhost:8000').replace(/\/$/, '');
export type Site = { id: number; name: string; origin: string; site_key: string; respect_dnt: boolean; is_demo: boolean };
export type Row = { name: string; pageviews: number; visitors: number };
export type Point = { date: string; pageviews: number; visitors: number };
export type Stats = { site: Site; pageviews: number; visitors: number; live: number; previous: { visitors: number; pageviews: number }; series: Point[]; start: string; end: string; visitor_definition: string } & Record<'path'|'referrer'|'source'|'device'|'browser'|'country', Row[]>;
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(API + '/api' + path, { credentials: 'include', ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Something went wrong. Please try again.');
  }
  return response.status === 204 ? undefined as T : response.json();
}
export function utcRange(days: number, now = new Date()) {
  const end = now.toISOString().slice(0, 10);
  const start = new Date(end + 'T00:00:00Z');
  start.setUTCDate(start.getUTCDate() - days + 1);
  return { start: start.toISOString().slice(0, 10), end };
}
export function compare(current: number, previous: number) {
  if (!previous) return current ? 'New activity' : 'No change';
  const change = (current - previous) / previous * 100;
  return `${change > 0 ? '+' : ''}${change.toFixed(1)}%`;
}
export function snippet(site: Site) {
  return `<script defer src="${COLLECTOR}/api/tracker.js" data-site="${site.site_key}"${site.respect_dnt ? '' : ' data-dnt="allow"'}></script>`;
}
export function csvCell(value: string | number) {
  let text = String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}
export function demoCSV(data: Stats) {
  const rows: (string|number)[][] = [['dimension', 'value', 'pageviews', 'daily_unique_visitors']];
  data.series.forEach(r => rows.push(['date', r.date, r.pageviews, r.visitors]));
  (['path','referrer','source','device','browser','country'] as const).forEach(d => data[d].forEach(r => rows.push([d, r.name, r.pageviews, r.visitors])));
  return '\ufeff' + rows.map(r => r.map(csvCell).join(',')).join('\r\n');
}
export const number = (n: number) => new Intl.NumberFormat('en-US').format(n);
export const countryName = (code: string) => code === 'ZZ' ? 'Unknown' : ({ US:'United States',IN:'India',GB:'United Kingdom',DE:'Germany',CA:'Canada',AU:'Australia' }[code] || code);