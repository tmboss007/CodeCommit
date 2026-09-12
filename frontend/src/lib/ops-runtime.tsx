'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { snapshotAPI } from './api';
import { connectToEventStream, type StreamStatus } from './sse';

type OpsContextValue = {
  data: any | null;
  error: string | null;
  connection: StreamStatus;
  refresh: (force?: boolean) => Promise<void>;
};

const OpsContext = createContext<OpsContextValue | null>(null);

export function useOps() {
  const ctx = useContext(OpsContext);
  if (!ctx) {
    throw new Error('useOps must be used within OpsProvider');
  }
  return ctx;
}

export function OpsProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connection, setConnection] = useState<StreamStatus>('connecting');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const refreshRef = useRef<Promise<void> | null>(null);

  const refresh = useCallback(async (force = false) => {
    if (refreshRef.current) {
      await refreshRef.current;
      if (!force) return;
    }
    const ac = new AbortController();
    abortRef.current = ac;
    const timer = setTimeout(() => ac.abort(), 8000);
    const request = (async () => {
      try {
        const res = await snapshotAPI.get(ac.signal);
        if (ac.signal.aborted) return;
        setData(res.data);
        setError(null);
      } catch {
        if (ac.signal.aborted) return;
        setError('Unable to reach the operations API. Check that the backend is running on port 8000.');
      } finally {
        clearTimeout(timer);
      }
    })();
    refreshRef.current = request;
    try {
      await request;
    } finally {
      if (refreshRef.current === request) refreshRef.current = null;
    }
  }, []);

  const scheduleRefresh = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      refresh().catch(() => null);
    }, 180);
  }, [refresh]);

  useEffect(() => {
    refresh().catch(() => null);
    const stop = connectToEventStream({
      onStatus: setConnection,
      onEvent: (eventType) => {
        if (eventType === 'heartbeat') return;
        scheduleRefresh();
      },
    });
    return () => {
      stop();
      abortRef.current?.abort();
      refreshRef.current = null;
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [refresh, scheduleRefresh]);

  useEffect(() => {
    if (connection === 'live') return undefined;
    const timer = setInterval(() => {
      refresh().catch(() => null);
    }, 4000);
    return () => clearInterval(timer);
  }, [connection, refresh]);

  const value = useMemo(
    () => ({ data, error, connection, refresh }),
    [data, error, connection, refresh],
  );

  return <OpsContext.Provider value={value}>{children}</OpsContext.Provider>;
}
