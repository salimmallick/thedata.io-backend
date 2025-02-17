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
    Button,
    CircularProgress,
    Alert
} from '@mui/material';
import { adminService } from '../../../services/adminService';
import { Organization } from '../../../types/admin';

export const BillingDashboard: React.FC = () => {
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadOrganizations();
    }, []);

    const loadOrganizations = async () => {
        try {
            setLoading(true);
            const orgs = await adminService.getOrganizations();
            setOrganizations(orgs);
        } catch (err) {
            setError('Failed to load organizations');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getBillingStatusChip = (status: string) => {
        const colors: Record<string, "success" | "warning" | "error"> = {
            active: "success",
            pending: "warning",
            failed: "error"
        };

        return (
            <Chip
                label={status}
                color={colors[status] || "default"}
                size="small"
            />
        );
    };

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    };

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box p={3}>
            <Typography variant="h4" gutterBottom>
                Billing Dashboard
            </Typography>

            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Organization</TableCell>
                            <TableCell>Plan</TableCell>
                            <TableCell>Billing Status</TableCell>
                            <TableCell>Next Billing</TableCell>
                            <TableCell>Monthly Revenue</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {organizations.map((org) => (
                            <TableRow key={org.id}>
                                <TableCell>{org.name}</TableCell>
                                <TableCell>
                                    <Chip
                                        label={org.tier.toUpperCase()}
                                        color="primary"
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    {getBillingStatusChip(org.billing.status)}
                                </TableCell>
                                <TableCell>
                                    {new Date(org.billing.next_billing_date).toLocaleDateString()}
                                </TableCell>
                                <TableCell>
                                    {formatCurrency(
                                        org.tier === 'basic' ? 99 :
                                        org.tier === 'pro' ? 299 :
                                        org.tier === 'enterprise' ? 999 : 0
                                    )}
                                </TableCell>
                                <TableCell>
                                    <Button
                                        size="small"
                                        onClick={() => {/* TODO: Implement billing details view */}}
                                    >
                                        View Details
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Box mt={4}>
                <Paper sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        Monthly Revenue Overview
                    </Typography>
                    <Box display="flex" gap={4}>
                        <Box>
                            <Typography variant="subtitle2" color="text.secondary">
                                Total Monthly Revenue
                            </Typography>
                            <Typography variant="h4">
                                {formatCurrency(
                                    organizations.reduce((total, org) => {
                                        const prices = {
                                            basic: 99,
                                            pro: 299,
                                            enterprise: 999
                                        };
                                        return total + (prices[org.tier as keyof typeof prices] || 0);
                                    }, 0)
                                )}
                            </Typography>
                        </Box>
                        <Box>
                            <Typography variant="subtitle2" color="text.secondary">
                                Active Subscriptions
                            </Typography>
                            <Typography variant="h4">
                                {organizations.filter(org => org.billing.status === 'active').length}
                            </Typography>
                        </Box>
                    </Box>
                </Paper>
            </Box>
        </Box>
    );
}; 