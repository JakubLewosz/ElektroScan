export type AppStatus = 'idle' | 'processing' | 'error';
export type BoxStatus = 'pending' | 'confirmed' | 'rejected';
export type ResultsTab = 'legend' | 'detections';
export type DetectionFilter = 'all' | 'low' | 'pending';
export type CanvasMode = 'idle' | 'zone' | 'manual';

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PageSize {
  width: number;
  height: number;
}

export interface LayerInfo {
  name: string;
  visible: boolean;
}

export interface PreviewResponse {
  sessionId: string;
  fileName: string;
  previewImage: string;
  pageSize: PageSize;
}

export interface RenderPreviewResponse {
  previewImage: string;
  pageSize: PageSize;
  layers: LayerInfo[];
}

export interface TemplateInfo {
  name: string;
  displayName: string;
  imgBase64: string;
  width: number;
  height: number;
}

export interface ProgressEvent {
  stage: string;
  message: string;
  percent: number;
}

export interface AnalysisContext {
  analysisId: string;
  generatedAtUtc: string;
  sessionId: string;
  sourcePdf: string;
  hiddenLayersUsed: string[];
  excludedZonesUsed: Rect[];
}

export interface ResultItem {
  name: string;
  count: number;
  color: string;
  minVerificationScore: number;
  avgVerificationScore: number;
  maxVerificationScore: number;
  lowConfidenceCount: number;
}

export interface DetectionBox {
  id: string;
  symbolName: string;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  verificationScore: number;
  color: string;
}

export interface SlideshowMode {
  symbolName: string;
  boxIds: string[];
  currentIndex: number;
  completed: boolean;
  confirmed: number;
  rejected: number;
}

export interface AnalyzeResponse {
  analysisContext: AnalysisContext;
  results: ResultItem[];
  boxes: DetectionBox[];
}

export interface AnalyzePayload {
  excludedZones: Rect[];
  hiddenLayers: string[];
}
