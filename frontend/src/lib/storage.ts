export function createScopedStorageKey(
  sessionId: string,
  analysisId: string,
  key: string,
): string {
  return `elektroscan:${sessionId}:${analysisId}:${key}`;
}
