import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('material discovery clears stale results on failure and handles unavailable clipboard', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.addInitScript(() =>
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true }),
  );
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await page.getByRole('button', { name: '素材库', exact: true }).click();
  await page.getByLabel('素材风格').selectOption('soft3d');
  await expect(page.locator('.material-card')).toHaveCount(3);
  await page.locator('.material-card').first().getByRole('button', { name: '复制引用' }).click();
  await expect(page.getByRole('alert')).toHaveText('复制失败，请从下方引用文本复制。');
  expect(errors).toEqual([]);
  await page.route('**/api/v1/material-library?**', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: { message: '素材目录暂不可用' } }),
    }),
  );
  await page.getByLabel('搜索素材').fill('temporary-error');
  await expect(page.getByRole('alert')).toHaveText('素材目录暂不可用');
  await expect(page.locator('.material-card')).toHaveCount(0);
  await expect(page.getByLabel('搜索素材')).toHaveAttribute('maxlength', '160');
});

test('material library filters real previews, kinds and resolution limits', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByRole('button', { name: '素材库', exact: true }).click();
  await page.getByLabel('素材风格').selectOption('soft3d');
  await expect(page.locator('.material-card')).toHaveCount(3);
  const book = page.locator('.material-card').filter({ hasText: '立体书本' });
  await expect(book.getByRole('img', { name: '立体书本' })).toBeVisible();
  await expect
    .poll(() => book.locator('img').evaluate((img: HTMLImageElement) => img.naturalWidth))
    .toBeGreaterThan(0);
  await expect(page.getByText(/原始 132×120px/)).toBeVisible();
  await page.getByLabel('素材风格').selectOption('');
  await page.getByLabel('素材类型').selectOption('model');
  await expect(page.locator('.material-card')).toHaveCount(1);
  await expect(page.getByRole('heading', { name: '牛油果三维模型' })).toBeVisible();
  await page.getByLabel('搜索素材').fill('不存在的对象');
  await expect(page.locator('.material-card')).toHaveCount(0);
  await expect(page.getByText('0 项素材', { exact: true })).toBeVisible();
});

test('4K design settings and editable motion survive a revision fork', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('输出分辨率').selectOption('4k');
  await page.getByLabel('设计体系').selectOption('editorial_warm');
  await page.getByLabel('生成方式').selectOption('storyboard');
  await page.getByRole('button', { name: '开始创作' }).click();
  await expect(page.getByLabel('讲解旁白')).toBeVisible({ timeout: 30000 });
  await expect(page.getByText(/SEC · 4K/)).toBeVisible();
  const previewTitle = page
    .locator('.preview-panel')
    .getByText('解释一个概念', { exact: true })
    .and(page.locator('div'));
  await expect(previewTitle).toBeVisible();
  await expect
    .poll(() =>
      previewTitle.evaluate((element) => {
        let opacity = 1;
        for (let node: Element | null = element; node; node = node.parentElement) {
          opacity *= Number(getComputedStyle(node).opacity);
        }
        return opacity;
      }),
    )
    .toBeGreaterThan(0.9);
  await page.getByRole('button', { name: '音画时间轴', exact: true }).click();
  await page.getByLabel('视觉表达', { exact: true }).selectOption('queue');
  await expect(page.getByLabel('镜头讲解目标')).toBeVisible();
  await page.getByRole('button', { name: '添加旁白同步事件' }).click();
  await expect(page.getByText('input · progress', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  await expect(page.getByRole('heading', { name: '与上一版本比较' })).toBeVisible({
    timeout: 30000,
  });
  await expect(page.getByLabel('视觉表达', { exact: true })).toHaveValue('queue');
  await page.getByLabel('视觉表达', { exact: true }).selectOption('overview');
  await page.getByLabel('总览布局').selectOption('fan');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  await expect(page.getByLabel('总览布局')).toHaveValue('fan', { timeout: 30000 });
});

test('prompt → storyboard → edit → independent revision', async ({ page, context }) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await expect(page.getByText('让复杂，')).toBeVisible();
  await page.screenshot({ path: 'test-results/studio-home.png', fullPage: true });
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await expect(page.getByLabel('视频标题')).toHaveValue('解释一个概念');
  await page.getByLabel('生成方式').selectOption('storyboard');
  await page.getByRole('button', { name: '开始创作' }).click();
  await expect(page.getByRole('heading', { name: '解释一个概念', exact: true })).toBeVisible();
  await expect(page.getByLabel('讲解旁白')).toBeVisible({ timeout: 30000 });
  await expect(page.getByRole('button', { name: '仅保存脚本分镜' })).toBeEnabled({
    timeout: 30000,
  });
  await page.getByLabel('场景标题').fill('API 的工作方式');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  await expect(page.getByLabel('场景标题')).toHaveValue('API 的工作方式', { timeout: 30000 });
  await page.getByRole('button', { name: '视频与版本' }).click();
  expect(await page.locator('.video-card').count()).toBeGreaterThanOrEqual(2);
  await page.getByRole('button', { name: '环境与能力', exact: true }).click();
  await expect(page.getByText('已注册适配器')).toBeVisible();
  await expect(page.getByText('source.static', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '自有素材库', exact: true })).toBeVisible();
  await expect(page.getByText(/主题封面 · v1.1/)).toBeVisible();
  await expect(page.getByText(/关系网络 · v1.1 · 未验证/)).toBeVisible();
});

