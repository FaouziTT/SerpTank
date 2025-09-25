# --- START OF CORRECTED FILE projects.py ---

from fastapi import APIRouter, Depends, HTTPException, status, Path, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from typing import List, Dict, Any, Optional
import logging
import asyncio

from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.services.multi_tenancy_service import TenantContext
from app.core.tenant_dependencies import (
    validate_project_access_dependency,
    get_current_tenant_context_dependency,
    get_tenant_service
)
from app.core.rate_limit_dependencies import (
    rate_limit_general_api,
    rate_limit_data_intensive
)
from app.schemas.project import ProjectCreate, ProjectOut, ProjectTeamMemberCreate, ProjectTeamMemberUpdate, ProjectTeamMemberOut, ProjectSettingsUpdate
from app.models.project_team_member import ProjectTeamMember
from app.services.core_web_vitals import cwv_service
from app.services.crawler import crawler_service
from app.services.google_analytics4 import ga4_service
from app.models.crawl import Site, Crawl
from app.services.background_task_service import BackgroundTaskService
from app.models.background_task import TaskType
from datetime import datetime, timezone
from app.core.pagination import PageParams, get_pagination_params, paginate
from app.core.db_optimization import QueryOptimizer, optimize_for_read
from app.core.structured_logging import get_logger, log_execution_time, log_business_event
from app.core.audit import audit_action, AuditActions, ResourceTypes

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)

router = APIRouter(
    tags=["projects"]
)

@router.get("/", response_model=Dict[str, Any])
@optimize_for_read
async def list_projects(
    organization_id: Optional[str] = None,
    pagination: PageParams = Depends(get_pagination_params),
    include_team: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
    _: None = Depends(rate_limit_general_api)  # 60 requests per minute
):
    """
    List all projects for the current user with pagination.
    
    Args:
        organization_id: Optional organization ID to filter by
        pagination: Pagination parameters (page, page_size)
        include_team: Whether to include team members in response
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Paginated list of projects
    """
    # Get tenant context for proper scoping
    from app.services.multi_tenancy_service import MultiTenancyService
    tenant_service = MultiTenancyService(db)
    tenant_context = await tenant_service.get_user_tenant_context(current_user.id)
    
    if not tenant_context:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not belong to any organization"
        )
    
    # Build tenant-scoped query
    if organization_id:
        # Validate access to the specific organization
        if not tenant_context.can_access_organization(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization"
            )
        query = tenant_service.add_organization_filter(
            select(Project).where(Project.organization_id == organization_id),
            Project,
            tenant_context
        )
    else:
        # Return projects scoped to user's organization
        query = tenant_service.add_organization_filter(
            select(Project),
            Project,
            tenant_context
        )
    
    # Add eager loading if requested
    if include_team:
        query = query.options(selectinload(Project.team_members))
    
    # Order by created_at using index
    query = query.order_by(Project.created_at.desc())
    
    return await paginate(
        db=db,
        query=query,
        page_params=pagination,
        response_model=ProjectOut
    )

