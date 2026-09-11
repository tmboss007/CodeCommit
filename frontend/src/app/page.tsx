'use client';

import { useEffect, useState } from 'react';
import { zonesAPI, incidentsAPI, resourcesAPI, auditAPI } from '@/lib/api';
import type { Zone, Incident, Resource, AuditEvent } from '@/types';
import { formatRelativeTime, getPriorityColor, getSeverityColor, getStatusColor } from '@/lib/utils';
import Link from 'next/link';

export default function CommandCenter() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [zonesRes, incidentsRes, resourcesRes, auditRes] = await Promise.all([
        zonesAPI.list(),
        incidentsAPI.list({ limit: 10 }),
        resourcesAPI.list(),
        auditAPI.list({ limit: 20 }),
      ]);

      setZones(zonesRes.data);
      setIncidents(incidentsRes.data);
      setResources(resourcesRes.data);
      setAuditEvents(auditRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  };

  const stats = {
    activeIncidents: incidents.filter((i) => i.status === 'active').length,
    criticalZones: zones.filter((z) => z.priority_score >= 80).length,
    availableResources: resources.filter((r) => r.status === 'available').length,
    deployedResources: resources.filter((r) => r.status === 'deployed').length,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="container mx-auto">
          <h1 className="text-2xl font-bold">NEXUS-R Command Center</h1>
          <p className="text-blue-100 text-sm">Agentic Disaster Resource Orchestration Platform</p>
        </div>
      </header>

      <div className="container mx-auto p-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard title="Active Incidents" value={stats.activeIncidents} color="red" />
          <StatCard title="Critical Zones" value={stats.criticalZones} color="orange" />
          <StatCard title="Available Resources" value={stats.availableResources} color="green" />
          <StatCard title="Deployed Resources" value={stats.deployedResources} color="blue" />
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Zones Priority */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Zone Priority</h2>
            <div className="space-y-3">
              {zones
                .sort((a, b) => b.priority_score - a.priority_score)
                .slice(0, 5)
                .map((zone) => (
                  <div key={zone.id} className="flex items-center justify-between border-b pb-2">
                    <div>
                      <div className="font-medium">{zone.name}</div>
                      <div className="text-sm text-gray-500">
                        Severity: <span className={`inline-block w-16 h-2 ${getSeverityColor(zone.severity)} rounded`}></span>
                      </div>
                    </div>
                    <div className={`text-2xl font-bold ${getPriorityColor(zone.priority_score)}`}>
                      {zone.priority_score.toFixed(0)}
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Recent Incidents */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Recent Incidents</h2>
            <div className="space-y-3">
              {incidents.slice(0, 5).map((incident) => (
                <div key={incident.id} className="border-b pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-sm">{incident.report_text.slice(0, 80)}...</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {incident.zone_id} • {formatRelativeTime(incident.timestamp)}
                      </div>
                    </div>
                    <span className={`px-2 py-1 text-xs rounded ${getStatusColor(incident.status)}`}>
                      {incident.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Activity Stream */}
          <div className="bg-white rounded-lg shadow p-6 lg:col-span-2">
            <h2 className="text-lg font-semibold mb-4">Activity Stream</h2>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {auditEvents.map((event) => (
                <div key={event.id} className="flex items-start space-x-3 text-sm border-b pb-2">
                  <div className="text-gray-400 text-xs w-16 flex-shrink-0">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="flex-1">
                    <span className="font-medium text-blue-600">{event.agent || event.actor}</span>
                    <span className="text-gray-600"> • {event.description}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex gap-4">
          <Link href="/incidents" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            View All Incidents
          </Link>
          <Link href="/resources" className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
            Manage Resources
          </Link>
          <Link href="/coordination" className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700">
            Coordination Tasks
          </Link>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, color }: { title: string; value: number; color: string }) {
  const colorClasses = {
    red: 'bg-red-50 text-red-600 border-red-200',
    orange: 'bg-orange-50 text-orange-600 border-orange-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
  };

  return (
    <div className={`rounded-lg border-2 p-4 ${colorClasses[color as keyof typeof colorClasses]}`}>
      <div className="text-sm font-medium opacity-80">{title}</div>
      <div className="text-3xl font-bold mt-2">{value}</div>
    </div>
  );
}
