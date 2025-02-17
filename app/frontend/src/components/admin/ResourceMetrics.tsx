import React from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  useTheme
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { format } from 'date-fns';

interface MetricsData {
  timestamp: string;
  cpu: number;
  memory: number;
  disk: number;
  network: number;
}

interface ResourceMetricsProps {
  metrics: {
    history: MetricsData[];
  };
}

export const ResourceMetrics: React.FC<ResourceMetricsProps> = ({ metrics }) => {
  const theme = useTheme();
  
  const formatTime = (timestamp: string) => {
    return format(new Date(timestamp), 'HH:mm:ss');
  };
  
  return (
    <Box>
      <Grid container spacing={2}>
        {/* CPU Usage Chart */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                CPU Usage Over Time
              </Typography>
              <Box height={200}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={metrics.history}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={formatTime}
                    />
                    <YAxis unit="%" />
                    <Tooltip
                      labelFormatter={formatTime}
                      formatter={(value: number) => [`${value}%`, 'CPU Usage']}
                    />
                    <Line
                      type="monotone"
                      dataKey="cpu"
                      stroke={theme.palette.primary.main}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Memory Usage Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Memory Usage
              </Typography>
              <Box height={200}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={metrics.history}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={formatTime}
                    />
                    <YAxis unit="%" />
                    <Tooltip
                      labelFormatter={formatTime}
                      formatter={(value: number) => [`${value}%`, 'Memory Usage']}
                    />
                    <Line
                      type="monotone"
                      dataKey="memory"
                      stroke={theme.palette.secondary.main}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Disk Usage Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Disk Usage
              </Typography>
              <Box height={200}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={metrics.history}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={formatTime}
                    />
                    <YAxis unit="%" />
                    <Tooltip
                      labelFormatter={formatTime}
                      formatter={(value: number) => [`${value}%`, 'Disk Usage']}
                    />
                    <Line
                      type="monotone"
                      dataKey="disk"
                      stroke={theme.palette.error.main}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Network Usage Chart */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Network Usage
              </Typography>
              <Box height={200}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={metrics.history}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={formatTime}
                    />
                    <YAxis unit="MB/s" />
                    <Tooltip
                      labelFormatter={formatTime}
                      formatter={(value: number) => [`${value} MB/s`, 'Network Usage']}
                    />
                    <Line
                      type="monotone"
                      dataKey="network"
                      stroke={theme.palette.info.main}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}; 