import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    Box,
    Typography,
    Alert,
    CircularProgress
} from '@mui/material';
import { adminService } from '../../../services/adminService';
import { PipelineComponent } from '../../../types/data-management';

interface ComponentSettingsDialogProps {
    open: boolean;
    onClose: () => void;
    component: PipelineComponent | null;
}

export const ComponentSettingsDialog: React.FC<ComponentSettingsDialogProps> = ({
    open,
    onClose,
    component
}) => {
    const [config, setConfig] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (component) {
            setConfig(JSON.stringify(component.config || {}, null, 2));
        }
    }, [component]);

    const handleSave = async () => {
        if (!component) return;

        try {
            setLoading(true);
            setError(null);
            const configObj = JSON.parse(config);
            await adminService.updatePipelineConfig(component.name, configObj);
            onClose();
        } catch (err) {
            if (err instanceof SyntaxError) {
                setError('Invalid JSON format');
            } else {
                setError('Failed to update component configuration');
                console.error(err);
            }
        } finally {
            setLoading(false);
        }
    };

    if (!component) return null;

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <DialogTitle>
                Component Settings: {component.name}
            </DialogTitle>
            <DialogContent>
                <Box sx={{ mt: 2 }}>
                    {error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            {error}
                        </Alert>
                    )}
                    <Typography variant="subtitle2" gutterBottom>
                        Configuration (JSON)
                    </Typography>
                    <TextField
                        multiline
                        rows={15}
                        fullWidth
                        value={config}
                        onChange={(e) => setConfig(e.target.value)}
                        error={!!error}
                        sx={{
                            fontFamily: 'monospace',
                            '& .MuiInputBase-input': {
                                fontFamily: 'monospace'
                            }
                        }}
                    />
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>
                    Cancel
                </Button>
                <Button
                    onClick={handleSave}
                    variant="contained"
                    disabled={loading}
                >
                    {loading ? <CircularProgress size={24} /> : 'Save Changes'}
                </Button>
            </DialogActions>
        </Dialog>
    );
}; 