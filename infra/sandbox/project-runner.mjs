import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const delay = (n) => new Promise((r) => setTimeout(r, n));
export async function runProject({
  plan,
  source,
  output,
  cacheRoot = '/opt/npm-cache',
  python = '/opt/python/bin/python',
  browserExecutable,
}) {
  fs.mkdirSync(output, { recursive: true });
  const work = path.join(output, 'work');
  fs.rmSync(work, { recursive: true, force: true });
  fs.cpSync(source, work, { recursive: true });
  const cwd = path.resolve(work, plan.working_directory || '.');
  if (cwd !== work && !cwd.startsWith(work + path.sep)) throw Error('Unsafe working directory');
  const log = [];
  let process, server, browser;
  const env = {
    ...globalThis.process.env,
    PORT: '8765',
    HOST: '127.0.0.1',
    HOME: '/tmp',
    PYTHONUNBUFFERED: '1',
    PYTHONDONTWRITEBYTECODE: '1',
  };
  const result = {
    schema_version: '1.0',
    kind: plan.kind,
    entry: plan.entry,
    exit_code: 1,
    actions: [],
    requests: [],
    page_errors: [],
  };
  const command = async (args) => {
    const argv = args.map((a) => (a === '/opt/python/bin/python' ? python : a));
    const p = spawn(argv[0], argv.slice(1), { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let text = '',
      size = 0;
    for (const stream of [p.stdout, p.stderr])
      stream.on('data', (chunk) => {
        size += chunk.length;
        if (size > 2 * 1024 * 1024) p.kill('SIGKILL');
        else text += chunk.toString();
      });
    const timeout = setTimeout(() => p.kill('SIGKILL'), 90000);
    const code = await new Promise((resolve, reject) => {
      p.on('error', reject);
      p.on('exit', resolve);
    });
    clearTimeout(timeout);
    log.push(text.slice(-12000));
    if (code !== 0) throw Error(`Command failed (${code}): ${text.slice(-1500)}`);
    return text;
  };
  try {
    if (plan.install?.length) {
      if (fs.existsSync(cacheRoot)) fs.cpSync(cacheRoot, '/tmp/npm-cache', { recursive: true });
      await command(plan.install);
    }
    if (plan.build?.length) await command(plan.build);
    if (['python-cli', 'node-cli'].includes(plan.kind)) {
      result.stdout = await command(plan.start);
      result.exit_code = 0;
    } else {
      if (plan.kind === 'static-web') {
        server = http.createServer((req, res) => {
          try {
            const relative = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
            const file = path.resolve(work, '.' + relative);
            if (!file.startsWith(work + path.sep)) {
              res.writeHead(403).end();
              return;
            }
            const real = fs.realpathSync(file);
            if (!real.startsWith(work + path.sep)) {
              res.writeHead(403).end();
              return;
            }
            const ext = path.extname(real);
            const mime =
              {
                '.html': 'text/html',
                '.js': 'text/javascript',
                '.css': 'text/css',
                '.json': 'application/json',
                '.svg': 'image/svg+xml',
              }[ext] || 'application/octet-stream';
            res.setHeader('Content-Type', mime);
            res.end(fs.readFileSync(real));
          } catch {
            res.writeHead(404).end();
          }
        });
        await new Promise((r) => server.listen(8765, '127.0.0.1', r));
      } else {
        const argv = plan.start.map((a) => (a === '/opt/python/bin/python' ? python : a));
        process = spawn(argv[0], argv.slice(1), {
          cwd,
          env,
          stdio: ['ignore', 'pipe', 'pipe'],
          detached: true,
        });
        process.on('error', (e) => log.push(e.message));
        let logged = 0;
        for (const stream of [process.stdout, process.stderr])
          stream.on('data', (c) => {
            logged += c.length;
            if (logged < 1000000) log.push(c.toString());
          });
      }
      let ready = false;
      for (let i = 0; i < 120; i++) {
        if (process && process.exitCode !== null) throw Error('Project server exited');
        try {
          await fetch('http://127.0.0.1:8765/', { signal: AbortSignal.timeout(1000) });
          ready = true;
          break;
        } catch {}
        await delay(250);
      }
      if (!ready) throw Error('Project health timeout');
      for (const spec of plan.requests || []) {
        if (
          !spec.path.startsWith('/') ||
          spec.path.startsWith('//') ||
          spec.path.includes('://') ||
          spec.path.includes('\\')
        )
          throw Error('Unsafe request URL');
        const response = await fetch('http://127.0.0.1:8765' + spec.path, {
          method: spec.method,
          redirect: 'error',
          signal: AbortSignal.timeout(10000),
          headers: { 'Content-Type': 'application/json' },
          body: spec.body ? JSON.stringify(spec.body) : undefined,
        });
        const text = (await response.text()).slice(0, 12000);
        result.requests.push({
          path: spec.path,
          method: spec.method,
          status: response.status,
          response: text,
        });
        if (response.status !== spec.expected_status) throw Error('API status assertion failed');
      }
      if (plan.kind === 'python-api') result.stdout = JSON.stringify(result.requests, null, 2);
      else {
        browser = await chromium.launch({
          executablePath: browserExecutable || undefined,
          args: ['--no-sandbox', '--disable-dev-shm-usage'],
        });
        const context = await browser.newContext({
          viewport: { width: 1720, height: 900 },
          serviceWorkers: 'block',
          recordVideo: { dir: path.join(output, 'raw'), size: { width: 1720, height: 900 } },
        });
        await context.route('**/*', (route) => {
          const u = new URL(route.request().url());
          return ['127.0.0.1', 'localhost'].includes(u.hostname) && u.port === '8765'
            ? route.continue()
            : route.abort();
        });
        const page = await context.newPage();
        page.on('pageerror', (e) => result.page_errors.push(e.message));
        const pathname = plan.kind === 'static-web' ? '/' + plan.entry : '/';
        const response = await page.goto('http://127.0.0.1:8765' + pathname, {
          waitUntil: 'domcontentloaded',
          timeout: 30000,
        });
        if (!response?.ok()) throw Error('Page HTTP response not successful');
        await page.locator('body').waitFor({ state: 'visible' });
        await page.evaluate(() => document.fonts.ready);
        const widthBefore = new Map();
        let actions = plan.actions || [];
        if (!actions.length) {
          const count = await page.locator('[data-demo-action="click"]').count();
          actions = Array.from({ length: Math.min(count, 3) }, (_, i) => ({
            kind: 'click',
            target: `[data-demo-action="click"] >> nth=${i}`,
          }));
        }
        for (const action of actions) {
          const locator = page.locator(action.target);
          const started = Date.now();
          if (!widthBefore.has(action.target))
            widthBefore.set(action.target, (await locator.boundingBox())?.width || 0);
          switch (action.kind) {
            case 'click':
              await locator.click({ timeout: action.timeout_ms || 10000 });
              break;
            case 'fill':
              await locator.fill(action.value);
              break;
            case 'press':
              await locator.press(action.value);
              break;
            case 'select':
              await locator.selectOption(action.value);
              break;
            case 'wait_visible':
            case 'assert_visible':
              await locator.waitFor({ state: 'visible', timeout: action.timeout_ms || 10000 });
              break;
            case 'assert_text':
              if (!(await locator.innerText()).includes(action.value))
                throw Error('Text assertion failed');
              break;
            case 'assert_width_increased':
              if (
                ((await locator.boundingBox())?.width || 0) <=
                Number(action.value || widthBefore.get(action.target))
              )
                throw Error('Width assertion failed');
              break;
            default:
              throw Error('Unsupported action');
          }
          result.actions.push({
            kind: action.kind,
            target: action.target,
            passed: true,
            elapsed_ms: Date.now() - started,
          });
        }
        await delay(600);
        await page.screenshot({ path: path.join(output, 'page.png') });
        const video = page.video();
        await context.close();
        fs.copyFileSync(await video.path(), path.join(output, 'capture.webm'));
        if (result.page_errors.length) throw Error('Page script errors observed');
      }
      result.exit_code = 0;
    }
  } catch (error) {
    result.error = error.message;
    result.stdout = log.join('\n').slice(-12000);
  } finally {
    if (browser) await browser.close();
    if (server) await new Promise((r) => server.close(r));
    if (process && process.exitCode === null) {
      try {
        globalThis.process.kill(-process.pid, 'SIGKILL');
      } catch {
        process.kill('SIGKILL');
      }
    }
    fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify(result, null, 2));
  }
  return result;
}

if (
  globalThis.process.argv[1] &&
  path.resolve(globalThis.process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const values = {};
  for (let i = 2; i < process.argv.length; i += 2) values[process.argv[i]] = process.argv[i + 1];
  const plan = JSON.parse(fs.readFileSync(values['--plan'], 'utf8'));
  await runProject({
    plan,
    source: values['--source'],
    output: values['--output'],
    cacheRoot: values['--cache-root'] || '/opt/npm-cache',
    python: values['--python'] || '/opt/python/bin/python',
    browserExecutable: globalThis.process.env.CHROME_EXECUTABLE,
  });
}
