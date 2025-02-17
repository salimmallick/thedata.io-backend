import { apiClient } from './apiClient';
import {
    User,
    Organization,
    ApiKey,
    SystemOverview
} from '../types/admin';
import { DataPipeline } from '../types/data-management';

class AdminService {
    // User Management
    async getUsers(): Promise<User[]> {
        const response = await apiClient.get('/api/admin/users');
        return response.data;
    }

    async getUser(id: string): Promise<User> {
        const response = await apiClient.get(`/api/admin/users/${id}`);
        return response.data;
    }

    async createUser(user: Partial<User>): Promise<User> {
        const response = await apiClient.post('/api/admin/users', user);
        return response.data;
    }

    async updateUser(id: string, updates: Partial<User>): Promise<User> {
        const response = await apiClient.put(`/api/admin/users/${id}`, updates);
        return response.data;
    }

    async deleteUser(id: string): Promise<void> {
        await apiClient.delete(`/api/admin/users/${id}`);
    }

    // Organization Management
    async getOrganizations(): Promise<Organization[]> {
        const response = await apiClient.get('/api/admin/organizations');
        return response.data;
    }

    async getOrganization(id: string): Promise<Organization> {
        const response = await apiClient.get(`/api/admin/organizations/${id}`);
        return response.data;
    }

    async createOrganization(org: Partial<Organization>): Promise<Organization> {
        const response = await apiClient.post('/api/admin/organizations', org);
        return response.data;
    }

    async updateOrganization(id: string, updates: Partial<Organization>): Promise<Organization> {
        const response = await apiClient.put(`/api/admin/organizations/${id}`, updates);
        return response.data;
    }

    async deleteOrganization(id: string): Promise<void> {
        await apiClient.delete(`/api/admin/organizations/${id}`);
    }

    // API Key Management
    async getApiKeys(userId: string): Promise<ApiKey[]> {
        const response = await apiClient.get(`/api/admin/users/${userId}/api-keys`);
        return response.data;
    }

    async createApiKey(userId: string, name?: string): Promise<ApiKey> {
        const response = await apiClient.post(`/api/admin/users/${userId}/api-keys`, { name });
        return response.data;
    }

    async revokeApiKey(userId: string, keyId: string): Promise<void> {
        await apiClient.delete(`/api/admin/users/${userId}/api-keys/${keyId}`);
    }

    // System Overview
    async getSystemOverview(): Promise<SystemOverview> {
        const response = await apiClient.get('/api/admin/system/overview');
        return response.data;
    }

    async getSystemMetrics(timeRange: string): Promise<SystemOverview['metrics'][]> {
        const response = await apiClient.get('/api/admin/system/metrics', {
            params: { timeRange }
        });
        return response.data;
    }

    async acknowledgeAlert(alertId: string): Promise<void> {
        await apiClient.post(`/api/admin/system/alerts/${alertId}/acknowledge`);
    }

    // User Permissions
    async getUserPermissions(userId: string): Promise<string[]> {
        const response = await apiClient.get(`/api/admin/users/${userId}/permissions`);
        return response.data;
    }

    async updateUserPermissions(userId: string, permissions: string[]): Promise<void> {
        await apiClient.put(`/api/admin/users/${userId}/permissions`, { permissions });
    }

    // Organization Settings
    async updateOrganizationSettings(
        orgId: string,
        settings: Organization['settings']
    ): Promise<void> {
        await apiClient.put(`/api/admin/organizations/${orgId}/settings`, settings);
    }

    async updateOrganizationBilling(
        orgId: string,
        billing: Organization['billing']
    ): Promise<void> {
        await apiClient.put(`/api/admin/organizations/${orgId}/billing`, billing);
    }

    // Pipeline Management
    async getPipelineStatus(): Promise<DataPipeline> {
        const response = await apiClient.get('/api/admin/pipeline/status');
        return response.data;
    }

    async controlPipelineComponent(
        componentName: string,
        action: 'start' | 'stop' | 'restart'
    ): Promise<void> {
        await apiClient.post(`/api/admin/pipeline/components/${componentName}/${action}`);
    }

    async getPipelineMetrics(timeRange: string): Promise<any> {
        const response = await apiClient.get('/api/admin/pipeline/metrics', {
            params: { timeRange }
        });
        return response.data;
    }

    async getPipelineAlerts(): Promise<any> {
        const response = await apiClient.get('/api/admin/pipeline/alerts');
        return response.data;
    }

    async acknowledgePipelineAlert(alertId: string): Promise<void> {
        await apiClient.post(`/api/admin/pipeline/alerts/${alertId}/acknowledge`);
    }

    async updatePipelineConfig(
        componentName: string,
        config: any
    ): Promise<void> {
        await apiClient.put(
            `/api/admin/pipeline/components/${componentName}/config`,
            config
        );
    }
}

export const adminService = new AdminService(); 