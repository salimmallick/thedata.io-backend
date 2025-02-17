import { apiClient } from './apiClient';
import {
    TransformationRule,
    MaterializedView,
    DataSink,
    RetentionPolicy
} from '../types/data-management';

class DataManagementService {
    // Transformation Rules
    async getTransformationRules(): Promise<TransformationRule[]> {
        const response = await apiClient.get('/api/data-management/transformation-rules');
        return response.data;
    }

    async getTransformationRule(name: string): Promise<TransformationRule> {
        const response = await apiClient.get(`/api/data-management/transformation-rules/${name}`);
        return response.data;
    }

    async createTransformationRule(rule: TransformationRule): Promise<TransformationRule> {
        const response = await apiClient.post('/api/data-management/transformation-rules', rule);
        return response.data;
    }

    async updateTransformationRule(name: string, rule: Partial<TransformationRule>): Promise<TransformationRule> {
        const response = await apiClient.put(`/api/data-management/transformation-rules/${name}`, rule);
        return response.data;
    }

    async deleteTransformationRule(name: string): Promise<void> {
        await apiClient.delete(`/api/data-management/transformation-rules/${name}`);
    }

    // Materialized Views
    async getMaterializedViews(): Promise<MaterializedView[]> {
        const response = await apiClient.get('/api/data-management/materialized-views');
        return response.data;
    }

    async createMaterializedView(view: MaterializedView): Promise<MaterializedView> {
        const response = await apiClient.post('/api/data-management/materialized-views', view);
        return response.data;
    }

    async refreshMaterializedView(name: string): Promise<void> {
        await apiClient.post(`/api/data-management/materialized-views/${name}/refresh`);
    }

    // Data Sinks
    async getDataSinks(): Promise<DataSink[]> {
        const response = await apiClient.get('/api/data-management/sinks');
        return response.data;
    }

    async createDataSink(sink: DataSink): Promise<DataSink> {
        const response = await apiClient.post('/api/data-management/sinks', sink);
        return response.data;
    }

    async updateDataSink(name: string, sink: Partial<DataSink>): Promise<DataSink> {
        const response = await apiClient.put(`/api/data-management/sinks/${name}`, sink);
        return response.data;
    }

    async deleteDataSink(name: string): Promise<void> {
        await apiClient.delete(`/api/data-management/sinks/${name}`);
    }

    // Retention Policies
    async getRetentionPolicies(): Promise<RetentionPolicy[]> {
        const response = await apiClient.get('/api/data-management/retention-policies');
        return response.data;
    }

    async updateRetentionPolicy(tableName: string, retentionDays: number): Promise<RetentionPolicy> {
        const response = await apiClient.put(`/api/data-management/retention-policies/${tableName}`, {
            retention_days: retentionDays
        });
        return response.data;
    }
}

export const dataManagementService = new DataManagementService(); 