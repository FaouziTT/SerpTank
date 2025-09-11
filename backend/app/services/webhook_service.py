"""
Webhook service for triggering webhook events.
"""
import httpx
import hmac
import hashlib
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.webhook import Webhook
from app.models.project import Project
from app.core.config import settings
from app.core.structured_logging import get_logger

logger = get_logger(__name__)


class WebhookService:
    """Service for managing and triggering webhooks."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def trigger_event(
        self,
        project_id: int,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Trigger webhooks for a specific event."""
        try:
            # Get all active webhooks for this project and event
            result = await self.db.execute(
                select(Webhook).where(
                    Webhook.project_id == project_id,
                    Webhook.active == True,
                    Webhook.events.contains([event_type])
                )
            )
            webhooks = result.scalars().all()
            
            if not webhooks:
                return
            
            # Get project info
            project_result = await self.db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = project_result.scalar_one_or_none()
            
            if not project:
                return
            
            # Prepare payload
            payload = {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "url": project.url
                },
                "data": data
            }
            
            # Trigger webhooks concurrently
            tasks = []
            for webhook in webhooks:
                task = self._send_webhook(webhook, payload)
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Failed to trigger webhooks: {str(e)}")
    
    async def _send_webhook(
        self,
        webhook: Webhook,
        payload: Dict[str, Any]
    ) -> None:
        """Send a single webhook."""
        try:
            # Prepare request
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = hmac.new(
                webhook.secret.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                "Content-Type": "application/json",
                "X-Voltex-Signature": signature,
                "X-Voltex-Event": payload["event"],
                "X-Voltex-Timestamp": str(int(datetime.utcnow().timestamp())),
                "User-Agent": f"Voltex-Webhook/{settings.VERSION}"
            }
            
            # Send request with retries
            retry_count = 0
            last_error = None
            
            while retry_count <= webhook.max_retries:
                try:
                    response = await self.client.post(
                        webhook.url,
                        content=payload_bytes,
                        headers=headers
                    )
                    
                    # Update webhook status
                    webhook.last_triggered_at = datetime.utcnow()
                    webhook.last_status_code = response.status_code
                    
                    if response.status_code >= 200 and response.status_code < 300:
                        webhook.last_error_message = None
                        webhook.retry_count = 0
                        await self.db.commit()
                        
                        logger.info(
                            f"Webhook delivered successfully",
                            extra={
                                "webhook_id": webhook.id,
                                "url": webhook.url,
                                "event": payload["event"],
                                "status_code": response.status_code
                            }
                        )
                        return
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                        
                except httpx.TimeoutException:
                    last_error = "Request timeout"
                except Exception as e:
                    last_error = str(e)
                
                retry_count += 1
                
                if retry_count <= webhook.max_retries:
                    # Exponential backoff
                    await asyncio.sleep(2 ** retry_count)
            
            # All retries failed
            webhook.last_error_message = last_error
            webhook.retry_count = retry_count
            await self.db.commit()
            
            logger.error(
                f"Webhook delivery failed after {retry_count} retries",
                extra={
                    "webhook_id": webhook.id,
                    "url": webhook.url,
                    "event": payload["event"],
                    "error": last_error
                }
            )
            
        except Exception as e:
            logger.error(
                f"Unexpected error sending webhook",
                extra={
                    "webhook_id": webhook.id,
                    "error": str(e)
                }
            )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Event types
class WebhookEvents:
    """Webhook event type constants."""
    
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    
    # Crawl events
    CRAWL_STARTED = "crawl.started"
    CRAWL_COMPLETED = "crawl.completed"
    CRAWL_FAILED = "crawl.failed"
    
    # Performance events
    PERFORMANCE_ALERT = "performance.alert"
    PERFORMANCE_IMPROVED = "performance.improved"
    
    # SEO events
    SEO_ISSUE_FOUND = "seo.issue_found"
    SEO_ISSUE_RESOLVED = "seo.issue_resolved"
    
    # Ranking events
    RANKING_IMPROVED = "ranking.improved"
    RANKING_DECLINED = "ranking.declined"
    RANKING_CHANGED = "ranking.changed"
    
    # Competitor events
    COMPETITOR_ADDED = "competitor.added"
    COMPETITOR_UPDATE = "competitor.update"
    COMPETITOR_ALERT = "competitor.alert"
    
    # Content events
    CONTENT_OPPORTUNITY = "content.opportunity"
    CONTENT_PUBLISHED = "content.published"