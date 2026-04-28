import { useEffect, useMemo, useRef, useState } from 'react';

import { CanvasView, type CanvasViewHandle } from './components/CanvasView';
import { ResultsPanel } from './components/ResultsPanel';
import { Sidebar } from './components/Sidebar';
import {
  analyzePlan,
  clearSession,
  clearTemplates,
  deleteTemplate,
  extractLegend,
  fetchLayers,
  fetchTemplates,
  renderPreview,
  renameTemplate,
  uploadPreview,
} from './api';
import { createScopedStorageKey } from './lib/storage';
import type {
  AnalyzeResponse,
  AppStatus,
  BoxStatus,
  CanvasMode,
  DetectionBox,
  LayerInfo,
  PreviewResponse,
  Rect,
  ResultItem,
  ResultsTab,
  SlideshowMode,
  TemplateInfo,
} from './types';

const LOW_CONFIDENCE_THRESHOLD = 0.6;

type RecoveryAction = 'upload' | 'analyze';

function legendNumberFromName(value: string): string | null {
  return value.match(/^(\d{1,3})(?:[_-]|$)/)?.[1] ?? null;
}

function fallbackLegendNumber(index: number): string {
  return String(index + 1).padStart(2, '0');
}

function statusOf(statuses: Record<string, BoxStatus>, boxId: string): BoxStatus {
  return statuses[boxId] ?? 'pending';
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  return Boolean(
    target.closest('input, textarea, select, [contenteditable="true"], [contenteditable=""]'),
  );
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof TypeError) {
    return 'Nie można połączyć się z backendem. Sprawdź, czy API działa, i spróbuj ponownie.';
  }
  return error instanceof Error ? error.message : fallback;
}

function resultFromBoxes(boxes: DetectionBox[], statuses: Record<string, BoxStatus>): ResultItem[] {
  const grouped = new Map<string, DetectionBox[]>();
  for (const box of boxes) {
    if (statusOf(statuses, box.id) === 'rejected') {
      continue;
    }
    grouped.set(box.symbolName, [...(grouped.get(box.symbolName) ?? []), box]);
  }

  return [...grouped.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, items]) => {
      const scores = items.map((item) => item.verificationScore);
      return {
        name,
        count: items.length,
        color: items[0]?.color ?? '#c6a87c',
        minVerificationScore: Math.min(...scores),
        avgVerificationScore: scores.reduce((sum, score) => sum + score, 0) / scores.length,
        maxVerificationScore: Math.max(...scores),
        lowConfidenceCount: scores.filter((score) => score < LOW_CONFIDENCE_THRESHOLD).length,
      };
    });
}

