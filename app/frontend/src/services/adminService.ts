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
        const response = await apiClient.get('/api/v1/users');
        return response.data;
    }

    async getUser(id: string): Promise<User> {
        const response = await apiClient.get(`/api/v1/users/${id}`);
        return response.data;
    }

    async createUser(user: Partial<User>): Promise<User> {
        const response = await apiClient.post('/api/v1/users', user);
        return response.data;
    }

    async updateUser(id: string, updates: Partial<User>): Promise<User> {
        const response = await apiClient.put(`/api/v1/users/${id}`, updates);
        return response.data;
    }

    async deleteUser(id: string): Promise<void> {
        await apiClient.delete(`/api/v1/users/${id}`);
    }

    // Organization Management
    async getOrganizations(): Promise<Organization[]> {
        const response = await apiClient.get('/api/v1/organizations');
        return response.data;
    }

    async getOrganization(id: string): Promise<Organization> {
        const response = await apiClient.get(`/api/v1/organizations/${id}`);
        return response.data;
    }

    async createOrganization(org: Partial<Organization>): Promise<Organization> {
        const response = await apiClient.post('/api/v1/organizations', org);
        return response.data;
    }

    async updateOrganization(id: string, updates: Partial<Organization>): Promise<Organization> {
        const response = await apiClient.put(`/api/v1/organizations/${id}`, updates);
        return response.data;
    }

    async deleteOrganization(id: string): Promise<void> {
        await apiClient.delete(`/api/v1/organizations/${id}`);
    }

    // API Key Management
    async getApiKeys(userId: string): Promise<ApiKey[]> {
        const response = await apiClient.get(`/api/v1/users/${userId}/api-keys`);
        return response.data;
    }

    async createApiKey(userId: string, name?: string): Promise<ApiKey> {
        const response = await apiClient.post(`/api/v1/users/${userId}/api-keys`, { name });
        return response.data;
    }

    async revokeApiKey(userId: string, keyId: string): Promise<void> {
        await apiClient.delete(`/api/v1/users/${userId}/api-keys/${keyId}`);
    }

    // System Overview
    async getSystemOverview(): Promise<SystemOverview> {
        try {
            const response = await apiClient.get('/api/v1/admin/system/status');
            const { metrics, health } = response.data;
            
            // Transform API response to match frontend format
            return {
                metrics: {
                    cpu_usage: metrics?.cpu?.usage_percent || 0,
                    memory_usage: metrics?.memory?.percent || 0,
                    disk_usage: metrics?.disk?.percent || 0,
                    network_in: 0,
                    network_out: 0,
                    historical_data: []
                },
                components: [
                    {
                        name: 'API Server',
                        status: health ? 'healthy' : 'degraded',
                        message: metrics?.message || 'System is running',
                        metrics: {
                            latency: 0,
                            error_rate: 0,
                            throughput: 0
                        }
                    }
                ],
                alerts: (metrics?.cpu?.above_threshold || metrics?.memory?.above_threshold) ? [
                    {
                        id: 'resource-alert',
                        severity: 'warning',
                        message: `High resource usage detected: ${
                            metrics?.cpu?.above_threshold ? 'CPU ' : ''
                        }${
                            metrics?.memory?.above_threshold ? 'Memory ' : ''
                        }above threshold`,
                        timestamp: new Date().toISOString(),
                        acknowledged: false
                    }
                ] : [],
                events: []
            };
        } catch (error) {
            console.error('Error fetching system overview:', error);
            // Return a default state when the API fails
            return {
                metrics: {
                    cpu_usage: 0,
                    memory_usage: 0,
                    disk_usage: 0,
                    network_in: 0,
                    network_out: 0,
                    historical_data: []
                },
                components: [
                    {
                        name: 'API Server',
                        status: 'error',
                        message: 'Failed to fetch system status',
                        metrics: {
                            latency: 0,
                            error_rate: 1,
                            throughput: 0
                        }
                    }
                ],
                alerts: [{
                    id: 'system-error',
                    severity: 'error',
                    message: 'Failed to fetch system status',
                    timestamp: new Date().toISOString(),
                    acknowledged: false
                }],
                events: []
            };
        }
    }

    async getSystemMetrics(timeRange: string): Promise<SystemOverview['metrics'][]> {
        const response = await apiClient.get('/api/v1/admin/system/metrics', {
            params: { timeRange }
        });
        return response.data;
    }

    async acknowledgeAlert(alertId: string): Promise<void> {
        await apiClient.post(`/api/v1/admin/alerts/${alertId}/acknowledge`);
    }

    // User Permissions
    async getUserPermissions(userId: string): Promise<string[]> {
        const response = await apiClient.get(`/api/v1/users/${userId}/permissions`);
        return response.data;
    }

    async updateUserPermissions(userId: string, permissions: string[]): Promise<void> {
        await apiClient.put(`/api/v1/users/${userId}/permissions`, { permissions });
    }

    // Organization Settings
    async updateOrganizationSettings(
        orgId: string,
        settings: Organization['settings']
    ): Promise<void> {
        await apiClient.put(`/api/v1/organizations/${orgId}/settings`, settings);
    }

    async updateOrganizationBilling(
        orgId: string,
        billing: Organization['billing']
    ): Promise<void> {
        await apiClient.put(`/api/v1/organizations/${orgId}/billing`, billing);
    }

    // Pipeline Management
    async getPipelineStatus(): Promise<DataPipeline> {
        const response = await apiClient.get('/api/v1/admin/pipeline/status');
        return response.data;
    }

    async controlPipelineComponent(
        componentName: string,
        action: 'start' | 'stop' | 'restart'
    ): Promise<void> {
        await apiClient.post(`/api/v1/admin/pipeline/components/${componentName}/${action}`);
    }

    async getPipelineMetrics(timeRange: string): Promise<any> {
        const response = await apiClient.get('/api/v1/admin/pipeline/metrics', {
            params: { timeRange }
        });
        return response.data;
    }

    async getPipelineAlerts(): Promise<any> {
        const response = await apiClient.get('/api/v1/admin/pipeline/alerts');
        return response.data;
    }

    async acknowledgePipelineAlert(alertId: string): Promise<void> {
        await apiClient.post(`/api/v1/admin/pipeline/alerts/${alertId}/acknowledge`);
    }

    async updatePipelineConfig(
        componentName: string,
        config: any
    ): Promise<void> {
        await apiClient.put(
            `/api/v1/admin/pipeline/components/${componentName}/config`,
            config
        );
    }
}

export const adminService = new AdminService(); 