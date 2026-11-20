import { readFile, writeFile } from 'node:fs/promises';
const source = await readFile(new URL('./tracker.js', import.meta.url));
if (source.byteLength >= 3000) throw new Error(`Tracker too large: ${source.byteLength} bytes`);
await writeFile(new URL('../backend/app/tracker.js', import.meta.url), source);
console.log(`Tracker built: ${source.byteLength} uncompressed bytes (< 3,000).`);