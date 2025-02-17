export interface User {
    id: string;
    email: string;
    full_name: string;
    role: 'user' | 'admin';
    organization_id: string;
    status: 'active' | 'inactive' | 'suspended';
    created_at: string;
    last_login?: string;
    permissions: string[];
}

export interface Organization {
    id: string;
    name: string;
    tier: 'free' | 'basic' | 'pro' | 'enterprise';
    status: 'active' | 'inactive' | 'suspended';
    created_at: string;
    settings: {
        max_users: number;
        max_events_per_day: number;
        max_retention_days: number;
        features: string[];
    };
    billing: {
        plan: string;
        status: string;
        next_billing_date: string;
        payment_method?: string;
    };
    api_keys: ApiKey[];
}

export interface ApiKey {
    id: string;
    name: string;
    status: 'active' | 'revoked';
    created_at: string;
    last_used?: string;
    token?: string;
}

export interface SystemMetrics {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    network_in: number;
    network_out: number;
    historical_data: Array<{
        timestamp: string;
        cpu_usage: number;
        memory_usage: number;
        disk_usage: number;
        network_in: number;
        network_out: number;
    }>;
}

export interface SystemComponent {
    name: string;
    status: 'healthy' | 'degraded' | 'error';
    message?: string;
    metrics: {
        latency: number;
        error_rate: number;
        throughput: number;
    };
}

export interface SystemOverview {
    metrics: SystemMetrics;
    components: SystemComponent[];
    alerts: {
        id: string;
        severity: 'info' | 'warning' | 'error';
        message: string;
        timestamp: string;
        acknowledged: boolean;
    }[];
    events: {
        id: string;
        type: string;
        message: string;
        timestamp: string;
        details: Record<string, any>;
    }[];
} 