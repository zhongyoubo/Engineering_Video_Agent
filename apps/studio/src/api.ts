export async function request<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set('Content-Type', 'application/json');
  const response = await fetch('/api' + path, { ...options, headers, credentials: 'include' });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error?.message || `请求失败 (${response.status})`);
  }
  return response.json();
}
export const media = (id: string, download = false) =>
  '/api/v1/assets/' + id + (download ? '?download=true' : '');
export const post = <T = any>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) });
export type Project = { id: string; name: string; created: number };
export type Job = {
  id: string;
  revision_id: string;
  state: string;
  stage: string;
  progress: number;
  error?: string;
  created: number;
  brief: string;
};
