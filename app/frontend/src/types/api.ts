export interface SystemMetricsData {
  cpu: {
    usage_percent: number;
    above_threshold: boolean;
  };
  memory: {
    total: number;
    available: number;
    used: number;
    percent: number;
    above_threshold: boolean;
  };
  disk: {
    total: number;
    used: number;
    free: number;
    percent: number;
  };
  error?: string;
  message?: string;
}

export type SystemMetrics = SystemMetricsData;

export interface ResourceMetrics {
  history: Array<{
    timestamp: string;
    cpu: number;
    memory: number;
    disk: number;
    network: number;
  }>;
}

export interface Alert {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  name: string;
  description: string;
  timestamp: string;
  status: 'active' | 'resolved';
  value: number;
  threshold: number;
}

export interface SystemStatus {
  metrics: SystemMetrics;
  resources: ResourceMetrics;
  alerts: Alert[];
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
} 