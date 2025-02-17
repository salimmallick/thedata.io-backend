import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Save as SaveIcon
} from '@mui/icons-material';
import { api } from '../../services/api';

interface Config {
  resource_tracking: {
    enabled: boolean;
    interval: number;  // seconds
    retention: number;  // days
  };
  query_optimization: {
    enabled: boolean;
    slow_query_threshold: number;  // ms
    pattern_retention: number;  // days
  };
  metrics: {
    collection_enabled: boolean;
    intervals: {
      resource: number;  // seconds
      query: number;    // seconds
      system: number;   // seconds
    };
    retention: {
      resource: number;  // days
      query: number;    // days
      system: number;   // days
    };
  };
  alerts: {
    enabled: boolean;
    channels: string[];
    thresholds: {
      cpu: number;      // percent
      memory: number;   // percent
      disk: number;     // percent
      network: number;  // connections
    };
    notification_settings: {
      email: Record<string, any>;
      slack: Record<string, any>;
      pagerduty: Record<string, any>;
    };
  };
}

const defaultConfig: Config = {
  resource_tracking: {
    enabled: false,
    interval: 60,
    retention: 7
  },
  query_optimization: {
    enabled: false,
    slow_query_threshold: 1000,
    pattern_retention: 30
  },
  metrics: {
    collection_enabled: false,
    intervals: {
      resource: 60,
      query: 60,
      system: 60
    },
    retention: {
      resource: 7,
      query: 30,
      system: 7
    }
  },
  alerts: {
    enabled: false,
    channels: ['email'],
    thresholds: {
      cpu: 80,
      memory: 85,
      disk: 85,
      network: 1000
    },
    notification_settings: {
      email: {},
      slack: {},
      pagerduty: {}
    }
  }
};

type ConfigSection = keyof Config;
type ConfigValue = boolean | number;