@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
@audit_action(
    action=AuditActions.CREATE,
    resource_type=ResourceTypes.PROJECT,
    get_resource_id=lambda result: result.id,
    get_new_value=lambda result: {"name": result.name, "url": result.url, "organization_id": result.organization_id}
)
@log_execution_time(logger)
async def create_project(
    project_in: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
    _: None = Depends(rate_limit_data_intensive)  # 10 requests per minute (project creation is resource intensive)
):
    # MANDATORY: Validate Google OAuth connections for project creation
    from app.services.oauth_validation_service import get_oauth_validation_service
    oauth_validator = get_oauth_validation_service(db)
    
    # Validate Google Search Console connection (MANDATORY for projects)
    search_console_validation = await oauth_validator.validate_google_search_console_connection(current_user.id)
    if not search_console_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Google Search Console connection required",
                "message": search_console_validation["error"],
                "action_required": search_console_validation["action_required"],
                "oauth_url": search_console_validation.get("oauth_url", ""),
                "help": "Projects require Google Search Console access to analyze website performance. Please connect your Google account with Search Console permissions."
            }
        )
    
    # Validate Google Analytics connection (MANDATORY for projects)
    analytics_validation = await oauth_validator.validate_google_analytics_connection(current_user.id)
    if not analytics_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Google Analytics connection required",
                "message": analytics_validation["error"],
                "action_required": analytics_validation["action_required"],
                "oauth_url": analytics_validation.get("oauth_url", ""),
                "help": "Projects require Google Analytics access to track website traffic and performance. Please connect your Google account with Analytics permissions."
            }
        )
    
    logger.info(f"User {current_user.id} passed OAuth validation for project creation")
    
    # Verify user has access to the organization using tenant service
    from app.services.multi_tenancy_service import MultiTenancyService
    tenant_service = MultiTenancyService(db)
    
    try:
        tenant_context = await tenant_service.get_user_tenant_context(current_user.id)
        if not tenant_context:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not belong to any organization"
            )
        
        # Validate organization access
        await tenant_service.validate_organization_access(
            tenant_context, project_in.organization_id
        )
    except Exception as e:
        logger.error(f"Tenant validation failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to create projects in this organization"
        )
    
    # Check for duplicates using tenant-scoped queries
    url_query = tenant_service.add_organization_filter(
        select(Project).where(Project.url == str(project_in.url)),
        Project,
        tenant_context
    )
    existing_project_check = await db.execute(url_query)
    existing_project = existing_project_check.scalar_one_or_none()
    
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A project with URL '{project_in.url}' already exists in this organization"
        )
    
    # Check for duplicate name using tenant-scoped query
    name_query = tenant_service.add_organization_filter(
        select(Project).where(Project.name.ilike(project_in.name.strip())),
        Project,
        tenant_context
    )
    existing_name_check = await db.execute(name_query)
    existing_name = existing_name_check.scalar_one_or_none()
    
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A project with name '{project_in.name}' already exists in this organization"
        )
    
    project = Project(
        user_id=current_user.id,
        organization_id=project_in.organization_id,
        name=project_in.name,
        url=str(project_in.url),
        description=project_in.description,
        ga4_property_id=project_in.ga4_property_id,
        ga4_measurement_id=project_in.ga4_measurement_id,
        ga4_configured=bool(project_in.ga4_property_id),
        analytics_enabled=project_in.analytics_enabled,
        profitability_tracking=project_in.profitability_tracking,
    )
    
    site = Site(
        user_id=current_user.id,
        url=str(project_in.url),
        name=project_in.name,
        status="active"
    )
    
    db.add(project)
    db.add(site)
    await db.commit()
    await db.refresh(project)
    await db.refresh(site)
    
    # Log business event
    log_business_event(
        logger,
        "project_created",
        f"New project '{project.name}' created for {project.url}",
        project_id=project.id,
        user_id=current_user.id,
        project_name=project.name,
        project_url=project.url
    )
    
    logger.info(f"Starting automatic analysis for new project: {project.name} ({project.url})")
    
    # Initialize setup status
    import json
    from app.schemas.project import SetupTaskStatus
    setup_status = {
        "crawl": {
            "status": SetupTaskStatus.NOT_STARTED if project_in.run_initial_crawl else SetupTaskStatus.SKIPPED,
            "progress": 0,
            "message": None,
            "error": None
        },
        "core_web_vitals": {
            "status": SetupTaskStatus.NOT_STARTED if project_in.run_initial_core_web_vitals else SetupTaskStatus.SKIPPED,
            "progress": 0,
            "message": None,
            "error": None
        },
        "search_console": {
            "status": SetupTaskStatus.NOT_STARTED,
            "progress": 0,
            "message": "Connect Google Search Console to see search performance data",
            "error": None
        },
        "google_analytics": {
            "status": SetupTaskStatus.NOT_STARTED,
            "progress": 0,
            "message": "Connect Google Analytics to see traffic data",
            "error": None
        }
    }
    
    # Update project with initial setup status
    project.setup_status = json.dumps(setup_status)
    db.add(project)
    await db.commit()
    
    # Initialize background task service
    task_service = BackgroundTaskService()
    
    # Only run Core Web Vitals analysis if requested
    if project_in.run_initial_core_web_vitals and cwv_service.is_configured():
        # Create task record for CWV analysis
        from app.models.background_task import TaskType
        cwv_task_id = await task_service.create_task(
            user_id=current_user.id,
            task_type=TaskType.CORE_WEB_VITALS_ANALYSIS,
            task_name="Core Web Vitals Analysis",
            description=f"Analyzing Core Web Vitals for {project_in.url}",
            site_id=site.id,
            parameters={"url": str(project_in.url), "project_id": project.id}
        )
        background_tasks.add_task(trigger_core_web_vitals_analysis, site.id, str(project_in.url), current_user.id, cwv_task_id, db)
        logger.info(f"Queued Core Web Vitals analysis with task_id: {cwv_task_id}")
        
        # Update setup status to in_progress
        setup_status["core_web_vitals"]["status"] = SetupTaskStatus.IN_PROGRESS
        setup_status["core_web_vitals"]["message"] = "Analyzing Core Web Vitals..."
        project.setup_status = json.dumps(setup_status)
        await db.commit()
    
    # Debug logging for crawl condition
    logger.info(f"Project creation - run_initial_crawl: {project_in.run_initial_crawl}")
    logger.info(f"Project input data: {project_in.dict()}")
    
    # Only run website crawl if requested
    if project_in.run_initial_crawl:
        # Create task record for website crawl
        crawl_task_id = await task_service.create_task(
            user_id=current_user.id,
            task_type=TaskType.WEBSITE_CRAWL,
            task_name="Website Crawl",
            description=f"Crawling website {project_in.url}",
            site_id=site.id,
            parameters={"url": str(project_in.url), "project_id": project.id}
        )
        background_tasks.add_task(trigger_website_crawl, str(project_in.url), current_user.id, project.id, crawl_task_id, db)
        logger.info(f"Queued website crawl with task_id: {crawl_task_id}")
        
        # Update setup status to in_progress
        setup_status["crawl"]["status"] = SetupTaskStatus.IN_PROGRESS
        setup_status["crawl"]["message"] = "Crawling website structure..."
        project.setup_status = json.dumps(setup_status)
        await db.commit()
    else:
        logger.warning(f"Website crawl SKIPPED for project: {project.name} (run_initial_crawl={project_in.run_initial_crawl})")
    
    # Check if user has Google OAuth tokens for GA4 analysis
    from app.services.oauth_service import oauth_service
    if await oauth_service.get_valid_access_token(db, current_user.id):
        # Only create GA4 task if user has OAuth tokens
        if project.ga4_configured:
            # Create task record for GA4 analysis
            ga4_task_id = await task_service.create_task(
                user_id=current_user.id,
                task_type=TaskType.REVENUE_ANALYSIS,
                task_name="Revenue Analysis",
                description=f"Analyzing revenue data for {project_in.url}",
                site_id=site.id,
                parameters={"url": str(project_in.url), "project_id": project.id}
            )
            background_tasks.add_task(trigger_revenue_analysis, current_user.id, str(project_in.url), ga4_task_id, db)
            logger.info(f"Queued revenue attribution analysis with task_id: {ga4_task_id}")
        else:
            logger.info("GA4 not configured for project, skipping revenue analysis")
    else:
        logger.info("User has no Google OAuth tokens, skipping GA4 analysis")
    
    return project


