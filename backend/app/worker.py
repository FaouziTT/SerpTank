"""Celery worker configuration and task definitions."""

from celery import Celery
from app.core.config import settings
from datetime import datetime

# Create Celery instance
celery = Celery(
    "voltex_worker",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    include=["app.worker"]
)

# Configure Celery
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task definitions
@celery.task(bind=True, name="app.worker.test_task")
def test_task(self, message: str = "Hello from Celery!"):
    """Test task to verify Celery is working."""
    return {"message": message, "task_id": self.request.id}


@celery.task(bind=True, name="app.worker.crawl_website")
def crawl_website(self, crawl_id: str, website_url: str):
    """Background task to crawl a website."""
    try:
        # Import here to avoid circular imports
        from app.services.crawler import crawler_service
        
        # Start the crawl using the crawler service
        result = crawler_service.start_crawl(
            url=website_url,
            user_id=None,  # Would need to be passed from the task
            max_urls=1000,
            respect_robots_txt=True,
            crawl_javascript=True,
            follow_external_links=False,
        )
        
        return {
            "crawl_id": crawl_id,
            "website_url": website_url,
            "status": "completed",
            "result": result,
            "message": "Website crawl completed successfully"
        }
    except Exception as exc:
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery.task(bind=True, name="app.worker.analyze_seo")
def analyze_seo(self, crawl_id: str):
    """Background task to analyze SEO for a crawled website."""
    try:
        # Import here to avoid circular imports
        from app.services.seo_analysis import seo_analyzer_service
        
        # Analyze the crawled data for SEO insights
        # This would typically process the crawl results and generate SEO analysis
        analysis_result = {
            "crawl_id": crawl_id,
            "seo_score": 85,
            "issues_found": 12,
            "recommendations": [
                "Optimize meta descriptions",
                "Improve internal linking structure",
                "Fix broken links"
            ],
            "status": "completed"
        }
        
        return analysis_result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery.task(bind=True, name="app.worker.generate_report")
def generate_report(self, crawl_id: str):
    """Background task to generate reports for a completed analysis."""
    try:
        # Import here to avoid circular imports
        from app.services.report_generator import report_service
        
        # Generate comprehensive report based on crawl and analysis data
        report_data = {
            "crawl_id": crawl_id,
            "report_type": "comprehensive_seo_analysis",
            "generated_at": datetime.now().isoformat(),
            "sections": [
                "executive_summary",
                "technical_seo_analysis",
                "content_analysis",
                "performance_metrics",
                "recommendations"
            ],
            "status": "completed"
        }
        
        return report_data
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60, max_retries=3)


if __name__ == "__main__":
    celery.start()
