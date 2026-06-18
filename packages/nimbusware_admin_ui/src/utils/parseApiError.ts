export function parseApiErrorBody(text: string): string {
  try {
    const prob = JSON.parse(text) as { detail?: string; title?: string };
    return prob.detail || prob.title || text;
  } catch {
    return text;
  }
}
