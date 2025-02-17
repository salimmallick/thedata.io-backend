import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  CircularProgress,
  Alert
} from '@mui/material';
import { SystemStatus } from './SystemStatus';
import { ResourceMetrics } from './ResourceMetrics';
import { ConfigurationPanel } from './ConfigurationPanel';
import { AlertsPanel } from './AlertsPanel';
import { useAuth } from '../../hooks/useAuth';
import { api } from '../../services/api';
import { SystemStatus as SystemStatusType, ApiError } from '../../types/api';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatusType | null>(null);
  
  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const response = await api.get<SystemStatusType>('/api/v1/admin/system/status');
        setSystemStatus(response.data);
        setError(null);
      } catch (err) {
        const apiError = err as ApiError;
        setError(apiError.message || 'Failed to fetch system status');
      } finally {
        setLoading(false);
      }
    };
    
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000); // Refresh every 30s
    
    return () => clearInterval(interval);
  }, []);
  
  if (!user?.isAdmin) {
    return (
      <Alert severity="error">
        You don't have permission to access this page.
      </Alert>
    );
  }
  
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Grid container spacing={3}>
        {/* System Status */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              System Status
            </Typography>
            <SystemStatus metrics={systemStatus?.metrics || null} />
          </Paper>
        </Grid>
        
        {/* Resource Metrics */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Resource Metrics
            </Typography>
            <ResourceMetrics metrics={systemStatus?.resources || { history: [] }} />
          </Paper>
        </Grid>
        
        {/* Configuration */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Configuration
            </Typography>
            <ConfigurationPanel />
          </Paper>
        </Grid>
        
        {/* Alerts */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Active Alerts
            </Typography>
            <AlertsPanel />
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}; 