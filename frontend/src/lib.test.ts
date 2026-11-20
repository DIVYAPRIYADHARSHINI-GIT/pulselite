import { describe, expect, it } from 'vitest';
import { compare, csvCell, snippet, utcRange, countryName } from './lib';
describe('UTC date ranges', () => {
  it('today is inclusive', () => expect(utcRange(1, new Date('2026-11-20T04:00:00Z'))).toEqual({start:'2026-11-20',end:'2026-11-20'}));
  it('7 days cross the year boundary', () => expect(utcRange(7, new Date('2026-01-03T23:00:00Z'))).toEqual({start:'2025-12-28',end:'2026-01-03'}));
  it('30 days handles leap years', () => expect(utcRange(30, new Date('2024-03-01T00:00:00Z')).start).toBe('2024-02-01'));
  it('local timezone never shifts UTC day', () => expect(utcRange(1, new Date('2026-11-20T01:00:00+05:30')).end).toBe('2026-11-19'));
});
describe('comparison is honest', () => {
  it('zero baseline is new activity, not infinity', () => expect(compare(10,0)).toBe('New activity'));
  it('two zeroes is no change', () => expect(compare(0,0)).toBe('No change'));
  it('positive growth', () => expect(compare(120,100)).toBe('+20.0%'));
  it('negative growth', () => expect(compare(50,100)).toBe('-50.0%'));
});
describe('CSV safety and privacy-aware snippet', () => {
  it.each(['=SUM(A1:A2)','+cmd','-cmd','@cmd','\tcmd','\rcmd'])('neutralizes spreadsheet prefix %s', value => expect(csvCell(value)).toMatch(/^"'/));
  it('escapes commas and double quotes', () => expect(csvCell('a,"b"')).toBe('"a,""b"""'));
  it('uses defer and defaults to DNT', () => expect(snippet({id:1,name:'Test',origin:'https://test.test',site_key:'public-key',respect_dnt:true,is_demo:false})).not.toContain('data-dnt'));
  it('explicit override is represented in snippet', () => expect(snippet({id:1,name:'Test',origin:'https://test.test',site_key:'public-key',respect_dnt:false,is_demo:false})).toContain('data-dnt="allow"'));
  it('unknown country is not invented', () => expect(countryName('ZZ')).toBe('Unknown'));
});