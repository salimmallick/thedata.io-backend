import axios, { 
  AxiosInstance, 
  InternalAxiosRequestConfig,
  AxiosResponse, 
  AxiosError 
} from 'axios';
import { apiClient } from './apiClient';

declare global {
  namespace NodeJS {
    interface ProcessEnv {
      REACT_APP_API_URL: string;
      REACT_APP_DAGSTER_URL: string;
    }
  }
}

const api: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // Enable sending cookies
});

// Login function with correct content type
export const login = async (email: string, password: string) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  
  try {
    const response = await api.post(
      '/api/v1/auth/login',
      formData,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );
    
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
      // Set the token in the default headers for future requests
      api.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
      return response.data;
    }
    
    throw new Error('Invalid response from server');
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

// Add request interceptor for authentication
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = localStorage.getItem('auth_token');
    console.log('Request config:', { url: config.url, method: config.method, token: !!token });
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse): AxiosResponse => response,
  async (error: AxiosError) => {
    console.error('Response error:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    
    if (error.response?.status === 401) {
      // Handle token expiration
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth endpoints
export const auth = {
  login: (credentials: any) => api.post('/api/v1/auth/login', credentials),
  logout: () => api.post('/api/v1/auth/logout'),
  refreshToken: () => api.post('/api/v1/auth/refresh'),
  me: () => api.get('/api/v1/auth/me')
};

// Data Management endpoints
export const dataManagement = {
  getDataSources: () => api.get('/api/v1/data-sources'),
  createDataSource: (data: any) => api.post('/api/v1/data-sources', data),
  updateDataSource: (id: string, data: any) => api.put(`/api/v1/data-sources/${id}`, data),
  deleteDataSource: (id: string) => api.delete(`/api/v1/data-sources/${id}`),
  getDataSourceMetrics: (id: string) => api.get(`/api/v1/data-sources/${id}/metrics`),
  validateConnection: (data: any) => api.post('/api/v1/data-sources/validate', data)
};

// Pipeline Management endpoints
export const pipelineManagement = {
  getPipelines: () => api.get('/api/v1/pipelines'),
  createPipeline: (data: any) => api.post('/api/v1/pipelines', data),
  updatePipeline: (id: string, data: any) => api.put(`/api/v1/pipelines/${id}`, data),
  deletePipeline: (id: string) => api.delete(`/api/v1/pipelines/${id}`),
  startPipeline: (id: string) => api.post(`/api/v1/pipelines/${id}/start`),
  stopPipeline: (id: string) => api.post(`/api/v1/pipelines/${id}/stop`),
  getPipelineStatus: (id: string) => api.get(`/api/v1/pipelines/${id}/status`),
  getPipelineLogs: (id: string) => api.get(`/api/v1/pipelines/${id}/logs`)
};

// Analytics endpoints
export const analytics = {
  getMetrics: (params: any) => api.get('/api/v1/analytics/metrics', { params }),
  getEvents: (params: any) => api.get('/api/v1/analytics/events', { params }),
  getDashboards: () => api.get('/api/v1/analytics/dashboards'),
  createDashboard: (data: any) => api.post('/api/v1/analytics/dashboards', data),
  updateDashboard: (id: string, data: any) => api.put(`/api/v1/analytics/dashboards/${id}`, data),
  deleteDashboard: (id: string) => api.delete(`/api/v1/analytics/dashboards/${id}`)
};

// System Management endpoints
export const system = {
  getSystemStatus: () => api.get('/api/v1/system/status'),
  getSystemMetrics: () => api.get('/api/v1/system/metrics'),
  getSystemLogs: (params: any) => api.get('/api/v1/system/logs', { params }),
  updateSystemConfig: (data: any) => api.put('/api/v1/system/config', data),
  restartService: (service: string) => api.post(`/api/v1/system/services/${service}/restart`)
};

// User Management endpoints
export const users = {
  getUsers: () => api.get('/api/v1/users'),
  createUser: (data: any) => api.post('/api/v1/users', data),
  updateUser: (id: string, data: any) => api.put(`/api/v1/users/${id}`, data),
  deleteUser: (id: string) => api.delete(`/api/v1/users/${id}`),
  getUserRoles: () => api.get('/api/v1/users/roles'),
  updateUserRoles: (id: string, roles: string[]) => api.put(`/api/v1/users/${id}/roles`, { roles })
};

// Organization Management endpoints
export const organizations = {
  getOrganizations: () => api.get('/api/v1/organizations'),
  createOrganization: (data: any) => api.post('/api/v1/organizations', data),
  updateOrganization: (id: string, data: any) => api.put(`/api/v1/organizations/${id}`, data),
  deleteOrganization: (id: string) => api.delete(`/api/v1/organizations/${id}`),
  getOrganizationMembers: (id: string) => api.get(`/api/v1/organizations/${id}/members`),
  addOrganizationMember: (id: string, userId: string, role: string) => 
    api.post(`/api/v1/organizations/${id}/members`, { userId, role })
};

// Dagster Integration endpoints
const dagsterApi = axios.create({
  baseURL: process.env.REACT_APP_DAGSTER_URL || 'http://localhost:3001',
  headers: {
    'Content-Type': 'application/json'
  }
});

export const dagster = {
  getAssets: () => dagsterApi.get('/assets'),
  getJobs: () => dagsterApi.get('/jobs'),
  getJobRuns: (jobId: string) => dagsterApi.get(`/jobs/${jobId}/runs`),
  startJob: (jobId: string, config?: any) => dagsterApi.post(`/jobs/${jobId}/start`, config),
  stopJob: (runId: string) => dagsterApi.post(`/runs/${runId}/stop`),
  getRunStatus: (runId: string) => dagsterApi.get(`/runs/${runId}/status`),
  getRunLogs: (runId: string) => dagsterApi.get(`/runs/${runId}/logs`)
};

export { api }; 