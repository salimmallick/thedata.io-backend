import React, { useState } from 'react';
import {
    Box,
    Paper,
    Typography,
    Button,
    TextField,
    Alert,
    Divider,
    List,
    ListItem,
    ListItemIcon,
    ListItemText
} from '@mui/material';
import {
    CheckCircle as CheckCircleIcon,
    ContentCopy as ContentCopyIcon,
    Code as CodeIcon,
    Book as BookIcon,
    Settings as SettingsIcon
} from '@mui/icons-material';
import { useLocation } from 'react-router-dom';

export const SignupSuccess: React.FC = () => {
    const [copied, setCopied] = useState(false);
    const location = useLocation();
    const searchParams = new URLSearchParams(location.search);
    const apiKey = searchParams.get('apiKey');

    const handleCopyApiKey = () => {
        navigator.clipboard.writeText(apiKey || '');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const nextSteps = [
        {
            icon: <CodeIcon />,
            title: 'Install SDK',
            description: 'Install our SDK in your application using npm or yarn'
        },
        {
            icon: <SettingsIcon />,
            title: 'Configure SDK',
            description: 'Initialize the SDK with your API key'
        },
        {
            icon: <BookIcon />,
            title: 'Read Documentation',
            description: 'Check our documentation for advanced configuration options'
        }
    ];

    return (
        <Box maxWidth={800} mx="auto" mt={4} p={3}>
            <Paper elevation={3} sx={{ p: 4 }}>
                <Box display="flex" alignItems="center" mb={3}>
                    <CheckCircleIcon color="success" sx={{ fontSize: 40, mr: 2 }} />
                    <Typography variant="h4">
                        Account Created Successfully!
                    </Typography>
                </Box>

                <Alert severity="success" sx={{ mb: 4 }}>
                    Your account has been created and is ready to use.
                </Alert>

                <Typography variant="h6" gutterBottom>
                    Your API Key
                </Typography>
                <Box sx={{ mb: 4 }}>
                    <TextField
                        fullWidth
                        value={apiKey}
                        InputProps={{
                            readOnly: true,
                            endAdornment: (
                                <Button
                                    startIcon={<ContentCopyIcon />}
                                    onClick={handleCopyApiKey}
                                    variant="contained"
                                    size="small"
                                >
                                    {copied ? 'Copied!' : 'Copy'}
                                </Button>
                            ),
                        }}
                    />
                    <Typography variant="caption" color="text.secondary">
                        Keep this API key safe! You'll need it to authenticate your SDK.
                    </Typography>
                </Box>

                <Divider sx={{ my: 4 }} />

                <Typography variant="h6" gutterBottom>
                    Next Steps
                </Typography>
                <List>
                    {nextSteps.map((step, index) => (
                        <ListItem key={index}>
                            <ListItemIcon>
                                {step.icon}
                            </ListItemIcon>
                            <ListItemText
                                primary={step.title}
                                secondary={step.description}
                            />
                        </ListItem>
                    ))}
                </List>

                <Box sx={{ mt: 4 }}>
                    <Button
                        variant="contained"
                        color="primary"
                        href="/docs/quickstart"
                        sx={{ mr: 2 }}
                    >
                        View Documentation
                    </Button>
                    <Button
                        variant="outlined"
                        href="/dashboard"
                    >
                        Go to Dashboard
                    </Button>
                </Box>
            </Paper>
        </Box>
    );
}; 