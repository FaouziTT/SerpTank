# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SerpTank is a comprehensive SEO Decision Superiority Engine (DSE) built with a FastAPI backend and Next.js frontend. It provides advanced SEO analysis, SERP monitoring, content optimization, and competitive intelligence tools for digital marketers and SEO professionals.

## Architecture

### Backend (Python/FastAPI)
- **Main Application**: `backend/app/main.py` - FastAPI app with comprehensive middleware stack
- **Database**: PostgreSQL + TimescaleDB for time-series data + Redis for caching/sessions
- **Authentication**: Dual authentication system (JWT tokens + secure httpOnly cookies)
- **Task Queue**: Celery with Redis broker for background processing
- **Vector Database**: Weaviate for AI-powered content analysis
- **API Structure**: RESTful API with versioning (`/api/v1/`)

### Frontend (Next.js/React)
- **Framework**: Next.js 15 with React 19
- **UI Components**: Radix UI with custom component library
- **State Management**: Zustand for client state, TanStack Query for server state
- **Styling**: Tailwind CSS with custom design system
- **Authentication**: Secure cookie-based session management

### Key Services
- **Multi-tenancy**: Organization-scoped data isolation (`app/services/multi_tenancy_service.py`)
- **SEO Analysis**: Comprehensive on-page and technical SEO analysis
- **SERP Monitoring**: Real-time search result tracking and analysis  
- **Content Intelligence**: AI-powered content optimization recommendations
- **Social Media Integration**: Cross-platform social media monitoring
- **Knowledge Engine**: Semantic search and content relationships

## Development Commands

### Frontend (from `frontend/` directory)
```bash
# Development
npm run dev              # Start development server (port 3000)
npm run build           # Build for production
npm run start           # Start production server
npm run lint            # ESLint checking
npm run type-check      # TypeScript type checking
npm run format          # Prettier formatting

# Testing
npm run test            # Run Vitest unit tests
npm run test:ui         # Run tests with UI
npm run test:run        # Run tests once (CI mode)
npm run e2e             # Run Playwright e2e tests
npm run e2e:ui          # Run e2e tests with UI
npm run e2e:debug       # Debug e2e tests
```

### Backend (from `backend/` directory)
```bash
# Development (requires Python dependencies from requirements.txt)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000    # Development server
python -m pytest                                             # Run tests
python -m pytest --cov=app                                  # Run tests with coverage
black app/ --check                                          # Check code formatting
black app/                                                  # Format code
flake8 app/                                                 # Lint code
mypy app/                                                   # Type checking

# Database
alembic upgrade head    # Apply database migrations
alembic revision --autogenerate -m "description"  # Generate migration

# Celery
celery -A app.worker.celery worker --loglevel=info         # Start worker
celery -A app.worker.celery flower --port=5555             # Start Flower monitoring
```

### Docker Development
```bash
# Full stack
docker-compose up -d            # Start all services
docker-compose down             # Stop all services
docker-compose logs -f backend  # View backend logs
docker-compose logs -f frontend # View frontend logs

# Individual services
docker-compose up backend       # Start backend only
docker-compose up frontend      # Start frontend only
```

## Security Implementation

### Authentication Architecture
- **Secure Sessions**: httpOnly cookies with CSRF protection (`app/auth/core/session_security.py`)
- **Multi-tenancy**: Organization-scoped access control (`app/services/multi_tenancy_service.py`)
- **Rate Limiting**: Progressive rate limiting for security endpoints (`app/core/enhanced_rate_limiting.py`)
- **CSRF Protection**: Double-submit cookie pattern with middleware exemptions

### Key Security Features
- Session-based auth eliminates localStorage JWT vulnerabilities
- Tenant enforcement prevents cross-organization data access
- Rate limiting protects against brute force and DoS attacks
- Comprehensive input validation and sanitization

## Database Schema

### Core Models
- **Organizations**: Multi-tenant structure (`app/models/organization.py`)
- **Projects**: SEO project management (`app/models/project.py`)
- **Domains**: Website domain tracking (`app/models/domain.py`)
- **Content**: Content analysis and optimization (`app/models/content.py`)
- **Knowledge**: Semantic content relationships (`app/models/knowledge.py`)

### Time-Series Data (TimescaleDB)
- SERP ranking data over time
- Performance metrics and analytics
- User activity and engagement tracking

## API Integration

### External Services
- **Google APIs**: Search Console, Analytics, PageSpeed Insights
- **OpenAI**: Content analysis and optimization suggestions
- **Social Media APIs**: Twitter, Facebook, LinkedIn monitoring
- **SerpAPI**: SERP data collection and analysis

### Rate Limiting Strategy
- Authentication endpoints: 5/min, 15/hour, 30/day
- Data export: 10/hour, 50/day
- General API: 60 requests/min
- Bulk operations: 30/min, 300/hour

## Testing Strategy

### Backend Testing
- **Unit Tests**: pytest with coverage reporting
- **Integration Tests**: Database and external API testing
- **Security Tests**: Authentication and authorization testing

### Frontend Testing
- **Unit Tests**: Vitest for component and utility testing
- **E2E Tests**: Playwright for user flow testing
- **Visual Testing**: Component story testing

## Development Guidelines

### Code Organization
- Follow established patterns in existing modules
- Use dependency injection for services and external integrations
- Implement proper error handling with custom exceptions
- Follow security best practices for authentication and data access

### Database Operations
- Always use tenant-scoped queries for multi-tenant data
- Use proper migrations for schema changes
- Implement caching for expensive queries
- Use TimescaleDB for time-series data storage

### API Development
- Follow RESTful conventions with proper HTTP status codes
- Implement rate limiting on all endpoints
- Use proper input validation and sanitization
- Include comprehensive error responses with error codes

## Environment Configuration

### Required Environment Variables
- Database: `POSTGRES_*`, Redis: `REDIS_*`
- Authentication: `SECRET_KEY`, `ALGORITHM`
- External APIs: `OPENAI_API_KEY`, `SERPAPI_KEY`, etc.
- CORS: `CORS_ORIGINS`, Security: `ALLOWED_HOSTS`

### Development vs Production
- Development: Docker Compose with hot reload
- Production: Separate container orchestration with SSL/TLS
- Environment-specific configurations in `.env` files

## Deployment Architecture

### Services
- **Backend**: FastAPI with Uvicorn ASGI server
- **Frontend**: Next.js with server-side rendering
- **Databases**: PostgreSQL + TimescaleDB + Redis cluster
- **Task Processing**: Celery workers with Flower monitoring
- **Vector Search**: Weaviate for semantic search capabilities

### Monitoring
- Performance metrics via `/metrics` endpoint
- Structured logging with correlation IDs
- Cache warming and performance optimization
- Health checks for all services