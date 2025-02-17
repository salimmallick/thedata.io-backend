import React from 'react';
import { render as rtlRender } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { BrowserRouter } from 'react-router-dom';
import { theme } from '../theme';

// Mock auth context
export const mockAuthContext = {
    isAuthenticated: true,
    isLoading: false,
    user: {
        id: 'test-user-id',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'admin',
        permissions: ['manage_users', 'manage_organizations', 'manage_pipeline', 'manage_data']
    },
    login: jest.fn(),
    logout: jest.fn(),
};

// Custom render function
function render(ui: React.ReactElement, { route = '/' } = {}) {
    window.history.pushState({}, 'Test page', route);

    return rtlRender(
        <ThemeProvider theme={theme}>
            <BrowserRouter>
                {ui}
            </BrowserRouter>
        </ThemeProvider>
    );
}

// Re-export everything
export * from '@testing-library/react';
export { render }; 