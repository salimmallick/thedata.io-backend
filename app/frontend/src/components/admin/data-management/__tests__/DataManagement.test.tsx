import React from 'react';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DataManagement } from '../DataManagement';
import { dataManagementService } from '../../../../services/dataManagementService';
import { MaterializedView, TransformationRule, DataSink, RetentionPolicy } from '../../../../types/data-management';

// Mock the service
jest.mock('../../../../services/dataManagementService');

const mockTransformationRules: TransformationRule[] = [
    {
        name: 'test-rule',
        type: 'normalize',
        input_table: 'test_input',
        output_table: 'test_output',
        transformation_sql: 'SELECT * FROM test_input',
        enabled: true,
        order: 1,
        config: {}
    }
];

const mockViews: MaterializedView[] = [
    {
        name: 'test_view',
        query: 'SELECT * FROM test',
        refresh_interval: '5 minutes',
        status: 'active',
        last_refresh: new Date().toISOString()
    }
];

const mockDataSinks: DataSink[] = [
    {
        name: 'test-sink',
        type: 'kafka',
        status: 'active',
        config: {},
        metrics: {
            records_processed: 1000,
            bytes_processed: 5000,
            last_latency: 50
        }
    }
];

const mockRetentionPolicies: RetentionPolicy[] = [
    {
        table_name: 'test_table',
        retention_days: 30,
        last_cleanup: '2024-02-12T10:00:00Z',
        rows_deleted: 1000
    }
];

describe('DataManagement', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (dataManagementService.getTransformationRules as jest.Mock).mockResolvedValue(mockTransformationRules);
        (dataManagementService.getMaterializedViews as jest.Mock).mockResolvedValue(mockViews);
        (dataManagementService.getDataSinks as jest.Mock).mockResolvedValue(mockDataSinks);
        (dataManagementService.getRetentionPolicies as jest.Mock).mockResolvedValue(mockRetentionPolicies);
    });

    it('renders all tabs correctly', () => {
        render(<DataManagement />);
        
        expect(screen.getByText('Transformation Rules')).toBeInTheDocument();
        expect(screen.getByText('Materialized Views')).toBeInTheDocument();
        expect(screen.getByText('Data Sinks')).toBeInTheDocument();
        expect(screen.getByText('Retention Policies')).toBeInTheDocument();
    });

    it('switches between tabs correctly', async () => {
        render(<DataManagement />);
        
        // Click on Materialized Views tab
        fireEvent.click(screen.getByText('Materialized Views'));
        await waitFor(() => {
            expect(screen.getByText('test_view')).toBeInTheDocument();
        });

        // Click on Data Sinks tab
        fireEvent.click(screen.getByText('Data Sinks'));
        await waitFor(() => {
            expect(screen.getByText('test-sink')).toBeInTheDocument();
        });

        // Click on Retention Policies tab
        fireEvent.click(screen.getByText('Retention Policies'));
        await waitFor(() => {
            expect(screen.getByText('test_table')).toBeInTheDocument();
        });
    });

    it('handles loading states correctly', async () => {
        render(<DataManagement />);
        
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
        
        await waitFor(() => {
            expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
        });
    });

    it('handles error states correctly', async () => {
        const error = new Error('Failed to load data');
        (dataManagementService.getTransformationRules as jest.Mock).mockRejectedValue(error);
        
        render(<DataManagement />);
        
        await waitFor(() => {
            expect(screen.getByText(/error loading data/i)).toBeInTheDocument();
        });
    });

    it('maintains tab state when switching between tabs', async () => {
        render(<DataManagement />);
        
        // Switch to Materialized Views
        fireEvent.click(screen.getByText('Materialized Views'));
        await waitFor(() => {
            expect(screen.getByText('test_view')).toBeInTheDocument();
        });

        // Switch to Data Sinks and back
        fireEvent.click(screen.getByText('Data Sinks'));
        fireEvent.click(screen.getByText('Materialized Views'));
        
        // Should still show the view
        expect(screen.getByText('test_view')).toBeInTheDocument();
    });
}); 