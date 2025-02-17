import React from 'react';
import { render, screen, fireEvent, waitFor } from '../../../../utils/test-utils';
import { SystemOverview } from '../SystemOverview';
import { adminService } from '../../../../services/adminService';

// Mock the admin service
jest.mock('../../../../services/adminService');

const mockSystemData = {
    metrics: {
        cpu_usage: 45.5,
        memory_usage: 60.2,
        disk_usage: 72.8,
        network_in: 1024,
        network_out: 2048,
        historical_data: []
    },
    components: [
        {
            name: 'API Server',
            status: 'healthy',
            message: 'Running normally'
        },
        {
            name: 'Database',
            status: 'degraded',
            message: 'High latency detected'
        }
    ],
    alerts: [
        {
            id: 'alert-1',
            severity: 'warning',
            message: 'High CPU usage',
            timestamp: '2024-02-12T10:00:00Z',
            acknowledged: false
        }
    ]
};

describe('SystemOverview', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (adminService.getSystemOverview as jest.Mock).mockResolvedValue(mockSystemData);
    });

    it('renders loading state initially', () => {
        render(<SystemOverview />);
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('renders system metrics after loading', async () => {
        render(<SystemOverview />);

        await waitFor(() => {
            expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
        });

        expect(screen.getByText('45.5%')).toBeInTheDocument(); // CPU usage
        expect(screen.getByText('60.2%')).toBeInTheDocument(); // Memory usage
    });

    it('renders component status list', async () => {
        render(<SystemOverview />);

        await waitFor(() => {
            expect(screen.getByText('API Server')).toBeInTheDocument();
            expect(screen.getByText('Database')).toBeInTheDocument();
        });

        expect(screen.getByText('Running normally')).toBeInTheDocument();
        expect(screen.getByText('High latency detected')).toBeInTheDocument();
    });

    it('handles error state', async () => {
        (adminService.getSystemOverview as jest.Mock).mockRejectedValue(new Error('Failed to load'));
        render(<SystemOverview />);

        await waitFor(() => {
            expect(screen.getByText('Failed to load system overview')).toBeInTheDocument();
        });
    });

    it('allows acknowledging alerts', async () => {
        (adminService.acknowledgeAlert as jest.Mock).mockResolvedValue(undefined);
        render(<SystemOverview />);

        await waitFor(() => {
            expect(screen.getByText('High CPU usage')).toBeInTheDocument();
        });

        const acknowledgeButton = screen.getByRole('button', { name: /acknowledge/i });
        fireEvent.click(acknowledgeButton);

        await waitFor(() => {
            expect(adminService.acknowledgeAlert).toHaveBeenCalledWith('alert-1');
        });
    });

    it('refreshes data periodically', async () => {
        jest.useFakeTimers();
        render(<SystemOverview />);

        await waitFor(() => {
            expect(adminService.getSystemOverview).toHaveBeenCalledTimes(1);
        });

        jest.advanceTimersByTime(30000); // 30 seconds

        await waitFor(() => {
            expect(adminService.getSystemOverview).toHaveBeenCalledTimes(2);
        });

        jest.useRealTimers();
    });
}); 