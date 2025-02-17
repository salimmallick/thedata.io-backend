import React, { useState, useEffect } from 'react';
import {
    Box,
    Grid,
    Paper,
    Typography,
    CircularProgress,
    Alert,
    Card,
    CardContent,
    IconButton,
    Chip,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction,
    Tooltip,
    LinearProgress
} from '@mui/material';
import {
    CheckCircle as HealthyIcon,
    Warning as DegradedIcon,
    Error as ErrorIcon,
    Done as DoneIcon,
    Refresh as RefreshIcon
} from '@mui/icons-material';
import { SystemMetrics, SystemOverview as SystemOverviewType } from '../../../types/admin';
import { adminService } from '../../../services/adminService';
import { MetricsChart } from './MetricsChart';

export const SystemOverview: React.FC = () => {
    const [overview, setOverview] = useState<SystemOverviewType | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        loadOverview();
        const interval = setInterval(loadOverview, 30000); // Refresh every 30 seconds
        return () => clearInterval(interval);
    }, []);

    const loadOverview = async () => {
        try {
            setRefreshing(true);
            const data = await adminService.getSystemOverview();
            setOverview(data);
            setError(null);
        } catch (err) {
            setError('Failed to load system overview');
            console.error(err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const handleAcknowledgeAlert = async (alertId: string) => {
        try {
            await adminService.acknowledgeAlert(alertId);
            await loadOverview();
        } catch (err) {
            setError('Failed to acknowledge alert');
            console.error(err);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'healthy':
                return <HealthyIcon color="success" />;
            case 'degraded':
                return <DegradedIcon color="warning" />;
            case 'error':
                return <ErrorIcon color="error" />;
            default:
                return null;
        }
    };

    const getAlertSeverityColor = (severity: string) => {
        switch (severity) {
            case 'error':
                return 'error';
            case 'warning':
                return 'warning';
            case 'info':
                return 'info';
            default:
                return 'default';
        }
    };

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" p={3}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box>
            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
            )}

            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">System Overview</Typography>
                <Tooltip title="Refresh">
                    <IconButton onClick={loadOverview} disabled={refreshing}>
                        <RefreshIcon />
                    </IconButton>
                </Tooltip>
            </Box>

            {refreshing && <LinearProgress sx={{ mb: 2 }} />}

            <Grid container spacing={3}>
                {/* System Metrics */}
                <Grid item xs={12} lg={8}>
                    <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>
                            System Metrics
                        </Typography>
                        <Grid container spacing={2}>
                            <Grid item xs={12} md={6}>
                                <Card>
                                    <CardContent>
                                        <Typography color="textSecondary" gutterBottom>
                                            CPU Usage
                                        </Typography>
                                        <Typography variant="h4">
                                            {overview?.metrics.cpu_usage.toFixed(1)}%
                                        </Typography>
                                        <LinearProgress
                                            variant="determinate"
                                            value={overview?.metrics.cpu_usage || 0}
                                            sx={{ mt: 1 }}
                                        />
                                    </CardContent>
                                </Card>
                            </Grid>
                            <Grid item xs={12} md={6}>
                                <Card>
                                    <CardContent>
                                        <Typography color="textSecondary" gutterBottom>
                                            Memory Usage
                                        </Typography>
                                        <Typography variant="h4">
                                            {overview?.metrics.memory_usage.toFixed(1)}%
                                        </Typography>
                                        <LinearProgress
                                            variant="determinate"
                                            value={overview?.metrics.memory_usage || 0}
                                            sx={{ mt: 1 }}
                                        />
                                    </CardContent>
                                </Card>
                            </Grid>
                            <Grid item xs={12}>
                                <MetricsChart 
                                    data={overview?.metrics ? [overview.metrics] : undefined}
                                    timeRange="24h"
                                />
                            </Grid>
                        </Grid>
                    </Paper>
                </Grid>

                {/* Component Status */}
                <Grid item xs={12} lg={4}>
                    <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>
                            Component Status
                        </Typography>
                        <List>
                            {overview?.components.map((component) => (
                                <ListItem key={component.name}>
                                    <ListItemText
                                        primary={component.name}
                                        secondary={component.message}
                                    />
                                    <ListItemSecondaryAction>
                                        {getStatusIcon(component.status)}
                                    </ListItemSecondaryAction>
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Grid>

                {/* Alerts */}
                <Grid item xs={12}>
                    <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>
                            Active Alerts
                        </Typography>
                        <List>
                            {overview?.alerts
                                .filter((alert) => !alert.acknowledged)
                                .map((alert) => (
                                    <ListItem key={alert.id}>
                                        <ListItemText
                                            primary={alert.message}
                                            secondary={new Date(alert.timestamp).toLocaleString()}
                                        />
                                        <ListItemSecondaryAction>
                                            <Chip
                                                label={alert.severity}
                                                color={getAlertSeverityColor(alert.severity)}
                                                size="small"
                                                sx={{ mr: 1 }}
                                            />
                                            <Tooltip title="Acknowledge">
                                                <IconButton
                                                    edge="end"
                                                    size="small"
                                                    onClick={() => handleAcknowledgeAlert(alert.id)}
                                                >
                                                    <DoneIcon />
                                                </IconButton>
                                            </Tooltip>
                                        </ListItemSecondaryAction>
                                    </ListItem>
                                ))}
                        </List>
                    </Paper>
                </Grid>

                {/* Recent Events */}
                <Grid item xs={12}>
                    <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>
                            Recent Events
                        </Typography>
                        <List>
                            {overview?.events.map((event) => (
                                <ListItem key={event.id}>
                                    <ListItemText
                                        primary={event.message}
                                        secondary={new Date(event.timestamp).toLocaleString()}
                                    />
                                    <ListItemSecondaryAction>
                                        <Chip label={event.type} size="small" />
                                    </ListItemSecondaryAction>
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );
}; 