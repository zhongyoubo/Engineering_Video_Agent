// Explicit fixed-fixture renderer only. Production rendering remains isolated.
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
const directory = resolve(process.argv[2]);
const props = {...JSON.parse(readFileSync(resolve(directory, 'props.json'), 'utf8')), width: 3840, height: 2160};
const serveUrl = await bundle({entryPoint: resolve('packages/video/src/index.tsx'), publicDir: resolve(directory, 'public')});
const browserExecutable = process.env.CHROME_EXECUTABLE;
const browser = await openBrowser('chrome', {browserExecutable});
try {
  const composition = await selectComposition({serveUrl, id: 'PublicationThumbnail', inputProps: props, browserExecutable, puppeteerInstance: browser});
  await renderStill({serveUrl, composition, inputProps: props, frame: 0, output: resolve(directory, 'cover-4k.png'), browserExecutable, puppeteerInstance: browser});
} finally { await browser.close({silent: true}); }
