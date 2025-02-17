/// <reference types="@mui/material" />
/// <reference types="@mui/icons-material" />

import '@mui/material/styles';
import '@mui/material';
import '@mui/icons-material';

declare module '@mui/material/styles' {
    interface Theme {
        palette: {
            mode: string;
            primary: {
                main: string;
                light: string;
                dark: string;
            };
            secondary: {
                main: string;
                light: string;
                dark: string;
            };
            error: {
                main: string;
                light: string;
                dark: string;
            };
            warning: {
                main: string;
                light: string;
                dark: string;
            };
            info: {
                main: string;
                light: string;
                dark: string;
            };
            success: {
                main: string;
                light: string;
                dark: string;
            };
            background: {
                default: string;
                paper: string;
            };
        };
        spacing: (factor: number) => number;
    }
}

declare module '@mui/material' {
    export * from '@mui/material';
    export { createTheme, ThemeProvider } from '@mui/material/styles';
    export * from '@mui/material/AppBar';
    export * from '@mui/material/Box';
    export * from '@mui/material/Button';
    export * from '@mui/material/Card';
    export * from '@mui/material/CardContent';
    export * from '@mui/material/CircularProgress';
    export * from '@mui/material/Dialog';
    export * from '@mui/material/DialogActions';
    export * from '@mui/material/DialogContent';
    export * from '@mui/material/DialogTitle';
    export * from '@mui/material/Drawer';
    export * from '@mui/material/IconButton';
    export * from '@mui/material/List';
    export * from '@mui/material/ListItem';
    export * from '@mui/material/ListItemIcon';
    export * from '@mui/material/ListItemText';
    export * from '@mui/material/TextField';
    export * from '@mui/material/Toolbar';
    export * from '@mui/material/Typography';
    export * from '@mui/material/Alert';
    export * from '@mui/material/Tooltip';
    export * from '@mui/material/Table';
    export * from '@mui/material/TableBody';
    export * from '@mui/material/TableCell';
    export * from '@mui/material/TableContainer';
    export * from '@mui/material/TableHead';
    export * from '@mui/material/TableRow';
    export * from '@mui/material/Chip';
    export * from '@mui/material/Paper';
    export * from '@mui/material/Select';
    export * from '@mui/material/MenuItem';
    export * from '@mui/material/FormControl';
    export * from '@mui/material/InputLabel';
}

declare module '@mui/icons-material' {
    export * from '@mui/icons-material';
    export { 
        Menu,
        ChevronLeft,
        Dashboard,
        People,
        Business,
        Storage,
        AccountBalance,
        Analytics,
        Settings,
        Logout,
        Add,
        Edit,
        Delete,
        Key,
        CheckCircle,
        ContentCopy,
        Code,
        Book,
        Error,
        ExitToApp,
        Notifications
    } from '@mui/icons-material';
}

declare module '@emotion/react' {
    export * from '@emotion/react';
    export interface Theme {
        palette: {
            primary: {
                main: string;
                light: string;
                dark: string;
            };
            secondary: {
                main: string;
                light: string;
                dark: string;
            };
            error: {
                main: string;
            };
            background: {
                default: string;
                paper: string;
            };
        };
        spacing: (factor: number) => number;
    }
} 