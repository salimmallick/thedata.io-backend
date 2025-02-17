import React, { useState, useEffect } from 'react';
import {
    Box,
    Paper,
    Typography,
    Button,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    IconButton,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Chip,
    CircularProgress,
    Alert,
    Tooltip
} from '@mui/material';
import {
    Add as AddIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    Key as KeyIcon
} from '@mui/icons-material';
import { User } from '../../../types/admin';
import { adminService } from '../../../services/adminService';
import { ApiKeyDialog } from './ApiKeyDialog';

export const UserManager: React.FC = () => {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [apiKeyDialogOpen, setApiKeyDialogOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [formData, setFormData] = useState<Partial<User>>({
        email: '',
        full_name: '',
        role: 'user' as const,
        organization_id: '',
        status: 'active' as const
    });

    const initialFormData = {
        email: '',
        full_name: '',
        role: 'user' as const,
        organization_id: '',
        status: 'active' as const
    };

    useEffect(() => {
        loadUsers();
    }, []);

    const loadUsers = async () => {
        try {
            setLoading(true);
            const data = await adminService.getUsers();
            setUsers(data);
            setError(null);
        } catch (err) {
            setError('Failed to load users');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setSelectedUser(null);
        setFormData(initialFormData);
        setDialogOpen(true);
    };

    const handleEdit = (user: User) => {
        setSelectedUser(user);
        setFormData({
            email: user.email,
            full_name: user.full_name,
            role: user.role,
            organization_id: user.organization_id,
            status: user.status
        });
        setDialogOpen(true);
    };

    const handleDelete = async (userId: string) => {
        if (window.confirm('Are you sure you want to delete this user?')) {
            try {
                await adminService.deleteUser(userId);
                await loadUsers();
            } catch (err) {
                setError('Failed to delete user');
                console.error(err);
            }
        }
    };

    const handleSubmit = async () => {
        try {
            if (selectedUser) {
                await adminService.updateUser(selectedUser.id, formData);
            } else {
                await adminService.createUser(formData);
            }
            setDialogOpen(false);
            await loadUsers();
        } catch (err) {
            setError('Failed to save user');
            console.error(err);
        }
    };

    const handleApiKeys = (user: User) => {
        setSelectedUser(user);
        setApiKeyDialogOpen(true);
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
                <Typography variant="h6">User Management</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={handleAdd}
                >
                    Add User
                </Button>
            </Box>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Email</TableCell>
                            <TableCell>Role</TableCell>
                            <TableCell>Organization</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Last Login</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {users.map((user) => (
                            <TableRow key={user.id}>
                                <TableCell>{user.full_name}</TableCell>
                                <TableCell>{user.email}</TableCell>
                                <TableCell>
                                    <Chip 
                                        label={user.role} 
                                        color={user.role === 'admin' ? 'primary' : 'default'}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>{user.organization_id}</TableCell>
                                <TableCell>
                                    <Chip 
                                        label={user.status}
                                        color={user.status === 'active' ? 'success' : 'error'}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    {user.last_login 
                                        ? new Date(user.last_login).toLocaleString()
                                        : 'Never'
                                    }
                                </TableCell>
                                <TableCell align="right">
                                    <Tooltip title="API Keys">
                                        <IconButton
                                            size="small"
                                            onClick={() => handleApiKeys(user)}
                                        >
                                            <KeyIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Edit">
                                        <IconButton
                                            size="small"
                                            onClick={() => handleEdit(user)}
                                        >
                                            <EditIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Delete">
                                        <IconButton
                                            size="small"
                                            onClick={() => handleDelete(user.id)}
                                            color="error"
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

            <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {selectedUser ? 'Edit User' : 'Add User'}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} pt={1}>
                        <TextField
                            label="Email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            fullWidth
                        />
                        <TextField
                            label="Full Name"
                            value={formData.full_name}
                            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                            fullWidth
                        />
                        <FormControl fullWidth>
                            <InputLabel>Role</InputLabel>
                            <Select
                                value={formData.role}
                                onChange={(e) => setFormData({ ...formData, role: e.target.value as 'user' | 'admin' })}
                                label="Role"
                            >
                                <MenuItem value="user">User</MenuItem>
                                <MenuItem value="admin">Admin</MenuItem>
                            </Select>
                        </FormControl>
                        <TextField
                            label="Organization ID"
                            value={formData.organization_id}
                            onChange={(e) => setFormData({ ...formData, organization_id: e.target.value })}
                            fullWidth
                        />
                        <FormControl fullWidth>
                            <InputLabel>Status</InputLabel>
                            <Select
                                value={formData.status}
                                onChange={(e) => setFormData({ ...formData, status: e.target.value as 'active' | 'inactive' | 'suspended' })}
                                label="Status"
                            >
                                <MenuItem value="active">Active</MenuItem>
                                <MenuItem value="inactive">Inactive</MenuItem>
                                <MenuItem value="suspended">Suspended</MenuItem>
                            </Select>
                        </FormControl>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleSubmit} variant="contained" color="primary">
                        {selectedUser ? 'Save' : 'Add'}
                    </Button>
                </DialogActions>
            </Dialog>

            {selectedUser && (
                <ApiKeyDialog
                    open={apiKeyDialogOpen}
                    onClose={() => setApiKeyDialogOpen(false)}
                    userId={selectedUser.id}
                />
            )}
        </Box>
    );
}; 