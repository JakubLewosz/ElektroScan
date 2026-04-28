from datetime import datetime

from pydantic import BaseModel, Field


class Rect(BaseModel):
    x: int
    y: int
    width: int
    height: int


class PageSize(BaseModel):
    width: int
    height: int


class LayerInfo(BaseModel):
    name: str
    visible: bool


class PreviewResponse(BaseModel):
    sessionId: str
    fileName: str
    previewImage: str
    pageSize: PageSize


class RenderPreviewRequest(BaseModel):
    hiddenLayers: list[str] = Field(default_factory=list)


class RenderPreviewResponse(BaseModel):
    previewImage: str
    pageSize: PageSize
    layers: list[LayerInfo]


class ExtractLegendRequest(BaseModel):
    excludedZones: list[Rect] = Field(default_factory=list)
    hiddenLayers: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    excludedZones: list[Rect] = Field(default_factory=list)
    hiddenLayers: list[str] = Field(default_factory=list)


class RenameTemplateRequest(BaseModel):
    newName: str


class TemplateInfo(BaseModel):
    name: str
    displayName: str
    imgBase64: str
    width: int
    height: int


class ProgressEvent(BaseModel):
    stage: str
    message: str
    percent: int


class AnalysisContext(BaseModel):
    analysisId: str
    generatedAtUtc: datetime
    sessionId: str
    sourcePdf: str
    hiddenLayersUsed: list[str]
    excludedZonesUsed: list[Rect]


class ResultItem(BaseModel):
    name: str
    count: int
    color: str
    minVerificationScore: float
    avgVerificationScore: float
    maxVerificationScore: float
    lowConfidenceCount: int


class DetectionBox(BaseModel):
    id: str
    symbolName: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    verificationScore: float
    color: str


class AnalyzeResponse(BaseModel):
    analysisContext: AnalysisContext
    results: list[ResultItem]
    boxes: list[DetectionBox]
