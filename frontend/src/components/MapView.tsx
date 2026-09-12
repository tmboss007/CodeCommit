'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

export type DetailRow = { label: string; value: string };

export type MarkerItem = {
  id: string;
  latitude?: number | null;
  longitude?: number | null;
  label: string;
  color: string;
  kind?: 'zone' | 'resource' | 'incident';
  critical?: boolean;
  high?: boolean;
  rows?: DetailRow[];
};

export type RouteItem = {
  id: string;
  from: [number, number];
  to: [number, number];
  kind?: 'assignment' | 'reallocation';
  callsign?: string;
  shortPath?: string;
  etaLabel?: string;
  rows?: DetailRow[];
};

type Selection = { title: string; rows: DetailRow[] };

const LINE_LAYERS = ['routes-assign-line', 'routes-reassign-line'];

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
  const [selected, setSelected] = useState<Selection | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const routeIndex = useMemo(() => Object.fromEntries((routes || []).map((r) => [r.id, r])), [routes]);

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
    let skipMapClick = false;

    const select = (title: string, rows?: DetailRow[], routeId?: string | null) => {
      setSelected({ title, rows: rows || [] });
      setSelectedRouteId(routeId || null);
    };

    const add = (items: MarkerItem[], size: string) => {
      (items || []).forEach((item) => {
        if (item.latitude == null || item.longitude == null) return;
        const el = document.createElement('div');
        el.title = item.label;
        el.setAttribute('aria-label', item.label);
        el.setAttribute('role', 'button');
        el.tabIndex = 0;
        const shape = item.kind === 'resource' ? ' eoc-marker-resource' : '';
        const hi = item.high ? ' eoc-marker-high' : '';
        el.className = `eoc-marker${item.critical ? ' eoc-marker-critical' : ''}${hi}${shape}`;
        el.style.cssText += `width:${size};height:${size};background:${item.color};`;
        const open = () => select(item.label, item.rows);
        el.addEventListener('click', (ev) => {
          ev.stopPropagation();
          skipMapClick = true;
          open();
        });
        el.addEventListener('keydown', (ev) => {
          if (ev.key === 'Enter' || ev.key === ' ') {
            ev.preventDefault();
            open();
          }
        });
        markers.push(new maplibregl.Marker({ element: el }).setLngLat([item.longitude, item.latitude]).addTo(map));
      });
    };
    add(zones.map((z) => ({ ...z, kind: z.kind || 'zone' })), '16px');
    add(resources.map((r) => ({ ...r, kind: r.kind || 'resource' })), '12px');
    add(incidents.map((i) => ({ ...i, kind: i.kind || 'incident' })), '8px');

    const placeLabel = (r: RouteItem, third: string) => {
      const el = document.createElement('div');
      el.className = 'eoc-route-label';
      el.setAttribute('role', 'button');
      el.title = r.callsign || 'Route';
      el.innerHTML = `<strong>${r.callsign || ''}</strong><div>${r.shortPath || ''}</div><div>${third}</div>`;
      el.addEventListener('click', (ev) => {
        ev.stopPropagation();
        skipMapClick = true;
        select(r.callsign || 'Route', r.rows, r.id);
      });
      markers.push(
        new maplibregl.Marker({ element: el, anchor: 'center' })
          .setLngLat([(r.from[0] + r.to[0]) / 2, (r.from[1] + r.to[1]) / 2])
          .addTo(map),
      );
    };

    const labeled = (routes || []).filter((r) => r.kind === 'reallocation').slice(0, 8);
    labeled.forEach((r) => placeLabel(r, 'REALLOCATION'));

    if (selectedRouteId) {
      const r = routeIndex[selectedRouteId];
      if (r && r.kind !== 'reallocation') {
        placeLabel(r, r.etaLabel || '');
      }
    }

    const asFeatures = (kind: string) => ({
      type: 'FeatureCollection' as const,
      features: (routes || [])
        .filter((r) => r.from && r.to && (r.kind || 'assignment') === kind)
        .map((r) => ({
          type: 'Feature' as const,
          properties: { id: r.id },
          geometry: { type: 'LineString' as const, coordinates: [r.from, r.to] },
        })),
    });

    const applyRoutes = () => {
      const ensure = (id: string, data: any, paint: Record<string, unknown>) => {
        if (map.getSource(id)) {
          (map.getSource(id) as maplibregl.GeoJSONSource).setData(data);
          return;
        }
        map.addSource(id, { type: 'geojson', data });
        map.addLayer({ id: `${id}-line`, type: 'line', source: id, paint, layout: { 'line-cap': 'round' } });
      };
      ensure('routes-assign', asFeatures('assignment'), { 'line-color': '#243B53', 'line-width': 2, 'line-opacity': 0.75 });
      ensure('routes-reassign', asFeatures('reallocation'), {
        'line-color': '#A15C00',
        'line-width': 2.25,
        'line-opacity': 0.9,
        'line-dasharray': [2, 1.4],
      });
      const selectedFeat = {
        type: 'FeatureCollection' as const,
        features: (routes || [])
          .filter((r) => r.id === selectedRouteId)
          .map((r) => ({
            type: 'Feature' as const,
            properties: { id: r.id },
            geometry: { type: 'LineString' as const, coordinates: [r.from, r.to] },
          })),
      };
      ensure('routes-selected', selectedFeat, { 'line-color': '#171A1F', 'line-width': 4, 'line-opacity': 0.95 });
    };

    const onLineClick = (e: maplibregl.MapLayerMouseEvent) => {
      const id = e.features?.[0]?.properties?.id as string | undefined;
      const route = id ? routeIndex[id] : null;
      if (!route) return;
      e.originalEvent.stopPropagation();
      skipMapClick = true;
      select(route.callsign || 'Route', route.rows, route.id);
    };
    const onEnter = () => {
      map.getCanvas().style.cursor = 'pointer';
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
    };
    const onMapClick = (e: maplibregl.MapMouseEvent) => {
      if (skipMapClick) {
        skipMapClick = false;
        return;
      }
      const hits = map.queryRenderedFeatures(e.point, { layers: LINE_LAYERS.filter((id) => map.getLayer(id)) });
      if (!hits.length) {
        setSelected(null);
        setSelectedRouteId(null);
      }
    };

    const wire = () => {
      applyRoutes();
      LINE_LAYERS.forEach((layer) => {
        if (!map.getLayer(layer)) return;
        map.on('click', layer, onLineClick);
        map.on('mouseenter', layer, onEnter);
        map.on('mouseleave', layer, onLeave);
      });
      map.on('click', onMapClick);
    };

    if (map.isStyleLoaded()) wire();
    else map.once('load', wire);

    return () => {
      markers.forEach((m) => m.remove());
      try {
        LINE_LAYERS.forEach((layer) => {
          if (!map.getStyle() || !map.getLayer(layer)) return;
          map.off('click', layer, onLineClick);
          map.off('mouseenter', layer, onEnter);
          map.off('mouseleave', layer, onLeave);
        });
        map.off('click', onMapClick);
      } catch {
        /* map already tearing down */
      }
    };
  }, [zones, resources, incidents, routes, routeIndex, selectedRouteId]);

  return (
    <div className="relative min-h-[28rem] flex-1">
      <div ref={ref} className="h-[28rem] w-full overflow-hidden border border-line lg:h-[34rem]" />
      {simulation && (
        <div className="absolute right-3 top-3 border border-line bg-white px-2 py-1 text-[11px] uppercase tracking-[0.06em] text-muted">
          Simulation data
        </div>
      )}
      {selected && (
        <aside className="absolute left-3 top-3 max-h-[18rem] w-[15.5rem] overflow-auto border border-line bg-white p-3 text-[12px]">
          <div className="flex items-start justify-between gap-2">
            <div className="font-semibold text-ink">{selected.title}</div>
            <button type="button" className="text-[11px] text-muted" onClick={() => { setSelected(null); setSelectedRouteId(null); }}>
              Close
            </button>
          </div>
          <dl className="mt-2 space-y-1">
            {selected.rows.map((row) => (
              <div key={row.label} className="grid grid-cols-[4.5rem_1fr] gap-2">
                <dt className="text-muted">{row.label}</dt>
                <dd className="text-ink">{row.value}</dd>
              </div>
            ))}
          </dl>
        </aside>
      )}
      <div className="absolute bottom-3 left-3 space-y-1 border border-line bg-white/95 p-2 text-[11px] text-muted">
        <Legend color="#B42318" label="Critical zone" round />
        <Legend color="#C75B12" label="High priority" round />
        <Legend color="#7A2634" label="Incident" round />
        <Legend color="#59636E" label="Resource" triangle />
        <Legend color="#243B53" label="Assignment" line />
        <Legend color="#A15C00" label="Reallocation" dash />
      </div>
    </div>
  );
}

function Legend({
  color,
  label,
  round,
  line,
  dash,
  triangle,
}: {
  color: string;
  label: string;
  round?: boolean;
  line?: boolean;
  dash?: boolean;
  triangle?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        aria-hidden
        className={line || dash ? 'h-0.5 w-4' : triangle ? 'eoc-legend-triangle' : 'h-2.5 w-2.5'}
        style={
          triangle
            ? { borderBottomColor: color }
            : {
                background: dash ? undefined : color,
                borderRadius: round ? 999 : 0,
                backgroundImage: dash ? `repeating-linear-gradient(90deg, ${color} 0 6px, transparent 6px 10px)` : undefined,
              }
        }
      />
      {label}
    </div>
  );
}
