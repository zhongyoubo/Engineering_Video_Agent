(() => {
  const definitions = {
    definition: { purpose: '讲清“它是什么”', detail: '先给准确的一句话，再用具体动作说明边界。适合概念开场。', composition: '大词 + 可识别对象', layout: '一个重点词，一个能完成任务的对象；保留字幕和结果区。', motion: '标题先出现，对象再入场，最后显示行动结果。', visual: 'object' },
    analogy: { purpose: '借熟悉的经验理解新概念', detail: '类比只解释一个关系，随后点明类比的边界。', composition: '熟悉事物 → 新概念', layout: '两个对应对象和一条明确的关系线。', motion: '先展示生活情境，再揭示对应关系，最后标出差异。', visual: 'pair' },
    anatomy: { purpose: '认识组成与职责', detail: '把部件和作用配对；组成不等于固定公式，不同 Agent 的实现可能不同。', composition: '部件与职责成组', layout: '同层部件使用网格；有依赖时改用连接线。', motion: '按讲述顺序逐个出现，停留后再归纳整体。', visual: 'parts' },
    process: { purpose: '看懂动作如何产生结果', detail: '呈现目标、操作、观察和调整；用可见结果检验因果链。', composition: '前态 → 动作 → 后态', layout: '对象要保持身份，状态变化和结果应能被直接看见。', motion: '前态停留、动作发生、结果显现；结果至少保持 2 秒。', visual: 'flow' },
    comparison: { purpose: '比较两种方式的差异', detail: '使用同一任务和同一衡量维度，避免只用颜色表达优劣。', composition: '共同问题 + 并列结果', layout: '左右保持同尺度；每侧只展示一个关键差异。', motion: '先提出共同问题，再展示两侧行为，最后点明差异。', visual: 'compare' },
    summary: { purpose: '留下观众可用的结论', detail: '回顾一条核心判断，并给出一个能够尝试的下一步。', composition: '结论 + 下一步', layout: '一句结论、一个行动提示，画面保持简洁。', motion: '结论与下一步依次出现，结束前留足阅读时间。', visual: 'finish' }
  };
  const content = {
    dark: {
      label: '01 深青编辑', caption: '1920×1080 基准：字幕置于底部 155 px 区域，建议 42–52 px、每行不超过 18 个汉字；最多两行。浅色字配深色半透明底，避免遮挡动作结果。',
      scenes: {
        definition: ['什么是 AI Agent？', '会完成任务的助手', '它能围绕目标采取行动，并检查结果。'],
        analogy: ['换个生活例子', '数字员工', '你交代目标，它选择步骤、使用工具并汇报。'],
        anatomy: ['一个 Agent 包含什么？', '能力需要协作', '模型、工具、状态与约束共同支撑任务。'],
        process: ['它怎样完成任务？', '行动 → 观察', '执行后检查结果，必要时调整下一步。'],
        comparison: ['与聊天式 GPT 有何区别？', '回答 vs 完成任务', '用同一个预约任务比较行动范围。'],
        summary: ['现在你可以试一试', '给出目标与权限', '从一项明确、可检查的小任务开始。']
      }
    },
    warm: {
      label: '02 暖白插画', caption: '1920×1080 基准：底部预留 155 px 字幕区，建议 42–52 px、每行不超过 18 个汉字；最多两行。深青字幕底确保浅色背景上仍清晰。',
      scenes: {
        definition: ['认识 AI Agent', '目标驱动的助手', '它会用可用的工具推进任务。'],
        analogy: ['想象一个数字员工', '交代任务 → 查看成果', '类比帮助入门，实际能力取决于工具和权限。'],
        anatomy: ['一个 Agent 包含什么？', '模型 · 工具 · 状态', '还需要任务目标、执行规则与结果检查。'],
        process: ['任务如何推进？', '计划 · 执行 · 观察', '每一步都要看实际结果，再决定是否继续。'],
        comparison: ['两种使用方式', '聊天回答 / 任务执行', '同样的问题，工具与权限决定能做什么。'],
        summary: ['开始使用 Agent', '从小任务开始', '写清目标、可用资料、权限和验收结果。']
      }
    }
  };
  const $ = (id) => document.getElementById(id);
  const stage = $('scene-stage');
  const frame = $('scene-frame');
  let pack = location.hash === '#warm' ? 'warm' : 'dark';
  let playing = null;
  const iconCatalog = {
    dark: [['goal','目标'],['model','模型'],['memory','记忆'],['tool','工具'],['observe','观察'],['result','结果']],
    warm: [['brain','模型'],['file','记忆'],['tool','工具'],['calendar','规划'],['search','观察'],['shield','权限']]
  };
  const iconShapes = {
    dark: {
      goal: '<circle cx="50" cy="50" r="31"/><circle cx="50" cy="50" r="16"/><circle cx="50" cy="50" r="3"/>',
      model: '<path d="M24 38c-11-15 8-29 19-20 8-10 29-5 30 9 15 4 17 23 5 31 7 16-9 29-23 22-12 10-30 2-29-12-14-5-15-22-2-30Z"/><path d="M42 31c-7 8-7 16 1 23m17-26c9 8 10 18 2 27M37 68c8-8 18-8 27 0"/>',
      memory: '<rect x="20" y="17" width="60" height="66" rx="8"/><path d="M31 35h38M31 49h38M31 63h24"/>',
      tool: '<rect x="14" y="34" width="72" height="49" rx="8"/><path d="M35 34V22h30v12M14 56c20 16 52 16 72 0"/>',
      observe: '<circle cx="43" cy="43" r="24"/><path d="m61 61 23 23M33 43h20m-10-10v20"/>',
      result: '<path d="M21 18h58v64H21zM32 50l11 11 25-27M33 72h35"/>'
    },
    warm: {
      brain: '<circle cx="50" cy="50" r="17"/><path d="M50 9v15m0 52v15M9 50h15m52 0h15M21 21l11 11m36 36 11 11M79 21 68 32M32 68 21 79"/>',
      file: '<path d="M23 10h38l17 18v60H23zM61 10v19h17M34 46h32M34 59h32M34 72h22"/>',
      tool: '<rect x="12" y="32" width="76" height="53" rx="10"/><path d="M34 32V20h32v12M12 55c22 19 54 19 76 0"/>',
      calendar: '<rect x="15" y="22" width="70" height="65" rx="9"/><path d="M15 42h70M33 12v20M67 12v20M33 58h10M56 58h10M33 73h10"/>',
      search: '<circle cx="44" cy="43" r="25"/><path d="m63 63 24 24"/>',
      shield: '<path d="M50 10 81 23v24c0 21-12 34-31 44-19-10-31-23-31-44V23z"/><path d="m36 50 10 10 20-23"/>'
    }
  };
  const iconSvg = (id) => `<svg viewBox="0 0 100 100" aria-hidden="true">${iconShapes[pack][id]}</svg>`;
  const part = (markup, start, motion = 'rise') => `<span class="motion-part" data-appear="${start}" data-motion="${motion}">${markup}</span>`;
  const card = (label, icon, start) => part(`<span class="visual-card">${iconSvg(icon)}<span>${label}</span></span>`, start);
  const arrow = (start) => part('<span class="visual-arrow">→</span>', start, 'draw');
  const visualFor = (kind) => {
    const ids = pack === 'dark' ? ['goal','model','memory','tool','observe','result'] : ['calendar','brain','file','tool','search','shield'];
    switch (kind) {
      case 'object': return `${part(iconSvg(ids[0]),14,'pop')}${arrow(30)}${part('<span class="visual-label">完成一项可检查的任务</span>',42)}`;
      case 'pair': return `${card('熟悉的任务',ids[0],14)}${arrow(28)}${card('Agent 的任务',ids[3],42)}${part('<span class="visual-small">类比有边界</span>',52)}`;
      case 'parts': return `${card('模型',ids[1],14)}${card('记忆',ids[2],22)}${card('工具',ids[3],30)}${card('观察',ids[4],38)}${part('<span class="visual-small">部件各有职责</span>',48)}`;
      case 'flow': return `${card('目标',ids[0],12)}${arrow(22)}${card('动作',ids[3],30)}${arrow(40)}${card('结果',ids[5],48)}`;
      case 'compare': return `${card('回答问题',ids[1],14)}${arrow(28)}${card('完成任务',ids[3],40)}${part('<span class="visual-small">同一任务 · 不同行为</span>',52)}`;
      default: return `${card('核心结论',ids[5],14)}${arrow(28)}${card('下一步',ids[0],42)}`;
    }
  };
  function currentKind() { return $('scene-kind').value; }
  function stop() { if (playing) cancelAnimationFrame(playing); playing = null; $('play-scene').textContent = '▶ 播放'; }
  function drawFrame() {
    const f = Number(frame.value);
    $('frame-label').textContent = `${f} / 150 帧`;
    const progress = (start, duration) => Math.max(0, Math.min(1, (f - start) / duration));
    const reveal = (element, start, duration = 9) => {
      const p = progress(start, duration);
      element.style.opacity = String(p);
      element.style.transform = `translateY(${(1-p)*16}px)`;
    };
    reveal($('scene-preview-title'), 0);
    reveal($('scene-preview-key'), 10);
    reveal($('scene-preview-detail'), 34);
    reveal($('scene-caption'), 44);
    $('scene-visual').querySelectorAll('[data-appear]').forEach(element => {
      const p = progress(Number(element.dataset.appear), 10);
      element.style.opacity = String(p);
      element.style.transform = element.dataset.motion === 'draw' ? `scaleX(${p})` : element.dataset.motion === 'pop' ? `scale(${.75+.25*p})` : `translateY(${(1-p)*17}px)`;
    });
  }
  function drawText() {
    $('scene-preview-title').textContent = $('scene-title').value || '场景标题';
    $('scene-preview-key').textContent = $('scene-key').value || '重点词';
    $('scene-preview-detail').textContent = $('scene-detail').value || '一句说明';
    $('scene-caption').textContent = $('scene-detail').value || '一句字幕';
  }
  function selectScene() {
    stop();
    const kind = currentKind();
    const spec = definitions[kind];
    $('scene-brow').textContent = `AI AGENT / ${$('scene-kind').selectedOptions[0].textContent}`;
    const [title, key, detail] = content[pack].scenes[kind];
    $('scene-title').value = title;
    $('scene-key').value = key;
    $('scene-detail').value = detail;
    $('scene-purpose').textContent = spec.purpose;
    $('scene-purpose-detail').textContent = spec.detail;
    $('scene-composition').textContent = spec.composition;
    $('scene-composition-detail').textContent = spec.layout;
    $('scene-motion-detail').textContent = spec.motion;
    $('scene-visual').innerHTML = visualFor(spec.visual);
    frame.value = 150;
    drawText(); drawFrame();
  }
  function setPack(next) {
    pack = next;
    stage.classList.toggle('dark-theme', next === 'dark');
    stage.classList.toggle('warm-theme', next === 'warm');
    $('studio-pack-name').textContent = content[next].label;
    $('caption-spec').textContent = content[next].caption;
    $('caption-demo').textContent = next === 'dark' ? '先给明确目标，再观察 Agent 如何行动。' : '模型负责理解，工具负责执行，结果需要检查。';
    $('studio-icon-download').href = `${next === 'dark' ? 'dark-editorial' : 'warm-illustrated'}/assets/icon-set.svg`;
    $('studio-icon-gallery').classList.toggle('dark-icons', next === 'dark');
    $('studio-icon-gallery').innerHTML = iconCatalog[next].map(([id,label]) => `<div class="studio-icon"><div>${iconSvg(id)}</div><strong>${label}</strong><small>#${id}</small></div>`).join('');
    selectScene();
  }
  $('scene-kind').addEventListener('change', selectScene);
  ['scene-title', 'scene-key', 'scene-detail'].forEach(id => $(id).addEventListener('input', drawText));
  document.querySelectorAll('.ratio').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.ratio').forEach(b => { const selected = b === button; b.classList.toggle('active', selected); b.setAttribute('aria-pressed', String(selected)); });
    stage.classList.remove('wide', 'square', 'vertical');
    stage.classList.add(button.dataset.ratio);
  }));
  frame.addEventListener('input', () => { stop(); drawFrame(); });
  $('play-scene').addEventListener('click', () => {
    if (playing) { stop(); return; }
    frame.value = 0; drawFrame();
    $('play-scene').textContent = 'Ⅱ 暂停';
    let start;
    const tick = (now) => {
      if (start === undefined) start = now;
      frame.value = Math.min(150, Math.floor((now - start) / 1000 * 30));
      drawFrame();
      if (Number(frame.value) >= 150) { stop(); return; }
      playing = requestAnimationFrame(tick);
    };
    playing = requestAnimationFrame(tick);
  });
  document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => setPack(tab.dataset.tab)));
  document.querySelectorAll('.motion-card').forEach(button => button.addEventListener('click', () => {
    $('scene-kind').value = button.dataset.scene;
    selectScene();
    stage.scrollIntoView({behavior:'smooth',block:'center'});
    $('play-scene').click();
  }));
  setPack(pack);
})();
