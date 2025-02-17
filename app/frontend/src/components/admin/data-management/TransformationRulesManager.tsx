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
    FormControlLabel,
    Switch,
    Tooltip
} from '@mui/material';
import {
    Edit as EditIcon,
    Delete as DeleteIcon,
    Add as AddIcon,
    PlayArrow as RunIcon
} from '@mui/icons-material';
import { TransformationRule } from '../../../types/data-management';
import { dataManagementService } from '../../../services/dataManagementService';
import { JsonEditor } from '../../common/JsonEditor';

export const TransformationRulesManager: React.FC = () => {
    const [rules, setRules] = useState<TransformationRule[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [openDialog, setOpenDialog] = useState(false);
    const [editingRule, setEditingRule] = useState<TransformationRule | null>(null);
    const [formData, setFormData] = useState<Partial<TransformationRule>>({});

    useEffect(() => {
        loadRules();
    }, []);

    const loadRules = async () => {
        try {
            const data = await dataManagementService.getTransformationRules();
            setRules(data);
            setError(null);
        } catch (err) {
            setError('Failed to load transformation rules');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (rule: TransformationRule) => {
        setEditingRule(rule);
        setFormData(rule);
        setOpenDialog(true);
    };

    const handleAdd = () => {
        setEditingRule(null);
        setFormData({
            enabled: true,
            order: rules.length + 1,
            type: 'normalize',
            input_table: '',
            output_table: '',
            transformation_sql: '',
            config: {}
        });
        setOpenDialog(true);
    };

    const handleDelete = async (name: string) => {
        if (window.confirm('Are you sure you want to delete this rule?')) {
            try {
                await dataManagementService.deleteTransformationRule(name);
                await loadRules();
            } catch (err) {
                setError('Failed to delete transformation rule');
                console.error(err);
            }
        }
    };

    const handleSubmit = async () => {
        try {
            if (editingRule) {
                await dataManagementService.updateTransformationRule(
                    editingRule.name,
                    formData
                );
            } else {
                await dataManagementService.createTransformationRule(
                    formData as TransformationRule
                );
            }
            await loadRules();
            setOpenDialog(false);
        } catch (err) {
            setError('Failed to save transformation rule');
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
                <Typography variant="h6">Transformation Rules</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={handleAdd}
                >
                    Add Rule
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell>Input Table</TableCell>
                            <TableCell>Output Table</TableCell>
                            <TableCell>Order</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Last Updated</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rules.map((rule) => (
                            <TableRow key={rule.name}>
                                <TableCell>{rule.name}</TableCell>
                                <TableCell>{rule.type}</TableCell>
                                <TableCell>{rule.input_table}</TableCell>
                                <TableCell>{rule.output_table}</TableCell>
                                <TableCell>{rule.order}</TableCell>
                                <TableCell>
                                    {rule.enabled ? 'Enabled' : 'Disabled'}
                                </TableCell>
                                <TableCell>
                                    {rule.updated_at ? new Date(rule.updated_at).toLocaleString() : '-'}
                                </TableCell>
                                <TableCell>
                                    <Tooltip title="Edit">
                                        <IconButton
                                            size="small"
                                            onClick={() => handleEdit(rule)}
                                        >
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Delete">
                                        <IconButton
                                            size="small"
                                            onClick={() => handleDelete(rule.name)}
                                        >
                                            <DeleteIcon />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    {editingRule ? 'Edit Rule' : 'Add Rule'}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} pt={1}>
                        <TextField
                            label="Name"
                            value={formData.name || ''}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            disabled={!!editingRule}
                        />
                        <TextField
                            label="Description"
                            value={formData.description || ''}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            multiline
                            rows={2}
                        />
                        <TextField
                            label="Type"
                            value={formData.type || ''}
                            onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                            select
                            SelectProps={{ native: true }}
                        >
                            <option value="normalize">Normalize</option>
                            <option value="enrich">Enrich</option>
                            <option value="validate">Validate</option>
                            <option value="filter">Filter</option>
                            <option value="aggregate">Aggregate</option>
                        </TextField>
                        <TextField
                            label="Input Table"
                            value={formData.input_table || ''}
                            onChange={(e) => setFormData({ ...formData, input_table: e.target.value })}
                        />
                        <TextField
                            label="Output Table"
                            value={formData.output_table || ''}
                            onChange={(e) => setFormData({ ...formData, output_table: e.target.value })}
                        />
                        <TextField
                            label="Transformation SQL"
                            value={formData.transformation_sql || ''}
                            onChange={(e) => setFormData({ ...formData, transformation_sql: e.target.value })}
                            multiline
                            rows={4}
                        />
                        <TextField
                            label="Order"
                            type="number"
                            value={formData.order || ''}
                            onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) })}
                        />
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={formData.enabled || false}
                                    onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                                />
                            }
                            label="Enabled"
                        />
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