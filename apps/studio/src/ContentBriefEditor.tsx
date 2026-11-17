import React from 'react';
import type { EditorialRequest, ContentStrategy } from '@explainer/video';

type Option = {
  id: string;
  label: string;
  entry_label?: string;
  question?: string;
  success_criteria?: string[];
};
type Taxonomy = {
  version: string;
  intents: Option[];
  subjects: Option[];
  presentation_forms: Option[];
  audience_levels: Option[];
};
export const defaultEditorialRequest: EditorialRequest = {
  intent: 'auto',
  secondary_intents: [],
  subject_kind: 'auto',
  audience_description: '',
  audience_level: 'auto',
  presentation_forms: [],
  core_message: '',
  viewer_takeaway: '',
};

export function editorialRequestChanged(a?: EditorialRequest, b?: EditorialRequest) {
  return (
    JSON.stringify({ ...defaultEditorialRequest, ...a }) !==
    JSON.stringify({ ...defaultEditorialRequest, ...b })
  );
}

export function ContentBriefEditor({
  value,
  onChange,
  taxonomy,
  prefix = '',
}: {
  value: EditorialRequest;
  onChange: (value: EditorialRequest) => void;
  taxonomy?: Taxonomy;
  prefix?: string;
}) {
  const update = (patch: Partial<EditorialRequest>) => onChange({ ...value, ...patch });
  const selected = taxonomy?.intents.find((i) => i.id === value.intent);
  const secondary = value.secondary_intents || [];
  const forms = value.presentation_forms || [];
  return (
    <div className="content-brief-fields">
      <label>{prefix}内容目的</label>
      <select
        aria-label={prefix + '内容目的'}
        value={value.intent}
        onChange={(e) =>
          update({
            intent: e.target.value as EditorialRequest['intent'],
            secondary_intents: secondary.filter((i) => i !== e.target.value),
          })
        }
      >
        <option value="auto">根据观众问题与资料策划</option>
        {taxonomy?.intents.map((i) => (
          <option key={i.id} value={i.id}>
            {i.entry_label} · {i.label}
          </option>
        ))}
      </select>
      {selected && (
        <div className="notice" data-content-purpose>
          {selected.question}
        </div>
      )}
      <details>
        <summary>辅助目的（可选，最多两项）</summary>
        {taxonomy?.intents.map((i) => (
          <label className="checkbox" key={i.id}>
            <input
              type="checkbox"
              aria-label={prefix + '辅助目的：' + i.label}
              checked={secondary.includes(i.id as EditorialRequest['secondary_intents'][number])}
              disabled={
                i.id === value.intent ||
                (secondary.length >= 2 &&
                  !secondary.includes(i.id as EditorialRequest['secondary_intents'][number]))
              }
              onChange={(e) =>
                update({
                  secondary_intents: e.target.checked
                    ? [...secondary, i.id as EditorialRequest['secondary_intents'][number]]
                    : secondary.filter((s) => s !== i.id),
                })
              }
            />
            {i.label}
          </label>
        ))}
      </details>
      <label>{prefix}讲述对象</label>
      <select
        aria-label={prefix + '讲述对象'}
        value={value.subject_kind}
        onChange={(e) =>
          update({ subject_kind: e.target.value as EditorialRequest['subject_kind'] })
        }
      >
        <option value="auto">根据资料确定</option>
        {taxonomy?.subjects.map((i) => (
          <option key={i.id} value={i.id}>
            {i.label}
          </option>
        ))}
      </select>
      <label>{prefix}目标观众描述（可选）</label>
      <input
        aria-label={prefix + '目标观众描述'}
        maxLength={500}
        value={value.audience_description}
        onChange={(e) => update({ audience_description: e.target.value })}
        placeholder="例如：需要中文视频配音、缺少部署经验的创作者"
      />
      <label>{prefix}讲述深度</label>
      <select
        aria-label={prefix + '讲述深度'}
        value={value.audience_level}
        onChange={(e) =>
          update({ audience_level: e.target.value as EditorialRequest['audience_level'] })
        }
      >
        <option value="auto">根据观众与主题确定</option>
        {taxonomy?.audience_levels.map((i) => (
          <option key={i.id} value={i.id}>
            {i.label}
          </option>
        ))}
      </select>
      <details>
        <summary>表现形式（可选，最多四项）</summary>
        {taxonomy?.presentation_forms.map((i) => (
          <label key={i.id} className="checkbox">
            <input
              type="checkbox"
              aria-label={prefix + '表现形式：' + i.label}
              checked={forms.includes(i.id)}
              disabled={forms.length >= 4 && !forms.includes(i.id)}
              onChange={(e) =>
                update({
                  presentation_forms: e.target.checked
                    ? [...forms, i.id]
                    : forms.filter((f) => f !== i.id),
                })
              }
            />
            {i.label}
          </label>
        ))}
      </details>
      <label>{prefix}核心主张（可选）</label>
      <input
        aria-label={prefix + '核心主张'}
        maxLength={500}
        value={value.core_message}
        onChange={(e) => update({ core_message: e.target.value })}
        placeholder="希望观众记住的一句话"
      />
      <label>{prefix}观众收益（可选）</label>
      <input
        aria-label={prefix + '观众收益'}
        maxLength={500}
        value={value.viewer_takeaway}
        onChange={(e) => update({ viewer_takeaway: e.target.value })}
        placeholder="看完能够理解、判断或完成什么"
      />
    </div>
  );
}

export function ContentBriefSummary({
  request,
  strategy: savedStrategy,
  taxonomy,
  pending = false,
}: {
  request?: EditorialRequest;
  strategy?: ContentStrategy | null;
  taxonomy?: Taxonomy;
  pending?: boolean;
}) {
  const strategy = pending ? null : savedStrategy;
  const label = (items: Option[] | undefined, id: string | undefined) =>
    items?.find((i) => i.id === id)?.label || (id === 'auto' || !id ? '待策划' : id);
  return (
    <div className="content-strategy-summary" aria-label="内容定位摘要">
      {pending && <p role="status">内容目标已修改，待另存版本后重新策划；当前画面仍为原分镜。</p>}
      <p>
        <b>主要目的：</b>
        {label(taxonomy?.intents, strategy?.intent || request?.intent)}
        {!strategy && '（尚未完成类型策划）'}
      </p>
      <p>
        <b>辅助目的：</b>
        {(strategy?.secondary_intents || request?.secondary_intents || [])
          .map((i) => label(taxonomy?.intents, i))
          .join('、') || '无'}
      </p>
      <p>
        <b>讲述对象：</b>
        {label(taxonomy?.subjects, strategy?.subject_kind || request?.subject_kind)}
      </p>
      <p>
        <b>目标观众：</b>
        {strategy?.audience_description || request?.audience_description || '待策划'} ·{' '}
        {label(taxonomy?.audience_levels, strategy?.audience_level || request?.audience_level)}
      </p>
      <p>
        <b>表现形式：</b>
        {(strategy?.presentation_forms || request?.presentation_forms || [])
          .map((i) => label(taxonomy?.presentation_forms, i))
          .join('、') || '待策划'}
      </p>
      {strategy && (
        <>
          <p>
            <b>策划理由：</b>
            {strategy.rationale}
          </p>
          <details>
            <summary>叙事结构与验收目标</summary>
            <ol>
              {strategy.outline.map((b, i) => (
                <li key={i}>{b.purpose}</li>
              ))}
            </ol>
            <ul>
              {strategy.success_criteria.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </div>
  );
}
