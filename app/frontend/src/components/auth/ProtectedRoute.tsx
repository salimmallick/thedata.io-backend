import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';
import { useAuth } from '../../hooks/useAuth';

interface ProtectedRouteProps {
    children: React.ReactNode;
    requiredPermissions?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
    children,
    requiredPermissions = []
}) => {
    const { isAuthenticated, isLoading, user } = useAuth();
    const location = useLocation();

    if (isLoading) {
        return (
            <Box
                display="flex"
                justifyContent="center"
                alignItems="center"
                minHeight="100vh"
            >
                <CircularProgress />
            </Box>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Check permissions if required
    if (requiredPermissions.length > 0 && user) {
        const hasRequiredPermissions = requiredPermissions.every(
            permission => user.permissions.includes(permission)
        );

        if (!hasRequiredPermissions) {
            return <Navigate to="/unauthorized" replace />;
        }
    }

    return <>{children}</>;
}; 