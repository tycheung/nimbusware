/** Trigger a browser download for in-memory content. */
export function downloadBlob(content, filename, mimeType = "application/octet-stream") {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
