# Voltex Frontend

A modern, production-ready React/Next.js frontend for the Voltex SEO Decision Superiority Engine.

## Features

- 🔐 **Authentication**: JWT-based auth with Google OAuth support
- 🏢 **Multi-tenancy**: Organization and project management
- 📊 **Six Core Pillars**:
  - Diagnostic & Monitoring
  - Profitability Engine
  - Market Simulation
  - Content Workflow
  - SGE Readiness
  - Knowledge Engine
- 🔄 **Real-time Updates**: WebSocket integration
- 📱 **Responsive Design**: Mobile-first approach
- 🎨 **Modern UI**: Built with Tailwind CSS and Radix UI
- 🚀 **Performance**: Next.js with SSR/SSG capabilities
- 🔒 **Security**: CSRF protection, secure token management

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI + custom components
- **State Management**: Zustand + React Query
- **API Client**: Axios with interceptors
- **Forms**: React Hook Form + Zod validation
- **Charts**: Recharts
- **Real-time**: Socket.io-client

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running at http://localhost:8000

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. Copy environment variables:
```bash
cp .env.example .env.local
```

4. Update `.env.local` with your configuration:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME=Voltex
```

### Development

Run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm run start
```

## Project Structure

```
frontend/
├── app/                   # Next.js app directory
│   ├── login/            # Authentication pages
│   ├── register/
│   ├── dashboard/        # Main dashboard
│   ├── diagnostic/       # Site health analysis
│   ├── profitability/    # ROI tracking
│   ├── market-simulation/# Competitive analysis
│   ├── content-workflow/ # Content management
│   ├── sge-readiness/    # AI search optimization
│   ├── knowledge-engine/ # Knowledge base
│   └── ...
├── components/           # Reusable components
│   ├── ui/              # Base UI components
│   └── layout/          # Layout components
├── lib/                 # Utilities and helpers
│   ├── api-client.ts    # API configuration
│   ├── auth-context.tsx # Authentication context
│   └── utils.ts         # Common utilities
├── types/               # TypeScript types
│   └── api.ts          # API response types
└── public/             # Static assets
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking
- `npm run format` - Format code with Prettier

## Authentication Flow

1. User logs in with credentials or Google OAuth
2. Backend returns JWT tokens (access + refresh)
3. Tokens are stored in localStorage
4. API client automatically includes tokens in requests
5. Expired tokens are refreshed automatically
6. Failed auth redirects to login page

## API Integration

The frontend uses a centralized API client (`lib/api-client.ts`) with:
- Automatic token management
- Request/response interceptors
- CSRF protection
- Error handling
- Retry logic for failed requests

## State Management

- **Global State**: Zustand for client-side state
- **Server State**: React Query for API data
- **Auth State**: React Context for authentication
- **Form State**: React Hook Form for forms

## Contributing

1. Follow the existing code style
2. Use TypeScript for all new code
3. Add proper types for API responses
4. Test your changes thoroughly
5. Update documentation as needed

## Security Considerations

- All API calls use HTTPS in production
- JWT tokens are stored securely
- CSRF tokens are included in requests
- Sensitive data is never logged
- Input validation on all forms
- XSS protection via React
- Content Security Policy headers

## Performance Optimizations

- Code splitting with dynamic imports
- Image optimization with Next.js Image
- API response caching with React Query
- Debounced search inputs
- Virtual scrolling for large lists
- Progressive enhancement

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome)

## License

Proprietary - All rights reserved