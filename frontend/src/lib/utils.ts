import { type ClassValue, clsx } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString();
}

export function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function getSeverityColor(severity: number): string {
  if (severity >= 8) return 'bg-red-600';
  if (severity >= 6) return 'bg-orange-500';
  if (severity >= 4) return 'bg-yellow-500';
  return 'bg-blue-500';
}

export function getPriorityColor(priority: number): string {
  if (priority >= 80) return 'text-red-600';
  if (priority >= 60) return 'text-orange-500';
  if (priority >= 40) return 'text-yellow-600';
  return 'text-blue-600';
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    pending: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-blue-100 text-blue-800',
    rejected: 'bg-red-100 text-red-800',
    completed: 'bg-gray-100 text-gray-800',
    available: 'bg-green-100 text-green-800',
    deployed: 'bg-blue-100 text-blue-800',
    unavailable: 'bg-gray-100 text-gray-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}
