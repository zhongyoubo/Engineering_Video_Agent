import React, { useEffect, useState } from 'react';
import type { Scene } from '@explainer/video';
import { designPacks } from '../../../packages/engineering-template/src/theme';
import { media, request } from './api';

export function ProductionInspector({
  revision,
  scene,
  onEdit,
  disabled,
}: {
  revision: any;
  scene: Scene;
  onEdit: (patch: Partial<Scene>) => void;
  disabled: boolean;
}) {
  const [audio, setAudio] = useState<any>(null);
  const [clips, setClips] = useState<any[]>([]);
  const [comparison, setComparison] = useState<any>(null);
  const [loadError, setLoadError] = useState('');
  useEffect(() => {
    let live = true;
    setAudio(null);
    setClips([]);
    setComparison(null);
    setLoadError('');
    const getAsset = (id: string) =>
      fetch(media(id), { credentials: 'same-origin' }).then((r) => {
        if (!r.ok) throw new Error('产物暂不可读取');
        return r.json();
      });
    const tasks: Promise<unknown>[] = [];
    if (revision.outputs?.audio_analysis)
      tasks.push(
        getAsset(revision.outputs.audio_analysis).then((a) => {
          if (live) setAudio(a);
        }),
      );
    if (revision.outputs?.motion_previews)
      tasks.push(
        getAsset(revision.outputs.motion_previews).then((a) => {
          if (live) setClips(a);
        }),
      );
    if (revision.parent_id)
      tasks.push(
        request(`/v1/revisions/${revision.id}/compare/${revision.parent_id}`).then((a) => {
          if (live) setComparison(a);
        }),
      );
    Promise.all(tasks).catch((e) => {
      if (live) setLoadError(e.message);
    });
    return () => {
      live = false;
    };
  }, [revision.id, revision.outputs?.audio_analysis, revision.outputs?.motion_previews]);
  const activeTheme =
    designPacks[
      revision?.brief?.design_pack === 'neon_horizon'
        ? 'neon_horizon'
        : revision?.brief?.design_pack === 'editorial_warm'
          ? 'editorial_warm'
          : 'workspace_tech'
    ];
  const sceneClips = clips.filter((c) => c.scene_id === scene.id);
  const update = (motion: NonNullable<Scene['motion']>) => onEdit({ motion, compiled_events: [] });
  const updateVisual = (patch: Partial<NonNullable<Scene['visual_scene']>>) =>
    onEdit({ visual_scene: { ...scene.visual_scene!, ...patch }, compiled_object_events: [] });
  return (
    <div className="production-inspector">
      <h3>镜头与音画时间轴</h3>
      <p className="subtle">只展示实际产物。修改后请另存版本；共享组件变化仍需全片复审。</p>
      {scene.semantic_scene && (
        <div aria-label="语义场景时间轴">
          <h4>信息、状态与可见结果</h4>
          <p>{scene.semantic_scene.viewer_question}</p>
          <label>
            画面底色
            <input
              aria-label="语义画面底色"
              type="color"
              value={scene.semantic_scene.background_color || activeTheme.background}
              disabled={disabled}
              onChange={(event) =>
                onEdit({
                  semantic_scene: {
                    ...scene.semantic_scene!,
                    background_color: event.target.value,
                  },
                  compiled_semantic_events: [],
                })
              }
            />
          </label>
          {(scene.semantic_scene.parameters || []).map((parameter) => (
            <label key={parameter.id}>
              参数 {parameter.id} {parameter.unit}
              <input
                aria-label={'机制参数：' + parameter.id}
                type="number"
                min={parameter.minimum}
                max={parameter.maximum}
                step="any"
                value={parameter.initial}
                disabled={disabled}
                onChange={(event) => {
                  const value = Number(event.target.value);
                  if (
                    !Number.isFinite(value) ||
                    value < parameter.minimum ||
                    value > parameter.maximum
                  )
                    return;
                  onEdit({
                    semantic_scene: {
                      ...scene.semantic_scene!,
                      parameters: scene.semantic_scene!.parameters!.map((p) =>
                        p.id === parameter.id ? { ...p, initial: value } : p,
                      ),
                    },
                    compiled_semantic_events: [],
                  });
                }}
              />
            </label>
          ))}
          <p>插画背景：{scene.semantic_scene.background_asset_key || '无'}</p>
          {scene.semantic_scene.entities.map((entity) => (
            <label key={entity.id}>
              {entity.component}
              {entity.bind_to ? ' → ' + entity.bind_to + '.screen' : ''}
              <input
                aria-label={'语义标题：' + entity.id}
                value={entity.title}
                disabled={disabled}
                maxLength={60}
                onChange={(event) =>
                  onEdit({
                    semantic_scene: {
                      ...scene.semantic_scene!,
                      entities: scene.semantic_scene!.entities.map((e) =>
                        e.id === entity.id ? { ...e, title: event.target.value } : e,
                      ),
                    },
                    compiled_semantic_events: [],
                  })
                }
              />
            </label>
          ))}
          {scene.semantic_scene.events.map((e) => (
            <label key={e.id}>
              {e.action} · {e.target}
              {e.action === 'transform' &&
                ` → x:${e.x ?? '保持'} y:${e.y ?? '保持'} 透明度:${e.opacity ?? '保持'} 缩放:${e.scale ?? '保持'}`}
              <input
                aria-label={'语义旁白：' + e.id}
                value={e.anchor.phrase}
                disabled={disabled}
                onChange={(event) =>
                  onEdit({
                    semantic_scene: {
                      ...scene.semantic_scene!,
                      events: scene.semantic_scene!.events.map((v) =>
                        v.id === e.id
                          ? { ...v, anchor: { ...v.anchor, phrase: event.target.value } }
                          : v,
                      ),
                    },
                    compiled_semantic_events: [],
                  })
                }
              />
            </label>
          ))}
          <ul>
            {scene.semantic_scene.expectations.map((e) => (
              <li key={e.id}>{e.visible_result}</li>
            ))}
          </ul>
          <p>
            {scene.compiled_semantic_events?.length
              ? scene.compiled_semantic_events.every((e) => e.timing_source === 'measured_words')
                ? '真实旁白时间戳'
                : '草稿估计时间'
              : '保存后编译语义动作'}
          </p>
        </div>
      )}
      {scene.visual_scene && (
        <div aria-label="对象场景时间轴">
          <h4>对象、动作与结果</h4>
          <p>{scene.visual_scene.purpose}</p>
          <p>
            场景：{scene.visual_scene.setting}；对象：
            {scene.visual_scene.objects.map((o) => o.label).join('、')}
          </p>
          <p>交互提示音：{scene.visual_scene.sound_enabled ? '开启，旁白优先' : '关闭'}</p>
          <label className="checkbox">
            <input
              type="checkbox"
              aria-label="启用交互提示音"
              disabled={disabled}
              checked={scene.visual_scene.sound_enabled}
              onChange={(e) => updateVisual({ sound_enabled: e.target.checked })}
            />
            启用交互提示音
          </label>
          {scene.visual_scene.objects.map((o) => (
            <label key={o.id}>
              {o.label}
              <input
                aria-label={'对象标注：' + o.id}
                value={o.label}
                maxLength={40}
                disabled={disabled}
                onChange={(e) =>
                  updateVisual({
                    objects: scene.visual_scene!.objects.map((v) =>
                      v.id === o.id ? { ...v, label: e.target.value } : v,
                    ),
                  })
                }
              />
            </label>
          ))}
          {scene.visual_scene.events.map((e) => (
            <label key={e.id}>
              动作旁白：{e.action}
              <input
                aria-label={'动作旁白：' + e.id}
                value={e.anchor.phrase}
                maxLength={160}
                disabled={disabled}
                onChange={(event) =>
                  updateVisual({
                    events: scene.visual_scene!.events.map((v) =>
                      v.id === e.id
                        ? { ...v, anchor: { ...v.anchor, phrase: event.target.value } }
                        : v,
                    ),
                  })
                }
              />
            </label>
          ))}
          <ol>
            {scene.visual_scene.events.map((e) => (
              <li key={e.id}>
                {e.target} · {e.action} · 旁白“{e.anchor.phrase}”
              </li>
            ))}
          </ol>
          <p>
            {(scene.compiled_object_events || []).length
              ? scene.compiled_object_events!.some((e) => e.timing_source !== 'measured_words')
                ? '草稿估计时间，未验证实际配音'
                : '已依据实际时间戳编排'
              : '待配音对齐后编排'}
          </p>
        </div>
      )}
      {loadError && <p role="alert">{loadError}</p>}
      {sceneClips.length ? (
        sceneClips.map((clip) => (
          <div key={clip.asset_id}>
            <p>
              连续预览：{clip.start_frame}–{clip.end_frame} 帧
            </p>
            <video
              src={media(clip.asset_id)}
              controls
              preload="metadata"
              style={{ width: '100%' }}
            />
          </div>
        ))
      ) : (
        <p>连续预览：未生成 / 未验证</p>
      )}
      {audio ? (
        <>
          <svg
            viewBox="0 0 600 100"
            role="img"
            aria-label="实际旁白音频波形"
            style={{ width: '100%', background: '#eef4f7' }}
          >
            {audio.peaks.map((p: number, i: number) => (
              <line
                key={i}
                x1={(i * 600) / audio.peaks.length}
                x2={(i * 600) / audio.peaks.length}
                y1={50 - p * 48}
                y2={50 + p * 48}
                stroke="#087f83"
                strokeWidth="1"
              />
            ))}
          </svg>
          <small>
            全片 {audio.duration.toFixed(2)}s · Peak {audio.peak_dbfs} dBFS · RMS {audio.rms_dbfs}{' '}
            dBFS。波形与幅度不等于听感验收。
          </small>
          {revision.outputs?.narration && (
            <audio src={media(revision.outputs.narration)} controls style={{ width: '100%' }} />
          )}
        </>
      ) : (
        <p>实际波形：未生成 / 未验证</p>
      )}
      {(scene.motion?.code_focus || []).map((focus) => (
        <p key={focus.element_id}>
          代码定位：{focus.element_id} → 第 {focus.line}
          {focus.end_line ? `–${focus.end_line}` : ''} 行
        </p>
      ))}
      <label>
        视觉表达
        <select
          aria-label="视觉表达"
          disabled={disabled || Boolean(scene.visual_scene || scene.semantic_scene)}
          value={scene.visual_scene ? 'objects' : scene.motion?.pattern || ''}
          onChange={(e) => {
            if (!e.target.value) return;
            update({
              ...scene.motion,
              schema_version: '4.0',
              chapter: scene.motion?.chapter || '',
              purpose: scene.motion?.purpose || '解释当前镜头的核心机制',
              pattern: e.target.value as any,
              code_focus: e.target.value === 'code_scan' ? scene.motion?.code_focus || [] : [],
              layout: e.target.value === 'overview' ? scene.motion?.layout || 'grid' : 'grid',
              elements: scene.motion?.elements || [
                { id: 'input', label: '输入' },
                { id: 'output', label: '结果' },
              ],
              events: scene.motion?.events || [],
            });
          }}
        >
          {scene.visual_scene && <option value="objects">对象与交互场景</option>}
          <option value="">自由 TSX / 尚未指定</option>
          {Object.entries({
            overview: '卡片总览',
            code_scan: '代码扫描',
            compare: '左右对比',
            graph: '节点流程',
            capacity: '容量堆叠',
            queue: '队列瓶颈',
            depth: '深度隐喻',
          }).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {scene.motion && (
        <>
          {scene.motion.pattern === 'overview' && (
            <label>
              总览布局
              <select
                aria-label="总览布局"
                disabled={disabled}
                value={scene.motion.layout || 'grid'}
                onChange={(e) =>
                  update({ ...scene.motion!, layout: e.target.value as 'grid' | 'fan' })
                }
              >
                <option value="grid">网格</option>
                <option value="fan">弧形卡片</option>
              </select>
            </label>
          )}
          <label>
            讲解目标
            <textarea
              aria-label="镜头讲解目标"
              disabled={disabled}
              value={scene.motion.purpose}
              onChange={(e) => update({ ...scene.motion!, purpose: e.target.value })}
            />
          </label>
          {scene.motion.elements.map((element, i) => (
            <label key={element.id}>
              元素 {element.id}
              <input
                disabled={disabled}
                value={element.label}
                onChange={(e) =>
                  update({
                    ...scene.motion!,
                    elements: scene.motion!.elements.map((v, j) =>
                      i === j ? { ...v, label: e.target.value } : v,
                    ),
                  })
                }
              />
            </label>
          ))}
          <h4>旁白锚点与事件</h4>
          {scene.motion.events.map((event, i) => (
            <div key={event.id} className="motion-event">
              <b>
                {event.target} · {event.action}
              </b>
              <label>
                旁白短语
                <input
                  disabled={disabled}
                  value={event.anchor.phrase}
                  onChange={(e) =>
                    update({
                      ...scene.motion!,
                      events: scene.motion!.events.map((v, j) =>
                        i === j ? { ...v, anchor: { ...v.anchor, phrase: e.target.value } } : v,
                      ),
                    })
                  }
                />
              </label>
              <label>
                偏移毫秒
                <input
                  type="number"
                  min="-2000"
                  max="2000"
                  disabled={disabled}
                  value={event.anchor.offset_ms}
                  onChange={(e) =>
                    update({
                      ...scene.motion!,
                      events: scene.motion!.events.map((v, j) =>
                        i === j
                          ? { ...v, anchor: { ...v.anchor, offset_ms: Number(e.target.value) } }
                          : v,
                      ),
                    })
                  }
                />
              </label>
              <button
                disabled={disabled}
                onClick={() =>
                  update({
                    ...scene.motion!,
                    events: scene.motion!.events.filter((_, j) => j !== i),
                  })
                }
              >
                删除此事件
              </button>
            </div>
          ))}
          <button
            disabled={disabled || scene.motion.events.length >= 24}
            onClick={() => {
              const target = scene.motion!.elements.find(
                (el) =>
                  !scene.motion!.events.some((e) => e.target === el.id && e.action === 'progress'),
              );
              if (!target) return;
              update({
                ...scene.motion!,
                events: [
                  ...scene.motion!.events,
                  {
                    id: `event_${Date.now()}`,
                    target: target.id,
                    action: 'progress',
                    duration_ms: 700,
                    anchor: {
                      phrase: scene.narration.slice(0, 10),
                      occurrence: 1,
                      edge: 'start',
                      offset_ms: 0,
                    },
                  },
                ],
              });
            }}
          >
            添加旁白同步事件
          </button>
        </>
      )}
      <div className="event-track">
        {(scene.compiled_events || []).map((e) => (
          <div
            key={e.id}
            title={`${e.start_frame}–${e.end_frame} frames`}
            style={{
              marginLeft: `${(e.start_frame / scene.frames) * 100}%`,
              width: `${Math.max(1, ((e.end_frame - e.start_frame) / scene.frames) * 100)}%`,
              background: '#087f83',
              height: 8,
              marginTop: 6,
            }}
          />
        ))}
      </div>
      <small>时间锚点由实际旁白对齐后编译；缺失短语或超出镜头预算会报错。</small>
      {comparison && (
        <section>
          <h4>与上一版本比较</h4>
          <p>
            {comparison.changed_scenes.length} 个镜头变化 ·{' '}
            {comparison.settings_changed.join('、') || '制作配置相同'}
          </p>
          {comparison.changed_scenes.map((v: any) => (
            <p key={v.id}>
              {v.id}：{v.fields.join('、')}
            </p>
          ))}
        </section>
      )}
    </div>
  );
}
