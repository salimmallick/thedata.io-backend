import React from 'react';
import { render, screen, waitFor } from '../../../utils/test-utils';
import { ProtectedRoute } from '../ProtectedRoute';
import { useAuth } from '../../../hooks/useAuth';

// Mock the useAuth hook
jest.mock('../../../hooks/useAuth');

describe('ProtectedRoute', () => {
    const mockNavigate = jest.fn();

    beforeEach(() => {
        jest.clearAllMocks();
        // Mock useNavigate
        jest.mock('react-router-dom', () => ({
            ...jest.requireActual('react-router-dom'),
            useNavigate: () => mockNavigate,
            useLocation: () => ({ pathname: '/test' })
        }));
    });

    it('shows loading state when authentication is being checked', () => {
        (useAuth as jest.Mock).mockReturnValue({
            isAuthenticated: false,
            isLoading: true,
            user: null
        });

        render(
            <ProtectedRoute>
                <div>Protected Content</div>
            </ProtectedRoute>
        );

        expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('redirects to login when user is not authenticated', async () => {
        (useAuth as jest.Mock).mockReturnValue({
            isAuthenticated: false,
            isLoading: false,
            user: null
        });

        render(
            <ProtectedRoute>
                <div>Protected Content</div>
            </ProtectedRoute>
        );

        await waitFor(() => {
            expect(window.location.pathname).toBe('/login');
        });
    });

    it('renders children when user is authenticated', () => {
        (useAuth as jest.Mock).mockReturnValue({
            isAuthenticated: true,
            isLoading: false,
            user: {
                id: 'test-user',
                email: 'test@example.com',
                permissions: []
            }
        });

        render(
            <ProtectedRoute>
                <div>Protected Content</div>
            </ProtectedRoute>
        );

        expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    it('checks required permissions correctly', () => {
        (useAuth as jest.Mock).mockReturnValue({
            isAuthenticated: true,
            isLoading: false,
            user: {
                id: 'test-user',
                email: 'test@example.com',
                permissions: ['manage_users']
            }
        });

        render(
            <ProtectedRoute requiredPermissions={['manage_users']}>
                <div>Protected Content</div>
            </ProtectedRoute>
        );

        expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    it('redirects when user lacks required permissions', async () => {
        (useAuth as jest.Mock).mockReturnValue({
            isAuthenticated: true,
            isLoading: false,
            user: {
                id: 'test-user',
                email: 'test@example.com',
                permissions: ['view_dashboard']
            }
        });

        render(
            <ProtectedRoute requiredPermissions={['manage_users']}>
                <div>Protected Content</div>
            </ProtectedRoute>
        );

        await waitFor(() => {
            expect(window.location.pathname).toBe('/unauthorized');
        });
    });
}); 