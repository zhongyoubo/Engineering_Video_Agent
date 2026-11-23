import { MaterialBrowser } from './MaterialBrowser';
import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Player } from '@remotion/player';
import { Video, type Storyboard, type Scene } from '@explainer/video';
import {
  ArrowUpRight,
  ArrowRight,
  Plus,
  Layers,
  Film,
  Folder,
  Settings2,
  BookOpen,
  Upload,
  FileCode2,
  Sparkles,
  Play,
  ChevronRight,
  Check,
  Loader2,
  Clock,
  Download,
  Square,
  RefreshCw,
  ShieldCheck,
  AudioLines,
  LockKeyhole,
  LayoutTemplate,
  Command,
  LogOut,
  X,
  AlertCircle,
  CheckCircle2,
  Link,
  ChevronDown,
} from 'lucide-react';
import { media, post, request, type Project, type Job } from './api';
import './style.css';
import { ProductionInspector } from './ProductionInspector';
import {
  ContentBriefEditor,
  ContentBriefSummary,
  defaultEditorialRequest,
  editorialRequestChanged,
} from './ContentBriefEditor';

const finalStates = ['SUCCEEDED', 'PARTIAL', 'FAILED', 'CANCELED'];
const stateLabels: Record<string, string> = {
  QUEUED: '排队中',
  RUNNING: '生成中',
  SUCCEEDED: '已完成',
  PARTIAL: '部分完成',
  FAILED: '需要处理',
  CANCELED: '已取消',
  CANCEL_REQUESTED: '取消中',
};
const stageLabels: Record<string, string> = {
  queued: '等待 Worker',
  understanding: '理解内容',
  planning: '编排分镜',
  runtime: '准备演示',
  voice: '生成旁白',
  timeline: '对齐时间线',
  render: '渲染视频',
  quality: '质量检查',
  export: '打包工程',
};
const examples = [
  {
    title: '理解一个算法',
    text: '为初学者讲解二分查找：先解释适用条件，再用有序数组展示左右边界和中间位置如何变化，最后说明终止条件。',
  },
  {
    title: '介绍一个产品',
    text: '介绍一个团队知识库产品：说明信息分散的问题、统一检索的价值、知识整理流程，以及使用时需要考虑的权限和信息更新。',
  },
  {
    title: '解释一个概念',
    text: '面向非技术观众解释 API：用餐厅点单作类比，介绍请求、接口、服务处理和响应，最后用天气查询举例。',
  },
];