async def trigger_core_web_vitals_analysis(site_id: int, url: str, user_id: int, task_id: str, db: AsyncSession):
    """Background task to analyze Core Web Vitals for new project."""
    task_service = BackgroundTaskService()
    project = None  # Initialize project variable
    try:
        logger.info(f"Starting Core Web Vitals analysis for {url}")
        
        # Update task to running
        await task_service.update_progress(
            task_id=task_id,
            progress=10,
            status_message="Fetching data from Google PageSpeed API..."
        )
        
        # Get project directly using site_id (which is actually project_id)
        project = await db.get(Project, site_id)
        
        # Update project setup status
        import json
        from app.schemas.project import SetupTaskStatus
        if project and project.setup_status:
            setup_status = json.loads(project.setup_status)
            setup_status["core_web_vitals"]["status"] = SetupTaskStatus.IN_PROGRESS
            setup_status["core_web_vitals"]["progress"] = 50
            setup_status["core_web_vitals"]["message"] = "Analyzing Core Web Vitals..."
            project.setup_status = json.dumps(setup_status)
            await db.commit()
        
        # Perform the analysis
        result = await cwv_service.get_latest_cwv_data(site_id, user_id)
        
        # Complete the task
        await task_service.complete_task(
            task_id=task_id,
            result=result
        )
        
        # Update project setup status to completed
        if project and project.setup_status:
            setup_status = json.loads(project.setup_status)
            setup_status["core_web_vitals"]["status"] = SetupTaskStatus.COMPLETED
            setup_status["core_web_vitals"]["progress"] = 100
            setup_status["core_web_vitals"]["message"] = "Core Web Vitals analysis complete"
            project.setup_status = json.dumps(setup_status)
            await db.commit()
        
        logger.info(f"Core Web Vitals analysis completed for {url}")
    except Exception as e:
        logger.error(f"Core Web Vitals analysis failed for {url}: {e}")
        await task_service.fail_task(
            task_id=task_id,
            error_message=str(e)
        )
        
        # Update project setup status to failed
        if project and project.setup_status:
            setup_status = json.loads(project.setup_status)
            setup_status["core_web_vitals"]["status"] = SetupTaskStatus.FAILED
            setup_status["core_web_vitals"]["error"] = str(e)
            setup_status["core_web_vitals"]["message"] = "Analysis failed"
            project.setup_status = json.dumps(setup_status)
            await db.commit()


