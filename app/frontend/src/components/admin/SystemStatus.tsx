import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  LinearProgress,
  Chip,
  IconButton,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon,
  Speed as PerformanceIcon,
  CloudQueue as NetworkIcon
} from '@mui/icons-material';
import { api } from '../../services/api';
import { formatDistanceToNow, isValid } from 'date-fns';
import { ApiError } from '../../types/api';

interface SystemMetricsData {
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

interface SystemStatusProps {
  metrics?: SystemMetricsData | null;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({ metrics: initialMetrics }) => {
  const [metrics, setMetrics] = useState<SystemMetricsData | null>(initialMetrics || null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const response = await api.get<{ metrics: SystemMetricsData }>('/admin/system/status');
      if (response.data.metrics) {
        setMetrics(response.data.metrics);
        setError(null);
      } else {
        setError('Invalid metrics data received');
        setMetrics(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch system metrics');
      setMetrics(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialMetrics) {
      fetchMetrics();
      const interval = setInterval(fetchMetrics, 30000); // Refresh every 30s
      return () => clearInterval(interval);
    } else {
      setLoading(false);
    }
  }, [initialMetrics]);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!metrics) {
    return (
      <Alert severity="warning">
        No system metrics available
      </Alert>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">System Status</Typography>
        <IconButton onClick={fetchMetrics} size="small">
          <RefreshIcon />
        </IconButton>
      </Box>

      <Grid container spacing={3}>
        {/* CPU Usage */}
        {metrics.cpu && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <MemoryIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">CPU Usage</Typography>
                  <Chip
                    label={`${metrics.cpu.usage_percent.toFixed(1)}%`}
                    color={metrics.cpu.above_threshold ? 'error' : 'success'}
                    size="small"
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={metrics.cpu.usage_percent}
                  color={metrics.cpu.above_threshold ? 'error' : 'success'}
                />
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Memory Usage */}
        {metrics.memory && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <MemoryIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">Memory Usage</Typography>
                  <Chip
                    label={`${metrics.memory.percent.toFixed(1)}%`}
                    color={metrics.memory.above_threshold ? 'error' : 'success'}
                    size="small"
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={metrics.memory.percent}
                  color={metrics.memory.above_threshold ? 'error' : 'success'}
                />
                <Box mt={1}>
                  <Typography variant="body2" color="text.secondary">
                    Used: {formatBytes(metrics.memory.used)} / Total: {formatBytes(metrics.memory.total)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Available: {formatBytes(metrics.memory.available)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Disk Usage */}
        {metrics.disk && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <StorageIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">Disk Usage</Typography>
                  <Chip
                    label={`${metrics.disk.percent.toFixed(1)}%`}
                    color={metrics.disk.percent > 85 ? 'error' : 'success'}
                    size="small"
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={metrics.disk.percent}
                  color={metrics.disk.percent > 85 ? 'error' : 'success'}
                />
                <Box mt={1}>
                  <Typography variant="body2" color="text.secondary">
                    Used: {formatBytes(metrics.disk.used)} / Total: {formatBytes(metrics.disk.total)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Free: {formatBytes(metrics.disk.free)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}; 