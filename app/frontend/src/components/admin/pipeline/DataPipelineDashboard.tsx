import React, { useState, useEffect } from 'react';
import {
    Box,
    Paper,
    Typography,
    Grid,
    CircularProgress,
    Alert,
    Chip,
    IconButton,
    Card,
    CardContent,
    LinearProgress,
    Tooltip,
    Button
} from '@mui/material';
import {
    Refresh as RefreshIcon,
    PlayArrow as StartIcon,
    Stop as StopIcon,
    Settings as SettingsIcon,
    Warning as WarningIcon
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, Legend } from 'recharts';
import { adminService } from '../../../services/adminService';
import { PipelineComponent, PipelineMetrics, DataPipeline } from '../../../types/data-management';
import { ComponentSettingsDialog } from './ComponentSettingsDialog';

export const DataPipelineDashboard: React.FC = () => {
    const [pipeline, setPipeline] = useState<DataPipeline | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedComponent, setSelectedComponent] = useState<PipelineComponent | null>(null);

    useEffect(() => {
        loadPipelineData();
        const interval = setInterval(loadPipelineData, 30000); // Refresh every 30 seconds
        return () => clearInterval(interval);
    }, []);

    const loadPipelineData = async () => {
        try {
            setLoading(true);
            const data = await adminService.getPipelineStatus();
            setPipeline(data);
        } catch (err) {
            setError('Failed to load pipeline data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getHealthColor = (health: 'healthy' | 'degraded' | 'unhealthy'): "success" | "warning" | "error" => {
        switch (health) {
            case 'healthy':
                return "success";
            case 'degraded':
                return "warning";
            case 'unhealthy':
                return "error";
            default:
                return "error";
        }
    };

    const getComponentStatusChip = (status: string) => {
        const colors: Record<string, "success" | "warning" | "error"> = {
            healthy: "success",
            degraded: "warning",
            error: "error"
        };

        return (
            <Chip
                label={status}
                color={colors[status] || "default"}
                size="small"
            />
        );
    };

    const handleComponentAction = async (componentName: string, action: 'start' | 'stop' | 'restart') => {
        try {
            await adminService.controlPipelineComponent(componentName, action);
            await loadPipelineData();
        } catch (err) {
            setError(`Failed to ${action} component: ${componentName}`);
        }
    };

    const renderMetricsChart = (metrics: PipelineMetrics[]) => (
        <Box height={300}>
            <LineChart
                width={600}
                height={300}
                data={metrics}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <ChartTooltip />
                <Legend />
                <Line type="monotone" dataKey="throughput" stroke="#8884d8" name="Throughput" />
                <Line type="monotone" dataKey="latency" stroke="#82ca9d" name="Latency (ms)" />
                <Line type="monotone" dataKey="error_rate" stroke="#ff7300" name="Error Rate %" />
            </LineChart>
        </Box>
    );

    if (loading && !pipeline) {
        return (
            <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box p={3}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h4">
                    Data Pipeline Management
                </Typography>
                <Button
                    startIcon={<RefreshIcon />}
                    onClick={loadPipelineData}
                    disabled={loading}
                >
                    Refresh
                </Button>
            </Box>

            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            {pipeline && (
                <>
                    {/* Overall Health Card */}
                    <Card sx={{ mb: 3 }}>
                        <CardContent>
                            <Grid container spacing={3}>
                                <Grid item xs={4}>
                                    <Typography variant="h6" gutterBottom>
                                        Overall Health
                                    </Typography>
                                    <Box display="flex" alignItems="center">
                                        <Typography variant="h3" color={getHealthColor(pipeline.overall_health)}>
                                            {pipeline.overall_health.toUpperCase()}
                                        </Typography>
                                    </Box>
                                </Grid>
                                <Grid item xs={4}>
                                    <Typography variant="h6" gutterBottom>
                                        Active Alerts
                                    </Typography>
                                    <Box display="flex" alignItems="center">
                                        {pipeline.alerts.length > 0 ? (
                                            <Chip
                                                icon={<WarningIcon />}
                                                label={`${pipeline.alerts.length} Active Alerts`}
                                                color="warning"
                                            />
                                        ) : (
                                            <Chip label="No Active Alerts" color="success" />
                                        )}
                                    </Box>
                                </Grid>
                                <Grid item xs={4}>
                                    <Typography variant="h6" gutterBottom>
                                        Performance Bottlenecks
                                    </Typography>
                                    <Box>
                                        {pipeline.alerts
                                            .filter(alert => alert.severity === 'warning' || alert.severity === 'error')
                                            .map((alert, index) => (
                                                <Chip
                                                    key={alert.id}
                                                    label={alert.message}
                                                    color={alert.severity === 'error' ? 'error' : 'warning'}
                                                    sx={{ m: 0.5 }}
                                                />
                                            ))}
                                    </Box>
                                </Grid>
                            </Grid>
                        </CardContent>
                    </Card>

                    {/* Component Grid */}
                    <Grid container spacing={3}>
                        {pipeline.components.map((component) => (
                            <Grid item xs={12} md={6} lg={4} key={component.name}>
                                <Paper sx={{ p: 2 }}>
                                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                                        <Typography variant="h6">
                                            {component.name}
                                        </Typography>
                                        <Box>
                                            {getComponentStatusChip(component.status)}
                                            <IconButton
                                                size="small"
                                                onClick={() => handleComponentAction(component.name, 'restart')}
                                            >
                                                <RefreshIcon />
                                            </IconButton>
                                            <IconButton
                                                size="small"
                                                onClick={() => setSelectedComponent(component)}
                                            >
                                                <SettingsIcon />
                                            </IconButton>
                                        </Box>
                                    </Box>

                                    <Box mb={2}>
                                        <Typography variant="body2" color="text.secondary">
                                            Throughput
                                        </Typography>
                                        <Box display="flex" alignItems="center">
                                            <Box flexGrow={1} mr={1}>
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={(component.metrics.throughput / 1000) * 100}
                                                    color={component.metrics.throughput > 800 ? "warning" : "primary"}
                                                />
                                            </Box>
                                            <Typography variant="body2">
                                                {component.metrics.throughput}/s
                                            </Typography>
                                        </Box>
                                    </Box>

                                    <Box mb={2}>
                                        <Typography variant="body2" color="text.secondary">
                                            Latency
                                        </Typography>
                                        <Box display="flex" alignItems="center">
                                            <Box flexGrow={1} mr={1}>
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={(component.metrics.latency / 1000) * 100}
                                                    color={component.metrics.latency > 500 ? "error" : "primary"}
                                                />
                                            </Box>
                                            <Typography variant="body2">
                                                {component.metrics.latency}ms
                                            </Typography>
                                        </Box>
                                    </Box>

                                    <Box>
                                        <Typography variant="body2" color="text.secondary">
                                            Error Rate
                                        </Typography>
                                        <Box display="flex" alignItems="center">
                                            <Box flexGrow={1} mr={1}>
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={component.metrics.error_rate}
                                                    color={component.metrics.error_rate > 5 ? "error" : "primary"}
                                                />
                                            </Box>
                                            <Typography variant="body2">
                                                {component.metrics.error_rate}%
                                            </Typography>
                                        </Box>
                                    </Box>
                                </Paper>
                            </Grid>
                        ))}
                    </Grid>
                </>
            )}

            <ComponentSettingsDialog
                open={!!selectedComponent}
                onClose={() => setSelectedComponent(null)}
                component={selectedComponent}
            />
        </Box>
    );
}; 