async def trigger_website_crawl(url: str, user_id: int, project_id: int, task_id: str, db: AsyncSession):
    """Background task to crawl website for new project."""
    task_service = BackgroundTaskService()
    try:
        logger.info(f"Starting website crawl for {url}")
        
        # Update task to running
        await task_service.update_progress(
            task_id=task_id,
            progress=5,
            status_message="Starting website crawl..."
        )
        
        # Update project setup status
        import json
        from app.schemas.project import SetupTaskStatus
        project = await db.get(Project, project_id)
        if project and project.setup_status:
            setup_status = json.loads(project.setup_status)
            setup_status["crawl"]["status"] = SetupTaskStatus.IN_PROGRESS
            setup_status["crawl"]["progress"] = 5
            setup_status["crawl"]["message"] = "Starting website crawl..."
            project.setup_status = json.dumps(setup_status)
            await db.commit()
        
        # Start the crawl
        crawl_id = await crawler_service.start_crawl(
            url=url,
            user_id=user_id,
            max_urls=50,
            respect_robots_txt=True,
            crawl_javascript=True,
            follow_external_links=False
        )
        
        # Monitor crawl progress
        while True:
            crawl_status = await crawler_service.get_crawl_status(crawl_id, user_id)
            
            # Update task progress
            progress = min(95, (crawl_status.urls_crawled / 50) * 100) if crawl_status.urls_crawled else 5
            await task_service.update_progress(
                task_id=task_id,
                progress=int(progress),
                status_message=f"Crawled {crawl_status.urls_crawled} pages..."
            )
            
            # Update project setup status
            if project and project.setup_status:
                setup_status = json.loads(project.setup_status)
                setup_status["crawl"]["progress"] = int(progress)
                setup_status["crawl"]["message"] = f"Crawled {crawl_status.urls_crawled} pages..."
                project.setup_status = json.dumps(setup_status)
                await db.commit()
            
            if crawl_status.status in ["COMPLETED", "FAILED"]:
                break
            
            await asyncio.sleep(2)
        
        if crawl_status.status == "COMPLETED":
            await task_service.complete_task(
                task_id=task_id,
                result={"crawl_id": crawl_id, "urls_crawled": crawl_status.urls_crawled}
            )
            logger.info(f"Website crawl completed for {url}, crawl_id: {crawl_id}")
            
            # Update project setup status to completed
            if project and project.setup_status:
                setup_status = json.loads(project.setup_status)
                setup_status["crawl"]["status"] = SetupTaskStatus.COMPLETED
                setup_status["crawl"]["progress"] = 100
                setup_status["crawl"]["message"] = f"Crawled {crawl_status.urls_crawled} pages successfully"
                project.setup_status = json.dumps(setup_status)
                await db.commit()
        else:
            raise Exception(f"Crawl failed with status: {crawl_status.status}")
        
    except Exception as e:
        logger.error(f"Website crawl failed for {url}: {e}")
        await task_service.fail_task(
            task_id=task_id,
            error_message=str(e)
        )
        
        # Update project setup status to failed
        if project and project.setup_status:
            setup_status = json.loads(project.setup_status)
            setup_status["crawl"]["status"] = SetupTaskStatus.FAILED
            setup_status["crawl"]["error"] = str(e)
            setup_status["crawl"]["message"] = "Crawl failed"
            project.setup_status = json.dumps(setup_status)
            await db.commit()


