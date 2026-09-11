'use client';

import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

type MarkerItem = {
  id: string;
  latitude?: number | null;
  longitude?: number | null;
  label: string;
  color: string;
  kind?: 'zone' | 'resource' | 'incident';
  critical?: boolean;
};

type RouteItem = {
  id: string;
  from: [number, number];
  to: [number, number];
  kind?: 'assignment' | 'reallocation';
  label?: string;
};

export function MapView({
  zones = [],
  resources = [],
  incidents = [],
  routes = [],
  simulation = true,
}: {
  zones?: MarkerItem[];
  resources?: MarkerItem[];
  incidents?: MarkerItem[];
  routes?: RouteItem[];
  simulation?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap',
          },
        },
        layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
      },
      center: [72.88, 19.08],
      zoom: 10.2,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const markers: maplibregl.Marker[] = [];
    const add = (items: MarkerItem[], size: string) => {
      (items || []).forEach((item) => {
        if (item.latitude == null || item.longitude == null) return;
        const el = document.createElement('div');
        el.title = item.label;
        el.setAttribute('aria-label', item.label);
        el.className = `eoc-marker${item.critical ? ' eoc-marker-critical' : ''}`;
        el.style.cssText += `width:${size};height:${size};border-radius:${item.kind === 'resource' ? '2px' : '50%'};background:${item.color};`;
        markers.push(
          new maplibregl.Marker({ element: el })
            .setLngLat([item.longitude, item.latitude])
            .setPopup(new maplibregl.Popup({ offset: 12 }).setText(item.label))
            .addTo(map)
        );
      });
    };
    add(zones.map((z) => ({ ...z, kind: z.kind || 'zone' })), '16px');
    add(resources.map((r) => ({ ...r, kind: r.kind || 'resource' })), '10px');
    add(incidents.map((i) => ({ ...i, kind: i.kind || 'incident' })), '8px');

    const applyRoutes = () => {
      const asFeatures = (kind: string) => ({
        type: 'FeatureCollection' as const,
        features: (routes || [])
          .filter((r) => r.from && r.to && (r.kind || 'assignment') === kind)
          .map((r) => ({
            type: 'Feature' as const,
            properties: { label: r.label || '' },
            geometry: { type: 'LineString' as const, coordinates: [r.from, r.to] },
          })),
      });
      const ensure = (id: string, data: any, paint: Record<string, unknown>) => {
        if (map.getSource(id)) {
          (map.getSource(id) as maplibregl.GeoJSONSource).setData(data);
          return;
        }
        map.addSource(id, { type: 'geojson', data });
        map.addLayer({ id: `${id}-line`, type: 'line', source: id, paint });
      };
      ensure('routes-assign', asFeatures('assignment'), { 'line-color': '#38bdf8', 'line-width': 2, 'line-opacity': 0.55 });
      ensure('routes-reassign', asFeatures('reallocation'), {
        'line-color': '#f59e0b',
        'line-width': 2.5,
        'line-opacity': 0.9,
        'line-dasharray': [2, 1.4],
      });
    };

    if (map.isStyleLoaded()) applyRoutes();
    else map.once('load', applyRoutes);

    return () => {
      markers.forEach((m) => m.remove());
    };
  }, [zones, resources, incidents, routes]);

  return (
    <div className="relative min-h-[28rem] flex-1">
      <div ref={ref} className="h-[28rem] w-full overflow-hidden rounded-lg border border-slate-700 lg:h-[34rem]" />
      {simulation && (
        <div className="absolute right-3 top-3 rounded border border-amber-700/80 bg-slate-950/90 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-300">
          Simulation data
        </div>
      )}
      <div className="absolute bottom-3 left-3 space-y-1 rounded border border-slate-700 bg-slate-950/90 p-2 text-[10px] uppercase tracking-wide text-slate-300">
        <Legend color="#ef4444" label="Critical zone" round />
        <Legend color="#38bdf8" label="Zone" round />
        <Legend color="#a855f7" label="Resource" />
        <Legend color="#f43f5e" label="Incident" round />
        <Legend color="#f59e0b" label="Reallocation" line />
      </div>
    </div>
  );
}

function Legend({ color, label, round, line }: { color: string; label: string; round?: boolean; line?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span
        aria-hidden
        className={line ? 'h-0.5 w-4' : 'h-2.5 w-2.5'}
        style={{ background: color, borderRadius: round ? '999px' : line ? 0 : 2 }}
      />
      {label}
    </div>
  );
}
