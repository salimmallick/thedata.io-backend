import axios from 'axios';

const baseURL = process.env.REACT_APP_API_URL || 'http://api.localhost';

export const apiClient = axios.create({
    baseURL,
    headers: {
        'Content-Type': 'application/json'
    },
    timeout: 10000 // 10 second timeout
});

// Add request interceptor to include auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add response interceptor to handle errors
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            // Handle specific error cases
            switch (error.response.status) {
                case 401:
                    // Unauthorized - clear token and redirect to login
                    localStorage.removeItem('auth_token');
                    window.location.href = '/login';
                    break;
                case 403:
                    // Forbidden - user doesn't have required permissions
                    console.error('Access forbidden:', error.response.data);
                    break;
                case 404:
                    // Not found
                    console.error('Resource not found:', error.response.data);
                    break;
                case 422:
                    // Validation error
                    console.error('Validation error:', error.response.data);
                    break;
                case 504:
                    // Gateway timeout
                    console.error('Gateway timeout - server not responding');
                    break;
                default:
                    // Other errors
                    console.error('API error:', error.response.data);
            }
        } else if (error.request) {
            // Network error
            console.error('Network error:', error.request);
        } else {
            // Other errors
            console.error('Error:', error.message);
        }
        return Promise.reject(error);
    }
); 