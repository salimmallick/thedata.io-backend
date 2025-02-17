import React, { Component, ErrorInfo } from 'react';
import {
    Box,
    Typography,
    Button,
    Paper
} from '@mui/material';
import { Error as ErrorIcon } from '@mui/icons-material';

interface Props {
    children: React.ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null
        };
    }

    static getDerivedStateFromError(error: Error): State {
        return {
            hasError: true,
            error,
            errorInfo: null
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        this.setState({
            error,
            errorInfo
        });
        
        // Log error to your error tracking service
        console.error('Uncaught error:', error, errorInfo);
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null
        });
    };

    render() {
        if (this.state.hasError) {
            return (
                <Box
                    display="flex"
                    justifyContent="center"
                    alignItems="center"
                    minHeight="100vh"
                    bgcolor="#f5f5f5"
                >
                    <Paper
                        elevation={3}
                        sx={{
                            p: 4,
                            maxWidth: 600,
                            textAlign: 'center'
                        }}
                    >
                        <ErrorIcon
                            color="error"
                            sx={{ fontSize: 64, mb: 2 }}
                        />
                        <Typography variant="h5" gutterBottom>
                            Something went wrong
                        </Typography>
                        <Typography color="text.secondary" paragraph>
                            We apologize for the inconvenience. Please try refreshing the page or contact support if the problem persists.
                        </Typography>
                        <Button
                            variant="contained"
                            onClick={() => window.location.reload()}
                            sx={{ mr: 2 }}
                        >
                            Refresh Page
                        </Button>
                        <Button
                            variant="outlined"
                            onClick={this.handleReset}
                        >
                            Try Again
                        </Button>
                        {process.env.NODE_ENV === 'development' && (
                            <Box mt={4} textAlign="left">
                                <Typography variant="subtitle2" color="error">
                                    {this.state.error?.toString()}
                                </Typography>
                                <pre style={{ marginTop: 8, overflow: 'auto' }}>
                                    {this.state.errorInfo?.componentStack}
                                </pre>
                            </Box>
                        )}
                    </Paper>
                </Box>
            );
        }

        return this.props.children;
    }
} 