import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
    Box,
    Drawer,
    AppBar,
    Toolbar,
    List,
    Typography,
    Divider,
    IconButton,
    ListItem,
    ListItemIcon,
    ListItemText,
    useTheme,
    Tooltip
} from '@mui/material';
import {
    Menu as MenuIcon,
    ChevronLeft as ChevronLeftIcon,
    Dashboard as DashboardIcon,
    People as PeopleIcon,
    Business as BusinessIcon,
    Storage as StorageIcon,
    AccountBalance as BillingIcon,
    Analytics as AnalyticsIcon,
    Settings as SettingsIcon,
    Logout as LogoutIcon
} from '@mui/icons-material';

const drawerWidth = 240;

export const AdminLayout: React.FC = () => {
    const [open, setOpen] = useState(true);
    const theme = useTheme();
    const navigate = useNavigate();
    const location = useLocation();

    const menuItems = [
        { path: '/admin', label: 'System Overview', icon: <DashboardIcon /> },
        { path: '/admin/users', label: 'Users', icon: <PeopleIcon /> },
        { path: '/admin/organizations', label: 'Organizations', icon: <BusinessIcon /> },
        { path: '/admin/data-management', label: 'Data Management', icon: <StorageIcon /> },
        { path: '/admin/pipeline', label: 'Data Pipeline', icon: <AnalyticsIcon /> },
        { path: '/admin/billing', label: 'Billing', icon: <BillingIcon /> }
    ];

    const handleDrawerToggle = () => {
        setOpen(!open);
    };

    const handleNavigation = (path: string) => {
        navigate(path);
    };

    const handleLogout = () => {
        // Implement logout logic
        navigate('/login');
    };

    return (
        <Box sx={{ display: 'flex' }}>
            <AppBar
                position="fixed"
                sx={{
                    zIndex: theme.zIndex.drawer + 1,
                    transition: theme.transitions.create(['width', 'margin'], {
                        easing: theme.transitions.easing.sharp,
                        duration: theme.transitions.duration.leavingScreen,
                    }),
                    ...(open && {
                        marginLeft: drawerWidth,
                        width: `calc(100% - ${drawerWidth}px)`,
                        transition: theme.transitions.create(['width', 'margin'], {
                            easing: theme.transitions.easing.sharp,
                            duration: theme.transitions.duration.enteringScreen,
                        }),
                    }),
                }}
            >
                <Toolbar>
                    <IconButton
                        color="inherit"
                        aria-label="toggle drawer"
                        onClick={handleDrawerToggle}
                        edge="start"
                        sx={{ marginRight: 2 }}
                    >
                        {open ? <ChevronLeftIcon /> : <MenuIcon />}
                    </IconButton>
                    <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
                        theData.io Admin
                    </Typography>
                    <Tooltip title="Settings">
                        <IconButton color="inherit">
                            <SettingsIcon />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Logout">
                        <IconButton color="inherit" onClick={handleLogout}>
                            <LogoutIcon />
                        </IconButton>
                    </Tooltip>
                </Toolbar>
            </AppBar>
            <Drawer
                variant="permanent"
                open={open}
                sx={{
                    width: drawerWidth,
                    flexShrink: 0,
                    '& .MuiDrawer-paper': {
                        width: drawerWidth,
                        boxSizing: 'border-box',
                        whiteSpace: 'nowrap',
                        transition: theme.transitions.create('width', {
                            easing: theme.transitions.easing.sharp,
                            duration: theme.transitions.duration.enteringScreen,
                        }),
                        ...(!open && {
                            width: theme.spacing(7),
                            overflowX: 'hidden',
                            transition: theme.transitions.create('width', {
                                easing: theme.transitions.easing.sharp,
                                duration: theme.transitions.duration.leavingScreen,
                            }),
                        }),
                    },
                }}
            >
                <Toolbar />
                <List>
                    {menuItems.map((item) => (
                        <ListItem
                            button
                            key={item.path}
                            onClick={() => handleNavigation(item.path)}
                            selected={location.pathname === item.path}
                        >
                            <ListItemIcon>
                                {item.icon}
                            </ListItemIcon>
                            <ListItemText primary={item.label} />
                        </ListItem>
                    ))}
                </List>
                <Divider />
            </Drawer>
            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    p: 3,
                    width: { sm: `calc(100% - ${drawerWidth}px)` },
                    marginTop: '64px'
                }}
            >
                <Outlet />
            </Box>
        </Box>
    );
}; 