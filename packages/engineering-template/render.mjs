import { bundle } from '@remotion/bundler';
import { openBrowser, selectComposition, renderStill, renderMedia } from '@remotion/renderer';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

// This file is platform-owned. Generated edits cannot replace it.
const project = resolve(process.argv[2] || '.');
const action = process.argv[3] || 'preview';
const output = resolve(process.argv[4] || project + '/output');
mkdirSync(output, { recursive: true });
const props = JSON.parse(readFileSync(resolve(project, 'props.json'), 'utf8'));
if (!Number.isInteger(props.total_frames) || props.total_frames < 1 || props.total_frames > 27000)
  throw Error('Invalid frame budget');
if (!existsSync(resolve(project, 'public/noto.otf'))) throw Error('Required Chinese font missing');
let browser;
try {
  execFileSync(
    process.execPath,
    [
      resolve(project, 'node_modules/typescript/bin/tsc'),
      '--noEmit',
      '-p',
      resolve(project, 'tsconfig.json'),
    ],
    { stdio: 'pipe', timeout: 60000 },
  );
  const serveUrl = await bundle({
    entryPoint: resolve(project, 'src/index.tsx'),
    publicDir: resolve(project, 'public'),
    outDir: resolve(output, 'bundle'),
  });
  if (action === 'build') {
    writeFileSync(
      resolve(output, 'result.json'),
      JSON.stringify({ protocol: '3.0', action, ok: true }),
    );
  } else {
    const browserExecutable = process.env.CHROME_EXECUTABLE || undefined;
    browser = await openBrowser('chrome', { browserExecutable });
    const composition = await selectComposition({
      serveUrl,
      id: 'EngineeringVideo',
      inputProps: props,
      puppeteerInstance: browser,
      browserExecutable,
    });
    if (action === 'preview') {
      const frames = [];
      for (const scene of props.scenes) {
        for (const ratio of [0.1, 0.45, 0.85]) {
          const frame =
            scene.start_frame + Math.min(scene.frames - 1, Math.floor(scene.frames * ratio));
          if (!frames.includes(frame)) frames.push(frame);
        }
      }
      const files = [];
      for (const frame of frames) {
        const name = `frame-${String(frame).padStart(6, '0')}.png`;
        await renderStill({
          serveUrl,
          composition,
          inputProps: props,
          puppeteerInstance: browser,
          browserExecutable,
          frame,
          output: resolve(output, name),
          imageFormat: 'png',
          timeoutInMilliseconds: 30000,
        });
        files.push({ name, frame });
      }
      writeFileSync(
        resolve(output, 'result.json'),
        JSON.stringify({ protocol: '3.0', action, ok: true, frames: files, font_required: true }),
      );
    } else if (action === 'final') {
      await renderMedia({
        serveUrl,
        composition,
        inputProps: props,
        puppeteerInstance: browser,
        browserExecutable,
        codec: 'h264',
        crf: 18,
        pixelFormat: 'yuv420p',
        audioCodec: 'aac',
        audioBitrate: '192k',
        concurrency: 2,
        outputLocation: resolve(output, 'video.mp4'),
      });
      writeFileSync(
        resolve(output, 'result.json'),
        JSON.stringify({ protocol: '3.0', action, ok: true, total_frames: props.total_frames }),
      );
    } else throw Error('Unknown tool action');
  }
} catch (error) {
  const detail = error.stdout ? error.stdout.toString() : String(error.stack || error);
  writeFileSync(
    resolve(output, 'result.json'),
    JSON.stringify({ protocol: '3.0', action, ok: false, diagnostic: detail.slice(-8000) }),
  );
  process.exitCode = 1;
} finally {
  if (browser) await browser.close({ silent: true });
}
