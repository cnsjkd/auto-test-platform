import { mockArtifacts, mockCases, mockDevices, mockHealth, mockRunDetail, mockRuns, mockSmokeSuite } from './mockData';
import type {
  ApiEnvelope,
  Artifact,
  Device,
  DeviceCommandRequest,
  DeviceCommandResult,
  EntityId,
  FlowRunRequest,
  FlowRunResponse,
  Health,
  RunCreateRequest,
  RunDetail,
  SmokeSuite,
  SmokeSuiteRunRequest,
  SmokeSuiteRunResponse,
  TestCase,
  TestRun,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';
const ALLOW_MOCK_FALLBACK = import.meta.env.VITE_ENABLE_MOCK_FALLBACK === 'true';

class ApiError extends Error {
  constructor(public code: number, message: string, public status?: number, public details?: unknown) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions {
  fallbackOnHttpError?: boolean;
  fallbackOnStatuses?: number[];
  allowMockFallback?: boolean;
}

const requestId = () => `frontend-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const envelope = <T>(data: T, degraded = false): ApiEnvelope<T> => ({
  code: 0,
  message: degraded ? '后端不可用，已切换本地预览数据' : 'ok',
  requestId: requestId(),
  data,
  degraded,
});

const delay = async () => new Promise((resolve) => window.setTimeout(resolve, 180));

async function parseJsonResponse(response: Response) {
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    return undefined;
  }
  return response.json();
}

async function request<T>(path: string, init?: RequestInit, fallback?: () => T | Promise<T>, options: RequestOptions = {}): Promise<ApiEnvelope<T>> {
  const { fallbackOnHttpError = true, fallbackOnStatuses, allowMockFallback = ALLOW_MOCK_FALLBACK } = options;

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
      ...init,
    });
    const body = await parseJsonResponse(response);

    if (!response.ok) {
      const code = typeof body?.code === 'number' ? body.code : response.status;
      const message = typeof body?.message === 'string' && body.message ? body.message : response.statusText;
      throw new ApiError(code, message, response.status, body?.data);
    }

    if (typeof body?.code === 'number' && body.data !== undefined) {
      return body as ApiEnvelope<T>;
    }
    return envelope(body as T);
  } catch (error) {
    const shouldFallbackForStatus = error instanceof ApiError && error.status !== undefined && fallbackOnStatuses?.includes(error.status);
    if (!fallback || !allowMockFallback || (error instanceof ApiError && (!fallbackOnHttpError || (fallbackOnStatuses !== undefined && !shouldFallbackForStatus)))) {
      throw error;
    }
    await delay();
    return envelope(await fallback(), true);
  }
}

const ensurePixelAudit = (payload: DeviceCommandRequest) => {
  if (payload.action !== 'pixel_tap' && payload.action !== 'pixel_swipe') {
    return;
  }

  const required: Array<keyof DeviceCommandRequest> = [
    'pixelFallback',
    'fallbackReason',
    'riskNote',
    'improvementSuggestion',
    'x',
    'y',
    'screenWidth',
    'screenHeight',
    'orientation',
  ];
  const missing = required.filter((key) => payload[key] === undefined || payload[key] === '');

  if (payload.pixelFallback !== true || missing.length > 0) {
    throw new ApiError(52003, `像素兜底审计字段缺失：${missing.join(', ') || 'pixelFallback'}`);
  }
};

const toEntityPath = (id: EntityId) => String(id);

const createMockFlowRun = (payload: FlowRunRequest): FlowRunResponse => {
  const startedAt = new Date();
  const runId = `flow-local-${startedAt.getTime()}`;
  const steps = payload.steps.map((step, index) => {
    const artifact: Artifact = {
      ...mockArtifacts[0],
      id: `artifact-flow-${startedAt.getTime()}-${index + 1}`,
      runId,
      deviceId: payload.deviceId,
      path: `artifacts/${runId}/step-${index + 1}-${step.id}.png`,
      createdAt: new Date(startedAt.getTime() + (index + 1) * 700).toLocaleString(),
      meta: { title: `${step.name} 后截图` },
    };

    return {
      ...step,
      status: 'success' as const,
      startedAt: new Date(startedAt.getTime() + index * 1000).toLocaleString(),
      endedAt: new Date(startedAt.getTime() + (index + 1) * 1000).toLocaleString(),
      durationMs: 420 + index * 80,
      message: '本地预览流程步骤已模拟执行',
      command: { action: step.action, status: 'success' as const, message: '本地预览命令已模拟执行' },
      artifacts: payload.captureArtifacts === false ? [] : [artifact],
    };
  });
  const artifacts = steps.flatMap((step) => step.artifacts);

  return {
    run: {
      id: runId,
      status: 'passed',
      deviceId: payload.deviceId,
      deviceSerial: String(payload.deviceId),
      totalCount: steps.length,
      passedCount: steps.length,
      failedCount: 0,
      skippedCount: 0,
      startedAt: startedAt.toLocaleString(),
      endedAt: new Date(startedAt.getTime() + steps.length * 1000).toLocaleString(),
      pixelFallbackCount: 0,
      message: payload.name,
    },
    steps,
    artifacts,
  };
};

export const api = {
  health: () => request<Health>('/api/health', undefined, () => mockHealth),
  listDevices: () => request<{ devices: Device[] }>('/api/devices', undefined, () => ({ devices: mockDevices })),
  scanDevices: () => request<{ devices: Device[] }>('/api/devices/scan', { method: 'POST', body: JSON.stringify({ refresh: true }) }, () => ({ devices: mockDevices })),
  getDevice: (id: EntityId) => request<{ device: Device }>(`/api/devices/${toEntityPath(id)}`, undefined, () => ({ device: mockDevices.find((item) => String(item.id) === String(id)) ?? mockDevices[0] })),
  deviceCommand: (deviceId: EntityId, payload: DeviceCommandRequest) => {
    ensurePixelAudit(payload);
    return request<{ command: DeviceCommandResult; artifacts: Artifact[] }>(
      `/api/devices/${toEntityPath(deviceId)}/commands`,
      { method: 'POST', body: JSON.stringify(payload) },
      () => ({ command: { action: payload.action, status: 'success', message: '本地预览命令已模拟执行' }, artifacts: mockArtifacts.slice(0, 1) }),
    );
  },
  screenshot: (deviceId: EntityId) => request<{ artifact: Artifact }>(`/api/devices/${toEntityPath(deviceId)}/screenshot`, { method: 'POST', body: JSON.stringify({ name: 'manual-screenshot' }) }, () => ({ artifact: mockArtifacts[0] })),
  dumpHierarchy: (deviceId: EntityId) => request<{ artifact: Artifact }>(`/api/devices/${toEntityPath(deviceId)}/dump-hierarchy`, { method: 'POST', body: JSON.stringify({ name: 'manual-hierarchy' }) }, () => ({ artifact: { ...mockArtifacts[2], id: 'artifact-ui-xml-001', type: 'ui_xml', mimeType: 'application/xml', path: 'artifacts/run-20260630-001/A2TEST20260630/hierarchy.xml', meta: { title: 'UI XML', content: '<hierarchy><node text="会议记录" /></hierarchy>' } } })),
  logcatSnapshot: (deviceId: EntityId) => request<{ artifact: Artifact }>(`/api/devices/${toEntityPath(deviceId)}/logcat/snapshot`, { method: 'POST', body: JSON.stringify({ durationSec: 3, buffers: ['main'] }) }, () => ({ artifact: mockArtifacts[1] })),
  listCases: () => request<{ cases: TestCase[] }>('/api/test-cases', undefined, () => ({ cases: mockCases })),
  getP0SmokeSuite: () => request<SmokeSuite>('/api/smoke-suite/p0', undefined, () => mockSmokeSuite),
  createCase: (payload: Omit<TestCase, 'id' | 'hasPixelFallback' | 'pixelFallbackCount' | 'updatedAt'>) => request<{ case: TestCase }>('/api/test-cases', { method: 'POST', body: JSON.stringify(payload) }, () => {
    const pixelFallbackCount = payload.steps.filter((step) => step.action === 'pixel_tap' || step.action === 'pixel_swipe').length;
    return {
      case: {
        ...payload,
        id: `case-local-${Date.now()}`,
        hasPixelFallback: pixelFallbackCount > 0,
        pixelFallbackCount,
        updatedAt: new Date().toLocaleString(),
      },
    };
  }),
  createRun: (payload: RunCreateRequest) => request<{ run: TestRun; monitorUrl?: string }>('/api/test-runs/async', { method: 'POST', body: JSON.stringify(payload) }, () => ({ run: { ...mockRuns[0], id: `run-local-${Date.now()}`, status: 'queued', deviceId: payload.deviceId, totalCount: payload.caseIds.length, passedCount: 0, failedCount: 0, skippedCount: 0, startedAt: new Date().toLocaleString() }, monitorUrl: `/runs/run-local-${Date.now()}` })),
  cancelRun: (id: EntityId, reason = '用户从监控页取消运行') => request<{ run: TestRun }>(`/api/test-runs/${toEntityPath(id)}/cancel`, { method: 'POST', body: JSON.stringify({ reason }) }, () => ({ run: { ...mockRuns[0], id, status: 'canceled', endedAt: new Date().toLocaleString() } })),
  runFlow: (payload: FlowRunRequest) => request<FlowRunResponse>(
    '/api/automation-flows/run',
    { method: 'POST', body: JSON.stringify(payload) },
    () => createMockFlowRun(payload),
    { fallbackOnStatuses: [404, 405, 500, 501, 502, 503, 504] },
  ),
  runP0SmokeSuite: (payload: SmokeSuiteRunRequest) => request<SmokeSuiteRunResponse>(
    '/api/smoke-suite/p0/run-async',
    { method: 'POST', body: JSON.stringify(payload) },
    () => {
      if (mockSmokeSuite.requiresRiskAcceptance && payload.riskAccepted !== true) {
        throw new ApiError(42201, 'riskAccepted=true is required before running A2 P0 冒烟套件', 422);
      }
      return {
        suite: mockSmokeSuite,
        run: {
          ...mockRuns[0],
          id: `run-p0-local-${Date.now()}`,
          status: 'running',
          deviceId: payload.deviceId,
          totalCount: mockSmokeSuite.caseCount,
          passedCount: 0,
          failedCount: 0,
          skippedCount: 0,
          startedAt: new Date().toLocaleString(),
          config: {
            ...(payload.config ?? {}),
            suiteId: mockSmokeSuite.suite.id,
            suiteName: mockSmokeSuite.suite.name,
            riskAccepted: payload.riskAccepted,
          },
        },
      };
    },
    { fallbackOnHttpError: false },
  ),
  listRuns: () => request<{ runs: TestRun[] }>('/api/test-runs', undefined, () => ({ runs: mockRuns })),
  getRun: (id: EntityId) => request<RunDetail>(`/api/test-runs/${toEntityPath(id)}`, undefined, () => ({ ...mockRunDetail, run: { ...mockRunDetail.run, id } })),
  listRunArtifacts: (runId: EntityId) => request<{ artifacts: Artifact[] }>(`/api/test-runs/${toEntityPath(runId)}/artifacts`, undefined, () => ({ artifacts: mockArtifacts })),
  listArtifacts: () => request<{ artifacts: Artifact[] }>('/api/artifacts', undefined, () => ({ artifacts: mockArtifacts })),
  getArtifact: (id: EntityId) => request<{ artifact: Artifact }>(`/api/artifacts/${toEntityPath(id)}`, undefined, () => ({ artifact: mockArtifacts.find((item) => String(item.id) === String(id)) ?? mockArtifacts[0] })),
};

export { ApiError };
