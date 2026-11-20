const params = new URLSearchParams(location.search);
const site = params.get('site');
const api = params.get('api') || 'http://localhost:8000';
if (site && /^[A-Za-z0-9_-]{20,40}$/.test(site)) {
  let valid = false;
  try { const url = new URL(api); valid = url.protocol === 'https:' || (url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname)); } catch {}
  if (valid) {
    // This constructs exactly the script tag shown on PulseLite's install page.
    const tracker = document.createElement('script');
    tracker.src = new URL('/api/tracker.js', api).href;
    tracker.dataset.site = site;
    tracker.defer = true;
    document.head.appendChild(tracker);
    document.querySelector('#status').textContent = 'Tracker connected. Explore a page to generate another visit.';
    document.querySelector('#key').value = site;
    document.querySelector('#api').value = api;
    document.querySelectorAll('a[href^="/"]').forEach(link => link.href += '?' + params.toString());
  }
}
document.querySelector('#connect').addEventListener('submit', event => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  location.search = new URLSearchParams({ site: String(data.get('site')), api: String(data.get('api')) }).toString();
});