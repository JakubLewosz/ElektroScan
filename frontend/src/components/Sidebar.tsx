import {
  Activity,
  FileText,
  Layers,
  Loader2,
  MousePointer2,
  Pencil,
  Play,
  RotateCcw,
  Trash2,
  Upload,
} from 'lucide-react';
import type { RefObject } from 'react';

import type { AppStatus, CanvasMode, LayerInfo, TemplateInfo } from '../types';

interface SidebarProps {
  fileInputRef: RefObject<HTMLInputElement>;
  status: AppStatus;
  statusText: string;
  progressText: string;
  progressPercent: number;
  sessionId: string | null;
  layers: LayerInfo[];
  hiddenLayers: string[];
  templates: TemplateInfo[];
  mode: CanvasMode;
  manualSymbolName: string;
  symbolNames: string[];
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onRetry?: () => void;
  onExtractLegend: () => void;
  onAnalyze: () => void;
  onClearSession: () => void;
  onClearTemplates: () => void;
  onToggleLayer: (layerName: string) => void;
  onModeChange: (mode: CanvasMode) => void;
  onManualSymbolNameChange: (symbolName: string) => void;
  onRenameTemplate: (template: TemplateInfo) => void;
  onDeleteTemplate: (template: TemplateInfo) => void;
}

function templateCountLabel(count: number): string {
  if (count === 1) {
    return '1 wzorzec';
  }
  const lastDigit = count % 10;
  const lastTwoDigits = count % 100;
  if (lastDigit >= 2 && lastDigit <= 4 && (lastTwoDigits < 12 || lastTwoDigits > 14)) {
    return `${count} wzorce`;
  }
  return `${count} wzorców`;
}

