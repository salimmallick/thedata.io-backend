import React, { useState, useEffect } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Typography,
  Chip,
  IconButton,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import { api } from '../../services/api';

interface Alert {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  name: string;
  description: string;
  timestamp: string;
  status: 'active' | 'resolved';
  value: number;
  threshold: number;
}

export const AlertsPanel: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchAlerts = async () => {
    try {
      const response = await api.get('/admin/alerts/active');
      setAlerts(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch alerts');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);
  
  const getSeverityIcon = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical':
        return <ErrorIcon color="error" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      default:
        return <InfoIcon color="info" />;
    }
  };
  
  const getSeverityColor = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  };
  
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={2}>
        <CircularProgress />
      </Box>
    );
  }
  
  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          Active Alerts ({alerts.length})
        </Typography>
        <IconButton onClick={fetchAlerts} size="small">
          <RefreshIcon />
        </IconButton>
      </Box>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {alerts.length === 0 ? (
        <Alert severity="success">
          No active alerts
        </Alert>
      ) : (
        <List>
          {alerts.map((alert) => (
            <ListItem
              key={alert.id}
              sx={{
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                mb: 1
              }}
            >
              <ListItemIcon>
                {getSeverityIcon(alert.severity)}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="subtitle1">
                      {alert.name}
                    </Typography>
                    <Chip
                      label={alert.severity}
                      size="small"
                      color={getSeverityColor(alert.severity)}
                    />
                  </Box>
                }
                secondary={
                  <>
                    <Typography variant="body2" color="text.secondary">
                      {alert.description}
                    </Typography>
                    <Box display="flex" gap={1} mt={0.5}>
                      <Typography variant="caption" color="text.secondary">
                        Value: {alert.value}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Threshold: {alert.threshold}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Since: {format(new Date(alert.timestamp), 'MMM d, HH:mm:ss')}
                      </Typography>
                    </Box>
                  </>
                }
              />
              <Chip
                label={alert.status}
                size="small"
                color={alert.status === 'active' ? 'error' : 'success'}
                sx={{ ml: 1 }}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
}; 