async def trigger_revenue_analysis(user_id: int, url: str, task_id: str, db: AsyncSession):
    """Background task to set up revenue attribution for new project."""
    task_service = BackgroundTaskService()
    try:
        logger.info(f"Starting revenue attribution analysis for {url}")
        
        # Update task to running
        await task_service.update_progress(
            task_id=task_id,
            progress=10,
            status_message="Checking Google OAuth authorization..."
        )
        
        # Get user's OAuth token
        from app.models.user import User
        from app.services.oauth_service import oauth_service
        
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise Exception("User not found")
        
        # Check if user has Google OAuth tokens
        access_token = await oauth_service.get_valid_access_token(db, user_id)
        
        if not access_token:
            await task_service.fail_task(
                task_id=task_id,
                error_message="Google account not connected. Please connect your Google account to enable Analytics data."
            )
            logger.warning(f"GA4 analysis skipped for {url} - user has no OAuth tokens")
            return
        
        # Update progress
        await task_service.update_progress(
            task_id=task_id,
            progress=30,
            status_message="Fetching revenue data from Google Analytics..."
        )
        
        # Create GA4 service with user's OAuth token
        from app.services.google_analytics4 import GoogleAnalytics4Service
        user_ga4_service = GoogleAnalytics4Service(access_token=access_token)
        
        revenue_data = await user_ga4_service.get_revenue_metrics(
            start_date="30daysAgo",
            end_date="today"
        )
        
        # Complete the task
        await task_service.complete_task(
            task_id=task_id,
            result=revenue_data
        )
        
        logger.info(f"Revenue attribution analysis completed for {url}")
    except Exception as e:
        logger.error(f"Revenue attribution analysis failed for {url}: {e}")
        await task_service.fail_task(
            task_id=task_id,
            error_message=str(e)
        )

@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: int = Path(..., gt=0),
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db)
):
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    
    # The setup_status JSON parsing is now handled by the ProjectOut schema validator
    return project

@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_in: ProjectCreate,
    project_id: int = Path(..., gt=0),
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db)
):
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    
    project.name = project_in.name
    project.url = str(project_in.url)
    project.description = project_in.description
    await db.commit()
    await db.refresh(project)
    return project

@router.get("/{project_id}/analysis-status")
async def get_project_analysis_status(
    project_id: int = Path(..., gt=0),
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_general_api)  # 60 requests per minute
):
    """Get the status of background analysis tasks for a project."""
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    
    # Check if site exists
    site_result = await db.execute(
        select(Site).where(
            Site.url == project.url,
            Site.user_id == project.user_id
        )
    )
    site = site_result.scalar_one_or_none()
    
    if not site:
        # Fallback if site creation somehow delayed, though unlikely
        return {
            "project_id": project.id,
            "overall_status": "pending",
            "overall_progress": 0,
            # ... other initial fields ...
        }
    
    task_service = BackgroundTaskService()
    
    # Fetch status for all relevant tasks
    crawl_progress = await task_service.get_task_progress_status(
        user_id=tenant_context.user_id,
        task_type=TaskType.WEBSITE_CRAWL,
        site_id=site.id
    )

    cwv_progress = {"status": "not_configured", "progress": 100, "message": "Skipped (not configured)"}
    if cwv_service.is_configured():
        cwv_progress = await task_service.get_task_progress_status(
            user_id=tenant_context.user_id,
            task_type=TaskType.CORE_WEB_VITALS_ANALYSIS,
            site_id=site.id
        )

    revenue_progress = {"status": "not_configured", "progress": 100, "message": "Skipped (not configured)"}
    if ga4_service.is_configured() and project.ga4_configured:
        revenue_progress = await task_service.get_task_progress_status(
            user_id=tenant_context.user_id,
            task_type=TaskType.REVENUE_ANALYSIS,
            site_id=site.id
        )
    
    # Consolidate all tasks that are part of the analysis
    all_tasks = [crawl_progress, cwv_progress, revenue_progress]

    # --- START OF CORRECTED LOGIC ---
    
    # Calculate overall progress (this part is fine)
    total_progress = sum(task["progress"] for task in all_tasks)
    average_progress = total_progress / len(all_tasks) if all_tasks else 0
    
    # Determine the overall status with the correct priority
    overall_status = "complete"  # Assume completion by default

    # Check for any non-complete states in order of priority.
    # If any task is 'in_progress', the whole process is 'in_progress'.
    if any(task["status"] == "in_progress" for task in all_tasks):
        overall_status = "in_progress"
    # Else if any task is 'pending', the process is still running.
    elif any(task["status"] == "pending" for task in all_tasks):
        overall_status = "in_progress"  # Treat 'pending' as an 'in_progress' state for the overall UI

    analysis_status = {
        "project_id": project.id,
        "crawl_status": crawl_progress["status"],
        "cwv_status": cwv_progress["status"],
        "profitability_status": revenue_progress["status"],
        "overall_status": overall_status,
        "overall_progress": round(average_progress),
        "created_at": project.created_at,
        "time_elapsed": (datetime.now(timezone.utc) - project.created_at).total_seconds(),
        "tasks": {
            "crawl": crawl_progress,
            "cwv": cwv_progress,
            "revenue": revenue_progress
        }
    }
    
    return analysis_status

