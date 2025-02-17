import React from 'react';
import { TextField } from '@mui/material';

interface JsonEditorProps {
    value: Record<string, any>;
    onChange: (value: Record<string, any>) => void;
}

export const JsonEditor: React.FC<JsonEditorProps> = ({ value, onChange }) => {
    const [error, setError] = React.useState<string | null>(null);
    const [text, setText] = React.useState<string>('');

    React.useEffect(() => {
        setText(JSON.stringify(value, null, 2));
    }, [value]);

    const handleChange = (newText: string) => {
        setText(newText);
        try {
            const parsed = JSON.parse(newText);
            onChange(parsed);
            setError(null);
        } catch (err) {
            setError('Invalid JSON format');
        }
    };

    return (
        <TextField
            multiline
            rows={8}
            fullWidth
            value={text}
            onChange={(e) => handleChange(e.target.value)}
            error={!!error}
            helperText={error}
            placeholder="Enter JSON configuration"
            sx={{
                fontFamily: 'monospace',
                '& .MuiInputBase-input': {
                    fontFamily: 'monospace'
                }
            }}
        />
    );
}; 