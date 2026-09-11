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
};

type RouteItem = {
  id: string;
  from: [number, number];
  to: [number, number];
};

export function MapView({
  zones = [],
  resources = [],
  incidents = [],
  routes = [],
}: {
  zones?: MarkerItem[];
  resources?: MarkerItem[];
  incidents?: MarkerItem[];
  routes?: RouteItem[];
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
      zoom: 10,
    });
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
        el.style.cssText = `width:${size};height:${size};border-radius:50%;background:${item.color};border:2px solid white;box-shadow:0 0 0 1px #0f172a`;
        markers.push(
          new maplibregl.Marker({ element: el })
            .setLngLat([item.longitude, item.latitude])
            .setPopup(new maplibregl.Popup({ offset: 12 }).setText(item.label))
            .addTo(map)
        );
      });
    };
    add(zones, '16px');
    add(resources, '11px');
    add(incidents, '9px');

    const applyRoutes = () => {
      const features = (routes || [])
        .filter((r) => r.from && r.to)
        .map((r) => ({
          type: 'Feature' as const,
          properties: {},
          geometry: { type: 'LineString' as const, coordinates: [r.from, r.to] },
        }));
      const data = { type: 'FeatureCollection' as const, features };
      if (map.getSource('routes')) {
        (map.getSource('routes') as maplibregl.GeoJSONSource).setData(data);
        return;
      }
      map.addSource('routes', { type: 'geojson', data });
      map.addLayer({
        id: 'routes-line',
        type: 'line',
        source: 'routes',
        paint: { 'line-color': '#fbbf24', 'line-width': 2, 'line-opacity': 0.7 },
      });
    };

    if (map.isStyleLoaded()) applyRoutes();
    else map.once('load', applyRoutes);

    return () => {
      markers.forEach((m) => m.remove());
    };
  }, [zones, resources, incidents, routes]);

  return (
    <div className="relative">
      <div ref={ref} className="h-[380px] w-full overflow-hidden rounded-lg border border-slate-700" />
      <div className="absolute right-3 top-3 rounded bg-slate-950/80 px-2 py-1 text-[10px] uppercase tracking-wide text-amber-300">
        Simulation data
      </div>
    </div>
  );
}
