// Explicit fixed-repository verification helper; never a production host fallback.
import { bundle } from '@remotion/bundler';
import { openBrowser, selectComposition, renderMedia, renderStill } from '@remotion/renderer';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
const project = resolve(process.argv[2]),
  out = resolve(process.argv[3]);
mkdirSync(out, { recursive: true });
const props = JSON.parse(readFileSync(resolve(project, 'props.json'), 'utf8'));
execFileSync(
  process.execPath,
  [
    resolve(project, 'node_modules/typescript/bin/tsc'),
    '--noEmit',
    '-p',
    resolve(project, 'tsconfig.json'),
  ],
  { stdio: 'inherit' },
);
const serveUrl = await bundle({
  entryPoint: resolve(project, 'src/index.tsx'),
  publicDir: resolve(project, 'public'),
  outDir: resolve(out, 'bundle'),
});
const browserExecutable = process.env.CHROME_EXECUTABLE || undefined;
const browser = await openBrowser('chrome', { browserExecutable });
try {
  const composition = await selectComposition({
    serveUrl,
    id: 'EngineeringVideo',
    inputProps: props,
    puppeteerInstance: browser,
    browserExecutable,
  });
  const frames = [0, 45, 89, 140, 1076, 1857, 2016, 2017, 2077, 2136];
  for (const frame of frames)
    await renderStill({
      serveUrl,
      composition,
      inputProps: props,
      puppeteerInstance: browser,
      browserExecutable,
      frame,
      output: resolve(out, `frame-${frame}.png`),
      imageFormat: 'png',
    });
  for (const [name, start, end] of [
    ['cover', 0, 89],
    ['outro', 2017, 2136],
  ]) {
    await renderMedia({
      serveUrl,
      composition,
      inputProps: props,
      puppeteerInstance: browser,
      browserExecutable,
      frameRange: [start, end],
      codec: 'h264',
      crf: 18,
      pixelFormat: 'yuv420p',
      concurrency: 2,
      outputLocation: resolve(out, `${name}.mp4`),
    });
    console.log(`${name}: ${end - start + 1} real 4K frames rendered`);
  }
  writeFileSync(
    resolve(out, 'result.json'),
    JSON.stringify({ ok: true, frames, bookends_rendered_frames: 210, reused_body_frames: 1927 }),
  );
} finally {
  await browser.close({ silent: true });
}
