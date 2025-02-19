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
import { adminService } from '../../../services/adminService';

export const SystemOverview: React.FC = () => {
    const [overview, setOverview] = useState<any>(null);
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
            console.log('System overview data:', data);
            setOverview(data);
            setError(null);
        } catch (err) {
            console.error('Failed to load system overview:', err);
            setError('Failed to load system overview');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'healthy':
            case 'ok':
                return <HealthyIcon color="success" />;
            case 'degraded':
            case 'warning':
                return <DegradedIcon color="warning" />;
            case 'error':
                return <ErrorIcon color="error" />;
            default:
                return null;
        }
    };

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" p={3}>
                <CircularProgress />
            </Box>
        );
    }

    if (!overview?.metrics) {
        return (
            <Alert severity="error" sx={{ mb: 2 }}>
                {error || 'No system metrics available'}
            </Alert>
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
                                            {overview.metrics.cpu?.usage_percent?.toFixed(1)}%
                                        </Typography>
                                        <LinearProgress
                                            variant="determinate"
                                            value={overview.metrics.cpu?.usage_percent || 0}
                                            color={overview.metrics.cpu?.above_threshold ? "error" : "primary"}
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
                                            {overview.metrics.memory?.percent?.toFixed(1)}%
                                        </Typography>
                                        <LinearProgress
                                            variant="determinate"
                                            value={overview.metrics.memory?.percent || 0}
                                            color={overview.metrics.memory?.above_threshold ? "error" : "primary"}
                                            sx={{ mt: 1 }}
                                        />
                                    </CardContent>
                                </Card>
                            </Grid>
                            <Grid item xs={12} md={6}>
                                <Card>
                                    <CardContent>
                                        <Typography color="textSecondary" gutterBottom>
                                            Disk Usage
                                        </Typography>
                                        <Typography variant="h4">
                                            {overview.metrics.disk?.percent?.toFixed(1)}%
                                        </Typography>
                                        <LinearProgress
                                            variant="determinate"
                                            value={overview.metrics.disk?.percent || 0}
                                            sx={{ mt: 1 }}
                                        />
                                    </CardContent>
                                </Card>
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
                            <ListItem>
                                <ListItemText
                                    primary="API Server"
                                    secondary={overview.status}
                                />
                                <ListItemSecondaryAction>
                                    {getStatusIcon(overview.status)}
                                </ListItemSecondaryAction>
                            </ListItem>
                            <ListItem>
                                <ListItemText
                                    primary="Database"
                                    secondary={overview.health ? "Connected" : "Not Connected"}
                                />
                                <ListItemSecondaryAction>
                                    {getStatusIcon(overview.health ? "healthy" : "error")}
                                </ListItemSecondaryAction>
                            </ListItem>
                        </List>
                    </Paper>
                </Grid>

                {/* System Alerts */}
                <Grid item xs={12}>
                    <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>
                            System Alerts
                        </Typography>
                        <List>
                            {(overview.metrics.cpu?.above_threshold || overview.metrics.memory?.above_threshold) ? (
                                <>
                                    {overview.metrics.cpu?.above_threshold && (
                                        <ListItem>
                                            <ListItemText
                                                primary="High CPU Usage"
                                                secondary={`Current usage: ${overview.metrics.cpu.usage_percent.toFixed(1)}%`}
                                            />
                                            <Chip label="Warning" color="warning" />
                                        </ListItem>
                                    )}
                                    {overview.metrics.memory?.above_threshold && (
                                        <ListItem>
                                            <ListItemText
                                                primary="High Memory Usage"
                                                secondary={`Current usage: ${overview.metrics.memory.percent.toFixed(1)}%`}
                                            />
                                            <Chip label="Warning" color="warning" />
                                        </ListItem>
                                    )}
                                </>
                            ) : (
                                <ListItem>
                                    <ListItemText
                                        primary="No active alerts"
                                        secondary="System is running normally"
                                    />
                                    <Chip label="Healthy" color="success" />
                                </ListItem>
                            )}
                        </List>
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );
}; 