# theData.io Admin Portal

The admin portal for theData.io platform provides a comprehensive interface for managing organizations, users, data pipelines, and system monitoring.

## Features

- **User Management**: Create, edit, and manage user accounts and permissions
- **Organization Management**: Manage customer organizations and their settings
- **Billing Dashboard**: Monitor subscription status and revenue
- **Data Pipeline Management**: Monitor and control data processing pipelines
- **System Monitoring**: Real-time system metrics and health monitoring

## Getting Started

### Prerequisites

- Node.js (v16 or later)
- npm or yarn
- Access to theData.io backend services

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/thedata-admin.git
cd thedata-admin
```

2. Install dependencies:
```bash
npm install
```

3. Create environment configuration:
```bash
cp .env.example .env.local
```
Edit `.env.local` with your configuration values.

4. Start the development server:
```bash
npm start
```

### Building for Production

```bash
npm run build
```

## Testing

Run the test suite:
```bash
npm test
```

Run tests with coverage:
```bash
npm run test:coverage
```

## Code Quality

Run linting:
```bash
npm run lint
```

Fix linting issues:
```bash
npm run lint:fix
```

## Project Structure

```
src/
├── components/          # React components
│   ├── admin/          # Admin-specific components
│   ├── auth/           # Authentication components
│   └── common/         # Shared components
├── hooks/              # Custom React hooks
├── services/           # API services
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
└── App.tsx            # Main application component
```

## Key Technologies

- React 18
- TypeScript
- Material-UI
- React Router
- Axios
- Recharts
- Jest & React Testing Library
- Sentry for error tracking

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## Error Tracking

The application uses Sentry for error tracking in production. Configure your Sentry DSN in the environment variables to enable error tracking.

## Performance Monitoring

Web Vitals are tracked and can be monitored through the console or sent to an analytics endpoint. Configure the reporting endpoint in `reportWebVitals.ts`.

## Security

- All API requests require authentication
- Role-based access control is implemented
- Sensitive data is never stored in local storage
- API keys are handled securely

## License

Copyright © 2024 theData.io. All rights reserved. 