import React, { useState } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Box,
    Alert
} from '@mui/material';
import { Organization } from '../../../types/admin';
import { adminService } from '../../../services/adminService';

interface CreateOrganizationDialogProps {
    open: boolean;
    onClose: () => void;
    onCreated: (org: Organization) => void;
}

interface CreateOrganizationData {
    name: string;
    tier: Organization['tier'];
    settings: {
        max_users: number;
        max_events_per_day: number;
        max_retention_days: number;
        features: string[];
    };
}

export const CreateOrganizationDialog: React.FC<CreateOrganizationDialogProps> = ({
    open,
    onClose,
    onCreated
}) => {
    const [formData, setFormData] = useState<CreateOrganizationData>({
        name: '',
        tier: 'basic',
        settings: {
            max_users: 5,
            max_events_per_day: 10000,
            max_retention_days: 30,
            features: []
        }
    });
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        try {
            setLoading(true);
            setError(null);
            const newOrg = await adminService.createOrganization(formData);
            onCreated(newOrg);
            onClose();
        } catch (err) {
            setError('Failed to create organization');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>Create New Organization</DialogTitle>
            <DialogContent>
                <Box display="flex" flexDirection="column" gap={2} pt={1}>
                    {error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            {error}
                        </Alert>
                    )}

                    <TextField
                        label="Organization Name"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        fullWidth
                        required
                    />

                    <FormControl fullWidth required>
                        <InputLabel>Tier</InputLabel>
                        <Select
                            value={formData.tier}
                            onChange={(e) => setFormData({
                                ...formData,
                                tier: e.target.value as Organization['tier']
                            })}
                            label="Tier"
                        >
                            <MenuItem value="free">Free</MenuItem>
                            <MenuItem value="basic">Basic</MenuItem>
                            <MenuItem value="pro">Pro</MenuItem>
                            <MenuItem value="enterprise">Enterprise</MenuItem>
                        </Select>
                    </FormControl>

                    <TextField
                        label="Max Users"
                        type="number"
                        value={formData.settings.max_users}
                        onChange={(e) => setFormData({
                            ...formData,
                            settings: {
                                ...formData.settings,
                                max_users: parseInt(e.target.value)
                            }
                        })}
                        fullWidth
                        required
                    />

                    <TextField
                        label="Max Events per Day"
                        type="number"
                        value={formData.settings.max_events_per_day}
                        onChange={(e) => setFormData({
                            ...formData,
                            settings: {
                                ...formData.settings,
                                max_events_per_day: parseInt(e.target.value)
                            }
                        })}
                        fullWidth
                        required
                    />

                    <TextField
                        label="Data Retention (days)"
                        type="number"
                        value={formData.settings.max_retention_days}
                        onChange={(e) => setFormData({
                            ...formData,
                            settings: {
                                ...formData.settings,
                                max_retention_days: parseInt(e.target.value)
                            }
                        })}
                        fullWidth
                        required
                    />
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button
                    onClick={handleSubmit}
                    variant="contained"
                    color="primary"
                    disabled={loading || !formData.name}
                >
                    Create
                </Button>
            </DialogActions>
        </Dialog>
    );
}; 