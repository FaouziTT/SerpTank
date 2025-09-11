"""
Main API router for the Voltex DSE application.

This module defines the main API router and includes all sub-routers
for the different pillars and components of the application.
"""
from fastapi import APIRouter

from app.api.api_v1.endpoints import (
    diagnostic,
    profitability,
    market_simulation,
    content_workflow,
    sge_readiness,
    knowledge_engine,
    users,
    settings,
    project_settings,
    # billing,  # Commented out - requires stripe package
    serp_analysis,
    search_console,
    google_trends,
    youtube_analysis,
    social_media,
    oauth,
    domain_verification,
    subscriptions,
    organizations,
    projects,
    sites,
    csrf,
    cache,
    performance,
    health,
    websocket,
    password_reset,
    background_tasks,
    files,
)

api_router = APIRouter()

# User management (Auth is now in app.auth module)
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Password Reset
api_router.include_router(password_reset.router, prefix="/auth", tags=["Authentication"])

# CSRF Protection
api_router.include_router(csrf.router, prefix="/csrf", tags=["CSRF Protection"])

# Cache Management
api_router.include_router(cache.router, prefix="/cache", tags=["Cache Management"])

# Performance Monitoring
api_router.include_router(performance.router, prefix="/performance", tags=["Performance Monitoring"])

# Health Monitoring
api_router.include_router(health.router, prefix="/health", tags=["Health Monitoring"])

# OAuth integrations
api_router.include_router(oauth.router, prefix="/oauth", tags=["OAuth"])

# Subscriptions and billing
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])

# Organizations and multi-tenancy
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])

# Domain verification
api_router.include_router(domain_verification.router, prefix="/domains", tags=["Domain Verification"])

# Pillar 1: The Diagnostic & Monitoring Core
api_router.include_router(
    diagnostic.router, 
    prefix="/diagnostic", 
    tags=["Diagnostic & Monitoring"]
)

# Pillar 2: The Unified Profitability Engine
api_router.include_router(
    profitability.router, 
    prefix="/profitability", 
    tags=["Profitability Engine"]
)

# Pillar 3: The Market Simulation Engine
api_router.include_router(
    market_simulation.router, 
    prefix="/market-simulation", 
    tags=["Market Simulation"]
)

# Pillar 4: The Content Velocity Workflow
api_router.include_router(
    content_workflow.router, 
    prefix="/content-workflow", 
    tags=["Content Workflow"]
)

# Pillar 5: The Generative Experience Readiness Engine
api_router.include_router(
    sge_readiness.router, 
    prefix="/sge-readiness", 
    tags=["SGE Readiness"]
)

# Pillar 6: The Institutional Knowledge Engine
api_router.include_router(
    knowledge_engine.router, 
    prefix="/knowledge-engine", 
    tags=["Knowledge Engine"]
)

# Settings and User Management
api_router.include_router(
    settings.router,
    prefix="/settings",
    tags=["Settings"]
)

# Project-specific settings (social media, webhooks, domain verification)
api_router.include_router(
    project_settings.router,
    prefix="/project-settings",
    tags=["Project Settings"]
)

# Stripe billing integration
# Commented out - requires stripe package
# api_router.include_router(
#     billing.router,
#     prefix="/billing",
#     tags=["Billing"]
# )

# SERP Analysis and Keyword Research
api_router.include_router(
    serp_analysis.router,
    prefix="/serp-analysis", 
    tags=["SERP Analysis"]
)

# Google Search Console Integration
api_router.include_router(
    search_console.router,
    prefix="/search-console", 
    tags=["Google Search Console"]
)

# Google Trends Integration
api_router.include_router(
    google_trends.router,
    prefix="/google-trends",
    tags=["Google Trends"]
)

# YouTube Data Analysis
api_router.include_router(
    youtube_analysis.router,
    prefix="/youtube",
    tags=["YouTube Analysis"]
)

# Social Media Integration
api_router.include_router(
    social_media.router,
    prefix="/social-media",
    tags=["Social Media"]
)

api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])

# Sites API (interface to projects for frontend compatibility)
api_router.include_router(sites.router, prefix="/sites", tags=["Sites"])

# WebSocket endpoints for real-time updates
api_router.include_router(websocket.router, prefix="/websocket", tags=["WebSocket"])

# Background Task Management
api_router.include_router(background_tasks.router, prefix="/background-tasks", tags=["Background Tasks"])

# File Upload/Download Management
api_router.include_router(files.router, prefix="/files", tags=["File Management"])