/** Protected source viewport: wraps every character, keeps original line IDs and pages. */
import React from 'react';
import type { Scene } from './contracts';

export function codeRows(code: string, units = 68) {
  return code.split('\n').flatMap((line, index) => {
    const rows: { line: number; text: string; continued: boolean }[] = [];
    let text = '',
      width = 0;
    for (const char of line.replace(/\t/g, '    ')) {
      const size = char.codePointAt(0)! > 255 ? 2 : 1;
      if (width + size > units) {
        rows.push({ line: index + 1, text, continued: rows.length > 0 });
        text = '';
        width = 0;
      }
      text += char;
      width += size;
    }
    rows.push({ line: index + 1, text, continued: rows.length > 0 });
    return rows;
  });
}
export function codeViewport(scene: Scene, frame: number, progress: number) {
  const rows = codeRows(scene.code);
  const bindings = scene.motion?.code_focus || [];
  const active = bindings.filter((binding) =>
    (scene.compiled_events || []).some(
      (event) => event.target === binding.element_id && event.start_frame <= frame,
    ),
  );
  const binding = active
    .sort((a, b) => {
      const start = (id: string) =>
        Math.max(
          -1,
          ...(scene.compiled_events || [])
            .filter((e) => e.target === id && e.start_frame <= frame)
            .map((e) => e.start_frame),
        );
      return start(a.element_id) - start(b.element_id);
    })
    .at(-1);
  let position = Math.min(
    rows.length - 1,
    Math.floor(Math.max(0, Math.min(1, progress)) * rows.length),
  );
  if (binding) {
    const first = rows.findIndex((row) => row.line === binding.line);
    const last = rows.reduce(
      (index, row, i) => (row.line <= (binding.end_line || binding.line) ? i : index),
      first,
    );
    const event = (scene.compiled_events || [])
      .filter((e) => e.target === binding.element_id && e.start_frame <= frame)
      .sort((a, b) => a.start_frame - b.start_frame)
      .at(-1)!;
    const t = Math.max(
      0,
      Math.min(1, (frame - event.start_frame) / Math.max(1, event.end_frame - event.start_frame)),
    );
    position = first + Math.floor((last - first) * t);
  }
  const page = Math.floor(Math.max(0, position) / 14);
  return {
    rows: rows.slice(page * 14, page * 14 + 14),
    page,
    pages: Math.ceil(rows.length / 14),
    binding,
    scan: Math.max(0, position) % 14,
  };
}
export function CodeViewport({
  scene,
  frame,
  progress,
  accent,
}: {
  scene: Scene;
  frame: number;
  progress: number;
  accent: string;
}) {
  const view = codeViewport(scene, frame, progress);
  return (
    <g data-code-page={view.page + 1}>
      <rect x="0" y="10" width="1040" height="570" rx="20" fill="#102e34" />
      <text
        x="24"
        y="40"
        fontSize="17"
        fill="#b6cec8"
      >{`源码 ${view.page + 1}/${view.pages}`}</text>
      {view.rows.map((row, i) => (
        <g key={i} data-source-line={row.line}>
          {view.binding &&
            row.line >= view.binding.line &&
            row.line <= (view.binding.end_line || view.binding.line) && (
              <rect x="0" y={50 + i * 35} width="1040" height="34" fill={accent} opacity=".22" />
            )}
          <text x="22" y={75 + i * 35} fontSize="17" fill="#8ba7a2">
            {row.continued ? '↳' : row.line}
          </text>
          <text
            x="75"
            y={75 + i * 35}
            fontFamily="monospace"
            fontSize="21"
            fill="#e0ede7"
            xmlSpace="preserve"
          >
            {row.text}
          </text>
        </g>
      ))}
      <rect x="0" y={52 + view.scan * 35} width="1040" height="3" fill={accent} />
    </g>
  );
}
