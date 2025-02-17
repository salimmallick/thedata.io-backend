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
    Chip
} from '@mui/material';
import {
    Edit as EditIcon,
    Refresh as RefreshIcon,
    Add as AddIcon,
    CheckCircle as CheckCircleIcon,
    Error as ErrorIcon,
    Warning as WarningIcon
} from '@mui/icons-material';
import { MaterializedView } from '../../../types/data-management';
import { dataManagementService } from '../../../services/dataManagementService';

export const MaterializedViewManager: React.FC = () => {
    const [views, setViews] = useState<MaterializedView[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [openDialog, setOpenDialog] = useState(false);
    const [editingView, setEditingView] = useState<MaterializedView | null>(null);
    const [formData, setFormData] = useState<Partial<MaterializedView>>({});
    const [refreshing, setRefreshing] = useState<string | null>(null);

    const defaultFormData = {
        name: '',
        query: '',
        refresh_interval: '5 minutes',  // Default refresh interval
        status: 'active'
    };

    useEffect(() => {
        loadViews();
    }, []);

    const loadViews = async () => {
        try {
            const data = await dataManagementService.getMaterializedViews();
            setViews(data);
            setError(null);
        } catch (err) {
            setError('Failed to load materialized views');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (view: MaterializedView) => {
        setEditingView(view);
        setFormData(view);
        setOpenDialog(true);
    };

    const handleAdd = () => {
        setEditingView(null);
        setFormData(defaultFormData);
        setOpenDialog(true);
    };

    const handleRefresh = async (name: string) => {
        try {
            setRefreshing(name);
            await dataManagementService.refreshMaterializedView(name);
            await loadViews();
        } catch (err) {
            setError(`Failed to refresh view: ${name}`);
            console.error(err);
        } finally {
            setRefreshing(null);
        }
    };

    const handleSubmit = async () => {
        try {
            await dataManagementService.createMaterializedView(
                formData as MaterializedView
            );
            await loadViews();
            setOpenDialog(false);
        } catch (err) {
            setError('Failed to save view');
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
            case 'stale':
                return <Chip
                    icon={<WarningIcon />}
                    label="Stale"
                    color="warning"
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
                <Typography variant="h6">Materialized Views</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={handleAdd}
                >
                    Add View
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Refresh Interval</TableCell>
                            <TableCell>Last Refresh</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {views.map((view) => (
                            <TableRow key={view.name}>
                                <TableCell>{view.name}</TableCell>
                                <TableCell>{getStatusChip(view.status)}</TableCell>
                                <TableCell>{view.refresh_interval}</TableCell>
                                <TableCell>
                                    {new Date(view.last_refresh).toLocaleString()}
                                </TableCell>
                                <TableCell>
                                    <IconButton
                                        size="small"
                                        onClick={() => handleEdit(view)}
                                    >
                                        <EditIcon />
                                    </IconButton>
                                    <IconButton
                                        size="small"
                                        onClick={() => handleRefresh(view.name)}
                                        disabled={refreshing === view.name}
                                    >
                                        <RefreshIcon />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    {editingView ? 'Edit View' : 'Add View'}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} pt={1}>
                        <TextField
                            label="Name"
                            value={formData.name || ''}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            disabled={!!editingView}
                        />
                        <TextField
                            label="Query"
                            multiline
                            rows={4}
                            value={formData.query || ''}
                            onChange={(e) => setFormData({ ...formData, query: e.target.value })}
                        />
                        <TextField
                            label="Refresh Interval"
                            name="refresh_interval"
                            value={formData.refresh_interval || ''}
                            onChange={(e) => setFormData({
                                ...formData,
                                refresh_interval: e.target.value
                            })}
                            fullWidth
                            margin="normal"
                            helperText="e.g., '1 minute', '5 minutes', '30 seconds'"
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