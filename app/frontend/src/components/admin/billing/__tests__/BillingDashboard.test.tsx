import React from 'react';
import { render, screen, waitFor } from '../../../../utils/test-utils';
import { BillingDashboard } from '../BillingDashboard';
import { adminService } from '../../../../services/adminService';

// Mock the admin service
jest.mock('../../../../services/adminService');

const mockOrganizations = [
    {
        id: 'org-1',
        name: 'Test Org 1',
        tier: 'pro',
        status: 'active',
        billing: {
            plan: 'pro',
            status: 'active',
            next_billing_date: '2024-03-01',
            payment_method: 'card_*1234'
        },
        settings: {
            max_users: 10,
            max_events_per_day: 100000,
            max_retention_days: 90,
            features: ['advanced_analytics', 'custom_dashboards']
        }
    },
    {
        id: 'org-2',
        name: 'Test Org 2',
        tier: 'basic',
        status: 'active',
        billing: {
            plan: 'basic',
            status: 'past_due',
            next_billing_date: '2024-02-15',
            payment_method: 'card_*5678'
        },
        settings: {
            max_users: 5,
            max_events_per_day: 50000,
            max_retention_days: 30,
            features: ['basic_analytics']
        }
    }
];

describe('BillingDashboard', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (adminService.getOrganizations as jest.Mock).mockResolvedValue(mockOrganizations);
    });

    it('renders loading state initially', () => {
        render(<BillingDashboard />);
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('displays organization billing information', async () => {
        render(<BillingDashboard />);

        await waitFor(() => {
            expect(screen.getByText('Test Org 1')).toBeInTheDocument();
            expect(screen.getByText('Test Org 2')).toBeInTheDocument();
        });

        // Check billing status
        expect(screen.getByText('Active')).toBeInTheDocument();
        expect(screen.getByText('Past Due')).toBeInTheDocument();

        // Check plan information
        expect(screen.getByText('Pro')).toBeInTheDocument();
        expect(screen.getByText('Basic')).toBeInTheDocument();
    });

    it('handles error state', async () => {
        const error = new Error('Failed to load organizations');
        (adminService.getOrganizations as jest.Mock).mockRejectedValue(error);

        render(<BillingDashboard />);

        await waitFor(() => {
            expect(screen.getByText(/error loading billing data/i)).toBeInTheDocument();
        });
    });

    it('displays payment method information', async () => {
        render(<BillingDashboard />);

        await waitFor(() => {
            expect(screen.getByText('card_*1234')).toBeInTheDocument();
            expect(screen.getByText('card_*5678')).toBeInTheDocument();
        });
    });

    it('shows next billing dates', async () => {
        render(<BillingDashboard />);

        await waitFor(() => {
            expect(screen.getByText('2024-03-01')).toBeInTheDocument();
            expect(screen.getByText('2024-02-15')).toBeInTheDocument();
        });
    });

    it('displays organization tier limits', async () => {
        render(<BillingDashboard />);

        await waitFor(() => {
            // Pro tier limits
            expect(screen.getByText('10')).toBeInTheDocument(); // max users
            expect(screen.getByText('100,000')).toBeInTheDocument(); // events per day
            expect(screen.getByText('90')).toBeInTheDocument(); // retention days

            // Basic tier limits
            expect(screen.getByText('5')).toBeInTheDocument();
            expect(screen.getByText('50,000')).toBeInTheDocument();
            expect(screen.getByText('30')).toBeInTheDocument();
        });
    });
}); 