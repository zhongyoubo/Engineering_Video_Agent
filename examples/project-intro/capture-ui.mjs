import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const root = process.cwd();
const dir = path.join(root, '.verify-project-intro/ui');
fs.mkdirSync(dir, { recursive: true });
const b = await chromium.launch({
  executablePath: process.env.CHROME_EXECUTABLE || chromium.executablePath(),
  args: ['--no-sandbox'],
  headless: true,
});
const context = await b.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  recordVideo: { dir, size: { width: 1920, height: 1080 } },
});
await context.request.post('http://127.0.0.1:5173/api/session', {
  data: { token: 'intro-demo-only-not-production-123456' },
});
const page = await context.newPage();
let sent = [];
page.on('request', (r) => {
  if (r.url().endsWith('/api/v1/videos') && r.method() === 'POST') sent.push(r.postDataJSON());
});
const started = Date.now();
const marks = [];
const mark = (n) => marks.push({ name: n, seconds: (Date.now() - started) / 1000 });
await page.goto('http://127.0.0.1:5173/');
await page.getByLabel('制作方式').waitFor();
await page.getByLabel('制作方式').selectOption('template');
await page.getByRole('button', { name: '一份源码', exact: true }).click();
await page.getByLabel('视频标题').fill('Engineering Video Agent · 项目源码解析');
await page
  .locator('input[type=file]')
  .setInputFiles(path.join(root, '.verify-project-intro/source.zip'));
await page.getByLabel('输出分辨率').selectOption('4k');
await page.getByLabel('设计体系').selectOption('editorial_warm');
await page.getByLabel('生成方式').selectOption('storyboard');
await page.screenshot({ path: path.join(dir, '01-input.png') });
mark('input_ready');
await page.getByRole('button', { name: '开始创作', exact: true }).click();
await page.getByLabel('讲解旁白').waitFor({ timeout: 45000 });
await page.screenshot({ path: path.join(dir, '02-storyboard.png') });
mark('storyboard_ready');
await page.getByRole('button', { name: '内容证据', exact: true }).click();
await page.locator('.evidence-list details').first().locator('summary').click();
await page.screenshot({ path: path.join(dir, '03-evidence.png') });
mark('evidence');
await page.getByRole('button', { name: '音画时间轴', exact: true }).click();
await page.getByLabel('视觉表达', { exact: true }).selectOption('overview');
await page.getByLabel('总览布局').selectOption('fan');
await page.getByRole('button', { name: '添加旁白同步事件' }).click();
await page.screenshot({ path: path.join(dir, '04-motion.png') });
mark('motion');
await page.getByRole('button', { name: '仅保存脚本分镜', exact: true }).click();
await page.getByRole('heading', { name: '与上一版本比较' }).waitFor({ timeout: 45000 });
await page.screenshot({ path: path.join(dir, '05-compare.png') });
mark('comparison');
await page.waitForTimeout(1800);
const jobs = await (await context.request.get('http://127.0.0.1:5173/api/v1/jobs')).json();
const latest = jobs.items[0];
const revision = await (
  await context.request.get('http://127.0.0.1:5173/api/v1/revisions/' + latest.revision_id)
).json();
fs.writeFileSync(
  path.join(dir, 'evidence.json'),
  JSON.stringify({ marks, submitted: sent, revision }, null, 2),
);
const video = page.video();
await context.close();
await video.saveAs(path.join(dir, 'workbench.webm'));
await b.close();
console.log(
  JSON.stringify({
    marks,
    input_files: revision.content.files_count,
    version: revision.version,
    scenes: revision.storyboard.scenes.length,
    dimensions: [revision.storyboard.width, revision.storyboard.height],
  }),
);
