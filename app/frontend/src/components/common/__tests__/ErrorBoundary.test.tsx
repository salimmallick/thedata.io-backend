import React from 'react';
import { render, screen, fireEvent } from '../../../utils/test-utils';
import { ErrorBoundary } from '../ErrorBoundary';

// Component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
    if (shouldThrow) {
        throw new Error('Test error');
    }
    return <div>Normal Component</div>;
};

describe('ErrorBoundary', () => {
    beforeEach(() => {
        // Prevent console.error from cluttering test output
        jest.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it('renders children when there is no error', () => {
        render(
            <ErrorBoundary>
                <div>Test Content</div>
            </ErrorBoundary>
        );

        expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('renders error UI when an error occurs', () => {
        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );

        expect(screen.getByText('Something went wrong')).toBeInTheDocument();
        expect(screen.getByText(/we apologize for the inconvenience/i)).toBeInTheDocument();
    });

    it('provides retry functionality', () => {
        const { rerender } = render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );

        // Click "Try Again" button
        fireEvent.click(screen.getByText('Try Again'));

        // Rerender with non-throwing component
        rerender(
            <ErrorBoundary>
                <ThrowError shouldThrow={false} />
            </ErrorBoundary>
        );

        expect(screen.getByText('Normal Component')).toBeInTheDocument();
    });

    it('shows error details in development environment', () => {
        const originalEnv = process.env.NODE_ENV;
        process.env.NODE_ENV = 'development';

        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );

        expect(screen.getByText('Test error')).toBeInTheDocument();

        process.env.NODE_ENV = originalEnv;
    });

    it('hides error details in production environment', () => {
        const originalEnv = process.env.NODE_ENV;
        process.env.NODE_ENV = 'production';

        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );

        expect(screen.queryByText('Test error')).not.toBeInTheDocument();

        process.env.NODE_ENV = originalEnv;
    });

    it('provides refresh page functionality', () => {
        const refreshSpy = jest.spyOn(window.location, 'reload');
        
        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );

        fireEvent.click(screen.getByText('Refresh Page'));
        expect(refreshSpy).toHaveBeenCalled();
    });
}); 