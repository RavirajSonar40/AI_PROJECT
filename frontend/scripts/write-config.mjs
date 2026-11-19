import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const apiUrl = process.env.API_URL || '/api';
const publicDir = fileURLToPath(new URL('../public/', import.meta.url));
await mkdir(publicDir, { recursive: true });
await writeFile(
  `${publicDir}/config.js`,
  `window.__env = ${JSON.stringify({ API_URL: apiUrl })};\n`,
  'utf8',
);
