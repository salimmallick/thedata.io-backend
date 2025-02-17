import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

export const LoadingScreen: React.FC = () => {
    return (
        <Box
            display="flex"
            flexDirection="column"
            justifyContent="center"
            alignItems="center"
            minHeight="100vh"
            bgcolor="#f5f5f5"
        >
            <CircularProgress size={60} />
            <Typography
                variant="h6"
                color="textSecondary"
                sx={{ mt: 2 }}
            >
                Loading...
            </Typography>
        </Box>
    );
}; 