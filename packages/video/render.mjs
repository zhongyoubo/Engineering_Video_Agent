import { bundle } from '@remotion/bundler';
import { openBrowser, renderMedia, renderStill, selectComposition } from '@remotion/renderer';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = resolve(process.argv[2] || '.');
const props = JSON.parse(readFileSync(resolve(directory, 'props.json'), 'utf8'));
if (
  !Number.isInteger(props.total_frames) ||
  props.total_frames < 1 ||
  props.total_frames > 30 * 3600
)
  throw Error('Invalid frame count');
const root = dirname(fileURLToPath(import.meta.url));
const serveUrl = await bundle({
  entryPoint: resolve(root, 'src/index.tsx'),
  publicDir: resolve(directory, 'public'),
});
const browserExecutable = process.env.CHROME_EXECUTABLE || undefined;
const browser = await openBrowser('chrome', { browserExecutable });
try {
  const composition = await selectComposition({
    serveUrl,
    id: 'ExplainerVideo',
    inputProps: props,
    puppeteerInstance: browser,
    browserExecutable,
  });
  const thumbnail = await selectComposition({
    serveUrl,
    id: 'PublicationThumbnail',
    inputProps: props,
    puppeteerInstance: browser,
    browserExecutable,
  });
  await renderStill({
    serveUrl,
    composition: thumbnail,
    inputProps: props,
    puppeteerInstance: browser,
    browserExecutable,
    frame: 0,
    output: resolve(directory, 'cover.png'),
    imageFormat: 'png',
  });
  let last = -1;
  await renderMedia({
    serveUrl,
    composition,
    inputProps: props,
    puppeteerInstance: browser,
    browserExecutable,
    codec: 'h264',
    crf: 21,
    pixelFormat: 'yuv420p',
    audioCodec: 'aac',
    audioBitrate: '192k',
    concurrency: Number(process.env.RENDER_CONCURRENCY || 2),
    outputLocation: resolve(directory, 'video.mp4'),
    onProgress: (p) => {
      const next = Math.floor(p.progress * 10);
      if (next !== last) {
        last = next;
        console.log(`render ${next * 10}%`);
      }
    },
  });
} finally {
  await browser.close({ silent: true });
}
