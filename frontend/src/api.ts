import type {
  AnalyzePayload,
  AnalyzeResponse,
  LayerInfo,
  PreviewResponse,
  ProgressEvent,
  RenderPreviewResponse,
  TemplateInfo,
} from './types';

export const API_BASE_URL = 'http://127.0.0.1:8010/api';

async function readJsonError(response: Response, fallback: string): Promise<never> {
  const body = await response.json().catch(() => null);
  throw new Error(body?.detail ?? body?.message ?? fallback);
}

export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    return readJsonError(response, 'Backend health check failed');
  }
  return response.json();
}

export async function uploadPreview(file: File): Promise<PreviewResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/preview`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie wgrac PDF.');
  }

  return response.json();
}

export async function fetchLayers(sessionId: string): Promise<LayerInfo[]> {
  const response = await fetch(`${API_BASE_URL}/layers?session_id=${sessionId}`);
  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie pobrac warstw.');
  }
  return response.json();
}

export async function renderPreview(sessionId: string, hiddenLayers: string[]): Promise<RenderPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/render-preview?session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hiddenLayers }),
  });
  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie wyrenderowac podgladu.');
  }
  return response.json();
}

export async function extractLegend(sessionId: string, payload: AnalyzePayload): Promise<TemplateInfo[]> {
  const response = await fetch(`${API_BASE_URL}/extract-legend?session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie wyodrebnic legendy.');
  }
  return response.json();
}

export async function fetchTemplates(sessionId: string): Promise<TemplateInfo[]> {
  const response = await fetch(`${API_BASE_URL}/templates?session_id=${sessionId}`);
  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie pobrac wzorcow.');
  }
  return response.json();
}

export async function renameTemplate(sessionId: string, templateName: string, newName: string): Promise<TemplateInfo[]> {
  const response = await fetch(`${API_BASE_URL}/templates/${encodeURIComponent(templateName)}?session_id=${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ newName }),
  });
  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie zmienic nazwy wzorca.');
  }
  return response.json();
}

export async function deleteTemplate(sessionId: string, templateName: string): Promise<TemplateInfo[]> {
  const response = await fetch(`${API_BASE_URL}/templates/${encodeURIComponent(templateName)}?session_id=${sessionId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie usunac wzorca.');
  }
  return response.json();
}

export async function clearTemplates(sessionId: string): Promise<TemplateInfo[]> {
  const response = await fetch(`${API_BASE_URL}/templates?session_id=${sessionId}`, { method: 'DELETE' });
  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie wyczyscic wzorcow.');
  }
  return response.json();
}

export async function clearSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/clear?session_id=${sessionId}`, { method: 'POST' });
  if (!response.ok) {
    return readJsonError(response, 'Nie udalo sie wyczyscic sesji.');
  }
}

function parseSseMessage(raw: string): { event: string; data: string } | null {
  let event = 'message';
  const data: string[] = [];
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      data.push(line.slice(5).trimStart());
    }
  }
  if (!data.length) {
    return null;
  }
  return { event, data: data.join('\n') };
}

export async function analyzePlan(
  sessionId: string,
  payload: AnalyzePayload,
  signal: AbortSignal,
  handlers: {
    onProgress: (event: ProgressEvent) => void;
    onResult: (result: AnalyzeResponse) => void;
    onError: (message: string) => void;
    onHeartbeat: () => void;
  },
): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/analyze?session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok || !response.body) {
    return readJsonError(response, 'Nie udalo sie uruchomic analizy.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let gotResult = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    handlers.onHeartbeat();
    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replace(/\r\n/g, '\n');

    while (buffer.includes('\n\n')) {
      const boundary = buffer.indexOf('\n\n');
      const chunk = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const message = parseSseMessage(chunk);
      if (!message) {
        continue;
      }

      const data = JSON.parse(message.data);
      if (message.event === 'progress') {
        handlers.onProgress(data);
      } else if (message.event === 'result') {
        gotResult = true;
        handlers.onResult(data);
      } else if (message.event === 'error') {
        handlers.onError(data.message ?? 'Analiza zakonczona bledem.');
      }
    }
  }

  return gotResult;
}