@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int = Path(..., gt=0),
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db)
):
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    
    await db.delete(project)
    await db.commit()
    return None

# --- TEAM MANAGEMENT ENDPOINTS ---

@router.get("/{project_id}/team", response_model=List[ProjectTeamMemberOut])
async def get_project_team(
    project_id: int,
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the list of team members for a specific project.
    """
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    
    result = await db.execute(
        select(ProjectTeamMember)
        .where(ProjectTeamMember.project_id == project_id)
        .options(joinedload(ProjectTeamMember.user))
    )
    team_members = result.scalars().all()
    return team_members

@router.post("/{project_id}/team", response_model=ProjectTeamMemberOut, status_code=status.HTTP_201_CREATED)
async def add_project_team_member(
    project_id: int,
    member_in: ProjectTeamMemberCreate,
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db)
):
    # Validate project access using tenant service (requires modify access)
    project = await tenant_service.validate_project_access(tenant_context, project_id)

    user_to_add_result = await db.execute(select(User).where(User.email == member_in.email))
    user_to_add = user_to_add_result.scalar_one_or_none()
    if not user_to_add:
        raise HTTPException(status_code=404, detail=f"User with email {member_in.email} not found")

    existing_member_result = await db.execute(
        select(ProjectTeamMember).where(
            ProjectTeamMember.project_id == project_id,
            ProjectTeamMember.user_id == user_to_add.id
        )
    )
    if existing_member_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already a team member")

    member = ProjectTeamMember(
        project_id=project_id,
        user_id=user_to_add.id,
        can_edit=member_in.can_edit
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    result = await db.execute(
        select(ProjectTeamMember)
        .where(ProjectTeamMember.id == member.id)
        .options(joinedload(ProjectTeamMember.user))
    )
    final_member = result.scalar_one()
    return final_member

@router.put("/{project_id}/team/{user_id}", response_model=ProjectTeamMemberOut)
async def update_project_team_member(
    project_id: int,
    user_id: int,
    member_in: ProjectTeamMemberUpdate,
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db)
):
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    result = await db.execute(
        select(ProjectTeamMember).where(
            ProjectTeamMember.project_id == project_id,
            ProjectTeamMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    if member_in.can_edit is not None:
        member.can_edit = member_in.can_edit
    await db.commit()
    await db.refresh(member)
    return member

@router.delete("/{project_id}/team/{user_id}", status_code=204)
async def remove_project_team_member(
    project_id: int,
    user_id: int,
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db)
):
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    result = await db.execute(
        select(ProjectTeamMember).where(
            ProjectTeamMember.project_id == project_id,
            ProjectTeamMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    await db.delete(member)
    await db.commit()
    return None 

# --- PROJECT SETTINGS ENDPOINTS ---

@router.put("/{project_id}/settings", response_model=ProjectOut)
async def update_project_settings(
    project_id: int,
    settings_in: ProjectSettingsUpdate,
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_general_api)  # 60 requests per minute
):
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    
    if settings_in.ga4_property_id is not None:
        project.ga4_property_id = settings_in.ga4_property_id
        project.ga4_configured = bool(settings_in.ga4_property_id)
    
    if settings_in.ga4_measurement_id is not None:
        project.ga4_measurement_id = settings_in.ga4_measurement_id
    
    if settings_in.analytics_enabled is not None:
        project.analytics_enabled = settings_in.analytics_enabled
    
    if settings_in.profitability_tracking is not None:
        project.profitability_tracking = settings_in.profitability_tracking
    
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}/settings", response_model=ProjectOut)
async def get_project_settings(
    project_id: int,
    tenant_context: TenantContext = Depends(get_current_tenant_context_dependency),
    tenant_service = Depends(get_tenant_service),
    db: AsyncSession = Depends(get_db)
):
    # Validate project access using tenant service
    project = await tenant_service.validate_project_access(tenant_context, project_id)
    return project

# --- END OF CORRECTED FILE projects.py ---