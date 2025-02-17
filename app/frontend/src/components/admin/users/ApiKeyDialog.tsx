import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction,
    IconButton,
    Typography,
    Box,
    Alert,
    CircularProgress,
    Tooltip,
    Chip
} from '@mui/material';
import {
    Delete as DeleteIcon,
    ContentCopy as CopyIcon,
    Add as AddIcon
} from '@mui/icons-material';
import { ApiKey } from '../../../types/admin';
import { adminService } from '../../../services/adminService';

interface ApiKeyDialogProps {
    open: boolean;
    onClose: () => void;
    userId: string;
}

export const ApiKeyDialog: React.FC<ApiKeyDialogProps> = ({ open, onClose, userId }) => {
    const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [newKey, setNewKey] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            loadApiKeys();
        }
    }, [open, userId]);

    const loadApiKeys = async () => {
        try {
            setLoading(true);
            const data = await adminService.getApiKeys(userId);
            setApiKeys(data);
            setError(null);
        } catch (err) {
            setError('Failed to load API keys');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateKey = async () => {
        try {
            const key = await adminService.createApiKey(userId);
            if (key.token) {
                setNewKey(key.token);
                await loadApiKeys();
            } else {
                setError('API key was created but no token was returned');
            }
        } catch (err) {
            setError('Failed to create API key');
        }
    };

    const handleRevokeKey = async (keyId: string) => {
        if (window.confirm('Are you sure you want to revoke this API key?')) {
            try {
                await adminService.revokeApiKey(userId, keyId);
                await loadApiKeys();
            } catch (err) {
                setError('Failed to revoke API key');
                console.error(err);
            }
        }
    };

    const handleCopyKey = (key: string) => {
        navigator.clipboard.writeText(key);
    };

    const handleClose = () => {
        setNewKey(null);
        onClose();
    };

    return (
        <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
            <DialogTitle>API Keys</DialogTitle>
            <DialogContent>
                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                )}

                {newKey && (
                    <Alert severity="success" sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                            New API Key Created
                        </Typography>
                        <Box display="flex" alignItems="center" gap={1}>
                            <Typography
                                variant="body2"
                                sx={{
                                    fontFamily: 'monospace',
                                    backgroundColor: 'action.hover',
                                    p: 1,
                                    borderRadius: 1,
                                    flex: 1
                                }}
                            >
                                {newKey}
                            </Typography>
                            <Tooltip title="Copy">
                                <IconButton
                                    size="small"
                                    onClick={() => handleCopyKey(newKey)}
                                >
                                    <CopyIcon />
                                </IconButton>
                            </Tooltip>
                        </Box>
                        <Typography variant="caption" color="warning.main" sx={{ mt: 1, display: 'block' }}>
                            Make sure to copy this key now. You won't be able to see it again!
                        </Typography>
                    </Alert>
                )}

                {loading ? (
                    <Box display="flex" justifyContent="center" p={3}>
                        <CircularProgress />
                    </Box>
                ) : (
                    <>
                        <List>
                            {apiKeys.map((key) => (
                                <ListItem key={key.id}>
                                    <ListItemText
                                        primary={
                                            <Box display="flex" alignItems="center" gap={1}>
                                                <Typography variant="body2">
                                                    {key.name || 'Unnamed Key'}
                                                </Typography>
                                                <Chip
                                                    label={key.status}
                                                    size="small"
                                                    color={key.status === 'active' ? 'success' : 'error'}
                                                />
                                            </Box>
                                        }
                                        secondary={
                                            <>
                                                Created: {new Date(key.created_at).toLocaleString()}
                                                {key.last_used && (
                                                    <><br />Last used: {new Date(key.last_used).toLocaleString()}</>
                                                )}
                                            </>
                                        }
                                    />
                                    <ListItemSecondaryAction>
                                        <Tooltip title="Revoke">
                                            <IconButton
                                                edge="end"
                                                size="small"
                                                onClick={() => handleRevokeKey(key.id)}
                                                color="error"
                                            >
                                                <DeleteIcon />
                                            </IconButton>
                                        </Tooltip>
                                    </ListItemSecondaryAction>
                                </ListItem>
                            ))}
                        </List>

                        <Box display="flex" justifyContent="center" mt={2}>
                            <Button
                                variant="outlined"
                                startIcon={<AddIcon />}
                                onClick={handleCreateKey}
                            >
                                Generate New API Key
                            </Button>
                        </Box>
                    </>
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={handleClose}>Close</Button>
            </DialogActions>
        </Dialog>
    );
}; 