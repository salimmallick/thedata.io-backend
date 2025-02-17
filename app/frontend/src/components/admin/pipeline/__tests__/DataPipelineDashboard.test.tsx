import React from 'react';
import { render, screen, fireEvent, waitFor } from '../../../../utils/test-utils';
import { DataPipelineDashboard } from '../DataPipelineDashboard';
import { adminService } from '../../../../services/adminService';

// Mock the admin service
jest.mock('../../../../services/adminService');

const mockPipelineData = {
    components: [
        {
            id: 'comp-1',
            name: 'Ingestion Service',
            status: 'running',
            health: 'healthy',
            metrics: {
                throughput: 1000,
                latency: 50,
                error_rate: 0.01,
                queue_size: 100,
                processing_time: 25
            },
            config: {
                batch_size: 100,
                workers: 5
            }
        },
        {
            id: 'comp-2',
            name: 'Transform Service',
            status: 'running',
            health: 'degraded',
            metrics: {
                throughput: 800,
                latency: 150,
                error_rate: 0.05,
                queue_size: 500,
                processing_time: 75
            },
            config: {
                rules_enabled: true,
                max_retries: 3
            }
        }
    ],
    alerts: [
        {
            id: 'alert-1',
            component_id: 'comp-2',
            severity: 'warning',
            message: 'High latency detected',
            timestamp: '2024-02-12T10:00:00Z',
            acknowledged: false
        }
    ],
    overall_health: 'degraded',
    metrics: {
        total_throughput: 1800,
        average_latency: 100,
        total_errors: 45
    }
};

describe('DataPipelineDashboard', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (adminService.getPipelineStatus as jest.Mock).mockResolvedValue(mockPipelineData);
        (adminService.controlPipelineComponent as jest.Mock).mockResolvedValue(undefined);
        (adminService.acknowledgePipelineAlert as jest.Mock).mockResolvedValue(undefined);
    });

    it('renders loading state initially', () => {
        render(<DataPipelineDashboard />);
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('displays pipeline components and their status', async () => {
        render(<DataPipelineDashboard />);

        await waitFor(() => {
            expect(screen.getByText('Ingestion Service')).toBeInTheDocument();
            expect(screen.getByText('Transform Service')).toBeInTheDocument();
        });

        // Check health status
        expect(screen.getByText('Healthy')).toBeInTheDocument();
        expect(screen.getByText('Degraded')).toBeInTheDocument();
    });

    it('shows pipeline metrics', async () => {
        render(<DataPipelineDashboard />);

        await waitFor(() => {
            expect(screen.getByText('1,800')).toBeInTheDocument(); // total throughput
            expect(screen.getByText('100ms')).toBeInTheDocument(); // average latency
            expect(screen.getByText('45')).toBeInTheDocument(); // total errors
        });
    });

    it('handles component control actions', async () => {
        render(<DataPipelineDashboard />);

        await waitFor(() => {
            expect(screen.getByText('Ingestion Service')).toBeInTheDocument();
        });

        // Find and click restart button
        const restartButton = screen.getByRole('button', { name: /restart/i });
        fireEvent.click(restartButton);

        await waitFor(() => {
            expect(adminService.controlPipelineComponent).toHaveBeenCalledWith(
                'Ingestion Service',
                'restart'
            );
        });
    });

    it('displays and handles alerts', async () => {
        render(<DataPipelineDashboard />);

        await waitFor(() => {
            expect(screen.getByText('High latency detected')).toBeInTheDocument();
        });

        // Find and click acknowledge button
        const acknowledgeButton = screen.getByRole('button', { name: /acknowledge/i });
        fireEvent.click(acknowledgeButton);

        await waitFor(() => {
            expect(adminService.acknowledgePipelineAlert).toHaveBeenCalledWith('alert-1');
        });
    });

    it('handles error state', async () => {
        const error = new Error('Failed to load pipeline data');
        (adminService.getPipelineStatus as jest.Mock).mockRejectedValue(error);

        render(<DataPipelineDashboard />);

        await waitFor(() => {
            expect(screen.getByText(/error loading pipeline data/i)).toBeInTheDocument();
        });
    });

    it('displays component metrics', async () => {
        render(<DataPipelineDashboard />);

        await waitFor(() => {
            // Ingestion Service metrics
            expect(screen.getByText('1,000')).toBeInTheDocument(); // throughput
            expect(screen.getByText('50ms')).toBeInTheDocument(); // latency
            expect(screen.getByText('0.01%')).toBeInTheDocument(); // error rate

            // Transform Service metrics
            expect(screen.getByText('800')).toBeInTheDocument(); // throughput
            expect(screen.getByText('150ms')).toBeInTheDocument(); // latency
            expect(screen.getByText('0.05%')).toBeInTheDocument(); // error rate
        });
    });

    it('allows component configuration', async () => {
        render(<DataPipelineDashboard />);

        await waitFor(() => {
            expect(screen.getByText('Ingestion Service')).toBeInTheDocument();
        });

        // Find and click settings button
        const settingsButton = screen.getByRole('button', { name: /settings/i });
        fireEvent.click(settingsButton);

        // Check if configuration dialog is shown
        expect(screen.getByText(/component settings/i)).toBeInTheDocument();
        expect(screen.getByText('batch_size')).toBeInTheDocument();
        expect(screen.getByText('workers')).toBeInTheDocument();
    });
}); 