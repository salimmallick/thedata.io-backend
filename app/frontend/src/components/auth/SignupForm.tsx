import React, { useState } from 'react';
import {
    Box,
    Paper,
    Typography,
    TextField,
    Button,
    Stepper,
    Step,
    StepLabel,
    Alert,
    CircularProgress
} from '@mui/material';
import { adminService } from '../../services/adminService';

export const SignupForm: React.FC = () => {
    const [activeStep, setActiveStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    const [formData, setFormData] = useState({
        organization: {
            name: '',
            tier: 'basic',
        },
        user: {
            email: '',
            full_name: '',
            password: '',
        },
        billing: {
            plan: 'monthly',
            payment_method: 'credit_card',
        }
    });

    const steps = ['Organization Details', 'Account Setup', 'Billing Information'];

    const handleNext = async () => {
        if (activeStep === steps.length - 1) {
            await handleSubmit();
        } else {
            setActiveStep((prev) => prev + 1);
        }
    };

    const handleBack = () => {
        setActiveStep((prev) => prev - 1);
    };

    const handleSubmit = async () => {
        try {
            setLoading(true);
            setError(null);

            // Create organization
            const org = await adminService.createOrganization({
                name: formData.organization.name,
                tier: 'basic',
                status: 'active',
                settings: {
                    max_users: 5,
                    max_events_per_day: 10000,
                    max_retention_days: 30,
                    features: ['data_ingestion', 'basic_analytics']
                }
            });

            // Create admin user
            const user = await adminService.createUser({
                email: formData.user.email,
                full_name: formData.user.full_name,
                role: 'admin',
                organization_id: org.id,
                status: 'active',
                permissions: ['manage_users', 'manage_api_keys']
            });

            // Generate initial API key
            const apiKey = await adminService.createApiKey(user.id, 'Default API Key');

            // Redirect to success page with API key
            window.location.href = `/signup/success?apiKey=${apiKey.token}`;

        } catch (err) {
            setError('Failed to create account. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const renderStepContent = (step: number) => {
        switch (step) {
            case 0:
                return (
                    <Box display="flex" flexDirection="column" gap={2}>
                        <TextField
                            label="Organization Name"
                            value={formData.organization.name}
                            onChange={(e) => setFormData({
                                ...formData,
                                organization: {
                                    ...formData.organization,
                                    name: e.target.value
                                }
                            })}
                            fullWidth
                            required
                        />
                    </Box>
                );
            case 1:
                return (
                    <Box display="flex" flexDirection="column" gap={2}>
                        <TextField
                            label="Full Name"
                            value={formData.user.full_name}
                            onChange={(e) => setFormData({
                                ...formData,
                                user: {
                                    ...formData.user,
                                    full_name: e.target.value
                                }
                            })}
                            fullWidth
                            required
                        />
                        <TextField
                            label="Email"
                            type="email"
                            value={formData.user.email}
                            onChange={(e) => setFormData({
                                ...formData,
                                user: {
                                    ...formData.user,
                                    email: e.target.value
                                }
                            })}
                            fullWidth
                            required
                        />
                        <TextField
                            label="Password"
                            type="password"
                            value={formData.user.password}
                            onChange={(e) => setFormData({
                                ...formData,
                                user: {
                                    ...formData.user,
                                    password: e.target.value
                                }
                            })}
                            fullWidth
                            required
                        />
                    </Box>
                );
            case 2:
                return (
                    <Box display="flex" flexDirection="column" gap={2}>
                        <Typography variant="body1" gutterBottom>
                            Select your billing plan:
                        </Typography>
                        <Button
                            variant={formData.billing.plan === 'monthly' ? 'contained' : 'outlined'}
                            onClick={() => setFormData({
                                ...formData,
                                billing: { ...formData.billing, plan: 'monthly' }
                            })}
                        >
                            Monthly Plan - $99/month
                        </Button>
                        <Button
                            variant={formData.billing.plan === 'annual' ? 'contained' : 'outlined'}
                            onClick={() => setFormData({
                                ...formData,
                                billing: { ...formData.billing, plan: 'annual' }
                            })}
                        >
                            Annual Plan - $990/year (Save 2 months!)
                        </Button>
                    </Box>
                );
            default:
                return null;
        }
    };

    return (
        <Box maxWidth={600} mx="auto" mt={4} p={3}>
            <Paper elevation={3} sx={{ p: 4 }}>
                <Typography variant="h4" gutterBottom align="center">
                    Create Your Account
                </Typography>

                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                )}

                <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
                    {steps.map((label) => (
                        <Step key={label}>
                            <StepLabel>{label}</StepLabel>
                        </Step>
                    ))}
                </Stepper>

                {renderStepContent(activeStep)}

                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
                    <Button
                        onClick={handleBack}
                        disabled={activeStep === 0 || loading}
                    >
                        Back
                    </Button>
                    <Button
                        variant="contained"
                        onClick={handleNext}
                        disabled={loading}
                    >
                        {loading ? <CircularProgress size={24} /> : 
                         activeStep === steps.length - 1 ? 'Complete' : 'Next'}
                    </Button>
                </Box>
            </Paper>
        </Box>
    );
}; 