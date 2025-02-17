import React, { useState, useEffect } from 'react';
import {
    Box,
    Paper,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    IconButton,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Alert,
    CircularProgress,
    Chip,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Tooltip
} from '@mui/material';
import {
    Add as AddIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    CheckCircle as CheckCircleIcon,
    Error as ErrorIcon
} from '@mui/icons-material';
import { DataSink } from '../../../types/data-management';
import { dataManagementService } from '../../../services/dataManagementService';
import { JsonEditor } from '../../common/JsonEditor';

export const DataSinkManager: React.FC = () => {
    const [sinks, setSinks] = useState<DataSink[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [openDialog, setOpenDialog] = useState(false);
    const [editingSink, setEditingSink] = useState<DataSink | null>(null);
    const [formData, setFormData] = useState<Partial<DataSink>>({});

    useEffect(() => {
        loadSinks();
    }, []);

    const loadSinks = async () => {
        try {
            const data = await dataManagementService.getDataSinks();
            setSinks(data);
            setError(null);
        } catch (err) {
            setError('Failed to load data sinks');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (sink: DataSink) => {
        setEditingSink(sink);
        setFormData(sink);
        setOpenDialog(true);
    };

    const handleAdd = () => {
        setEditingSink(null);
        setFormData({
            name: '',
            type: 'postgres',
            status: 'inactive',
            config: {}
        });
        setOpenDialog(true);
    };

    const handleSubmit = async () => {
        try {
            await dataManagementService.createDataSink(formData as DataSink);
            await loadSinks();
            setOpenDialog(false);
        } catch (err) {
            setError('Failed to save data sink');
            console.error(err);
        }
    };

    const getStatusChip = (status: string) => {
        switch (status) {
            case 'active':
                return <Chip
                    icon={<CheckCircleIcon />}
                    label="Active"
                    color="success"
                    size="small"
                />;
            case 'error':
                return <Chip
                    icon={<ErrorIcon />}
                    label="Error"
                    color="error"
                    size="small"
                />;
            default:
                return <Chip label={status} size="small" />;
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
                <Typography variant="h6">Data Sinks</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={handleAdd}
                >
                    Add Sink
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Records Processed</TableCell>
                            <TableCell>Last Error</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {sinks.map((sink) => (
                            <TableRow key={sink.name}>
                                <TableCell>{sink.name}</TableCell>
                                <TableCell>{sink.type}</TableCell>
                                <TableCell>{getStatusChip(sink.status)}</TableCell>
                                <TableCell>{sink.metrics?.records_processed || 0}</TableCell>
                                <TableCell>
                                    {sink.metrics?.last_error ? (
                                        <Tooltip title={sink.metrics.last_error}>
                                            <Typography
                                                variant="body2"
                                                sx={{
                                                    maxWidth: 200,
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                    whiteSpace: 'nowrap'
                                                }}
                                            >
                                                {sink.metrics.last_error}
                                            </Typography>
                                        </Tooltip>
                                    ) : (
                                        '-'
                                    )}
                                </TableCell>
                                <TableCell>
                                    <IconButton
                                        size="small"
                                        onClick={() => handleEdit(sink)}
                                    >
                                        <EditIcon />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    {editingSink ? 'Edit Sink' : 'Add Sink'}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} pt={1}>
                        <TextField
                            label="Name"
                            value={formData.name || ''}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            disabled={!!editingSink}
                        />
                        <FormControl>
                            <InputLabel>Type</InputLabel>
                            <Select
                                value={formData.type || ''}
                                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                label="Type"
                            >
                                <MenuItem value="postgres">PostgreSQL</MenuItem>
                                <MenuItem value="clickhouse">ClickHouse</MenuItem>
                                <MenuItem value="questdb">QuestDB</MenuItem>
                                <MenuItem value="s3">S3</MenuItem>
                                <MenuItem value="kafka">Kafka</MenuItem>
                            </Select>
                        </FormControl>
                        <Typography variant="subtitle2" sx={{ mt: 1 }}>
                            Configuration
                        </Typography>
                        <JsonEditor
                            value={formData.config || {}}
                            onChange={(config) => setFormData({ ...formData, config })}
                        />
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
                    <Button onClick={handleSubmit} variant="contained" color="primary">
                        Save
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}; 