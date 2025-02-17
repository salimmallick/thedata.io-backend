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
    CircularProgress
} from '@mui/material';
import {
    Edit as EditIcon,
    Add as AddIcon
} from '@mui/icons-material';
import { RetentionPolicy } from '../../../types/data-management';
import { dataManagementService } from '../../../services/dataManagementService';

export const RetentionPolicyManager: React.FC = () => {
    const [policies, setPolicies] = useState<RetentionPolicy[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [openDialog, setOpenDialog] = useState(false);
    const [editingPolicy, setEditingPolicy] = useState<RetentionPolicy | null>(null);
    const [formData, setFormData] = useState<Partial<RetentionPolicy>>({});

    useEffect(() => {
        loadPolicies();
    }, []);

    const loadPolicies = async () => {
        try {
            const data = await dataManagementService.getRetentionPolicies();
            setPolicies(data);
            setError(null);
        } catch (err) {
            setError('Failed to load retention policies');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (policy: RetentionPolicy) => {
        setEditingPolicy(policy);
        setFormData(policy);
        setOpenDialog(true);
    };

    const handleAdd = () => {
        setEditingPolicy(null);
        setFormData({
            retention_days: 30
        });
        setOpenDialog(true);
    };

    const handleSubmit = async () => {
        try {
            await dataManagementService.updateRetentionPolicy(
                formData.table_name!,
                formData.retention_days!
            );
            await loadPolicies();
            setOpenDialog(false);
        } catch (err) {
            setError('Failed to save retention policy');
            console.error(err);
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
                <Typography variant="h6">Retention Policies</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={handleAdd}
                >
                    Add Policy
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Table Name</TableCell>
                            <TableCell>Retention Days</TableCell>
                            <TableCell>Last Cleanup</TableCell>
                            <TableCell>Rows Deleted</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {policies.map((policy) => (
                            <TableRow key={policy.table_name}>
                                <TableCell>{policy.table_name}</TableCell>
                                <TableCell>{policy.retention_days} days</TableCell>
                                <TableCell>
                                    {new Date(policy.last_cleanup).toLocaleString()}
                                </TableCell>
                                <TableCell>{policy.rows_deleted}</TableCell>
                                <TableCell>
                                    <IconButton
                                        size="small"
                                        onClick={() => handleEdit(policy)}
                                    >
                                        <EditIcon />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {editingPolicy ? 'Edit Policy' : 'Add Policy'}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} pt={1}>
                        <TextField
                            label="Table Name"
                            value={formData.table_name || ''}
                            onChange={(e) => setFormData({ ...formData, table_name: e.target.value })}
                            disabled={!!editingPolicy}
                        />
                        <TextField
                            label="Retention Days"
                            type="number"
                            value={formData.retention_days || ''}
                            onChange={(e) => setFormData({
                                ...formData,
                                retention_days: parseInt(e.target.value)
                            })}
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