function App() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const lastUploadFileRef = useRef<File | null>(null);
  const canvasViewRef = useRef<CanvasViewHandle | null>(null);
  const analyzeControllerRef = useRef<AbortController | null>(null);
  const inactivityTimerRef = useRef<number | null>(null);

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [layers, setLayers] = useState<LayerInfo[]>([]);
  const [hiddenLayers, setHiddenLayers] = useState<string[]>([]);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [boxes, setBoxes] = useState<DetectionBox[]>([]);
  const [boxStatuses, setBoxStatuses] = useState<Record<string, BoxStatus>>({});
  const [hiddenSymbolTypes, setHiddenSymbolTypes] = useState<Record<string, boolean>>({});
  const [excludedZones, setExcludedZones] = useState<Rect[]>([]);
  const [focusedBoxId, setFocusedBoxId] = useState<string | null>(null);
  const [status, setStatus] = useState<AppStatus>('idle');
  const [statusText, setStatusText] = useState('Gotowy do wgrania PDF.');
  const [progressText, setProgressText] = useState('');
  const [progressPercent, setProgressPercent] = useState(0);
  const [tab, setTab] = useState<ResultsTab>('legend');
  const [mode, setMode] = useState<CanvasMode>('idle');
  const [manualSymbolName, setManualSymbolName] = useState('');
  const [slideshow, setSlideshow] = useState<SlideshowMode | null>(null);
  const [recoveryAction, setRecoveryAction] = useState<RecoveryAction | null>(null);

  const sessionId = preview?.sessionId ?? null;
  const analysisId = analysis?.analysisContext.analysisId ?? null;
  const derivedResults = useMemo(() => resultFromBoxes(boxes, boxStatuses), [boxes, boxStatuses]);
  const activeBoxes = useMemo(
    () => boxes.filter((box) => statusOf(boxStatuses, box.id) !== 'rejected'),
    [boxes, boxStatuses],
  );
  const visibleBoxes = useMemo(
    () => activeBoxes.filter((box) => !hiddenSymbolTypes[box.symbolName]),
    [activeBoxes, hiddenSymbolTypes],
  );
  const totalCount = activeBoxes.length;
  const symbolNames = useMemo(() => derivedResults.map((result) => result.name), [derivedResults]);
  const symbolNumberMap = useMemo(() => {
    const entries: Array<[string, string]> = [];
    const numberedNames = new Set<string>();
    let fallbackIndex = templates.length;

    templates.forEach((template, index) => {
      const symbolNumber = legendNumberFromName(template.displayName) ?? legendNumberFromName(template.name) ?? fallbackLegendNumber(index);
      const names = [template.displayName, template.name];
      for (const name of names) {
        if (!numberedNames.has(name)) {
          numberedNames.add(name);
          entries.push([name, symbolNumber]);
        }
      }
    });

    for (const result of derivedResults) {
      if (!numberedNames.has(result.name)) {
        numberedNames.add(result.name);
        entries.push([result.name, legendNumberFromName(result.name) ?? fallbackLegendNumber(fallbackIndex)]);
        fallbackIndex += 1;
      }
    }

    return Object.fromEntries(entries) as Record<string, string>;
  }, [derivedResults, templates]);
  const slideshowBox = slideshow && !slideshow.completed ? boxes.find((box) => box.id === slideshow.boxIds[slideshow.currentIndex]) ?? null : null;

  useEffect(() => {
    if (!sessionId || !analysisId) {
      return;
    }
    localStorage.setItem(createScopedStorageKey(sessionId, analysisId, 'boxStatuses'), JSON.stringify(boxStatuses));
  }, [analysisId, boxStatuses, sessionId]);

  useEffect(() => {
    if (!sessionId || !analysisId) {
      return;
    }
    localStorage.setItem(
      createScopedStorageKey(sessionId, analysisId, 'hiddenSymbolTypes'),
      JSON.stringify(hiddenSymbolTypes),
    );
  }, [analysisId, hiddenSymbolTypes, sessionId]);

  useEffect(() => {
    if (!manualSymbolName && symbolNames.length > 0) {
      setManualSymbolName(symbolNames[0]);
    }
  }, [manualSymbolName, symbolNames]);

  function markCurrentSlideshowBox(nextStatus: BoxStatus) {
    setSlideshow((current) => {
      if (!current || current.completed) {
        return current;
      }
      const boxId = current.boxIds[current.currentIndex];
      setBoxStatuses((previous) => ({ ...previous, [boxId]: nextStatus }));
      const nextIndex = current.currentIndex + 1;
      return {
        ...current,
        currentIndex: Math.min(nextIndex, current.boxIds.length - 1),
        completed: nextIndex >= current.boxIds.length,
        confirmed: current.confirmed + (nextStatus === 'confirmed' ? 1 : 0),
        rejected: current.rejected + (nextStatus === 'rejected' ? 1 : 0),
      };
    });
  }

  useEffect(() => {
    if (!slideshow) {
      return;
    }

    function advance(delta: number) {
      setSlideshow((current) => {
        if (!current) {
          return current;
        }
        const nextIndex = current.currentIndex + delta;
        if (nextIndex < 0) {
          return { ...current, currentIndex: 0, completed: false };
        }
        if (nextIndex >= current.boxIds.length) {
          return { ...current, currentIndex: current.boxIds.length - 1, completed: true };
        }
        return { ...current, currentIndex: nextIndex, completed: false };
      });
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.isComposing || isEditableTarget(event.target)) {
        return;
      }
      if (event.key === 'Escape') {
        setSlideshow(null);
        setMode('idle');
        return;
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        advance(-1);
        return;
      }
      if (event.key === 'Enter' || event.key === 'ArrowRight') {
        event.preventDefault();
        advance(1);
        return;
      }
      if (event.key.toLowerCase() === 'y' || event.key === '1') {
        event.preventDefault();
        markCurrentSlideshowBox('confirmed');
        return;
      }
      if (event.key.toLowerCase() === 'n' || event.key === '2' || event.key === 'Delete') {
        event.preventDefault();
        markCurrentSlideshowBox('rejected');
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [slideshow]);

  function resetInactivityTimer(controller: AbortController) {
    if (inactivityTimerRef.current) {
      window.clearTimeout(inactivityTimerRef.current);
    }
    inactivityTimerRef.current = window.setTimeout(() => {
      controller.abort();
      setStatus('error');
      setStatusText('Analiza przerwana: brak odpowiedzi backendu');
      setRecoveryAction('analyze');
    }, 30_000);
  }

  function stopInactivityTimer() {
    if (inactivityTimerRef.current) {
      window.clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = null;
    }
  }

  async function uploadSelectedFile(file: File) {
    lastUploadFileRef.current = file;
    setRecoveryAction(null);
    analyzeControllerRef.current?.abort();
    setStatus('processing');
    setStatusText(`Renderuję podgląd: ${file.name}`);
    setProgressText('');
    setProgressPercent(0);

    try {
      const nextPreview = await uploadPreview(file);
      const nextLayers = await fetchLayers(nextPreview.sessionId);
      const nextTemplates = await fetchTemplates(nextPreview.sessionId);
      setPreview(nextPreview);
      setLayers(nextLayers);
      setTemplates(nextTemplates);
      setHiddenLayers([]);
      setAnalysis(null);
      setBoxes([]);
      setBoxStatuses({});
      setHiddenSymbolTypes({});
      setExcludedZones([]);
      setFocusedBoxId(null);
      setStatus('idle');
      setStatusText(`Wgrano ${nextPreview.fileName}. Podgląd ${nextPreview.pageSize.width} x ${nextPreview.pageSize.height}px.`);
    } catch (error) {
      setStatus('error');
      setStatusText(errorMessage(error, 'Nie udało się wgrać PDF.'));
      setRecoveryAction('upload');
    }
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) {
      return;
    }

    await uploadSelectedFile(file);
  }

  async function toggleLayer(layerName: string) {
    if (!sessionId) {
      return;
    }
    const nextHidden = hiddenLayers.includes(layerName)
      ? hiddenLayers.filter((name) => name !== layerName)
      : [...hiddenLayers, layerName];
    setHiddenLayers(nextHidden);
    setStatus('processing');
    setStatusText('Renderuję podgląd z warstwami.');
    try {
      const response = await renderPreview(sessionId, nextHidden);
      setPreview((current) =>
        current ? { ...current, previewImage: response.previewImage, pageSize: response.pageSize } : current,
      );
      setLayers(response.layers);
      setStatus('idle');
      setStatusText('Podgląd warstw zaktualizowany.');
    } catch (error) {
      setStatus('error');
      setStatusText(errorMessage(error, 'Nie udało się przełączyć warstwy.'));
    }
  }

  async function handleExtractLegend() {
    if (!sessionId) {
      setStatus('error');
      setStatusText('Najpierw wgraj PDF.');
      return;
    }
    setStatus('processing');
    setStatusText('Wyodrębniam legendę.');
    try {
      const nextTemplates = await extractLegend(sessionId, { excludedZones, hiddenLayers });
      setTemplates(nextTemplates);
      setStatus('idle');
      setStatusText(`Wyodrębniono ${nextTemplates.length} wzorców.`);
    } catch (error) {
      setStatus('error');
      setStatusText(errorMessage(error, 'Nie udało się wyodrębnić legendy.'));
    }
  }

  async function handleAnalyze() {
    if (!sessionId) {
      setStatus('error');
      setStatusText('Najpierw wgraj PDF.');
      return;
    }

    analyzeControllerRef.current?.abort();
    const controller = new AbortController();
    analyzeControllerRef.current = controller;
    resetInactivityTimer(controller);
    setRecoveryAction(null);
    setStatus('processing');
    setStatusText('Analiza uruchomiona.');
    setProgressText('Start analizy');
    setProgressPercent(0);

    try {
      const gotResult = await analyzePlan(
        sessionId,
        { excludedZones, hiddenLayers },
        controller.signal,
        {
          onHeartbeat: () => resetInactivityTimer(controller),
          onProgress: (event) => {
            resetInactivityTimer(controller);
            setProgressText(event.message);
            setProgressPercent(event.percent);
          },
          onResult: (result) => {
            const storedStatuses = localStorage.getItem(
              createScopedStorageKey(sessionId, result.analysisContext.analysisId, 'boxStatuses'),
            );
            const storedHidden = localStorage.getItem(
              createScopedStorageKey(sessionId, result.analysisContext.analysisId, 'hiddenSymbolTypes'),
            );
            setAnalysis(result);
            setBoxes(result.boxes);
            setBoxStatuses(storedStatuses ? JSON.parse(storedStatuses) : {});
            setHiddenSymbolTypes(storedHidden ? JSON.parse(storedHidden) : {});
            setFocusedBoxId(null);
            setTab('legend');
            setProgressText('Analiza gotowa');
            setProgressPercent(100);
            setStatus('idle');
            setStatusText(`Analiza gotowa. Wykryto ${result.boxes.length} boxów.`);
          },
          onError: (message) => {
            setStatus('error');
            setStatusText(message);
            setRecoveryAction('analyze');
          },
        },
      );
      if (!gotResult && !controller.signal.aborted) {
        setStatus('error');
        setStatusText('Analiza przerwana: stream zamknął się bez wyniku.');
        setRecoveryAction('analyze');
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      setStatus('error');
      setStatusText(errorMessage(error, 'Nie udało się uruchomić analizy.'));
      setRecoveryAction('analyze');
    } finally {
      stopInactivityTimer();
    }
  }

  function handleRetry() {
    if (recoveryAction === 'upload' && lastUploadFileRef.current) {
      void uploadSelectedFile(lastUploadFileRef.current);
      return;
    }
    if (recoveryAction === 'analyze') {
      void handleAnalyze();
    }
  }

  async function handleClearTemplates() {
    if (!sessionId) {
      return;
    }
    setRecoveryAction(null);
    setStatus('processing');
    setStatusText('Czyszczę bazę wzorców.');
    try {
      const nextTemplates = await clearTemplates(sessionId);
      setTemplates(nextTemplates);
      setStatus('idle');
      setStatusText('Wyczyszczono bazę wzorców.');
    } catch (error) {
      setStatus('error');
      setStatusText(errorMessage(error, 'Nie udało się wyczyścić wzorców.'));
    }
  }

  async function handleClearSession() {
    if (!sessionId) {
      return;
    }
    analyzeControllerRef.current?.abort();
    await clearSession(sessionId);
    setPreview(null);
    setLayers([]);
    setHiddenLayers([]);
    setTemplates([]);
    setAnalysis(null);
    setBoxes([]);
    setBoxStatuses({});
    setHiddenSymbolTypes({});
    setExcludedZones([]);
    setFocusedBoxId(null);
    setRecoveryAction(null);
    setStatus('idle');
    setStatusText('Sesja wyczyszczona.');
  }

  async function handleRenameTemplate(template: TemplateInfo) {
    if (!sessionId) {
      return;
    }
    const nextName = window.prompt('Nowa nazwa wzorca', template.displayName);
    if (!nextName || nextName === template.displayName) {
      return;
    }
    setRecoveryAction(null);
    try {
      setTemplates(await renameTemplate(sessionId, template.name, nextName));
      setStatus('idle');
      setStatusText(`Zmieniono nazwę wzorca: ${nextName}.`);
    } catch (error) {
      setStatus('error');
      setStatusText(errorMessage(error, 'Nie udało się zmienić nazwy.'));
    }
  }

  async function handleDeleteTemplate(template: TemplateInfo) {
    if (!sessionId) {
      return;
    }
    setRecoveryAction(null);
    try {
      setTemplates(await deleteTemplate(sessionId, template.name));
      setStatus('idle');
      setStatusText(`Usunięto wzorzec: ${template.displayName}.`);
    } catch (error) {
      setStatus('error');
      setStatusText(errorMessage(error, 'Nie udało się usunąć wzorca.'));
    }
  }

  function handleAddManualBox(rect: Rect) {
    const symbolName = manualSymbolName || symbolNames[0];
    const result = derivedResults.find((item) => item.name === symbolName);
    if (!symbolName || !result) {
      setStatus('error');
      setStatusText('Najpierw uruchom analizę albo wybierz typ symbolu.');
      return;
    }
    const manualBox: DetectionBox = {
      id: `manual_${crypto.randomUUID()}`,
      symbolName,
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
      confidence: 1,
      verificationScore: 1,
      color: result.color,
    };
    setBoxes((current) => [...current, manualBox]);
    setBoxStatuses((current) => ({ ...current, [manualBox.id]: 'confirmed' }));
    setFocusedBoxId(manualBox.id);
  }

  function markBox(boxId: string, nextStatus: BoxStatus) {
    setBoxStatuses((current) => ({ ...current, [boxId]: nextStatus }));
  }

  function changeBoxType(boxId: string, symbolName: string) {
    const result = derivedResults.find((item) => item.name === symbolName);
    if (!result) {
      return;
    }
    setBoxes((current) =>
      current.map((box) => (box.id === boxId ? { ...box, symbolName, color: result.color } : box)),
    );
  }

  function startSlideshow(symbolName: string) {
    const boxIds = activeBoxes
      .filter((box) => box.symbolName === symbolName)
      .sort((a, b) => a.verificationScore - b.verificationScore)
      .map((box) => box.id);
    if (!boxIds.length) {
      return;
    }
    setMode('idle');
    setSlideshow({ symbolName, boxIds, currentIndex: 0, completed: false, confirmed: 0, rejected: 0 });
  }

  function showBox(box: DetectionBox) {
    canvasViewRef.current?.showBox(box);
  }

  async function copyBoxLog(box: DetectionBox) {
    const legendNumber = symbolNumberMap[box.symbolName] ?? null;
    const boxStatus = statusOf(boxStatuses, box.id);
    const log = {
      type: 'elektroscan_detection_box_log',
      copiedAtUtc: new Date().toISOString(),
      sessionId,
      analysisId,
      sourcePdf: analysis?.analysisContext.sourcePdf ?? preview?.fileName ?? null,
      legendNumber,
      boxStatus,
      box,
      referenceJsonCandidate: {
        id: box.id,
        symbolName: box.symbolName,
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        confidence: box.confidence,
        verificationScore: box.verificationScore,
        color: box.color,
      },
      analysisContext: analysis?.analysisContext ?? null,
      hiddenLayers,
      excludedZones,
    };

    try {
      await navigator.clipboard.writeText(JSON.stringify(log, null, 2));
      setStatus('idle');
      setStatusText(`Skopiowano log boxa ${legendNumber ? `#${legendNumber} ` : ''}${box.id}.`);
    } catch {
      setStatus('error');
      setStatusText('Nie udało się skopiować logu boxa do schowka.');
    }
  }

  return (
    <main className="grid min-h-screen grid-cols-1 bg-app-main text-zinc-100 xl:h-screen xl:min-h-0 xl:grid-cols-[320px_minmax(0,1fr)_400px]">
      <Sidebar
        fileInputRef={fileInputRef}
        status={status}
        statusText={statusText}
        progressText={progressText}
        progressPercent={progressPercent}
        sessionId={sessionId}
        layers={layers}
        hiddenLayers={hiddenLayers}
        templates={templates}
        mode={mode}
        manualSymbolName={manualSymbolName}
        symbolNames={symbolNames}
        onFileChange={handleFileChange}
        onRetry={recoveryAction ? handleRetry : undefined}
        onExtractLegend={handleExtractLegend}
        onAnalyze={handleAnalyze}
        onClearSession={handleClearSession}
        onClearTemplates={handleClearTemplates}
        onToggleLayer={toggleLayer}
        onModeChange={setMode}
        onManualSymbolNameChange={setManualSymbolName}
        onRenameTemplate={handleRenameTemplate}
        onDeleteTemplate={handleDeleteTemplate}
      />

      <CanvasView
        ref={canvasViewRef}
        preview={preview}
        visibleBoxes={visibleBoxes}
        boxes={boxes}
        boxStatuses={boxStatuses}
        symbolNumberMap={symbolNumberMap}
        excludedZones={excludedZones}
        focusedBoxId={focusedBoxId}
        mode={mode}
        slideshow={slideshow}
        slideshowBox={slideshowBox}
        symbolNames={symbolNames}
        onAddExcludedZone={(rect) => setExcludedZones((current) => [...current, rect])}
        onAddManualBox={handleAddManualBox}
        onFocusBox={setFocusedBoxId}
        onCopyBoxLog={copyBoxLog}
        onMarkBox={markBox}
        onMarkCurrentSlideshowBox={markCurrentSlideshowBox}
        onChangeBoxType={changeBoxType}
        onCloseSlideshow={() => setSlideshow(null)}
      />

      <ResultsPanel
        analysis={analysis}
        preview={preview}
        tab={tab}
        results={derivedResults}
        templates={templates}
        activeBoxes={activeBoxes}
        boxStatuses={boxStatuses}
        hiddenSymbolTypes={hiddenSymbolTypes}
        focusedBoxId={focusedBoxId}
        symbolNames={symbolNames}
        symbolNumberMap={symbolNumberMap}
        totalCount={totalCount}
        onTabChange={setTab}
        onToggleSymbolType={(symbolName) =>
          setHiddenSymbolTypes((current) => ({ ...current, [symbolName]: !current[symbolName] }))
        }
        onStartSlideshow={startSlideshow}
        onMarkBox={markBox}
        onChangeBoxType={changeBoxType}
        onShowBox={showBox}
      />
    </main>
  );
}

export default App;