test('upload source → evidence-backed storyboard', async ({ page, context }) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.getByRole('button', { name: '一份源码' }).click();
  await page.getByLabel('视频标题').fill('目录同步工具');
  await page.locator('input[type=file]').setInputFiles('examples/source-demo.zip');
  await page.getByLabel('生成方式').selectOption('storyboard');
  await page.getByRole('button', { name: '开始创作' }).click();
  await expect(page.getByLabel('讲解旁白')).toBeVisible({ timeout: 30000 });
  await page.getByRole('button', { name: '内容证据' }).click();
  await expect(page.getByText('sync_demo.py', { exact: true })).toBeVisible();
  await page.getByText('sync_demo.py', { exact: true }).click();
  await expect(
    page.locator('.evidence-list pre').filter({ hasText: 'changed_files' }),
  ).toBeVisible();
});

test('import exported media project and edit narration', async ({ page, context }) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.getByRole('button', { name: '视频与版本' }).click();
  await page
    .locator('input[type=file]')
    .setInputFiles('examples/generated/prompt/editable-project.zip');
  await expect(
    page.getByRole('heading', { name: 'Understanding an API', exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await expect(page.getByLabel('讲解旁白')).toHaveValue(
    'An API is a defined interface between software systems.',
    { timeout: 30000 },
  );
  await expect(page.getByRole('button', { name: '仅保存脚本分镜' })).toBeEnabled({
    timeout: 30000,
  });
  await page.getByLabel('修改指令').fill('标题改为清晰的接口');
  await page.getByRole('button', { name: '应用修改并另存分镜' }).click();
  await expect(page.getByLabel('场景标题')).toHaveValue('清晰的接口', { timeout: 30000 });
});

test('native Agent selection fails explicitly when deployment is not configured', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('执行引擎').selectOption('codex');
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForRequest(
    (request) => request.url().endsWith('/api/v1/videos') && request.method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  expect((await submitted).postDataJSON().brief.agent_engine).toBe('codex');
  await expect(page.getByText(/原生 Agent 未就绪/)).toBeVisible({ timeout: 30000 });
  await expect(page.getByText(/没有回退到模板/)).toBeVisible();
  await page.getByRole('button', { name: '环境与能力', exact: true }).click();
  await expect(page.getByText('agent.codex', { exact: true })).toBeVisible();
  await expect(page.getByText('agent.claude-code', { exact: true })).toBeVisible();
});

test('engineering is the default and submits a native professional production request', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await expect(page.getByLabel('制作方式')).toHaveValue('engineering');
  await expect(page.getByLabel('执行引擎')).toHaveValue('codex');
  await expect(page.getByLabel('交付质量')).toHaveValue('professional');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForRequest(
    (r) => r.url().endsWith('/api/v3/videos') && r.method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const brief = (await submitted).postDataJSON().brief;
  expect(brief.video_mode).toBe('engineering');
  expect(brief.voice).toBe('qwen');
  await expect(page.getByText(/原生 Agent 未就绪/)).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('工程 Agent 制作中', { exact: true })).toBeVisible();
});

test('creator intent and cover survive editing, and frame zero has no internal badge', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('内容目的').selectOption('advice');
  await page.getByLabel('核心主张', { exact: true }).fill('先理解请求和响应');
  await page.getByLabel('观众收益', { exact: true }).fill('能用例子说明 API');
  await page.getByLabel('账号或栏目名').fill('研发小课堂');
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForRequest(
    (r) => r.url().endsWith('/api/v1/videos') && r.method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const brief = (await submitted).postDataJSON().brief;
  expect(brief.presentation_profile).toBe('creator');
  expect(brief.editorial.intent).toBe('advice');
  expect(brief.editorial.core_message).toBe('先理解请求和响应');
  await expect(page.getByLabel('封面标题', { exact: true })).toHaveValue('解释一个概念', {
    timeout: 30000,
  });
  await expect(
    page.locator('[data-publication-card]').getByText('解释一个概念', { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator('[data-publication-card]').getByText('研发小课堂', { exact: true }),
  ).toBeVisible();
  await expect(page.locator('.preview-panel').getByText('概念讲解', { exact: true })).toHaveCount(
    0,
  );
  await expect(page.locator('.preview-panel').getByText(/EXPLAINER STUDIO/)).toHaveCount(0);
  await page.getByLabel('封面标题', { exact: true }).fill('API 可以这样理解');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  await expect(page.getByLabel('封面标题', { exact: true })).toHaveValue('API 可以这样理解', {
    timeout: 30000,
  });
  await expect(
    page.locator('[data-publication-card]').getByText('API 可以这样理解', { exact: true }),
  ).toBeVisible();
});

test('six purposes stay independent of subject, audience and form across replanning', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  const purpose = page.getByLabel('内容目的', { exact: true });
  await expect(purpose.locator('option')).toHaveCount(7);
  expect(
    await purpose
      .locator('option')
      .evaluateAll((options) => options.map((o) => (o as HTMLOptionElement).value)),
  ).toEqual(['auto', 'introduction', 'explanation', 'analysis', 'viewpoint', 'advice', 'tutorial']);
  await purpose.selectOption('tutorial');
  await page.getByLabel('讲述对象', { exact: true }).selectOption('concept');
  await page.getByLabel('目标观众描述', { exact: true }).fill('第一次接触 API 的内容创作者');
  await page.getByLabel('讲述深度', { exact: true }).selectOption('introductory');
  await page.getByText('辅助目的（可选，最多两项）', { exact: true }).click();
  await page.getByLabel('辅助目的：分析评估', { exact: true }).check();
  await page.getByText('表现形式（可选，最多四项）', { exact: true }).click();
  await page.getByLabel('表现形式：图解动画', { exact: true }).check();
  await page.getByLabel('表现形式：案例讲解', { exact: true }).check();
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForRequest(
    (r) => r.url().endsWith('/api/v1/videos') && r.method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const editorial = (await submitted).postDataJSON().brief.editorial;
  expect(editorial).toMatchObject({
    intent: 'tutorial',
    secondary_intents: ['analysis'],
    subject_kind: 'concept',
    audience_description: '第一次接触 API 的内容创作者',
    audience_level: 'introductory',
    presentation_forms: ['diagram', 'case_study'],
  });
  await expect(page.getByLabel('内容定位摘要')).toContainText('教学操作', { timeout: 30000 });
  await expect(page.getByLabel('内容定位摘要')).toContainText('概念');
  await expect(page.getByLabel('内容定位摘要')).toContainText('第一次接触 API 的内容创作者');
  await expect(page.getByLabel('内容定位摘要')).toContainText('尚未完成类型策划');
  await page.getByText('调整内容目标', { exact: true }).click();
  await page.getByLabel('版本内容目的', { exact: true }).selectOption('advice');
  await page.getByLabel('版本讲述深度', { exact: true }).selectOption('intermediate');
  await expect(page.getByLabel('内容定位摘要')).toContainText('待另存版本后重新策划');
  await expect(page.getByLabel('内容定位摘要')).toContainText('建议决策');
  const forked = page.waitForRequest((r) => r.url().endsWith('/fork') && r.method() === 'POST');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  expect((await forked).postDataJSON().brief.editorial.intent).toBe('advice');
  await expect(page.getByLabel('内容定位摘要')).toContainText('建议决策', { timeout: 30000 });
  await expect(page.getByLabel('内容定位摘要')).toContainText('进阶');
  await expect(page.getByLabel('内容定位摘要')).toContainText('图解动画、案例讲解');
  await expect(page.getByLabel('内容定位摘要')).not.toContainText('待另存版本后重新策划');
});

test('edited goals hide an obsolete resolved strategy until replanning', async ({
  page,
  context,
}) => {
  // Authored UI fixture only: this does not simulate or certify native inference.
  const fixture = JSON.parse(readFileSync('examples/content-strategies/explanation.json', 'utf8'));
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.route('**/api/v1/revisions/*', async (route) => {
    if (route.request().method() !== 'GET') return route.continue();
    const response = await route.fetch();
    const data = await response.json();
    if (data.storyboard && !data.brief.editorial.core_message) {
      data.storyboard.editorial = fixture.editorial;
    }
    await route.fulfill({ response, json: data });
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('生成方式').selectOption('storyboard');
  await page.getByRole('button', { name: '开始创作' }).click();
  const summary = page.getByLabel('内容定位摘要');
  await expect(summary).toContainText(fixture.editorial.strategy.rationale, { timeout: 30000 });
  await page.getByText('调整内容目标', { exact: true }).click();
  await page.getByLabel('版本核心主张', { exact: true }).fill('新主张需要重新检查整条内容');
  await expect(summary).toContainText('待另存版本后重新策划');
  await expect(summary).not.toContainText(fixture.editorial.strategy.rationale);
  await expect(summary.getByText('叙事结构与验收目标', { exact: true })).toHaveCount(0);
  await page.getByLabel('版本核心主张', { exact: true }).fill('');
  await expect(summary).toContainText(fixture.editorial.strategy.rationale);
  await expect(summary).not.toContainText('待另存版本后重新策划');
});

test('a saved object scene renders devices and preserves editable actions across versions', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForResponse(
    (r) => r.url().endsWith('/api/v1/videos') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const created = await (await submitted).json();
  await expect(page.getByLabel('讲解旁白')).toBeVisible({ timeout: 30000 });
  const original = await (
    await context.request.get('/api/v1/revisions/' + created.revision_id)
  ).json();
  original.storyboard.scenes[0].visual_scene = {
    purpose: '用真实对象造型说明连接关系',
    setting: 'studio',
    objects: [
      {
        id: 'player',
        kind: 'console',
        label: '游戏机',
        x: 100,
        y: 180,
        width: 210,
        height: 300,
        ports: [{ id: 'out', side: 'right' }],
      },
      {
        id: 'screen',
        kind: 'tv',
        label: '电视',
        x: 900,
        y: 50,
        width: 650,
        height: 400,
        ports: [{ id: 'in', side: 'left' }],
      },
    ],
    connections: [
      {
        id: 'hdmi',
        source: 'player',
        source_port: 'out',
        target: 'screen',
        target_port: 'in',
        label: 'HDMI',
      },
    ],
    events: [],
  };
  original.storyboard.scenes[0].diagram = null;
  original.storyboard.scenes[0].motion = null;
  const response = await context.request.post('/api/v1/revisions/' + original.id + '/fork', {
    data: {
      expected_version: original.version,
      storyboard: original.storyboard,
      auto_render: false,
    },
  });
  expect(response.status()).toBe(202);
  const fork = await response.json();
  await page.reload();
  await page.getByRole('button', { name: '视频与版本' }).click();
  await page.locator('.video-card').first().click();
  await expect(page.locator('[data-object-kind="tv"]')).toBeVisible({ timeout: 30000 });
  await expect(page.locator('[data-object-kind="console"]')).toBeVisible();
  await page.getByRole('button', { name: '音画时间轴', exact: true }).click();
  await expect(page.getByLabel('对象场景时间轴')).toContainText('游戏机');
  await expect(page.getByLabel('视觉表达', { exact: true })).toBeDisabled();
  await page.getByLabel('对象标注：screen').fill('客厅电视');
  await page.getByLabel('启用交互提示音').check();
  const saved = page.waitForRequest((r) => r.url().endsWith('/fork') && r.method() === 'POST');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  const payload = (await saved).postDataJSON();
  expect(payload.storyboard.scenes[0].visual_scene.objects[1].label).toBe('客厅电视');
  expect(payload.storyboard.scenes[0].visual_scene.sound_enabled).toBe(true);
  await expect(page.getByLabel('对象标注：screen')).toHaveValue('客厅电视', { timeout: 30000 });
  expect(fork.revision_id).toBeTruthy();
});

test('semantic screen content follows a device and preserves editable state across versions', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForResponse(
    (r) => r.url().endsWith('/api/v1/videos') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const created = await (await submitted).json();
  await expect(page.getByLabel('讲解旁白')).toBeVisible({ timeout: 30000 });
  const original = await (
    await context.request.get('/api/v1/revisions/' + created.revision_id)
  ).json();
  const scene = original.storyboard.scenes[0];
  scene.diagram = null;
  scene.motion = null;
  scene.visual_scene = {
    purpose: '具体手机屏幕绑定语义确认内容',
    setting: 'studio',
    objects: [
      {
        id: 'phone',
        kind: 'phone',
        label: '操作确认',
        x: 930,
        y: 30,
        width: 220,
        height: 460,
        screen: 'black',
      },
    ],
    connections: [],
    events: [],
  };
  scene.semantic_scene = {
    viewer_question: '关键操作由谁确认？',
    entities: [
      {
        id: 'gate',
        component: 'ApprovalGate',
        title: '风险通知',
        text: '发送给项目负责人',
        state: 'awaiting_confirmation',
        bind_to: 'phone',
        items: [{ text: '按既定权限执行', detail: '发送前确认' }],
      },
    ],
    events: [],
    expectations: [],
  };
  const response = await context.request.post('/api/v1/revisions/' + original.id + '/fork', {
    data: {
      expected_version: original.version,
      storyboard: original.storyboard,
      auto_render: false,
    },
  });
  expect(response.status()).toBe(202);
  await page.reload();
  await page.getByRole('button', { name: '视频与版本' }).click();
  await page.locator('.video-card').first().click();
  const panel = page.locator('[data-semantic-entity="gate"]');
  await expect(panel).toBeVisible({ timeout: 30000 });
  await expect(panel).toContainText('等待确认');
  const screen = page.locator('[data-object-id="phone"] [data-device-surface="screen"]');
  const a = await panel.boundingBox(),
    b = await screen.boundingBox();
  expect(a && b).toBeTruthy();
  expect(Math.abs(a!.width - b!.width)).toBeLessThan(2);
  expect(Math.abs(a!.height - b!.height)).toBeLessThan(2);
  await page.getByRole('button', { name: '音画时间轴', exact: true }).click();
  await expect(page.getByLabel('语义场景时间轴')).toContainText('phone.screen');
  await page.getByLabel('语义标题：gate').fill('发送前确认');
  const saved = page.waitForRequest((r) => r.url().endsWith('/fork') && r.method() === 'POST');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  expect((await saved).postDataJSON().storyboard.scenes[0].semantic_scene.entities[0].title).toBe(
    '发送前确认',
  );
  await expect(page.getByLabel('语义标题：gate')).toHaveValue('发送前确认', { timeout: 30000 });
  const capabilities = await (await context.request.get('/api/v1/capabilities')).json();
  expect(capabilities.semantic_scene_toolkit.components).toContain('ToolCall');
  expect(capabilities.asset_factory.image_service).toBe(false);
});

test('engineering uploads project images before requesting native production', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('生成方式').selectOption('storyboard');
  // A real small raster (not a forged content-type or a mocked upload response).
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 96;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#eb4b37';
    ctx.fillRect(0, 0, 128, 96);
    return canvas.toDataURL('image/png').split(',')[1];
  });
  await page.getByLabel('项目图片素材').setInputFiles({
    name: 'tomato.png',
    mimeType: 'image/png',
    buffer: Buffer.from(encoded, 'base64'),
  });
  const imageUploaded = page.waitForResponse(
    (r) =>
      r.url().includes('/api/v3/projects/') &&
      r.url().endsWith('/images') &&
      r.request().method() === 'POST',
  );
  const submitted = page.waitForRequest(
    (r) => r.url().endsWith('/api/v3/videos') && r.method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const upload = await imageUploaded;
  expect(upload.status()).toBe(201);
  const material = await upload.json();
  expect(material.provenance).toBe('user_import');
  const request = (await submitted).postDataJSON();
  const catalog = await context.request.get(`/api/v3/projects/${request.project_id}/images`);
  expect((await catalog.json()).items.map((x: { id: string }) => x.id)).toContain(material.id);
  await expect(page.getByText(/原生 Agent 未就绪/)).toBeVisible({ timeout: 30000 });
});

test('shared mechanism parameters update the rendered SVG and persist across versions', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForResponse(
    (r) => r.url().endsWith('/api/v1/videos') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const created = await (await submitted).json();
  await expect(page.getByLabel('讲解旁白')).toBeVisible({ timeout: 30000 });
  const original = await (
    await context.request.get('/api/v1/revisions/' + created.revision_id)
  ).json();
  const scene = original.storyboard.scenes[0];
  scene.diagram = null;
  scene.motion = null;
  scene.visual_scene = null;
  scene.semantic_scene = {
    viewer_question: '强度如何带动分支与指标？',
    parameters: [{ id: 'strength', minimum: 0, maximum: 1, initial: 0.2, unit: '' }],
    entities: [
      {
        id: 'dial',
        component: 'Dial',
        title: '强度',
        parameter_id: 'strength',
        width: 600,
        height: 400,
      },
    ],
    events: [],
    expectations: [],
  };
  const response = await context.request.post('/api/v1/revisions/' + original.id + '/fork', {
    data: {
      expected_version: original.version,
      storyboard: original.storyboard,
      auto_render: false,
    },
  });
  expect(response.status()).toBe(202);
  await page.reload();
  await page.getByRole('button', { name: '视频与版本' }).click();
  await page.locator('.video-card').first().click();
  const dial = page.locator('[data-mechanism="Dial"]');
  await expect(dial).toHaveAttribute('data-parameter-value', '0.2', { timeout: 30000 });
  await page.getByRole('button', { name: '音画时间轴', exact: true }).click();
  await page.getByLabel('机制参数：strength').fill('0.8');
  await expect(dial).toHaveAttribute('data-parameter-value', '0.8');
  const saved = page.waitForRequest((r) => r.url().endsWith('/fork') && r.method() === 'POST');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  expect(
    (await saved).postDataJSON().storyboard.scenes[0].semantic_scene.parameters[0].initial,
  ).toBe(0.8);
  await expect(page.getByLabel('机制参数：strength')).toHaveValue('0.8', { timeout: 30000 });
});

test('spatial network parameters move actual nodes and persist across revisions', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('设计体系').selectOption('neon_horizon');
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForResponse(
    (r) => r.url().endsWith('/api/v1/videos') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const created = await (await submitted).json();
  await expect(page.getByLabel('讲解旁白')).toBeVisible({ timeout: 30000 });
  const original = await (
    await context.request.get('/api/v1/revisions/' + created.revision_id)
  ).json();
  expect(original.storyboard.design_pack).toBe('neon_horizon');
  const scene = original.storyboard.scenes[0];
  scene.diagram = null;
  scene.motion = null;
  scene.visual_scene = null;
  scene.semantic_scene = {
    viewer_question: '位置改变后联系是否保留？',
    show_heading: false,
    parameters: [{ id: 'strength', minimum: 0, maximum: 1, initial: 0.2, unit: '' }],
    entities: [
      {
        id: 'network',
        component: 'NodeNetwork',
        title: '强度',
        parameter_id: 'strength',
        width: 1920,
        height: 1080,
        immersive: true,
        spatial: { seed: 17, count: 48, columns: 8 },
      },
    ],
    events: [],
    expectations: [],
  };
  const response = await context.request.post('/api/v1/revisions/' + original.id + '/fork', {
    data: {
      expected_version: original.version,
      storyboard: original.storyboard,
      auto_render: false,
    },
  });
  expect(response.status()).toBe(202);
  await page.reload();
  await page.getByRole('button', { name: '视频与版本' }).click();
  await page.locator('.video-card').first().click();
  const dial = page.locator('[data-spatial-component="NodeNetwork"]');
  await expect(dial).toHaveAttribute('data-spatial-progress', '0.2000', { timeout: 30000 });
  await page.getByRole('button', { name: '音画时间轴', exact: true }).click();
  const firstNode = dial.locator('[data-network-node="node-0"] circle').first();
  const before = await firstNode.getAttribute('cx');
  await page.getByLabel('机制参数：strength').fill('0.8');
  await expect(firstNode).not.toHaveAttribute('cx', before!);
  await expect(dial.locator('[data-network-node]')).toHaveCount(48);
  await expect(dial.locator('[data-network-edge]')).toHaveCount(96);
  await expect(dial).toHaveAttribute('data-spatial-progress', '0.8000');
  const saved = page.waitForRequest((r) => r.url().endsWith('/fork') && r.method() === 'POST');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  expect(
    (await saved).postDataJSON().storyboard.scenes[0].semantic_scene.parameters[0].initial,
  ).toBe(0.8);
  await expect(page.getByLabel('机制参数：strength')).toHaveValue('0.8', { timeout: 30000 });
});

test('creative scene design stays visible and persists without executing authored source in Studio', async ({
  page,
  context,
}) => {
  await context.request.post('/api/session', {
    data: { token: 'e2e-only-not-a-production-key-123456' },
  });
  await page.goto('/');
  await page.getByLabel('制作方式').selectOption('template');
  await page.locator('.example-row').getByRole('button', { name: '解释一个概念' }).click();
  await page.getByLabel('生成方式').selectOption('storyboard');
  const submitted = page.waitForResponse(
    (r) => r.url().endsWith('/api/v1/videos') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '开始创作' }).click();
  const created = await (await submitted).json();
  await expect(page.getByLabel('讲解旁白')).toBeVisible({ timeout: 30000 });
  const original = await (
    await context.request.get('/api/v1/revisions/' + created.revision_id)
  ).json();
  const scene = original.storyboard.scenes[0];
  scene.creation = {
    visual_goal: '通过翻开书本、抽出纸页说明资料如何被取用',
    composition: '书本在左侧展开，右侧留出纸页移动和文字空间',
    palette: ['#efb85d', '#305a67'],
    techniques: ['svg'],
    scene_source: 'src/scenes/Library.tsx',
    elements: [
      {
        id: 'book',
        role: 'subject',
        description: '有书脊和分层纸页的立体书本素材',
        implementation: 'source',
        source_file: 'src/assets/Book.tsx',
      },
    ],
    events: [],
  };
  const response = await context.request.post('/api/v1/revisions/' + original.id + '/fork', {
    data: {
      expected_version: original.version,
      storyboard: original.storyboard,
      auto_render: false,
    },
  });
  expect(response.status()).toBe(202);
  await page.reload();
  await page.getByRole('button', { name: '视频与版本' }).click();
  await page.locator('.video-card').first().click();
  await page.getByRole('button', { name: '音画时间轴', exact: true }).click();
  const design = page.getByRole('region', { name: '画面创作设计' });
  await expect(design).toContainText('通过翻开书本');
  await expect(design).toContainText('有书脊和分层纸页');
  await expect(page.getByLabel('视觉表达')).toBeDisabled();
  const saved = page.waitForRequest((r) => r.url().endsWith('/fork') && r.method() === 'POST');
  await page.getByRole('button', { name: '仅保存脚本分镜' }).click();
  expect((await saved).postDataJSON().storyboard.scenes[0].creation.scene_source).toBe(
    'src/scenes/Library.tsx',
  );
});
