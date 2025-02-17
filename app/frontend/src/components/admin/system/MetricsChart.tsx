import React from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer
} from 'recharts';
import { Box, Typography } from '@mui/material';
import { SystemMetrics } from '../../../types/admin';

interface MetricsChartProps {
    data?: SystemMetrics[];
    timeRange?: '1h' | '24h' | '7d' | '30d';
}

export const MetricsChart: React.FC<MetricsChartProps> = ({ 
    data = [], 
    timeRange = '24h' 
}) => {
    const formatXAxis = (timestamp: string) => {
        const date = new Date(timestamp);
        switch (timeRange) {
            case '1h':
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            case '24h':
                return date.toLocaleString([], { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    hour12: false 
                });
            case '7d':
            case '30d':
                return date.toLocaleDateString([], { 
                    month: 'short', 
                    day: 'numeric' 
                });
        }
    };

    if (data.length === 0) {
        return (
            <Box 
                display="flex" 
                justifyContent="center" 
                alignItems="center" 
                height={300}
            >
                <Typography color="textSecondary">
                    No metrics data available
                </Typography>
            </Box>
        );
    }

    return (
        <Box height={300}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart
                    data={data}
                    margin={{
                        top: 5,
                        right: 30,
                        left: 20,
                        bottom: 5
                    }}
                >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                        dataKey="timestamp" 
                        tickFormatter={formatXAxis}
                        interval="preserveStartEnd"
                    />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip
                        labelFormatter={(label) => new Date(label).toLocaleString()}
                        formatter={(value: number) => [`${value.toFixed(2)}%`, '']}
                    />
                    <Legend />
                    <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="cpu_usage"
                        name="CPU Usage"
                        stroke="#8884d8"
                        dot={false}
                    />
                    <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="memory_usage"
                        name="Memory Usage"
                        stroke="#82ca9d"
                        dot={false}
                    />
                </LineChart>
            </ResponsiveContainer>
        </Box>
    );
}; 