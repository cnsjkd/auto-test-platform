export const ACTIONS = [
  'semantic_click',
  'semantic_input',
  'semantic_assert',
  'swipe',
  'keyevent',
  'open_notification',
  'open_quick_settings',
  'shell',
  'pixel_tap',
  'pixel_swipe',
  'screenshot',
  'dump_hierarchy',
  'logcat_snapshot',
] as const;

export type Action = (typeof ACTIONS)[number];
export type EntityId = string | number;
export type Orientation = 'portrait' | 'landscape';
export type DeviceStatus = 'online' | 'offline' | 'unauthorized' | 'missing';
export type RunStatus = 'queued' | 'running' | 'passed' | 'failed' | 'canceled';
export type ArtifactType = 'screenshot' | 'logcat' | 'ui_xml' | 'report' | 'report_json' | 'report_html' | 'pixel_audit';

export interface ApiEnvelope<T> {
  code: number;
  message: string;
  requestId: string;
  data: T;
  degraded?: boolean;
}

export interface Health {
  status: 'ok' | 'degraded' | 'error';
  adbAvailable: boolean;
  pythonVersion: string;
  artifactRoot: string;
  checks: HealthCheck[];
}

export interface HealthCheck {
  id: string;
  label: string;
  status: 'pass' | 'warn' | 'fail';
  detail: string;
  suggestion?: string;
}

export interface Device {
  id: EntityId;
  serial: string;
  status: DeviceStatus;
  manufacturer: string;
  model: string;
  androidVersion: string;
  sdkInt: number;
  screenWidth: number;
  screenHeight: number;
  density: number;
  battery: number;
  network: string;
  storage: string;
  adbStatus: string;
  lastSeenAt: string;
  capabilities: string[] | Record<string, unknown>;
}

export interface Selector {
  resource_id?: string;
  text?: string;
  description?: string;
  class_name?: string;
  xpath?: string;
  hierarchy_path?: string;
}

export interface PixelAudit {
  pixelFallback: true;
  fallbackReason: string;
  riskNote: string;
  improvementSuggestion: string;
  x: number;
  y: number;
  screenWidth: number;
  screenHeight: number;
  orientation: Orientation;
}

export interface TestStep {
  id?: EntityId;
  name?: string;
  action: Action;
  selector?: Selector;
  params?: Record<string, string | number | boolean | string[]>;
  timeoutSec?: number;
  pixelAudit?: PixelAudit;
  pixelFallback?: boolean;
  fallbackReason?: string;
  riskNote?: string;
  improvementSuggestion?: string;
  x?: number;
  y?: number;
  screenWidth?: number;
  screenHeight?: number;
  orientation?: Orientation;
}

export interface TestCase {
  id: EntityId;
  name: string;
  type: string;
  priority: 'P0' | 'P1' | 'P2';
  tags: string[];
  status: 'enabled' | 'disabled';
  description: string;
  steps: TestStep[];
  hasPixelFallback: boolean;
  pixelFallbackCount: number;
  updatedAt: string;
}

export interface RunCreateRequest {
  deviceId: EntityId;
  caseIds: EntityId[];
  config?: Record<string, unknown>;
}

export interface SmokeSuiteMeta {
  id: string;
  name: string;
  tag?: string;
  priority: 'P0' | 'P1' | 'P2';
  description: string;
  tags: string[];
}

export interface SmokeSuite {
  suite: SmokeSuiteMeta;
  ready: boolean;
  cases: TestCase[];
  caseIds: number[];
  caseCount: number;
  pixelFallbackCount: number;
  requiresRiskAcceptance: boolean;
  acceptanceNotes: string[];
}

export interface SmokeSuiteRunRequest {
  deviceId: number;
  riskAccepted: boolean;
  config?: Record<string, unknown>;
}

export interface SmokeSuiteRunResponse {
  suite: SmokeSuite;
  run: TestRun;
}

export interface TestRun {
  id: EntityId;
  status: RunStatus;
  deviceId: EntityId;
  deviceSerial: string;
  totalCount: number;
  passedCount: number;
  failedCount: number;
  skippedCount: number;
  startedAt: string;
  endedAt?: string;
  reportPath?: string;
  pixelFallbackCount: number;
  config?: Record<string, unknown>;
}

export interface TestResult {
  id: EntityId;
  runId: EntityId;
  caseId: EntityId;
  caseName: string;
  status: RunStatus;
  durationMs: number;
  errorCode?: number;
  message: string;
  locatorStrategy: 'semantic' | 'pixel_fallback' | 'system' | 'evidence';
  pixelFallbackUsed: boolean;
  startedAt: string;
  endedAt?: string;
  pixelAudit?: PixelAudit;
}

export interface Artifact {
  id: EntityId;
  runId?: EntityId;
  resultId?: EntityId;
  deviceId?: EntityId;
  type: ArtifactType;
  path: string;
  mimeType: string;
  sizeBytes: number;
  checksum: string;
  createdAt: string;
  meta?: {
    title?: string;
    content?: string;
    pixelAudit?: PixelAudit;
  };
}

export interface RunDetail {
  run: TestRun;
  results: TestResult[];
  artifacts: Artifact[];
}

export interface DeviceCommandRequest {
  action: Action;
  selector?: Selector;
  params?: Record<string, string | number | boolean | string[]>;
  timeoutSec?: number;
  pixelFallback?: boolean;
  fallbackReason?: string;
  riskNote?: string;
  improvementSuggestion?: string;
  x?: number;
  y?: number;
  screenWidth?: number;
  screenHeight?: number;
  orientation?: Orientation;
}

export interface DeviceCommandResult {
  id?: EntityId;
  action: Action;
  status?: 'success' | 'failed' | 'running' | 'queued';
  startedAt?: string;
  endedAt?: string;
  durationMs?: number;
  message?: string;
  stdout?: string;
  stderr?: string;
}