export const ConfigurationPanel: React.FC = () => {
  const [config, setConfig] = useState<Config>(defaultConfig);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await api.get('/admin/system/config');
      setConfig(response.data || defaultConfig);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch configuration');
      setConfig(defaultConfig);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.put('/admin/system/config', config);
      setSuccessMessage('Configuration saved successfully');
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration');
      setSuccessMessage(null);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (section: ConfigSection, subsection: string, field: string, value: ConfigValue) => {
    setConfig(prev => {
      const updatedConfig = { ...prev };
      
      if (subsection === 'enabled') {
        (updatedConfig[section] as any).enabled = value;
      } else if (field === '') {
        (updatedConfig[section] as any)[subsection] = value;
      } else {
        const sectionData = updatedConfig[section] as any;
        if (sectionData[subsection]) {
          sectionData[subsection][field] = value;
        }
      }

      return updatedConfig;
    });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">System Configuration</Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? <CircularProgress size={24} /> : 'Save Changes'}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {successMessage}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Resource Tracking */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Resource Tracking
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography>Enabled</Typography>
                  <Switch
                    checked={config.resource_tracking.enabled}
                    onChange={(e) => handleChange('resource_tracking', 'enabled', '', e.target.checked)}
                  />
                </Box>
                <TextField
                  label="Interval (seconds)"
                  type="number"
                  value={config.resource_tracking.interval}
                  onChange={(e) => handleChange('resource_tracking', 'interval', '', parseInt(e.target.value) || 0)}
                  disabled={!config.resource_tracking.enabled}
                />
                <TextField
                  label="Retention (days)"
                  type="number"
                  value={config.resource_tracking.retention}
                  onChange={(e) => handleChange('resource_tracking', 'retention', '', parseInt(e.target.value) || 0)}
                  disabled={!config.resource_tracking.enabled}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Query Optimization */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Query Optimization
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography>Enabled</Typography>
                  <Switch
                    checked={config.query_optimization.enabled}
                    onChange={(e) => handleChange('query_optimization', 'enabled', '', e.target.checked)}
                  />
                </Box>
                <TextField
                  label="Slow Query Threshold (ms)"
                  type="number"
                  value={config.query_optimization.slow_query_threshold}
                  onChange={(e) => handleChange('query_optimization', 'slow_query_threshold', '', parseInt(e.target.value) || 0)}
                  disabled={!config.query_optimization.enabled}
                />
                <TextField
                  label="Pattern Retention (days)"
                  type="number"
                  value={config.query_optimization.pattern_retention}
                  onChange={(e) => handleChange('query_optimization', 'pattern_retention', '', parseInt(e.target.value) || 0)}
                  disabled={!config.query_optimization.enabled}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Metrics */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Metrics Collection
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography>Enabled</Typography>
                  <Switch
                    checked={config.metrics.collection_enabled}
                    onChange={(e) => handleChange('metrics', 'collection_enabled', '', e.target.checked)}
                  />
                </Box>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>
                      Collection Intervals
                    </Typography>
                    <Box display="flex" flexDirection="column" gap={2}>
                      <TextField
                        label="Resource Metrics (seconds)"
                        type="number"
                        value={config.metrics.intervals.resource}
                        onChange={(e) => handleChange('metrics', 'intervals', 'resource', parseInt(e.target.value) || 0)}
                        disabled={!config.metrics.collection_enabled}
                      />
                      <TextField
                        label="Query Metrics (seconds)"
                        type="number"
                        value={config.metrics.intervals.query}
                        onChange={(e) => handleChange('metrics', 'intervals', 'query', parseInt(e.target.value) || 0)}
                        disabled={!config.metrics.collection_enabled}
                      />
                      <TextField
                        label="System Metrics (seconds)"
                        type="number"
                        value={config.metrics.intervals.system}
                        onChange={(e) => handleChange('metrics', 'intervals', 'system', parseInt(e.target.value) || 0)}
                        disabled={!config.metrics.collection_enabled}
                      />
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>
                      Retention Periods
                    </Typography>
                    <Box display="flex" flexDirection="column" gap={2}>
                      <TextField
                        label="Resource Metrics (days)"
                        type="number"
                        value={config.metrics.retention.resource}
                        onChange={(e) => handleChange('metrics', 'retention', 'resource', parseInt(e.target.value) || 0)}
                        disabled={!config.metrics.collection_enabled}
                      />
                      <TextField
                        label="Query Metrics (days)"
                        type="number"
                        value={config.metrics.retention.query}
                        onChange={(e) => handleChange('metrics', 'retention', 'query', parseInt(e.target.value) || 0)}
                        disabled={!config.metrics.collection_enabled}
                      />
                      <TextField
                        label="System Metrics (days)"
                        type="number"
                        value={config.metrics.retention.system}
                        onChange={(e) => handleChange('metrics', 'retention', 'system', parseInt(e.target.value) || 0)}
                        disabled={!config.metrics.collection_enabled}
                      />
                    </Box>
                  </Grid>
                </Grid>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Alerts */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Alert Thresholds
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography>Enabled</Typography>
                  <Switch
                    checked={config.alerts.enabled}
                    onChange={(e) => handleChange('alerts', 'enabled', '', e.target.checked)}
                  />
                </Box>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="CPU Usage Threshold (%)"
                      type="number"
                      value={config.alerts.thresholds.cpu}
                      onChange={(e) => handleChange('alerts', 'thresholds', 'cpu', parseInt(e.target.value) || 0)}
                      disabled={!config.alerts.enabled}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Memory Usage Threshold (%)"
                      type="number"
                      value={config.alerts.thresholds.memory}
                      onChange={(e) => handleChange('alerts', 'thresholds', 'memory', parseInt(e.target.value) || 0)}
                      disabled={!config.alerts.enabled}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Disk Usage Threshold (%)"
                      type="number"
                      value={config.alerts.thresholds.disk}
                      onChange={(e) => handleChange('alerts', 'thresholds', 'disk', parseInt(e.target.value) || 0)}
                      disabled={!config.alerts.enabled}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Network Connections Threshold"
                      type="number"
                      value={config.alerts.thresholds.network}
                      onChange={(e) => handleChange('alerts', 'thresholds', 'network', parseInt(e.target.value) || 0)}
                      disabled={!config.alerts.enabled}
                    />
                  </Grid>
                </Grid>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}; 