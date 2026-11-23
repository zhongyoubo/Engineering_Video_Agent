import React, { useEffect, useState } from 'react';
import { request } from './api';

type Material = {
  id: string;
  version: string;
  name: string;
  purpose: string;
  asset_type?: string;
  styles?: string[];
  subjects?: string[];
  affordances?: string[];
  parameters?: Record<string, string>;
  preview?: string;
  module?: string;
  rights: string;
  provenance: string;
  source_sha256: string;
};

/** Authenticated previews are raster data; the Studio never imports pack/user TSX. */
export function MaterialBrowser() {
  const [query, setQuery] = useState(''),
    [style, setStyle] = useState(''),
    [type, setType] = useState('');
  const [items, setItems] = useState<Material[]>([]),
    [error, setError] = useState('');
  const [copied, setCopied] = useState(''),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const timer = setTimeout(() => {
      const search = new URLSearchParams({ query, style, asset_type: type });
      request<{ items: Material[] }>('/v1/material-library?' + search, {
        signal: controller.signal,
      })
        .then((data) => {
          if (controller.signal.aborted) return;
          setItems(data.items);
          setError('');
        })
        .catch((e) => {
          if (!controller.signal.aborted) {
            setItems([]);
            setError(e.message);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, style, type]);
  async function copyReference(item: Material) {
    const ref = `library:${item.id}@${item.version}`;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(ref);
      setCopied(ref);
    } catch {
      setError('复制失败，请从下方引用文本复制。');
    }
  }
  return (
    <div className="library-page">
      <h1>素材库</h1>
      <p>按对象、用途和风格查找素材。Agent 可按需装载组件，或通过素材工具导入图片和三维模型。</p>
      <div className="material-filters">
        <label>
          搜索素材
          <input
            aria-label="搜索素材"
            value={query}
            maxLength={160}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="书本、终端、对话、模型…"
          />
        </label>
        <label>
          素材风格
          <select aria-label="素材风格" value={style} onChange={(e) => setStyle(e.target.value)}>
            <option value="">全部风格</option>
            <option value="duotone">双色矢量</option>
            <option value="soft3d">立体插画</option>
            <option value="typography">文字动效</option>
            <option value="textured3d">实物三维</option>
          </select>
        </label>
        <label>
          素材类型
          <select aria-label="素材类型" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">全部类型</option>
            <option value="component">源码组件</option>
            <option value="image">PNG 图片</option>
            <option value="model">GLB 模型</option>
          </select>
        </label>
      </div>
      {error && <p role="alert">{error}</p>}
      <p aria-live="polite">{loading ? '正在加载素材…' : `${items.length} 项素材`}</p>
      <div className="material-grid">
        {!loading &&
          items.map((item) => (
            <article key={item.id + '@' + item.version} className="panel material-card">
              <div className="material-preview">
                {item.preview ? (
                  <img loading="lazy" src={item.preview} alt={item.name} />
                ) : (
                  <span>{item.asset_type === 'component' ? '按帧组件' : '工程积木'}</span>
                )}
              </div>
              <h3>{item.name}</h3>
              <p>{item.purpose}</p>
              <div className="material-tags">
                {item.styles?.map((s) => <span key={s}>{s}</span>)}
              </div>
              <small>
                {item.asset_type || '内置组件'} · v{item.version} · {item.rights}
              </small>
              <details>
                <summary>用法与来源</summary>
                <p>{item.affordances?.join(' · ')}</p>
                {item.module && <code>{item.module}</code>}
                {Object.entries(item.parameters || {}).map(([name, value]) => (
                  <p key={name}>
                    <b>{name}</b>：{value}
                  </p>
                ))}
                <p>{item.provenance}</p>
                <code>SHA256 {item.source_sha256}</code>
              </details>
              <button onClick={() => copyReference(item)}>
                {copied === `library:${item.id}@${item.version}` ? '已复制引用' : '复制引用'}
              </button>
              <code className="material-ref">
                library:{item.id}@{item.version}
              </code>
            </article>
          ))}
      </div>
    </div>
  );
}
