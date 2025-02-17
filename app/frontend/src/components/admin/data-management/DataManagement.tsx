import React, { useState } from 'react';
import {
    Box,
    Tabs,
    Tab,
    Paper
} from '@mui/material';
import { TransformationRulesManager } from './TransformationRulesManager';
import { MaterializedViewManager } from './MaterializedViewManager';
import { DataSinkManager } from './DataSinkManager';
import { RetentionPolicyManager } from './RetentionPolicyManager';

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;

    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`data-management-tabpanel-${index}`}
            aria-labelledby={`data-management-tab-${index}`}
            {...other}
        >
            {value === index && (
                <Box sx={{ p: 3 }}>
                    {children}
                </Box>
            )}
        </div>
    );
}

function a11yProps(index: number) {
    return {
        id: `data-management-tab-${index}`,
        'aria-controls': `data-management-tabpanel-${index}`,
    };
}

export const DataManagement: React.FC = () => {
    const [value, setValue] = useState(0);

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setValue(newValue);
    };

    return (
        <Box sx={{ width: '100%' }}>
            <Paper sx={{ borderRadius: '4px 4px 0 0' }}>
                <Tabs
                    value={value}
                    onChange={handleChange}
                    aria-label="data management tabs"
                    sx={{ borderBottom: 1, borderColor: 'divider' }}
                >
                    <Tab label="Transformation Rules" {...a11yProps(0)} />
                    <Tab label="Materialized Views" {...a11yProps(1)} />
                    <Tab label="Data Sinks" {...a11yProps(2)} />
                    <Tab label="Retention Policies" {...a11yProps(3)} />
                </Tabs>
            </Paper>

            <TabPanel value={value} index={0}>
                <TransformationRulesManager />
            </TabPanel>
            <TabPanel value={value} index={1}>
                <MaterializedViewManager />
            </TabPanel>
            <TabPanel value={value} index={2}>
                <DataSinkManager />
            </TabPanel>
            <TabPanel value={value} index={3}>
                <RetentionPolicyManager />
            </TabPanel>
        </Box>
    );
}; 