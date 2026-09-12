export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const SSE_DISABLED = process.env.NEXT_PUBLIC_DISABLE_SSE === 'true';

export type StreamStatus = 'connecting' | 'live' | 'reconnecting' | 'polling';

export const SSE_BACKOFF_MS = [1000, 2000, 4000, 8000, 15000] as const;

export function nextSseBackoffMs(failedAttempts: number): number {
  const i = Math.max(0, Math.min(failedAttempts - 1, SSE_BACKOFF_MS.length - 1));
  return SSE_BACKOFF_MS[i];
}

const SSE_EVENT_TYPES = [
  'heartbeat',
  'incident.created',
  'incident.updated',
  'priority.changed',
  'needs.updated',
  'duplicate.detected',
  'plan.created',
  'plan.replanned',
  'plan.approved',
  'plan.rejected',
  'allocation.changed',
  'resource.updated',
  'coordination.updated',
  'audit.created',
  'scenario.updated',
] as const;

type StreamHandlers = {
  onEvent: (eventType: string, data: Record<string, unknown>) => void;
  onStatus: (status: StreamStatus) => void;
};

const listeners = new Set<StreamHandlers>();
let source: EventSource | null = null;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
let releaseTimer: ReturnType<typeof setTimeout> | null = null;
let failedAttempts = 0;
let lastStatus: StreamStatus = 'connecting';

function parseMessage(message: MessageEvent, fallbackType?: string) {
  try {
    const data = JSON.parse(message.data) as Record<string, unknown>;
    const eventType = String(data.event_type || fallbackType || 'message');
    return { eventType, data };
  } catch {
    return null;
  }
}

function emitStatus(status: StreamStatus) {
  lastStatus = status;
  listeners.forEach((h) => h.onStatus(status));
}

function emitEvent(eventType: string, data: Record<string, unknown>) {
  listeners.forEach((h) => h.onEvent(eventType, data));
}

function clearRetry() {
  if (retryTimer) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }
}

function closeSource() {
  if (source) {
    source.onopen = null;
    source.onerror = null;
    source.onmessage = null;
    source.close();
    source = null;
  }
}

function stopShared() {
  clearRetry();
  closeSource();
  failedAttempts = 0;
}

function handleMessage(message: MessageEvent, fallbackType?: string) {
  const parsed = parseMessage(message, fallbackType);
  if (parsed) emitEvent(parsed.eventType, parsed.data);
}

function connectShared() {
  if (typeof EventSource === 'undefined' || listeners.size === 0) return;
  if (SSE_DISABLED) {
    emitStatus('polling');
    return;
  }
  clearRetry();
  closeSource();
  if (failedAttempts === 0) emitStatus('connecting');
  else if (failedAttempts === 1) emitStatus('reconnecting');
  else emitStatus('polling');

  const nextSource = new EventSource(`${API_URL}/api/events/stream`);
  source = nextSource;
  nextSource.onopen = () => {
    if (source !== nextSource) return;
    failedAttempts = 0;
    emitStatus('live');
  };
  nextSource.onmessage = (message) => {
    if (source === nextSource) handleMessage(message);
  };
  SSE_EVENT_TYPES.forEach((type) => {
    nextSource.addEventListener(type, (message) => {
      if (source === nextSource) handleMessage(message as MessageEvent, type);
    });
  });
  nextSource.onerror = () => {
    if (source !== nextSource) return;
    closeSource();
    if (listeners.size === 0) return;
    failedAttempts += 1;
    emitStatus(failedAttempts === 1 ? 'reconnecting' : 'polling');
    const delay = nextSseBackoffMs(failedAttempts);
    clearRetry();
    retryTimer = setTimeout(connectShared, delay);
  };
}

export function activeEventSourceCount(): number {
  return source ? 1 : 0;
}

export function connectToEventStream(handlers: StreamHandlers): () => void {
  if (releaseTimer) {
    clearTimeout(releaseTimer);
    releaseTimer = null;
  }
  listeners.add(handlers);
  handlers.onStatus(
    typeof EventSource !== 'undefined' && source?.readyState === EventSource.OPEN ? 'live' : lastStatus,
  );
  if (listeners.size === 1 && !source && !retryTimer) {
    failedAttempts = 0;
    connectShared();
  }
  return () => {
    listeners.delete(handlers);
    if (listeners.size > 0) return;
    releaseTimer = setTimeout(() => {
      releaseTimer = null;
      if (listeners.size === 0) stopShared();
    }, 100);
  };
}
