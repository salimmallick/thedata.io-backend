import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';
import { Event } from '@sentry/types';

export const initErrorTracking = () => {
    if (process.env.NODE_ENV === 'production') {
        Sentry.init({
            dsn: process.env.REACT_APP_SENTRY_DSN,
            integrations: [new BrowserTracing()],
            tracesSampleRate: 1.0,
            environment: process.env.REACT_APP_ENVIRONMENT || 'production',
            beforeSend(event: Event): Event | null {
                // Don't send events in development
                if (process.env.NODE_ENV === 'development') {
                    return null;
                }
                return event;
            },
        });
    }
};

export const captureError = (error: Error, context?: Record<string, any>) => {
    if (process.env.NODE_ENV === 'development') {
        console.error('Error:', error);
        if (context) {
            console.error('Context:', context);
        }
    } else {
        Sentry.captureException(error, {
            extra: context
        });
    }
};

interface UserContext {
    id: string;
    email: string;
    role: string;
}

export const setUserContext = (user: UserContext) => {
    Sentry.setUser({
        id: user.id,
        email: user.email,
        role: user.role
    });
};

export const clearUserContext = () => {
    Sentry.setUser(null);
}; 