export function Sidebar({
  fileInputRef,
  status,
  statusText,
  progressText,
  progressPercent,
  sessionId,
  layers,
  hiddenLayers,
  templates,
  mode,
  manualSymbolName,
  symbolNames,
  onFileChange,
  onRetry,
  onExtractLegend,
  onAnalyze,
  onClearSession,
  onClearTemplates,
  onToggleLayer,
  onModeChange,
  onManualSymbolNameChange,
  onRenameTemplate,
  onDeleteTemplate,
}: SidebarProps) {
  const hasTemplates = templates.length > 0;

  return (
    <aside className="min-h-0 overflow-auto border-b border-white/10 bg-app-panel xl:border-b-0 xl:border-r">
      <div className="border-b border-white/10 px-5 py-4">
        <h1 className="text-lg font-semibold tracking-normal text-white">ElektroScan</h1>
        <p className="mt-1 text-sm text-zinc-400">MVP zliczania symboli elektrycznych</p>
      </div>

      <nav className="space-y-4 p-4">
        <section className="rounded border border-white/10 bg-white/[0.03] p-4">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={status === 'processing'}
            className="flex w-full items-center gap-3 text-left text-sm font-medium text-zinc-200 transition hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Upload aria-hidden="true" className="h-4 w-4 text-app-accent" />
            <span>Upload PDF</span>
          </button>
          <input ref={fileInputRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={onFileChange} />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={status === 'processing'}
            className="mt-4 flex h-10 w-full items-center justify-center gap-2 rounded bg-app-strong px-3 text-sm font-semibold text-white transition hover:bg-orange-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {status === 'processing' ? (
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            ) : (
              <FileText aria-hidden="true" className="h-4 w-4" />
            )}
            Wybierz PDF
          </button>
        </section>

        <section className="space-y-2 rounded border border-white/10 bg-white/[0.03] p-4">
          <button
            type="button"
            className="flex w-full items-center gap-3 text-sm font-medium text-zinc-200"
            onClick={onExtractLegend}
            disabled={!sessionId || status === 'processing'}
          >
            <Pencil aria-hidden="true" className="h-4 w-4 text-app-accent" />
            Wyodrębnij legendę
          </button>
          <button
            type="button"
            className="flex w-full items-center gap-3 text-sm font-medium text-zinc-200"
            onClick={onAnalyze}
            disabled={!sessionId || status === 'processing'}
          >
            <Play aria-hidden="true" className="h-4 w-4 text-app-accent" />
            Analizuj plan
          </button>
          <button
            type="button"
            className="flex w-full items-center gap-3 text-sm font-medium text-zinc-200"
            onClick={onClearSession}
            disabled={!sessionId}
          >
            <Trash2 aria-hidden="true" className="h-4 w-4 text-app-accent" />
            Wyczyść sesję
          </button>
          <button
            type="button"
            className="flex w-full items-center gap-3 text-sm font-medium text-zinc-200"
            onClick={onClearTemplates}
            disabled={!sessionId}
          >
            <RotateCcw aria-hidden="true" className="h-4 w-4 text-app-accent" />
            Wyczyść wzorce
          </button>
        </section>

        <section className="rounded border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center gap-3 text-sm font-medium text-zinc-200">
            <Layers aria-hidden="true" className="h-4 w-4 text-app-accent" />
            <span>Warstwy PDF</span>
          </div>
          <div className="mt-3 space-y-2">
            {layers.length ? (
              layers.map((layer) => (
                <label key={layer.name} className="flex items-center gap-2 text-sm text-zinc-400">
                  <input
                    type="checkbox"
                    checked={!hiddenLayers.includes(layer.name)}
                    onChange={() => onToggleLayer(layer.name)}
                  />
                  <span>{layer.name}</span>
                </label>
              ))
            ) : (
              <p className="text-sm text-zinc-500">Brak warstw albo PDF nie jest jeszcze wgrany.</p>
            )}
          </div>
        </section>

        <section className="rounded border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center gap-3 text-sm font-medium text-zinc-200">
            <MousePointer2 aria-hidden="true" className="h-4 w-4 text-app-accent" />
            <span>Tryby canvasu</span>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {(['idle', 'zone', 'manual'] as CanvasMode[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onModeChange(item)}
                className={
                  mode === item
                    ? 'rounded bg-app-strong px-2 py-2 text-xs font-semibold text-white'
                    : 'rounded border border-white/10 px-2 py-2 text-xs text-zinc-300'
                }
              >
                {item === 'idle' ? 'Kursor' : item === 'zone' ? 'Exclude' : 'Manual'}
              </button>
            ))}
          </div>
          <select
            value={manualSymbolName}
            onChange={(event) => onManualSymbolNameChange(event.target.value)}
            className="mt-3 w-full rounded border border-white/10 bg-[#0f1013] px-2 py-2 text-sm text-zinc-200"
          >
            {symbolNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs text-zinc-500">Exclude/manual: przeciągnij prostokąt na planie.</p>
        </section>

        <section className="rounded border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center gap-3 text-sm font-medium text-zinc-200">
            <Activity aria-hidden="true" className="h-4 w-4 text-app-accent" />
            <span>Status</span>
          </div>
          <p className={status === 'error' ? 'mt-3 text-sm text-red-300' : 'mt-3 text-sm text-zinc-400'}>{statusText}</p>
          {status === 'error' && onRetry && (
            <button
              type="button"
              data-testid="status-retry"
              className="mt-3 flex h-9 w-full items-center justify-center gap-2 rounded border border-red-300/30 bg-red-500/10 px-3 text-sm font-semibold text-red-100 transition hover:bg-red-500/20"
              onClick={onRetry}
            >
              <RotateCcw aria-hidden="true" className="h-4 w-4" />
              Spróbuj ponownie
            </button>
          )}
          {progressText && (
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-xs text-zinc-500">
                <span>{progressText}</span>
                <span>{progressPercent}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded bg-white/10">
                <div className="h-full bg-app-strong transition-all" style={{ width: `${progressPercent}%` }} />
              </div>
            </div>
          )}
        </section>

        <section className="rounded border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-medium text-zinc-200">Baza wzorców</div>
            <span
              data-testid="template-count"
              className="shrink-0 rounded border border-white/10 px-2 py-1 text-[11px] font-semibold text-zinc-300"
            >
              {templateCountLabel(templates.length)}
            </span>
          </div>
          <p data-testid="template-state" className="mt-2 text-xs text-zinc-500">
            {!sessionId
              ? 'Wgraj PDF, żeby utworzyć bazę wzorców z legendy.'
              : hasTemplates
                ? 'Wzorce gotowe do analizy; możesz zmienić nazwy albo usunąć błędne pozycje.'
                : 'Brak wzorców. Użyj wyodrębnienia legendy albo dodaj je później ręcznie.'}
          </p>
          <div className="mt-3 space-y-2">
            {templates.map((template, index) => (
              <div key={template.name} data-testid="template-card" className="flex items-center gap-2 rounded border border-white/10 p-2">
                <span
                  data-testid="template-symbol-number"
                  className="grid h-6 min-w-6 shrink-0 place-items-center rounded border border-white/20 bg-black/50 px-1 text-xs font-bold text-white"
                >
                  {String(index + 1).padStart(2, '0')}
                </span>
                <img src={template.imgBase64} alt={template.displayName} className="h-8 w-8 object-contain" />
                <div className="min-w-0 flex-1">
                  <div data-testid="template-symbol-name" className="truncate text-xs text-zinc-200">{template.displayName}</div>
                  <div className="text-[11px] text-zinc-500">
                    {template.width} x {template.height}
                  </div>
                </div>
                <button
                  type="button"
                  aria-label={`Zmień nazwę wzorca ${template.displayName}`}
                  data-testid="template-rename"
                  disabled={status === 'processing'}
                  onClick={() => onRenameTemplate(template)}
                  className="text-zinc-400 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  aria-label={`Usuń wzorzec ${template.displayName}`}
                  data-testid="template-delete"
                  disabled={status === 'processing'}
                  onClick={() => onDeleteTemplate(template)}
                  className="text-zinc-400 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </section>
      </nav>
    </aside>
  );
}
