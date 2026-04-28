import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

import type {
  AnalyzeResponse,
  BoxStatus,
  DetectionBox,
  DetectionFilter,
  PreviewResponse,
  ResultItem,
  ResultsTab,
  TemplateInfo,
} from '../types';

interface ResultsPanelProps {
  analysis: AnalyzeResponse | null;
  preview: PreviewResponse | null;
  tab: ResultsTab;
  results: ResultItem[];
  templates: TemplateInfo[];
  activeBoxes: DetectionBox[];
  boxStatuses: Record<string, BoxStatus>;
  hiddenSymbolTypes: Record<string, boolean>;
  focusedBoxId: string | null;
  symbolNames: string[];
  symbolNumberMap: Record<string, string>;
  totalCount: number;
  onTabChange: (tab: ResultsTab) => void;
  onToggleSymbolType: (symbolName: string) => void;
  onStartSlideshow: (symbolName: string) => void;
  onMarkBox: (boxId: string, status: BoxStatus) => void;
  onChangeBoxType: (boxId: string, symbolName: string) => void;
  onShowBox: (box: DetectionBox) => void;
}

const LOW_CONFIDENCE_THRESHOLD = 0.6;

function statusOf(statuses: Record<string, BoxStatus>, boxId: string): BoxStatus {
  return statuses[boxId] ?? 'pending';
}

function cropStyle(preview: PreviewResponse, box: DetectionBox): React.CSSProperties {
  const size = 56;
  const margin = 10;
  const cropWidth = Math.max(box.width + margin * 2, box.height + margin * 2);
  const scale = size / cropWidth;
  return {
    width: size,
    height: size,
    backgroundImage: `url(${preview.previewImage})`,
    backgroundRepeat: 'no-repeat',
    backgroundSize: `${preview.pageSize.width * scale}px ${preview.pageSize.height * scale}px`,
    backgroundPosition: `${-(box.x - margin) * scale}px ${-(box.y - margin) * scale}px`,
  };
}

