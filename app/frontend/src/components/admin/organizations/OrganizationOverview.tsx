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
    Chip,
    IconButton,
    Button,
    Alert,
    CircularProgress,
    Tooltip,
    LinearProgress
} from '@mui/material';
import {
    Edit as EditIcon,
    Delete as DeleteIcon,
    Block as BlockIcon,
    CheckCircle as ActivateIcon,
    Visibility as ViewIcon
} from '@mui/icons-material';
import { Organization } from '../../../types/admin';
import { adminService } from '../../../services/adminService';

export const OrganizationOverview: React.FC = () => {
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadOrganizations();
    }, []);

    const loadOrganizations = async () => {
        try {
            setLoading(true);
            const data = await adminService.getOrganizations();
            setOrganizations(data);
            setError(null);
        } catch (err) {
            setError('Failed to load organizations');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleStatusChange = async (orgId: string, newStatus: 'active' | 'suspended') => {
        try {
            await adminService.updateOrganization(orgId, { status: newStatus });
            await loadOrganizations();
        } catch (err) {
            setError('Failed to update organization status');
            console.error(err);
        }
    };

    const handleDelete = async (orgId: string) => {
        if (window.confirm('Are you sure you want to delete this organization?')) {
            try {
                await adminService.deleteOrganization(orgId);
                await loadOrganizations();
            } catch (err) {
                setError('Failed to delete organization');
                console.error(err);
            }
        }
    };

    const getUsagePercentage = (org: Organization) => {
        const used = org.settings.max_events_per_day;
        const limit = org.settings.max_events_per_day;
        return Math.round((used / limit) * 100);
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
                <Typography variant="h6">Organizations</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    onClick={() => {/* Add organization creation handler */}}
                >
                    Add Organization
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Organization</TableCell>
                            <TableCell>Tier</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Users</TableCell>
                            <TableCell>API Usage</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {organizations.map((org) => (
                            <TableRow key={org.id}>
                                <TableCell>
                                    <Typography variant="body1">{org.name}</Typography>
                                    <Typography variant="caption" color="textSecondary">
                                        Created: {new Date(org.created_at).toLocaleDateString()}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Chip 
                                        label={org.tier}
                                        color={
                                            org.tier === 'enterprise' ? 'primary' :
                                            org.tier === 'pro' ? 'secondary' :
                                            'default'
                                        }
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    <Chip 
                                        label={org.status}
                                        color={org.status === 'active' ? 'success' : 'error'}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    {org.settings.max_users} users
                                </TableCell>
                                <TableCell>
                                    <Box display="flex" alignItems="center" gap={1}>
                                        <Typography variant="body2">
                                            {getUsagePercentage(org)}%
                                        </Typography>
                                        <LinearProgress
                                            variant="determinate"
                                            value={getUsagePercentage(org)}
                                            sx={{ width: 100 }}
                                        />
                                    </Box>
                                </TableCell>
                                <TableCell align="right">
                                    <Tooltip title="View Details">
                                        <IconButton size="small">
                                            <ViewIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Edit">
                                        <IconButton size="small">
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    {org.status === 'active' ? (
                                        <Tooltip title="Suspend">
                                            <IconButton
                                                size="small"
                                                onClick={() => handleStatusChange(org.id, 'suspended')}
                                            >
                                                <BlockIcon />
                                            </IconButton>
                                        </Tooltip>
                                    ) : (
                                        <Tooltip title="Activate">
                                            <IconButton
                                                size="small"
                                                onClick={() => handleStatusChange(org.id, 'active')}
                                            >
                                                <ActivateIcon />
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                    <Tooltip title="Delete">
                                        <IconButton
                                            size="small"
                                            color="error"
                                            onClick={() => handleDelete(org.id)}
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
        </Box>
    );
}; 