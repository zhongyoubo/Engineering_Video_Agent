import { test, expect } from '@playwright/test';

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