export function ResultsPanel({
  analysis,
  preview,
  tab,
  results,
  templates,
  activeBoxes,
  boxStatuses,
  hiddenSymbolTypes,
  focusedBoxId,
  symbolNames,
  symbolNumberMap,
  totalCount,
  onTabChange,
  onToggleSymbolType,
  onStartSlideshow,
  onMarkBox,
  onChangeBoxType,
  onShowBox,
}: ResultsPanelProps) {
  const [filter, setFilter] = useState<DetectionFilter>('all');
  const filteredBoxes = activeBoxes.filter((box) => {
    if (filter === 'low') {
      return box.verificationScore < LOW_CONFIDENCE_THRESHOLD;
    }
    if (filter === 'pending') {
      return statusOf(boxStatuses, box.id) === 'pending';
    }
    return true;
  });

  return (
    <aside className="min-h-0 overflow-auto border-t border-white/10 bg-app-panel xl:border-l xl:border-t-0">
      <div className="border-b border-white/10 px-5 py-4">
        <h2 className="text-base font-semibold text-white">Wyniki</h2>
        <p data-testid="analysis-id" className="mt-1 text-sm text-zinc-400">
          {analysis ? `Analiza ${analysis.analysisContext.analysisId}` : 'Legenda kolorów i wykryte boxy'}
        </p>
      </div>

      <div className="flex border-b border-white/10">
        <button
          type="button"
          className={
            tab === 'legend'
              ? 'flex-1 bg-white/10 px-3 py-3 text-sm text-white'
              : 'flex-1 px-3 py-3 text-sm text-zinc-400'
          }
          onClick={() => onTabChange('legend')}
        >
          Legenda kolorów
        </button>
        <button
          type="button"
          className={
            tab === 'detections'
              ? 'flex-1 bg-white/10 px-3 py-3 text-sm text-white'
              : 'flex-1 px-3 py-3 text-sm text-zinc-400'
          }
          onClick={() => onTabChange('detections')}
        >
          Wykryte
        </button>
      </div>

      {tab === 'legend' ? (
        <div className="space-y-3 p-4">
          {results.map((result) => {
            const template = templates.find((item) => item.displayName === result.name);
            const hidden = hiddenSymbolTypes[result.name];
            const symbolNumber = symbolNumberMap[result.name];
            return (
              <div key={result.name} data-testid="legend-result-card" className="rounded border border-white/10 bg-white/[0.03] p-3">
                <div className="flex items-start gap-3">
                  <span
                    data-testid="legend-symbol-number"
                    className="grid h-7 min-w-7 shrink-0 place-items-center rounded border text-xs font-bold text-white"
                    style={{ borderColor: result.color, background: `${result.color}33` }}
                  >
                    {symbolNumber}
                  </span>
                  <span className="mt-1 h-4 w-4 shrink-0 rounded-sm" style={{ background: result.color }} />
                  {template && <img src={template.imgBase64} alt={template.displayName} className="h-10 w-10 object-contain" />}
                  <div className="min-w-0 flex-1">
                    <div data-testid="legend-symbol-name" className="truncate text-sm font-semibold text-white">{result.name}</div>
                    <div className="text-xs text-zinc-400">
                      {result.count} szt. · low confidence {result.lowConfidenceCount}
                    </div>
                    <div className="mt-1 text-xs text-zinc-500">
                      min/avg/max {result.minVerificationScore.toFixed(2)} / {result.avgVerificationScore.toFixed(2)} /{' '}
                      {result.maxVerificationScore.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    data-testid="legend-hide-toggle"
                    className="flex items-center gap-1 rounded border border-white/10 px-2 py-2 text-xs"
                    onClick={() => onToggleSymbolType(result.name)}
                  >
                    {hidden ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
                    {hidden ? 'Pokaż' : 'Ukryj'}
                  </button>
                  <button
                    type="button"
                    data-testid="legend-start-slideshow"
                    className="rounded border border-white/10 px-2 py-2 text-xs"
                    onClick={() => onStartSlideshow(result.name)}
                  >
                    Pokaż wszystkie
                  </button>
                </div>
              </div>
            );
          })}
          {!results.length && (
            <div className="rounded border border-white/10 bg-white/[0.03] p-4 text-sm text-zinc-400">
              Wyniki pojawią się po analizie.
            </div>
          )}
          <div className="border-t border-white/10 pt-3 text-sm font-semibold text-white">
            Suma wszystkich symboli: {totalCount} szt.
          </div>
        </div>
      ) : (
        <div className="space-y-3 p-4">
          <div className="grid grid-cols-3 gap-2">
            {(['all', 'low', 'pending'] as DetectionFilter[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                className={
                  filter === item
                    ? 'rounded bg-app-strong px-2 py-2 text-xs font-semibold text-white'
                    : 'rounded border border-white/10 px-2 py-2 text-xs text-zinc-300'
                }
              >
                {item === 'all' ? 'wszystkie' : item === 'low' ? 'low' : 'pending'}
              </button>
            ))}
          </div>
          {filteredBoxes.map((box) => (
            <div
              key={box.id}
              data-testid="detection-row"
              className={
                focusedBoxId === box.id
                  ? 'rounded border border-app-accent bg-white/[0.06] p-3'
                  : 'rounded border border-white/10 bg-white/[0.03] p-3'
              }
            >
              <div className="flex gap-3">
                {preview && <div className="shrink-0 rounded border border-white/10 bg-black" style={cropStyle(preview, box)} />}
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      data-testid="detection-symbol-number"
                      className="grid h-5 min-w-5 shrink-0 place-items-center rounded border px-1 text-[11px] font-bold text-white"
                      style={{ borderColor: box.color, background: `${box.color}33` }}
                    >
                      {symbolNumberMap[box.symbolName]}
                    </span>
                    <div data-testid="detection-symbol-name" className="truncate text-sm font-semibold text-white">{box.symbolName}</div>
                  </div>
                  <div className="text-xs text-zinc-400">
                    confidence {box.confidence.toFixed(2)} · score {box.verificationScore.toFixed(2)}
                  </div>
                  <div className="text-xs text-zinc-500">status: {statusOf(boxStatuses, box.id)}</div>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  data-testid="detection-confirm"
                  className="rounded border border-white/10 px-2 py-2 text-xs"
                  onClick={() => onMarkBox(box.id, 'confirmed')}
                >
                  Potwierdź
                </button>
                <button
                  type="button"
                  className="rounded border border-white/10 px-2 py-2 text-xs"
                  onClick={() => onMarkBox(box.id, 'rejected')}
                >
                  Odrzuć
                </button>
                <select
                  value={box.symbolName}
                  onChange={(event) => onChangeBoxType(box.id, event.target.value)}
                  className="rounded border border-white/10 bg-[#0f1013] px-2 py-2 text-xs"
                >
                  {symbolNames.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="rounded border border-white/10 px-2 py-2 text-xs"
                  onClick={() => onShowBox(box)}
                >
                  Pokaż
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