function Logo() {
  return (
    <div className="brand">
      <div className="brand-mark">
        <Layers size={22} />
      </div>
      <div>
        explainer<span>STUDIO</span>
      </div>
    </div>
  );
}
function Studio({
  session,
  onLogout,
}: {
  session: { tenant: string };
  onLogout: () => Promise<void>;
}) {
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<Project[]>([]),
    [jobs, setJobs] = useState<Job[]>([]),
    [caps, setCaps] = useState<any>(null);
  const [view, setView] = useState<'create' | 'library' | 'materials' | 'settings'>('create'),
    [inputMode, setInputMode] = useState<'prompt' | 'source' | 'git'>('prompt');
  const [title, setTitle] = useState(''),
    [prompt, setPrompt] = useState(''),
    [duration, setDuration] = useState(90),
    [language, setLanguage] = useState('zh-CN');
  const [audience, setAudience] = useState('general'),
    [accent, setAccent] = useState('blue'),
    [voice, setVoice] = useState('qwen'),
    [mode, setMode] = useState('automatic');
  const [agentEngine, setAgentEngine] = useState('codex');
  const [resolution, setResolution] = useState('1080p'),
    [designPack, setDesignPack] = useState('workspace_tech'),
    [voiceId, setVoiceId] = useState(''),
    [voiceSpeed, setVoiceSpeed] = useState(1);
  const [videoMode, setVideoMode] = useState('engineering'),
    [qualityProfile, setQualityProfile] = useState('professional');
  const [presentationProfile, setPresentationProfile] = useState('creator');
  const [editorialInput, setEditorialInput] = useState(defaultEditorialRequest);
  const [creatorBrand, setCreatorBrand] = useState('');
  const [agentEvents, setAgentEvents] = useState<any[]>([]);
  const [eventRetry, setEventRetry] = useState(0);
  const eventCursor = useRef<{ job: string | null; seq: number }>({ job: null, seq: 0 });
  const [durationMode, setDurationMode] = useState('target'),
    [requireAlignment, setRequireAlignment] = useState(false);
  const [gitUrl, setGitUrl] = useState(''),
    [gitRef, setGitRef] = useState('HEAD'),
    [actionText, setActionText] = useState('[]');
  const [runtime, setRuntime] = useState('none'),
    [entry, setEntry] = useState(''),
    [real, setReal] = useState(false);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [file, setFile] = useState<File | null>(null),
    [busy, setBusy] = useState(false),
    [active, setActive] = useState<string | null>(null);
  const [revision, setRevision] = useState<any>(null),
    [board, setBoard] = useState<Storyboard | null>(null),
    [sceneIndex, setSceneIndex] = useState(0);
  const [instruction, setInstruction] = useState('');
  const [panel, setPanel] = useState<'script' | 'evidence' | 'quality' | 'timeline'>('script'),
    [help, setHelp] = useState(false),
    [toast, setToast] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const importRef = useRef<HTMLInputElement>(null),
    updateRef = useRef<HTMLInputElement>(null);
  const activeJob = jobs.find((j) => j.id === active);
  const refresh = async () => {
    const [p, j, c] = await Promise.all([
      request('/v1/projects'),
      request('/v1/jobs'),
      request('/v1/capabilities'),
    ]);
    setProjects(p.items);
    setJobs(j.items);
    setCaps(c);
  };

  useEffect(() => {
    if (!session) return;
    let live = true,
      polling = false;
    refresh().catch((e) => setError(e.message));
    const id = setInterval(async () => {
      if (polling) return;
      polling = true;
      try {
        // Capabilities include immutable source/font/pack hashes. Load on session entry or
        // explicit refresh; job polling must not re-hash the whole catalog every 3 seconds.
        const [p, j] = await Promise.all([request('/v1/projects'), request('/v1/jobs')]);
        if (live) {
          setProjects(p.items);
          setJobs(j.items);
        }
      } catch {
        /* A transient poll failure does not replace the current editor. */
      } finally {
        polling = false;
      }
    }, 3000);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [session]);
  useEffect(() => {
    if (!activeJob) return;
    let live = true;
    const load = () =>
      request('/v1/revisions/' + activeJob.revision_id).then((r) => {
        if (!live) return;
        setRevision(r);
        if (r.storyboard)
          setBoard((old) =>
            old && r.id === revision?.id && !['RUNNING', 'QUEUED'].includes(activeJob.state)
              ? old
              : r.storyboard,
          );
      });
    load().catch((e) => setError(e.message));
    const timer = setInterval(() => {
      if (!finalStates.includes(activeJob.state)) load().catch(() => {});
    }, 2500);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [activeJob?.id, activeJob?.state]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(''), 4000);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    setAgentEvents([]);
    if (!active) return;
    if (eventCursor.current.job !== active) eventCursor.current = { job: active, seq: 0 };
    const cursor = eventCursor.current;
    let live = true;
    const stream = new EventSource('/api/v1/jobs/' + active + '/events?after=' + cursor.seq, {
      withCredentials: true,
    });
    stream.addEventListener('update', (event) => {
      if (!live) return;
      try {
        const row = JSON.parse((event as MessageEvent).data);
        if (Number.isSafeInteger(row.seq)) {
          if (row.seq <= cursor.seq) return;
          cursor.seq = row.seq;
        }
        if (row.kind?.startsWith('agent.') || row.kind?.startsWith('engineering.')) {
          const payload = typeof row.payload === 'string' ? JSON.parse(row.payload) : row.payload;
          setAgentEvents((old) => [...old, { kind: row.kind, ...payload }].slice(-12));
        }
      } catch {
        /* An invalid status event must not break the editor. */
      }
    });
    stream.addEventListener('done', () => stream.close());
    return () => {
      live = false;
      stream.close();
    };
  }, [active, eventRetry]);

  function reset() {
    setActive(null);
    setRevision(null);
    setBoard(null);
    setView('create');
    setError('');
    setSceneIndex(0);
  }
  async function generate() {
    if (!title.trim()) {
      setError('先给视频起一个标题');
      return;
    }
    if (inputMode === 'source' && !file) {
      setError('请上传 ZIP 源码');
      return;
    }
    if (inputMode === 'prompt' && !prompt.trim()) {
      setError('描述一下你希望讲解的内容');
      return;
    }
    if (
      videoMode === 'engineering' &&
      (imageFiles.length > 24 || imageFiles.some((f) => f.size > 12 * 1024 * 1024))
    ) {
      setError('图片最多 24 张，每张不得超过 12 MB');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const actions = JSON.parse(actionText);
      if (!Array.isArray(actions)) throw new Error('演示动作必须是 JSON 数组');
      const project = await post('/v1/projects', { name: title });
      if (videoMode === 'engineering') {
        for (const image of imageFiles) {
          const material = new FormData();
          material.append('file', image);
          material.append('title', image.name.replace(/\.png$/i, '').slice(0, 60) || '图片素材');
          await request('/v3/projects/' + project.id + '/images', {
            method: 'POST',
            body: material,
          });
        }
      }
      let input_id = null;
      if (inputMode === 'source' && file) {
        const form = new FormData();
        form.append('file', file);
        const input = await request('/v1/projects/' + project.id + '/inputs', {
          method: 'POST',
          body: form,
        });
        input_id = input.id;
        setToast(`已解析 ${input.files_count} 个文本文件，跳过 ${input.skipped} 个文件`);
      }
      if (inputMode === 'git') {
        const input = await post('/v1/projects/' + project.id + '/git-import', {
          url: gitUrl,
          ref: gitRef,
        });
        input_id = input.id;
        setToast('已固定 Git commit：' + input.origin.commit.slice(0, 10));
      }
      const result = await post(videoMode === 'engineering' ? '/v3/videos' : '/v1/videos', {
        project_id: project.id,
        brief: {
          title,
          prompt,
          input_id,
          language,
          audience,
          target_seconds: duration,
          agent_engine: agentEngine,
          video_mode: videoMode,
          quality_profile: qualityProfile,
          presentation_profile: presentationProfile,
          creator_brand: creatorBrand,
          editorial: editorialInput,
          render_profile: { resolution, fps: 30 },
          design_pack: designPack,
          voice_spec: { voice_id: voiceId, speed: voiceSpeed, model: '', revision: '1' },
          duration_mode: durationMode,
          require_alignment: requireAlignment,
          runtime_actions: actions,
          accent,
          voice,
          mode,
          runtime: inputMode !== 'prompt' ? runtime : 'none',
          runtime_entry: entry,
          require_real_demo: real && inputMode !== 'prompt',
        },
      });
      await refresh();
      setActive(result.job_id);
      setRevision(null);
      setBoard(null);
      setView('create');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function importPackage(file: File) {
    setBusy(true);
    setError('');
    try {
      const p = await post('/v1/projects', { name: file.name.replace(/\.zip$/i, '') });
      const form = new FormData();
      form.append('file', file);
      const r = await request('/v1/projects/' + p.id + '/import', { method: 'POST', body: form });
      await refresh();
      setBoard(null);
      setRevision(null);
      setActive(r.job_id);
      setView('create');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function updateSource(file: File) {
    if (!revision) return;
    setBusy(true);
    setError('');
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await request('/v1/revisions/' + revision.id + '/source', {
        method: 'POST',
        body: form,
      });
      await refresh();
      setBoard(null);
      setRevision(null);
      setActive(r.job_id);
      setToast('源码新版本已导入；重新分析证据并复用未变化的旁白');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function selectJob(job: Job) {
    setBoard(null);
    setRevision(null);
    setSceneIndex(0);
    setActive(job.id);
    setView('create');
  }
  async function fork(render: boolean) {
    if (!revision || !board) return;
    setBusy(true);
    setError('');
    try {
      const result = await post('/v1/revisions/' + revision.id + '/fork', {
        expected_version: revision.version,
        storyboard: board,
        brief: {
          ...revision.brief,
          editorial: board.editorial_request || revision.brief.editorial,
        },
        auto_render: render,
      });
      await refresh();
      setRevision(null);
      setBoard(null);
      setActive(result.job_id);
      setToast(render ? '已创建新版本，保留原工程' : '已创建分镜版本');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function instruct() {
    if (!revision || !current || !instruction.trim()) return;
    setBusy(true);
    setError('');
    try {
      const result = await post('/v1/revisions/' + revision.id + '/changes', {
        scene_id: current.id,
        instruction,
        auto_render: false,
      });
      await refresh();
      setRevision(null);
      setBoard(null);
      setActive(result.job_id);
      setInstruction('');
      setToast('修改已另存为分镜版本');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function editScene(patch: Partial<Scene>) {
    setBoard((old) =>
      old
        ? { ...old, scenes: old.scenes.map((s, i) => (i === sceneIndex ? { ...s, ...patch } : s)) }
        : old,
    );
  }
  function preview() {
    if (!board) return null;
    let cursor = 0;
    const scenes = board.scenes.map((s) => {
      const frames = s.frames > 0 && s.start_frame > 0 ? s.frames : Math.round(s.duration * 30);
      const out = {
        ...s,
        start_frame: cursor,
        frames,
        audio_src: s.audio_id ? media(s.audio_id) : undefined,
        media_src: s.media_id ? media(s.media_id) : undefined,
      };
      cursor += frames;
      return out;
    });
    return { ...board, scenes, total_frames: cursor, fontSrc: '/fonts/NotoSansCJKsc-Regular.otf' };
  }
  const props = preview(),
    current = board?.scenes[sceneIndex];
  const inProgress = !!activeJob && !finalStates.includes(activeJob.state);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Logo />
        <button className="new-button" onClick={reset}>
          <Plus size={18} />
          新建视频<kbd>N</kbd>
        </button>
        <div className="nav-label">工作空间</div>
        <nav>
          <button className={view === 'create' ? 'active' : ''} onClick={() => setView('create')}>
            <LayoutTemplate size={18} />
            创作工作台
          </button>
          <button className={view === 'library' ? 'active' : ''} onClick={() => setView('library')}>
            <Folder size={18} />
            视频与版本<span>{jobs.length}</span>
          </button>
          <button
            className={view === 'materials' ? 'active' : ''}
            onClick={() => setView('materials')}
          >
            <BookOpen size={18} />
            素材库
          </button>
          <button
            className={view === 'settings' ? 'active' : ''}
            onClick={() => setView('settings')}
          >
            <Settings2 size={18} />
            环境与能力
          </button>
        </nav>
        <div className="sidebar-divider" />
        <div className="nav-label">最近的创作</div>
        <div className="recent">
          {jobs.slice(0, 7).map((j) => (
            <button
              key={j.id}
              className={active === j.id ? 'selected' : ''}
              onClick={() => selectJob(j)}
            >
              <span className={'dot ' + j.state.toLowerCase()} />
              <span>{JSON.parse(j.brief).title}</span>
            </button>
          ))}
          {!jobs.length && <div className="recent-empty">好故事从第一个想法开始</div>}
        </div>
        <div className="sidebar-bottom">
          <button onClick={() => setHelp(true)}>
            <BookOpen size={18} />
            使用与交付文档
            <ArrowUpRight size={14} />
          </button>
          <div className="profile">
            <span className="avatar">{session.tenant.slice(0, 1).toUpperCase()}</span>
            <div>
              <b>创作者工作空间</b>
              <small>{session.tenant}</small>
            </div>
            <button
              aria-label="退出登录"
              onClick={() => onLogout().catch((e) => setError(e.message))}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            工作空间
            <ChevronRight size={14} />
            <b>
              {view === 'library'
                ? '视频与版本'
                : view === 'materials'
                  ? '素材库'
                  : view === 'settings'
                    ? '环境与能力'
                    : '创作工作台'}
            </b>
          </div>
          <span className="connected">
            <span />
            本地优先 · 可扩展引擎
          </span>
          <button
            className="icon-btn"
            aria-label="刷新"
            onClick={() => refresh().catch((e) => setError(e.message))}
          >
            <RefreshCw size={16} />
          </button>
        </header>
        {error && (
          <div className="error banner">
            <AlertCircle size={17} />
            {error}
            <button onClick={() => setError('')}>
              <X size={16} />
            </button>
          </div>
        )}
        {view === 'create' && !active && (
          <div className="create-page">
            <section className="hero">
              <div className="eyebrow">
                <span /> EXPLAIN IT BEAUTIFULLY
              </div>
              <h1>
                让复杂，<span>一目了然。</span>
              </h1>
              <p>给我们一个想法，或一份源码。把内容变成有画面、有声音的讲解。</p>
              <div className="hero-tag">
                <Sparkles size={14} />
                从理解到表达，一次完成。
              </div>
            </section>
            <div className="creation-grid">
              <section className="composer panel">
                <div className="section-heading">
                  <div>
                    <span className="step">01</span>
                    <h2>从什么开始？</h2>
                  </div>
                  <span className="subtle">YOUR STARTING POINT</span>
                </div>
                <div className="segmented">
                  <button
                    className={inputMode === 'prompt' ? 'on' : ''}
                    onClick={() => setInputMode('prompt')}
                  >
                    <Sparkles size={16} />
                    一个想法
                  </button>
                  <button
                    className={inputMode === 'source' ? 'on' : ''}
                    onClick={() => setInputMode('source')}
                  >
                    <FileCode2 size={16} />
                    一份源码
                  </button>
                </div>
                <button
                  className="secondary full"
                  onClick={() => setInputMode(inputMode === 'git' ? 'prompt' : 'git')}
                >
                  <Link size={14} /> {inputMode === 'git' ? '退出 Git 导入' : '从公开 Git 仓库导入'}
                </button>
                <label>视频标题</label>
                <input
                  aria-label="视频标题"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={100}
                  placeholder="例如：三分钟理解二分查找"
                />
                {inputMode === 'git' && (
                  <>
                    <label>公开 HTTPS 仓库</label>
                    <input
                      aria-label="Git 仓库"
                      value={gitUrl}
                      onChange={(e) => setGitUrl(e.target.value)}
                      placeholder="https://github.com/owner/repo"
                    />
                    <label>分支或 commit</label>
                    <input
                      aria-label="Git 版本"
                      value={gitRef}
                      onChange={(e) => setGitRef(e.target.value)}
                    />
                  </>
                )}
                {inputMode === 'source' && (
                  <>
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".zip"
                      hidden
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                    <button
                      className={'upload-zone ' + (file ? 'uploaded' : '')}
                      onClick={() => fileRef.current?.click()}
                    >
                      <Upload size={25} />
                      <b>{file ? file.name : '点击选择项目 ZIP'}</b>
                      <span>
                        {file
                          ? `${(file.size / 1024).toFixed(0)} KB · 只读解析，不直接执行`
                          : '支持源码、README 和配置文件 · 最大 25 MB'}
                      </span>
                    </button>
                  </>
                )}
                {videoMode === 'engineering' && (
                  <div>
                    <label>参考图片与独立素材（可选）</label>
                    <input
                      aria-label="项目图片素材"
                      type="file"
                      accept="image/png"
                      multiple
                      disabled={busy}
                      onChange={(e) => setImageFiles(Array.from(e.target.files || []))}
                    />
                    <p className="subtle">
                      PNG，每张最多 12 MB，最多 24 张；使用透明图可单独编排元素动作。
                    </p>
                    {imageFiles.length > 0 && <p>{imageFiles.map((f) => f.name).join('、')}</p>}
                  </div>
                )}
                <label>
                  {inputMode === 'prompt' ? '你想讲解什么？' : '希望重点讲解什么？（可选）'}
                </label>
                <textarea
                  aria-label="讲解要求"
                  className="brief-text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  maxLength={12000}
                  placeholder={
                    inputMode === 'prompt'
                      ? '描述主题、观众和你希望表达的重点。\n例如：向初学者解释 API，并用天气查询演示请求与响应。'
                      : '例如：重点解释项目架构、核心算法与典型用法。'
                  }
                />
                {inputMode === 'prompt' && (
                  <div className="example-row">
                    <span>试一试</span>
                    {examples.map((x) => (
                      <button
                        key={x.title}
                        onClick={() => {
                          setTitle(x.title);
                          setPrompt(x.text);
                        }}
                      >
                        {x.title}
                        <ArrowUpRight size={12} />
                      </button>
                    ))}
                  </div>
                )}
                <div className="composer-footer">
                  <span>
                    <ShieldCheck size={15} />
                    {caps?.model
                      ? '仅向配置的模型发送脱敏摘要'
                      : '本地模板可直接使用，无需模型密钥'}
                  </span>
                </div>
              </section>
              <section className="settings-panel panel">
                <div className="section-heading">
                  <div>
                    <span className="step">02</span>
                    <h2>定义表达方式</h2>
                  </div>
                  <Settings2 size={17} />
                </div>
                <div className="field-row">
                  <div>
                    <label>目标时长</label>
                    <select
                      aria-label="目标时长"
                      value={duration}
                      onChange={(e) => setDuration(+e.target.value)}
                    >
                      <option value={30}>30 秒 · 精简</option>
                      <option value={60}>60 秒 · 概览</option>
                      <option value={90}>90 秒 · 标准</option>
                      <option value={180}>3 分钟 · 深入</option>
                      <option value={300}>5 分钟 · 教程</option>
                    </select>
                  </div>
                  <div>
                    <label>讲解语言</label>
                    <select
                      aria-label="讲解语言"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                    >
                      <option value="zh-CN">简体中文</option>
                      <option value="en-US">English</option>
                    </select>
                  </div>
                </div>
                <ContentBriefEditor
                  value={editorialInput}
                  onChange={setEditorialInput}
                  taxonomy={caps?.content_taxonomy}
                />
                <label>发布用途</label>
                <select
                  aria-label="发布用途"
                  value={presentationProfile}
                  onChange={(e) => setPresentationProfile(e.target.value)}
                >
                  <option value="creator">自媒体内容</option>
                  <option value="internal_demo">内部演示</option>
                  <option value="engineering_report">工程报告</option>
                </select>
                <label>账号或栏目名（可选）</label>
                <input
                  aria-label="账号或栏目名"
                  maxLength={80}
                  value={creatorBrand}
                  onChange={(e) => setCreatorBrand(e.target.value)}
                />
                <label>制作方式</label>
                <select
                  aria-label="制作方式"
                  value={videoMode}
                  onChange={(e) => {
                    setVideoMode(e.target.value);
                    setAgentEngine(e.target.value === 'engineering' ? 'codex' : 'pipeline');
                    setVoice(e.target.value === 'engineering' ? 'qwen' : 'auto');
                  }}
                >
                  <option value="engineering">工程 Agent · 编写并验证 Remotion 工程</option>
                  <option value="template">模板兼容模式</option>
                </select>
                <label>输出分辨率</label>
                <select
                  aria-label="输出分辨率"
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                >
                  <option value="1080p">1920 × 1080</option>
                  <option value="4k">3840 × 2160 · 4K</option>
                </select>
                <label>设计体系</label>
                <select
                  aria-label="设计体系"
                  value={designPack}
                  onChange={(e) => setDesignPack(e.target.value)}
                >
                  <option value="workspace_tech">工作台技术风格</option>
                  <option value="neon_horizon">霓虹空间风格</option>
                  <option value="editorial_warm">暖色图解风格</option>
                </select>
                {videoMode === 'engineering' && (
                  <>
                    <label>交付质量</label>
                    <select
                      aria-label="交付质量"
                      value={qualityProfile}
                      onChange={(e) => {
                        setQualityProfile(e.target.value);
                        setVoice(e.target.value === 'professional' ? 'qwen' : 'none');
                      }}
                    >
                      <option value="professional">正式成片 · 明确的配音服务与真实对齐</option>
                      <option value="draft">草稿 · 可无配音</option>
                    </select>
                  </>
                )}
                <label>执行引擎</label>
                <select
                  aria-label="执行引擎"
                  value={agentEngine}
                  onChange={(e) => setAgentEngine(e.target.value)}
                >
                  {videoMode === 'template' && <option value="pipeline">标准流水线</option>}
                  <option value="codex">Codex 原生 Agent</option>
                  <option value="claude-code">Claude Code 原生 Agent</option>
                </select>
                {agentEngine !== 'pipeline' && (
                  <div className="notice">
                    原生 Agent
                    负责理解项目、设计分镜与动画；需要管理员配置独立执行环境。未就绪会明确失败。
                  </div>
                )}
                <label>时长约束</label>
                <select
                  aria-label="时长约束"
                  value={durationMode}
                  onChange={(e) => setDurationMode(e.target.value)}
                >
                  <option value="target">目标时长 · 内容优先</option>
                  <option value="exact">严格等于目标时长</option>
                  <option value="max">不能超过目标时长</option>
                </select>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={requireAlignment}
                    onChange={(e) => setRequireAlignment(e.target.checked)}
                  />
                  必须使用真实词级对齐
                </label>
                <label>面向的观众</label>
                <select
                  aria-label="面向的观众"
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                >
                  <option value="general">通用受众</option>
                  <option value="beginner">初学者</option>
                  <option value="developer">开发者</option>
                  <option value="executive">管理者</option>
                </select>
                <label>旁白音色</label>
                <select
                  aria-label="旁白音色"
                  value={voice}
                  onChange={(e) => {
                    setVoice(e.target.value);
                    setVoiceId('');
                  }}
                >
                  <option value="auto">自动选择本地引擎</option>
                  <option value="espeak">eSpeak · 开发音色</option>
                  <option value="qwen">Qwen3-TTS · 专业音色服务</option>
                  <option value="edge">Edge 朗读 · 候选音色（需试听）</option>
                  <option value="ming">Ming-TTS · 本地音色设计（需配置服务）</option>
                  <option value="none">无旁白 · 字幕版</option>
                </select>
                {voice === 'edge' && (
                  <label>
                    Edge 声音 ID
                    <input
                      aria-label="声音 ID"
                      value={voiceId}
                      placeholder="默认使用服务配置"
                      onChange={(e) => setVoiceId(e.target.value)}
                    />
                  </label>
                )}
                <label>
                  旁白速度
                  <input
                    aria-label="旁白速度"
                    type="number"
                    min="0.85"
                    max="1.15"
                    step="0.05"
                    value={voiceSpeed}
                    onChange={(e) => setVoiceSpeed(Number(e.target.value))}
                  />
                </label>
                <div className="palette-label">
                  <label>视觉主题</label>
                  <span>清晰 · 简洁 · 有节奏</span>
                </div>
                <div className="palette">
                  {[
                    ['blue', '#3869ef', '远山蓝'],
                    ['violet', '#7953df', '鸢尾紫'],
                    ['teal', '#087f83', '松石青'],
                    ['amber', '#bc7620', '暖砂金'],
                  ].map(([value, color, label]) => (
                    <button
                      key={value}
                      className={accent === value ? 'chosen' : ''}
                      onClick={() => setAccent(value)}
                      aria-label={label}
                      title={label}
                      style={{ '--swatch': color } as React.CSSProperties}
                    >
                      {accent === value && <Check size={15} />}
                    </button>
                  ))}
                </div>
                <label>生成方式</label>
                <select
                  aria-label="生成方式"
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                >
                  <option value="automatic">生成完整视频</option>
                  <option value="storyboard">先生成脚本分镜</option>
                </select>
                {inputMode !== 'prompt' && (
                  <details className="runtime-settings">
                    <summary>
                      隔离演示设置
                      <ChevronDown size={14} />
                    </summary>
                    <label>运行适配器</label>
                    <select
                      aria-label="运行适配器"
                      value={runtime}
                      onChange={(e) => setRuntime(e.target.value)}
                    >
                      <option value="none">仅源码讲解</option>
                      <option value="auto">自动识别项目</option>
                      <option value="node-web">Node / Vue / React Web</option>
                      <option value="python-api">Python API 服务</option>
                      <option value="node-cli">Node CLI</option>
                      <option value="static-web">静态 Web 页面</option>
                      <option value="python-cli">Python CLI（标准库）</option>
                    </select>
                    {runtime !== 'none' && (
                      <>
                        <label>归档内入口路径</label>
                        <input
                          aria-label="归档内入口路径"
                          value={entry}
                          onChange={(e) => setEntry(e.target.value)}
                          placeholder={runtime === 'static-web' ? 'index.html' : 'demo.py'}
                        />
                        <label className="checkbox">
                          <input
                            type="checkbox"
                            checked={real}
                            onChange={(e) => setReal(e.target.checked)}
                          />
                          真实演示是必选目标
                        </label>
                        <label>声明式演示动作（JSON）</label>
                        <textarea
                          aria-label="演示动作"
                          rows={3}
                          value={actionText}
                          onChange={(e) => setActionText(e.target.value)}
                          placeholder='[ {"kind":"click","target":"#search"} ]'
                        />
                        <small>
                          运行需要隔离环境；可自动识别入口，也可在 explainer.json 中声明动作。
                        </small>
                      </>
                    )}
                  </details>
                )}
                <button className="primary generate" onClick={generate} disabled={busy}>
                  {busy ? <Loader2 size={18} className="spin" /> : <Sparkles size={18} />}开始创作
                  <ArrowRight size={17} />
                </button>
                <small className="footnote">严格约束无法满足时会报告冲突，不截断旁白。</small>
              </section>
            </div>
            <section className="process-strip">
              {[
                [FileCode2, '理解内容', '源码、文档与主题'],
                [Layers, '编排故事', '结构、分镜与证据'],
                [AudioLines, '赋予声音', '旁白与字幕'],
                [Film, '生成视频', '预览、修改与导出'],
              ].map(([Icon, t, s]: any, i) => (
                <div key={t}>
                  <span className="process-icon">
                    <Icon size={19} />
                  </span>
                  <div>
                    <b>{t}</b>
                    <span>{s}</span>
                  </div>
                  {i < 3 && <ArrowRight size={15} />}
                </div>
              ))}
            </section>
            <div className="bottom-note">
              <span>CRAFTED FOR UNDERSTANDING</span>
              <span>真实运行有证据，概念讲解有边界。</span>
            </div>
          </div>
        )}
        {view === 'create' && active && (
          <div className="editor-page">
            <div className="editor-heading">
              <div>
                <div className="eyebrow">YOUR VIDEO PROJECT</div>
                <h1>{revision?.brief?.title || '正在准备创作'}</h1>
                <p>每次修改创建独立版本，原有内容保持可追溯。</p>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  ref={updateRef}
                  hidden
                  type="file"
                  accept=".zip"
                  onChange={(e) => {
                    if (e.target.files?.[0]) updateSource(e.target.files[0]);
                    e.target.value = '';
                  }}
                />
                {revision?.brief?.input_id && (
                  <button
                    className="secondary"
                    disabled={busy || inProgress}
                    onClick={() => updateRef.current?.click()}
                  >
                    <Upload size={15} />
                    更新源码
                  </button>
                )}
                <button className="secondary" onClick={reset}>
                  <Plus size={16} />
                  新建视频
                </button>
              </div>
            </div>
            {agentEvents.length > 0 && (
              <div className="notice" aria-label="Agent 执行状态">
                <b>{agentEvents.at(-1)?.provider || revision?.brief?.agent_engine} · 工程 Agent</b>
                <span>
                  　
                  {(
                    {
                      'agent.started': '开始分析',
                      'agent.progress': '正在阅读与设计',
                      'agent.completed': '分镜校验通过',
                      'agent.failed': '执行或校验失败',
                      'engineering.action': agentEvents.at(-1)?.action || '工程执行',
                    } as Record<string, string>
                  )[agentEvents.at(-1)?.kind] || '处理中'}
                </span>
              </div>
            )}
            <div className="job-status">
              <div className={'status-icon ' + (inProgress ? 'working' : '')}>
                {inProgress ? <Loader2 size={19} className="spin" /> : <CheckCircle2 size={19} />}
              </div>
              <div>
                <b>{stateLabels[activeJob?.state || 'QUEUED']}</b>
                <span>{stageLabels[activeJob?.stage || 'queued'] || activeJob?.stage}</span>
              </div>
              <div className="status-track">
                <i style={{ width: Math.round((activeJob?.progress || 0) * 100) + '%' }} />
              </div>
              {inProgress ? (
                <button
                  className="secondary"
                  onClick={() =>
                    post('/v1/jobs/' + active + '/cancel', {})
                      .then(refresh)
                      .catch((e) => setError(e.message))
                  }
                >
                  <Square size={13} />
                  取消任务
                </button>
              ) : activeJob?.state === 'FAILED' ? (
                <button
                  className="secondary"
                  onClick={() =>
                    post('/v1/jobs/' + active + '/retry', {})
                      .then(() => setEventRetry((value) => value + 1))
                      .then(refresh)
                      .catch((e) => setError(e.message))
                  }
                >
                  <RefreshCw size={14} />
                  重试
                </button>
              ) : (
                <span className="subtle">
                  {Math.round((board?.total_frames || 0) / (board?.fps || 30))} SEC ·{' '}
                  {board?.width === 3840 ? '4K' : '1080P'}
                </span>
              )}
            </div>
            {activeJob?.error && <div className="error">{activeJob.error}</div>}
            <div className="editor-grid">
              <section className="preview-panel panel">
                <div className="preview-head">
                  <span>
                    <Play size={14} />
                    实时工程预览
                  </span>
                  <span>16:9 / 30 FPS</span>
                </div>
                {revision?.brief?.video_mode === 'engineering' ? (
                  revision?.outputs?.video || revision?.outputs?.motion_preview ? (
                    <video
                      style={{ width: '100%' }}
                      src={media(revision.outputs.video || revision.outputs.motion_preview)}
                      controls
                      preload="metadata"
                    />
                  ) : revision?.outputs?.engineering_preview || revision?.outputs?.cover ? (
                    <img
                      alt="实际工程试渲染"
                      style={{ width: '100%' }}
                      src={media(revision.outputs.engineering_preview || revision.outputs.cover)}
                    />
                  ) : (
                    <div className="preview-wait">
                      <Layers size={40} />
                      <h3>工程 Agent 制作中</h3>
                      <p>
                        先生成方案和脚本，再编写 TSX、构建、试渲染并检查。此处只展示实际工程产物。
                      </p>
                    </div>
                  )
                ) : props ? (
                  <Player
                    key={revision?.id + '-' + props.total_frames}
                    component={Video}
                    inputProps={props}
                    compositionWidth={props.width}
                    compositionHeight={props.height}
                    fps={props.fps}
                    initialFrame={0}
                    durationInFrames={Math.max(1, props.total_frames)}
                    controls
                    style={{ width: '100%', aspectRatio: '16/9' }}
                  />
                ) : (
                  <div className="preview-wait">
                    <Layers size={40} />
                    <h3>好故事正在成形</h3>
                    <p>理解内容后，脚本与分镜将在这里出现。</p>
                  </div>
                )}
                <div className="preview-notice">
                  <ShieldCheck size={15} />
                  {revision?.brief?.video_mode === 'engineering'
                    ? '工程画面由 Agent 编写的 TSX 渲染；原生审查不等于人工质量认证'
                    : caps?.model
                      ? '模型生成内容请结合证据审阅'
                      : '当前为本地模板模式，可编辑脚本或配置模型增强内容'}
                </div>
                {revision?.outputs?.video && (
                  <div className="rendered">
                    <b>导出成片</b>
                    <video src={media(revision.outputs.video)} controls preload="metadata" />
                  </div>
                )}
                {board?.cover && (
                  <div className="publication-panel" style={{ padding: 20 }}>
                    <h3>封面与内容主线</h3>
                    <ContentBriefSummary
                      request={board.editorial_request || revision?.brief.editorial}
                      strategy={board.editorial?.strategy}
                      taxonomy={caps?.content_taxonomy}
                      pending={editorialRequestChanged(
                        board.editorial_request || revision?.brief.editorial,
                        revision?.brief.editorial,
                      )}
                    />
                    <details>
                      <summary>调整内容目标</summary>
                      <ContentBriefEditor
                        value={
                          board.editorial_request ||
                          revision?.brief.editorial ||
                          defaultEditorialRequest
                        }
                        onChange={(value) => setBoard({ ...board, editorial_request: value })}
                        taxonomy={caps?.content_taxonomy}
                        prefix="版本"
                      />
                      <p>修改内容目标后，另存版本会重新策划正文与分镜。</p>
                    </details>
                    <label>封面标题</label>
                    <input
                      aria-label="封面标题"
                      maxLength={100}
                      value={board.cover.headline}
                      onChange={(e) =>
                        setBoard({ ...board, cover: { ...board.cover!, headline: e.target.value } })
                      }
                    />
                    <label>封面辅助文案</label>
                    <input
                      aria-label="封面辅助文案"
                      maxLength={160}
                      value={board.cover.subtitle}
                      onChange={(e) =>
                        setBoard({ ...board, cover: { ...board.cover!, subtitle: e.target.value } })
                      }
                    />
                    {board.editorial && (
                      <>
                        <p>
                          <b>核心主张：</b>
                          {board.editorial.core_message}
                        </p>
                        <p>
                          <b>观众收益：</b>
                          {board.editorial.viewer_takeaway}
                        </p>
                      </>
                    )}
                    {revision?.outputs?.cover && (
                      <img
                        alt="实际导出的发布封面"
                        src={media(revision.outputs.cover)}
                        style={{ width: '100%', marginTop: 16 }}
                      />
                    )}
                  </div>
                )}
                <div className="download-row">
                  {[
                    ['video', '视频 MP4'],
                    ['cover', '独立封面 PNG'],
                    ['script', '演讲脚本'],
                    ['subtitles', '字幕 SRT'],
                    ['package', '可编辑工程'],
                    ['quality', '质量报告'],
                    ['alignment', '词级对齐'],
                    ['agent', 'Agent 执行报告'],
                    ['production_plan', '制作方案与分镜'],
                    ['engineering_project', '完整 Remotion 源码'],
                    ['visual_review', '画面审查'],
                    ['keyframes', '关键帧索引'],
                    ['authoring_journal', '工程执行记录'],
                    ['narration', '完整旁白 WAV'],
                    ['motion_previews', '连续预览索引'],
                    ['audio_analysis', '音频测量与波形'],
                  ].map(
                    ([key, label]) =>
                      revision?.outputs?.[key] && (
                        <a key={key} href={media(revision.outputs[key], true)}>
                          <Download size={14} />
                          {label}
                        </a>
                      ),
                  )}
                </div>
                {board && (
                  <div className="scene-strip">
                    {board.scenes.map((s, i) => (
                      <button
                        key={s.id}
                        className={sceneIndex === i ? 'selected' : ''}
                        onClick={() => setSceneIndex(i)}
                      >
                        <span>{String(i + 1).padStart(2, '0')}</span>
                        <b>{s.title}</b>
                        <small>
                          {Math.round(s.duration)}s {s.locked ? '· 已锁定' : ''}
                        </small>
                      </button>
                    ))}
                  </div>
                )}
              </section>
              <section className="inspector panel">
                <div className="inspector-tabs">
                  {[
                    ['script', '脚本与分镜'],
                    ['evidence', '内容证据'],
                    ['quality', '质量检查'],
                    ['timeline', '音画时间轴'],
                  ].map(([key, label]) => (
                    <button
                      key={key}
                      className={panel === key ? 'on' : ''}
                      onClick={() => setPanel(key as any)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {panel === 'timeline' && current && revision && (
                  <>
                    <ProductionInspector
                      revision={revision}
                      scene={current}
                      onEdit={editScene}
                      disabled={inProgress || current.locked}
                    />
                    <div className="scene-form">
                      <button
                        className="primary"
                        disabled={busy || inProgress}
                        onClick={() => fork(true)}
                      >
                        保存为新版并导出
                      </button>
                      <button
                        className="secondary full"
                        disabled={busy || inProgress}
                        onClick={() => fork(false)}
                      >
                        仅保存脚本分镜
                      </button>
                    </div>
                  </>
                )}
                {panel === 'script' && current && (
                  <div className="scene-form">
                    <div className="scene-form-title">
                      <span>SCENE {String(sceneIndex + 1).padStart(2, '0')}</span>
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={current.locked}
                          onChange={(e) => editScene({ locked: e.target.checked })}
                        />
                        <LockKeyhole size={12} />
                        锁定
                      </label>
                    </div>
                    <label>场景标题</label>
                    <input
                      aria-label="场景标题"
                      value={current.title}
                      disabled={inProgress || current.locked}
                      onChange={(e) => editScene({ title: e.target.value })}
                    />
                    <label>画面类型</label>
                    <select
                      aria-label="画面类型"
                      value={current.type}
                      disabled={inProgress || current.locked}
                      onChange={(e) => editScene({ type: e.target.value as Scene['type'] })}
                    >
                      {[
                        'title',
                        'cards',
                        'flow',
                        'architecture',
                        'code',
                        'terminal',
                        'ui',
                        'summary',
                      ].map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                    <label>讲解旁白</label>
                    <textarea
                      aria-label="讲解旁白"
                      rows={7}
                      value={current.narration}
                      disabled={inProgress || current.locked}
                      onChange={(e) => editScene({ narration: e.target.value })}
                    />
                    <label>画面要点（每行一条，最多六条）</label>
                    <textarea
                      aria-label="画面要点"
                      rows={4}
                      value={current.bullets.join('\n')}
                      disabled={inProgress || current.locked}
                      onChange={(e) =>
                        editScene({ bullets: e.target.value.split('\n').slice(0, 6) })
                      }
                    />
                    {['code', 'terminal'].includes(current.type) && (
                      <>
                        <label>展示代码 / 输出</label>
                        <textarea
                          className="code-editor"
                          rows={6}
                          value={current.code}
                          disabled={inProgress || current.locked}
                          onChange={(e) => editScene({ code: e.target.value })}
                        />
                      </>
                    )}
                    <label>一句话修改当前场景</label>
                    <input
                      aria-label="修改指令"
                      value={instruction}
                      onChange={(e) => setInstruction(e.target.value)}
                      placeholder="例如：标题改为理解工作原理"
                    />
                    <button
                      className="secondary full"
                      disabled={busy || inProgress || !instruction.trim()}
                      onClick={instruct}
                    >
                      <Sparkles size={14} />
                      应用修改并另存分镜
                    </button>
                    <div className="verification">
                      <ShieldCheck size={14} />
                      验证级别：{current.verification}
                    </div>
                    <button
                      className="primary"
                      disabled={busy || inProgress}
                      onClick={() => fork(true)}
                    >
                      <RefreshCw size={16} />
                      保存为新版并导出
                    </button>
                    <button
                      className="secondary full"
                      disabled={busy || inProgress}
                      onClick={() => fork(false)}
                    >
                      仅保存脚本分镜
                    </button>
                    <small>修改旁白会重新配音；未变化的音频可复用。解锁需单独保存一次。</small>
                  </div>
                )}
                {panel === 'script' && !current && (
                  <div className="inspector-empty">脚本正在准备中…</div>
                )}
                {panel === 'evidence' && (
                  <div className="evidence-list">
                    <div className="notice">
                      静态分析不等同于运行验证。以下内容来自当前输入快照。
                    </div>
                    {revision?.content?.evidence?.map((e: any) => (
                      <details key={e.id}>
                        <summary>
                          <FileCode2 size={14} />
                          {e.path}
                        </summary>
                        <pre>{e.excerpt}</pre>
                      </details>
                    ))}
                    {!revision?.content?.evidence?.length && (
                      <p>提示词模式：讲解内容由用户材料提供，未附源码证据。</p>
                    )}
                  </div>
                )}
                {panel === 'quality' && (
                  <div className="quality-list">
                    {revision?.quality?.findings?.map((f: any, i: number) => (
                      <div key={i} className={'finding ' + f.severity}>
                        <AlertCircle size={16} />
                        <div>
                          <b>{f.code}</b>
                          <p>{f.message}</p>
                        </div>
                      </div>
                    ))}
                    {!revision?.quality && (
                      <div className="notice">
                        成片生成后将检查时间线、素材引用、真实性标记与媒体完整性。
                      </div>
                    )}
                  </div>
                )}
              </section>
            </div>
          </div>
        )}
        {view === 'materials' && <MaterialBrowser />}
        {view === 'library' && (
          <div className="library-page">
            <div className="page-title">
              <div className="eyebrow">YOUR CREATIVE ARCHIVE</div>
              <h1>视频与版本</h1>
              <input
                ref={importRef}
                type="file"
                accept=".zip"
                hidden
                onChange={(e) => {
                  if (e.target.files?.[0]) importPackage(e.target.files[0]);
                  e.target.value = '';
                }}
              />
              <button
                className="secondary"
                disabled={busy}
                onClick={() => importRef.current?.click()}
              >
                <Upload size={14} />
                导入可编辑工程
              </button>
              <p>每一个想法，每一次迭代，都有迹可循。</p>
            </div>
            <div className="video-grid">
              {jobs.map((j) => (
                <button key={j.id} className="video-card panel" onClick={() => selectJob(j)}>
                  <div className="video-card-cover">
                    <Film size={32} />
                    <span>EXPLAINER / {j.revision_id.slice(-6)}</span>
                  </div>
                  <div className="video-card-body">
                    <b>{JSON.parse(j.brief).title}</b>
                    <p>
                      <span className={'dot ' + j.state.toLowerCase()} />
                      {stateLabels[j.state]}
                      <span>{new Date(j.created * 1000).toLocaleDateString()}</span>
                    </p>
                  </div>
                </button>
              ))}
              {!jobs.length && (
                <div className="panel empty">
                  <Film />
                  <h3>还没有视频</h3>
                  <p>从一个想法开始你的第一次创作。</p>
                  <button className="primary" onClick={reset}>
                    新建视频
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
        {view === 'settings' && (
          <div className="settings-page">
            <div className="page-title">
              <div className="eyebrow">SYSTEM CAPABILITIES</div>
              <h1>环境与能力</h1>
              <p>服务配置由部署环境管理；页面不会展示或保存模型密钥。</p>
            </div>
            <div className="cap-grid">
              {[
                [
                  Sparkles,
                  '内容引擎',
                  caps?.model ? caps.model_name : '本地模板',
                  '通过环境变量接入兼容聊天协议的模型',
                ],
                [
                  AudioLines,
                  '配音服务',
                  caps?.voice?.espeak
                    ? 'eSpeak 可用'
                    : caps?.voice?.qwen_configured
                      ? 'Qwen 已配置'
                      : '字幕版可用',
                  '正式男声可使用附带 Qwen3-TTS 服务',
                ],
                [
                  ShieldCheck,
                  '隔离执行',
                  caps?.runtime?.enabled && caps?.runtime?.docker ? '已启用' : '默认关闭',
                  '支持静态 Web、标准库 Python CLI',
                ],
                [
                  Command,
                  '任务调度',
                  caps?.scheduler || 'local',
                  '持久化租约队列，支持 Temporal 调度模式',
                ],
              ].map(([Icon, t, value, note]: any) => (
                <div className="panel cap-card" key={t}>
                  <Icon size={24} />
                  <span>{t}</span>
                  <b>{value}</b>
                  <p>{note}</p>
                </div>
              ))}
            </div>
            <section className="panel adapter-panel">
              <h2>自有素材库</h2>
              <p>按讲解目的选用图形与动效。已实现不代表整片或听感验收通过。</p>
              {caps?.material_library?.items?.map((item: any) => (
                <details key={item.id} className="material-entry">
                  <summary>
                    {item.name} · v{item.version} ·{' '}
                    {
                      (
                        { implemented: '已实现', unverified: '未验证', blocked: '受阻' } as Record<
                          string,
                          string
                        >
                      )[item.readiness]
                    }
                  </summary>
                  <p>{item.purpose}</p>
                  <small>
                    {item.kind} / {item.id}
                  </small>
                  <p>{item.provenance}</p>
                  <p>{item.rights}</p>
                </details>
              ))}
              <h2>原生 Agent</h2>
              {caps?.native_agents?.map((item: any) => (
                <p key={item.provider}>
                  {item.provider}：
                  {item.ready ? '当前进程已配置，待执行验证' : '执行时由专用 Worker 检查配置'}
                </p>
              ))}
              <h2>已注册适配器</h2>
              {caps?.adapters?.map((a: any) => (
                <div className="adapter" key={a.id}>
                  <span>
                    <b>{a.id}</b>
                    <small>
                      v{a.version} · protocol {a.protocol}
                    </small>
                  </span>
                  <span>{a.capabilities.join(' / ')}</span>
                  <CheckCircle2 size={16} />
                </div>
              ))}
            </section>
          </div>
        )}
      </main>
      {toast && (
        <div className="toast">
          <CheckCircle2 size={17} />
          {toast}
        </div>
      )}
      {help && (
        <div className="modal-overlay" onClick={() => setHelp(false)}>
          <section className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setHelp(false)} aria-label="关闭">
              <X />
            </button>
            <div className="eyebrow">GETTING STARTED</div>
            <h2>从输入到讲解视频</h2>
            <ol>
              <li>选择提示词或 ZIP 源码，设置标题、语言与目标时长。</li>
              <li>本地模板无需密钥；更深入的脚本可配置大模型服务。</li>
              <li>先看分镜或直接生成视频；在编辑器修改后另存版本。</li>
              <li>从成片下方下载视频、脚本、字幕与可编辑工程。</li>
            </ol>
            <div className="notice">
              开发音色使用 eSpeak，正式配音请配置
              Qwen3-TTS。字幕对齐方法会记录在质量报告中。真实运行需要隔离容器，支持范围见文档。
            </div>
            <p>
              完整工程附带
              README.md、docs/architecture.md、docs/api.md、docs/deployment.md、docs/security.md、docs/acceptance.md
              和原始设计方案。
            </p>
          </section>
        </div>
      )}
    </div>
  );
}

// Authentication owns the workspace lifecycle: leaving a session unmounts every private
// state/effect, so delayed requests cannot populate a different tenant's workspace.
function App() {
  const [session, setSession] = useState<any>(undefined);
  const [token, setToken] = useState(''),
    [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    // Local convenience: #token=<key> in the URL hash auto-logs in once.
    // The fragment stays client-side; the backend still validates the key.
    const hash = new URLSearchParams(location.hash.replace(/^#/, ''));
    const prefill = hash.get('token');
    if (prefill) {
      history.replaceState(null, '', location.pathname + location.search);
      post('/session', { token: prefill })
        .then(setSession)
        .catch(() => setSession(null));
      return;
    }
    request('/session')
      .then(setSession)
      .catch(() => setSession(null));
  }, []);
  async function login(e: React.FormEvent) {
    e.preventDefault();
    try {
      setBusy(true);
      setSession(await post('/session', { token }));
      setToken('');
      setError('');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  if (session === undefined)
    return (
      <div className="boot">
        <Loader2 className="spin" />
        正在连接工作空间
      </div>
    );
  if (!session)
    return (
      <main className="login">
        <Logo />
        <div className="login-card">
          <div className="eyebrow">YOUR IDEAS, EXPLAINED.</div>
          <h1>
            开始你的
            <br />
            下一个好故事。
          </h1>
          <p>从源码或一个想法出发，创作可以看见、听见、继续编辑的讲解视频。</p>
          <form onSubmit={login}>
            <label>工作空间访问密钥</label>
            <input
              aria-label="工作空间访问密钥"
              type="password"
              autoComplete="current-password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="输入启动时生成的访问密钥"
            />
            {error && <div className="error">{error}</div>}
            <button className="primary" disabled={busy}>
              {busy ? <Loader2 className="spin" size={17} /> : <ArrowRight size={17} />}进入工作空间
            </button>
          </form>
          <small>
            首次启动请查看终端提示，或读取 .data/access-token。密钥不会保存在浏览器本地存储中。
          </small>
        </div>
        <div className="login-art">
          <div className="art-orbit" />
          <div className="art-card art-one">
            <FileCode2 />
            <b>从内容出发</b>
            <span>SOURCE & IDEAS</span>
          </div>
          <div className="art-card art-two">
            <Film />
            <b>让理解发生</b>
            <span>STORY & MOTION</span>
          </div>
          <div className="art-dot" />
        </div>
      </main>
    );

  return (
    <Studio
      key={session.tenant}
      session={session}
      onLogout={async () => {
        await request('/session', { method: 'DELETE' });
        setSession(null);
      }}
    />
  );
}

createRoot(document.getElementById('root')!).render(<App />);
