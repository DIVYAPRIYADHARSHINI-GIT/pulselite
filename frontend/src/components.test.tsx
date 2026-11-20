import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { Breakdown, Chart, ErrorState, Icon, Loading } from './components';

describe('accessible analytics components', () => {
  it('loading announces a status, not a fabricated metric', () => {
    const html = renderToStaticMarkup(<Loading/>);
    expect(html).toContain('role="status"');
    expect(html).toContain('Finding your pulse');
  });
  it('errors are escaped and announced', () => {
    const html = renderToStaticMarkup(<MemoryRouter><ErrorState message={'<script>untrusted</script>'}/></MemoryRouter>);
    expect(html).toContain('role="alert"');
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;script&gt;');
  });
  it('sign-in errors offer a real sign-in link', () => {
    const html = renderToStaticMarkup(<MemoryRouter><ErrorState message="Please sign in to continue"/></MemoryRouter>);
    expect(html).toContain('href="/signin"');
  });
  it('charts expose exact values in an alternative semantic table', () => {
    const html = renderToStaticMarkup(<Chart series={[{date:'2026-11-20',visitors:3,pageviews:5}]}/>);
    expect(html).toContain('<table>');
    expect(html).toContain('<td>3</td>');
    expect(html).toContain('<td>5</td>');
    expect(html).toContain('role="img"');
  });
  it('empty and zero charts never create NaN coordinates', () => {
    for (const series of [[], [{date:'2026-11-20',visitors:0,pageviews:0}]]) {
      const html = renderToStaticMarkup(<Chart series={series}/>);
      expect(html).not.toContain('NaN');
      expect(html).not.toContain('Infinity');
    }
  });
  it('empty breakdown tells the truth', () => {
    const html = renderToStaticMarkup(<Breakdown title="Devices" rows={[]} total={0}/>);
    expect(html).toContain('No pageviews in this selection');
  });
  it('decorative icons do not create unlabeled screen-reader noise', () => {
    expect(renderToStaticMarkup(<Icon name="shield"/>)).toContain('aria-hidden="true"');
  });
});