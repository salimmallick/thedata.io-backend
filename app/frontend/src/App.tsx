import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { theme } from './theme';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { LoadingScreen } from './components/common/LoadingScreen';

// Lazy load components
const AdminLayout = React.lazy(() => 
    import('./components/layouts/AdminLayout').then(module => ({ 
        default: module.AdminLayout 
    }))
);
const Login = React.lazy(() => 
    import('./components/auth/Login').then(module => ({ 
        default: module.Login 
    }))
);
const SignupForm = React.lazy(() => 
    import('./components/auth/SignupForm').then(module => ({ 
        default: module.SignupForm 
    }))
);
const SignupSuccess = React.lazy(() => 
    import('./components/auth/SignupSuccess').then(module => ({ 
        default: module.SignupSuccess 
    }))
);
const UserManager = React.lazy(() => 
    import('./components/admin/users/UserManager').then(module => ({ 
        default: module.UserManager 
    }))
);
const OrganizationOverview = React.lazy(() => 
    import('./components/admin/organizations/OrganizationOverview').then(module => ({ 
        default: module.OrganizationOverview 
    }))
);
const BillingDashboard = React.lazy(() => 
    import('./components/admin/billing/BillingDashboard').then(module => ({ 
        default: module.BillingDashboard 
    }))
);
const DataPipelineDashboard = React.lazy(() => 
    import('./components/admin/pipeline/DataPipelineDashboard').then(module => ({ 
        default: module.DataPipelineDashboard 
    }))
);
const DataManagement = React.lazy(() => 
    import('./components/admin/data-management/DataManagement').then(module => ({ 
        default: module.DataManagement 
    }))
);
const SystemOverview = React.lazy(() => 
    import('./components/admin/system/SystemOverview').then(module => ({ 
        default: module.SystemOverview 
    }))
);

export const App: React.FC = () => {
    return (
        <ErrorBoundary>
            <ThemeProvider theme={theme}>
                <CssBaseline />
                <Router>
                    <Suspense fallback={<LoadingScreen />}>
                        <Routes>
                            {/* Public routes */}
                            <Route path="/login" element={<Login />} />
                            <Route path="/signup" element={<SignupForm />} />
                            <Route path="/signup/success" element={<SignupSuccess />} />
                            
                            {/* Protected routes */}
                            <Route
                                path="/"
                                element={
                                    <ProtectedRoute>
                                        <AdminLayout />
                                    </ProtectedRoute>
                                }
                            >
                                <Route index element={<Navigate to="/system" replace />} />
                                <Route path="system" element={<SystemOverview />} />
                                <Route 
                                    path="users" 
                                    element={
                                        <ProtectedRoute requiredPermissions={['manage_users']}>
                                            <UserManager />
                                        </ProtectedRoute>
                                    } 
                                />
                                <Route 
                                    path="organizations" 
                                    element={
                                        <ProtectedRoute requiredPermissions={['manage_organizations']}>
                                            <OrganizationOverview />
                                        </ProtectedRoute>
                                    } 
                                />
                                <Route 
                                    path="billing" 
                                    element={
                                        <ProtectedRoute requiredPermissions={['manage_billing']}>
                                            <BillingDashboard />
                                        </ProtectedRoute>
                                    } 
                                />
                                <Route 
                                    path="pipeline" 
                                    element={
                                        <ProtectedRoute requiredPermissions={['manage_pipeline']}>
                                            <DataPipelineDashboard />
                                        </ProtectedRoute>
                                    } 
                                />
                                <Route 
                                    path="data-management" 
                                    element={
                                        <ProtectedRoute requiredPermissions={['manage_data']}>
                                            <DataManagement />
                                        </ProtectedRoute>
                                    } 
                                />
                            </Route>

                            {/* Catch all route */}
                            <Route path="*" element={<Navigate to="/" replace />} />
                        </Routes>
                    </Suspense>
                </Router>
            </ThemeProvider>
        </ErrorBoundary>
    );
}; 