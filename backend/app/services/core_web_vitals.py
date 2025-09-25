"""
Core Web Vitals service for analyzing website performance.

This module provides services for analyzing Core Web Vitals using Google PageSpeed Insights API
and Chrome User Experience Report (CrUX) data.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException

from app.core.config import settings
from app.db.session import get_db, async_session_factory
from app.models.crawl import Site
from app.schemas.diagnostic import CoreWebVitalsResponse
from app.models.background_task import TaskType
from app.services.background_task_service import background_task_service

logger = logging.getLogger(__name__)


class CoreWebVitalsService:
    """Service for analyzing Core Web Vitals."""
    
    def __init__(self):
        self.pagespeed_api_key = settings.GOOGLE_PAGESPEED_API_KEY
        self.crux_api_key = settings.GOOGLE_CRUX_API_KEY
        self.pagespeed_base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        
    def is_configured(self) -> bool:
        """Check if PageSpeed Insights API is configured."""
        return bool(self.pagespeed_api_key)

    def is_crux_configured(self) -> bool:
        """Check if Chrome UX Report API is configured."""
        return bool(self.crux_api_key)
    
    async def get_crux_data_all_devices(self, url: str) -> Dict[str, Any]:
        """Get CrUX data for all device types."""
        device_types = ["PHONE", "DESKTOP", "TABLET"]
        results = {}
        
        for device in device_types:
            results[device.lower()] = await self._get_crux_data_for_device(url, device)
        
        # Aggregate data across all devices
        all_devices_data = await self._get_crux_data_for_device(url, None)  # None = all devices
        results["all"] = all_devices_data
        
        return results
    
    async def _get_crux_data_for_device(self, url: str, form_factor: Optional[str]) -> Dict[str, Any]:
        """Get CrUX data for a specific device type."""
        # This is a refactored version of _get_crux_data that accepts form factor
        if not self.is_crux_configured():
            return {"data_available": False, "reason": "Chrome UX Report API key not configured"}

        try:
            crux_api_url = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
            normalized_url = url.rstrip('/')
            
            request_body = {
                "url": normalized_url,
                "metrics": [
                    "largest_contentful_paint",
                    "cumulative_layout_shift",
                    "experimental_time_to_first_byte",
                    "first_contentful_paint",
                    "interaction_to_next_paint"
                ]
            }
            
            # Only add formFactor if specified
            if form_factor:
                request_body["formFactor"] = form_factor
            
            params = {"key": self.crux_api_key}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(crux_api_url, json=request_body, params=params)
                
                if response.status_code == 404:
                    logger.warning(f"CrUX data not available for URL: {normalized_url}")
                    return {"data_available": False, "reason": "No CrUX data available for this URL"}
                
                if response.status_code == 403:
                    logger.warning(f"CrUX API access denied (403). API key may not have permission or API not enabled.")
                    return {"data_available": False, "reason": "API access denied - check API key permissions"}
                
                if response.status_code == 400:
                    error_details = response.text
                    logger.warning(f"CrUX API bad request (400) for URL: {normalized_url}. Error: {error_details}")
                    logger.warning(f"Request body was: {request_body}")
                    return {"data_available": False, "reason": f"Invalid request to CrUX API: {error_details}"}
                
                response.raise_for_status()
                return self._parse_crux_response(response.json())
                
        except Exception as e:
            logger.error(f"Error getting CrUX data for {form_factor or 'all'}: {e}")
            return {"error": str(e), "data_available": False}
    
    def _parse_crux_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse CrUX API response into a structured format."""
        metrics = data.get("record", {}).get("metrics", {})
        
        def get_p75_value(metric_data):
            if metric_data and "percentiles" in metric_data:
                return metric_data["percentiles"].get("p75")
            return None
        
        result = {
            "lcp": get_p75_value(metrics.get("largest_contentful_paint", {})),
            "fid": get_p75_value(metrics.get("first_input_delay", {})),
            "cls": get_p75_value(metrics.get("cumulative_layout_shift", {})),
            "inp": get_p75_value(metrics.get("interaction_to_next_paint", {})),
            "ttfb": get_p75_value(metrics.get("experimental_time_to_first_byte", {})),
            "fcp": get_p75_value(metrics.get("first_contentful_paint", {})),
            "data_available": True,
            "histogram": {
                "lcp": self._extract_histogram(metrics.get("largest_contentful_paint", {})),
                "fid": self._extract_histogram(metrics.get("first_input_delay", {})),
                "cls": self._extract_histogram(metrics.get("cumulative_layout_shift", {})),
                "inp": self._extract_histogram(metrics.get("interaction_to_next_paint", {}))
            }
        }
        
        collection_period = data.get("record", {}).get("collectionPeriod", {})
        if collection_period:
            result["collection_period"] = {
                "first_date": collection_period.get("firstDate", {}),
                "last_date": collection_period.get("lastDate", {})
            }
        
        return result
    
    async def analyze_core_web_vitals(
        self,
        url: str,
        use_crux: bool = True,
        use_lighthouse: bool = True,
        user_id: int = None,
        site_id: int = None,
        track_task: bool = True,
    ) -> CoreWebVitalsResponse:
        """
        Analyze Core Web Vitals for a website.
        
        Args:
            url: The URL to analyze
            use_crux: Whether to include CrUX data
            use_lighthouse: Whether to include Lighthouse data
            user_id: ID of the user requesting the analysis
            
        Returns:
            Core Web Vitals analysis results
            
        Raises:
            ValueError: If service is not configured
            Exception: If API request fails
        """
        if not self.is_configured():
            raise ValueError("Google PageSpeed Insights API is not configured. Please set GOOGLE_PAGESPEED_API_KEY in your environment variables.")
        
        # Create background task if tracking is enabled
        task_id = None
        if track_task and user_id:
            task_id = await background_task_service.create_task(
                user_id=user_id,
                task_type=TaskType.CORE_WEB_VITALS,
                task_name=f"Core Web Vitals Analysis: {url}",
                description=f"Analyzing Core Web Vitals for {url}",
                site_id=site_id,
                parameters={
                    "url": url,
                    "use_crux": use_crux,
                    "use_lighthouse": use_lighthouse
                }
            )
            await background_task_service.start_task(task_id)
        
        try:
            lab_data_raw = {}
            field_data_raw = {}
            lab_data = None
            field_data = None
            
            if use_lighthouse:
                if task_id:
                    await background_task_service.update_progress(task_id, 30, "Fetching Lighthouse data...")
                lab_data_raw = await self._get_lighthouse_data(url)
                if lab_data_raw:
                    lab_data = self._transform_to_core_web_vitals_data(lab_data_raw, "Lighthouse")
            
            if use_crux:
                if task_id:
                    await background_task_service.update_progress(task_id, 60, "Fetching CrUX field data...")
                field_data_raw = await self._get_crux_data(url)
                if field_data_raw:
                    field_data = self._transform_to_core_web_vitals_data(field_data_raw, "CrUX")
            
            # Generate recommendations based on the data
            if task_id:
                await background_task_service.update_progress(task_id, 90, "Generating recommendations...")
            recommendations = self._generate_recommendations(lab_data_raw, field_data_raw)
            
            result = CoreWebVitalsResponse(
                url=url,
                lab_data=lab_data,
                field_data=field_data,
                timestamp=datetime.now(),
                recommendations=recommendations,
            )
            
            # Complete the task
            if task_id:
                await background_task_service.complete_task(
                    task_id,
                    result={
                        "url": url,
                        "lab_data": lab_data,
                        "field_data": field_data,
                        "recommendations": recommendations,
                        "timestamp": datetime.now().isoformat()
                    },
                    resource_type="core_web_vitals_analysis"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Core Web Vitals analysis error: {e}")
            if task_id:
                await background_task_service.fail_task(task_id, str(e))
            raise ValueError(f"Failed to analyze Core Web Vitals: {e}")
        
    async def get_latest_cwv_data(self, site_id: int, user_id: int) -> Dict:
        """
        Get the latest Core Web Vitals data for a site.
        
        Args:
            site_id: The ID of the site
            user_id: ID of the user requesting the data
            
        Returns:
            The latest Core Web Vitals data
            
        Raises:
            HTTPException: If the site is not found for the user.
            ValueError: If the service is not configured.
        """
        if not self.is_configured():
            raise ValueError("Google PageSpeed Insights API is not configured.")

        try:
            # Use a single database session to find the site
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Site).where(Site.id == site_id, Site.user_id == user_id)
                )
                site = result.scalar_one_or_none()
            
            # --- THIS IS THE CORRECTED LOGIC ---
            if not site:
                # If the site doesn't exist, raise a 404 error immediately.
                logger.error(f"Site with ID {site_id} not found for user {user_id}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Site with ID {site_id} not found."
                )
            
            # If we get here, 'site' is guaranteed to be a valid object.
            site_url = site.url
            
            # Get both lab and field data
            lab_data = await self._get_lighthouse_data(site_url)
            field_data = await self._get_crux_data(site_url)
            
            # Get trending data from database
            trending_data = await self._get_trending_data(site_id, user_id)
            
            return {
                "lab_data": lab_data,
                "field_data": field_data,
                "trending": trending_data,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except HTTPException:
            # Re-raise HTTPException so FastAPI can handle it
            raise
        except Exception as e:
            logger.error(f"Error getting latest CWV data for site {site_id}: {e}")
            raise ValueError(f"Failed to get latest Core Web Vitals data: {e}")
    
    async def _get_lighthouse_data(self, url: str) -> Dict[str, Any]:
        """Get Lighthouse data from Google PageSpeed Insights API."""
        try:
            params = {
                "url": url,
                "key": self.pagespeed_api_key,
                "strategy": "mobile",  # Can be 'mobile' or 'desktop'
                "category": "performance"
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.pagespeed_base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract Core Web Vitals from Lighthouse data
                lighthouse_score = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0) * 100
                
                audits = data.get("lighthouseResult", {}).get("audits", {})
                
                return {
                    "lighthouse_score": round(lighthouse_score, 1),
                    "lcp": audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000,  # Convert to seconds
                    "fid": audits.get("max-potential-fid", {}).get("numericValue", 0),  # Already in milliseconds
                    "cls": audits.get("cumulative-layout-shift", {}).get("numericValue", 0),
                    "ttfb": audits.get("server-response-time", {}).get("numericValue", 0),
                    "fcp": audits.get("first-contentful-paint", {}).get("numericValue", 0) / 1000,  # Convert to seconds
                    "si": audits.get("speed-index", {}).get("numericValue", 0) / 1000,  # Convert to seconds
                    "tbt": audits.get("total-blocking-time", {}).get("numericValue", 0),  # Already in milliseconds
                }
                
        except Exception as e:
            logger.error(f"Error getting Lighthouse data: {e}")
            return {}
    
    async def _get_crux_data(self, url: str) -> Dict[str, Any]:
        """Get Chrome User Experience Report (CrUX) data for mobile devices."""
        # Default to mobile data for backward compatibility
        return await self._get_crux_data_for_device(url, "PHONE")
    
    def _extract_histogram(self, metric_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract histogram data from CrUX metric."""
        histogram = metric_data.get("histogram", [])
        result = {"good": 0, "needs_improvement": 0, "poor": 0}
        
        if len(histogram) >= 3:
            result["good"] = histogram[0].get("density", 0) * 100
            result["needs_improvement"] = histogram[1].get("density", 0) * 100
            result["poor"] = histogram[2].get("density", 0) * 100
            
        return result
    
    async def _get_trending_data(self, site_id: int, user_id: int) -> Dict[str, Any]:
        """Get trending Core Web Vitals data from database."""
        try:
            from app.models.performance import PerformanceMetric
            from sqlalchemy import select, and_
            
            async with async_session_factory() as db:
                # Get last 30 days of data
                thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
                
                result = await db.execute(
                    select(PerformanceMetric)
                    .join(Site)
                    .where(
                        and_(
                            PerformanceMetric.site_id == site_id,
                            Site.user_id == user_id,
                            PerformanceMetric.created_at >= thirty_days_ago,
                            PerformanceMetric.device_type == "mobile"  # Default to mobile
                        )
                    )
                    .order_by(PerformanceMetric.created_at)
                )
                
                metrics = result.scalars().all()
                
                if not metrics:
                    return {
                        "lcp": [],
                        "fid": [],
                        "cls": [],
                        "inp": [],
                        "dates": [],
                        "note": "No historical data available yet. Data will be populated as measurements are collected."
                    }
                
                # Extract trending data
                lcp_values = []
                fid_values = []
                cls_values = []
                inp_values = []
                dates = []
                
                for metric in metrics:
                    # Prefer field data, fallback to lab data
                    lcp = metric.field_lcp if metric.field_lcp is not None else metric.lab_lcp
                    fid = metric.field_fid if metric.field_fid is not None else metric.lab_fid
                    cls = metric.field_cls if metric.field_cls is not None else metric.lab_cls
                    inp = metric.field_inp if metric.field_inp is not None else None
                    
                    if lcp is not None:
                        lcp_values.append(round(lcp, 2))
                        fid_values.append(round(fid, 0) if fid is not None else None)
                        cls_values.append(round(cls, 3) if cls is not None else None)
                        inp_values.append(round(inp, 0) if inp is not None else None)
                        dates.append(metric.created_at.isoformat())
                
                return {
                    "lcp": lcp_values,
                    "fid": fid_values,
                    "cls": cls_values,
                    "inp": inp_values,
                    "dates": dates,
                    "count": len(metrics),
                    "period": "30 days"
                }
                
        except Exception as e:
            logger.error(f"Error getting trending data: {e}")
            return {
                "lcp": [],
                "fid": [],
                "cls": [],
                "inp": [],
                "dates": [],
                "error": str(e)
            }
    
    def _transform_to_core_web_vitals_data(self, raw_data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Transform raw data to CoreWebVitalsData format."""
        from app.schemas.diagnostic import CoreWebVitalsData, CoreWebVitalsMetric
        
        metrics = []
        
        # Map raw data to CoreWebVitalsMetric objects
        metric_mappings = {
            "lcp": ("Largest Contentful Paint", "seconds", 2.5, 4.0),
            "fid": ("First Input Delay", "milliseconds", 100, 300),
            "cls": ("Cumulative Layout Shift", "score", 0.1, 0.25),
            "ttfb": ("Time to First Byte", "milliseconds", 800, 1800),
            "fcp": ("First Contentful Paint", "seconds", 1.8, 3.0),
            "si": ("Speed Index", "seconds", 3.4, 5.8),
            "tbt": ("Total Blocking Time", "milliseconds", 200, 600),
            "inp": ("Interaction to Next Paint", "milliseconds", 200, 500),
        }
        
        for key, (name, unit, good_threshold, poor_threshold) in metric_mappings.items():
            if key in raw_data:
                value = raw_data[key]
                # Determine category based on thresholds
                if value <= good_threshold:
                    category = "Good"
                elif value <= poor_threshold:
                    category = "Needs Improvement"
                else:
                    category = "Poor"
                
                metrics.append(CoreWebVitalsMetric(
                    name=name,
                    value=value,
                    unit=unit,
                    category=category
                ))
        
        return CoreWebVitalsData(
            source=source,
            date=datetime.now(),
            metrics=metrics,
            overall_score=raw_data.get("lighthouse_score", raw_data.get("overall_score"))
        )
    
    def _generate_recommendations(self, lab_data: Dict[str, Any], field_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on Core Web Vitals data."""
        recommendations = []
        
        # LCP recommendations
        lcp = lab_data.get("lcp", 0)
        if lcp > 4.0:
            recommendations.append(
                "Poor Largest Contentful Paint (LCP): Optimize the largest contentful paint element. Consider image optimization, server response times, and render-blocking resources."
            )
        elif lcp > 2.5:
            recommendations.append(
                "Largest Contentful Paint needs improvement: Optimize the hero image and reduce server response times to improve LCP."
            )
        
        # FID recommendations
        fid = lab_data.get("fid", 0)
        if fid > 300:
            recommendations.append(
                "Poor First Input Delay (FID): Reduce JavaScript execution time and minimize main thread blocking to improve interactivity."
            )
        elif fid > 100:
            recommendations.append(
                "First Input Delay needs improvement: Optimize JavaScript execution and reduce main thread blocking."
            )
        
        # CLS recommendations
        cls = lab_data.get("cls", 0)
        if cls > 0.25:
            recommendations.append(
                "Poor Cumulative Layout Shift (CLS): Ensure images and other elements have explicit width and height attributes to prevent layout shifts."
            )
        elif cls > 0.1:
            recommendations.append(
                "Cumulative Layout Shift needs improvement: Add explicit dimensions to images and avoid inserting content above existing content."
            )
        
        # TTFB recommendations
        ttfb = lab_data.get("ttfb", 0)
        if ttfb > 1800:
            recommendations.append(
                "Poor Time to First Byte (TTFB): Optimize server response times by improving server performance and reducing server-side processing."
            )
        elif ttfb > 800:
            recommendations.append(
                "Time to First Byte needs improvement: Consider using a CDN, optimizing database queries, and enabling server-side caching."
            )
        
        # TBT recommendations
        tbt = lab_data.get("tbt", 0)
        if tbt > 600:
            recommendations.append(
                "Poor Total Blocking Time (TBT): Break up long tasks, defer unused JavaScript, and minimize main thread work."
            )
        elif tbt > 200:
            recommendations.append(
                "Total Blocking Time needs improvement: Optimize JavaScript execution and reduce main thread blocking."
            )
        
        return recommendations
    
    async def save_performance_metrics(
        self, 
        site_id: int, 
        url: str,
        lab_data: Dict[str, Any],
        field_data: Dict[str, Any],
        device_type: str = "mobile"
    ) -> None:
        """Save performance metrics to database for historical tracking."""
        try:
            from app.models.performance import PerformanceMetric
            from app.core.websocket import broadcast_dashboard_update
            
            async with async_session_factory() as db:
                # Determine data source
                has_lab = bool(lab_data and lab_data.get("lcp") is not None)
                has_field = bool(field_data and field_data.get("data_available"))
                data_source = "both" if has_lab and has_field else ("lighthouse" if has_lab else "crux")
                
                # Create performance metric record
                metric = PerformanceMetric(
                    site_id=site_id,
                    url=url,
                    collected_at=datetime.now(timezone.utc),
                    device_type=device_type,
                    data_source=data_source,
                    
                    # Lab data
                    lab_lcp=lab_data.get("lcp") if lab_data else None,
                    lab_fid=lab_data.get("fid") if lab_data else None,
                    lab_cls=lab_data.get("cls") if lab_data else None,
                    lab_ttfb=lab_data.get("ttfb") if lab_data else None,
                    lab_fcp=lab_data.get("fcp") if lab_data else None,
                    lab_si=lab_data.get("si") if lab_data else None,
                    lab_tbt=lab_data.get("tbt") if lab_data else None,
                    lab_tti=lab_data.get("tti") if lab_data else None,
                    
                    # Field data
                    field_lcp=field_data.get("lcp") if field_data else None,
                    field_fid=field_data.get("fid") if field_data else None,
                    field_cls=field_data.get("cls") if field_data else None,
                    field_inp=field_data.get("inp") if field_data else None,
                    field_ttfb=field_data.get("ttfb") if field_data else None,
                    field_fcp=field_data.get("fcp") if field_data else None,
                    
                    # Performance score
                    performance_score=lab_data.get("lighthouse_score") if lab_data else None,
                    
                    # CrUX histogram data
                    lcp_good=field_data.get("histogram", {}).get("lcp", {}).get("good") if field_data else None,
                    lcp_needs_improvement=field_data.get("histogram", {}).get("lcp", {}).get("needs_improvement") if field_data else None,
                    lcp_poor=field_data.get("histogram", {}).get("lcp", {}).get("poor") if field_data else None,
                    fid_good=field_data.get("histogram", {}).get("fid", {}).get("good") if field_data else None,
                    fid_needs_improvement=field_data.get("histogram", {}).get("fid", {}).get("needs_improvement") if field_data else None,
                    fid_poor=field_data.get("histogram", {}).get("fid", {}).get("poor") if field_data else None,
                    cls_good=field_data.get("histogram", {}).get("cls", {}).get("good") if field_data else None,
                    cls_needs_improvement=field_data.get("histogram", {}).get("cls", {}).get("needs_improvement") if field_data else None,
                    cls_poor=field_data.get("histogram", {}).get("cls", {}).get("poor") if field_data else None,
                    inp_good=field_data.get("histogram", {}).get("inp", {}).get("good") if field_data else None,
                    inp_needs_improvement=field_data.get("histogram", {}).get("inp", {}).get("needs_improvement") if field_data else None,
                    inp_poor=field_data.get("histogram", {}).get("inp", {}).get("poor") if field_data else None,
                    
                    # Metadata
                    crux_collection_period=field_data.get("collection_period") if field_data else None,
                    raw_lighthouse_data=lab_data if lab_data else None,
                    raw_crux_data=field_data if field_data else None
                )
                
                db.add(metric)
                await db.commit()
                logger.info(f"Saved performance metrics for site {site_id}, URL: {url}")
                
                # Warm cache with new data
                from app.core.cache import cache_manager
                
                if device_type == "desktop" and lab_data:
                    cache_key = f"cwv:desktop:{site_id}"
                    await cache_manager.set(
                        cache_key,
                        {
                            "lcp": lab_data.get("lcp"),
                            "fid": lab_data.get("fid"),
                            "cls": lab_data.get("cls"),
                            "ttfb": lab_data.get("ttfb"),
                            "inp": field_data.get("inp") if field_data else None,
                            "score": lab_data.get("lighthouse_score"),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        ttl=3600  # 1 hour TTL
                    )
                elif device_type == "mobile" and lab_data:
                    cache_key = f"cwv:mobile:{site_id}"
                    await cache_manager.set(
                        cache_key,
                        {
                            "lcp": lab_data.get("lcp"),
                            "fid": lab_data.get("fid"),
                            "cls": lab_data.get("cls"),
                            "ttfb": lab_data.get("ttfb"),
                            "inp": field_data.get("inp") if field_data else None,
                            "score": lab_data.get("lighthouse_score"),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        ttl=3600  # 1 hour TTL
                    )
                
                # Broadcast real-time update
                await broadcast_dashboard_update(
                    site_id=site_id,
                    update_data={
                        "type": "core_web_vitals",
                        "lab_data": lab_data,
                        "field_data": field_data,
                        "device_type": device_type,
                        "performance_score": lab_data.get("lighthouse_score") if lab_data else None,
                    },
                    priority="normal",
                    description="New Core Web Vitals data available"
                )
                
        except Exception as e:
            logger.error(f"Error saving performance metrics: {e}")
    
    async def analyze_competitor(
        self,
        site_id: int,
        competitor_url: str,
        user_id: int,
        device_type: str = "mobile"
    ) -> Dict[str, Any]:
        """
        Analyze a competitor's Core Web Vitals and compare with our site.
        
        Args:
            site_id: The ID of our site
            competitor_url: The competitor's URL to analyze
            user_id: The user ID for authorization
            device_type: Device type for analysis (mobile/desktop)
            
        Returns:
            Competitor analysis and comparison data
        """
        if not self.is_configured():
            raise ValueError("Google PageSpeed Insights API is not configured.")
        
        try:
            from app.models.performance import PerformanceBenchmark, PerformanceMetric
            
            # Get our site data first
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Site).where(Site.id == site_id, Site.user_id == user_id)
                )
                site = result.scalar_one_or_none()
                
                if not site:
                    raise HTTPException(status_code=404, detail="Site not found")
                
                # Get our latest metrics
                our_metrics_result = await db.execute(
                    select(PerformanceMetric)
                    .where(
                        and_(
                            PerformanceMetric.site_id == site_id,
                            PerformanceMetric.device_type == device_type
                        )
                    )
                    .order_by(PerformanceMetric.created_at.desc())
                    .limit(1)
                )
                our_latest = our_metrics_result.scalar_one_or_none()
            
            # Analyze competitor
            competitor_lab = await self._get_lighthouse_data(competitor_url)
            competitor_field = await self._get_crux_data(competitor_url)
            
            # Extract competitor metrics
            comp_lcp = competitor_field.get("lcp", competitor_lab.get("lcp", 0))
            comp_fid = competitor_field.get("fid", competitor_lab.get("fid", 0))
            comp_cls = competitor_field.get("cls", competitor_lab.get("cls", 0))
            comp_inp = competitor_field.get("inp", 0)
            comp_ttfb = competitor_field.get("ttfb", competitor_lab.get("ttfb", 0))
            comp_score = competitor_lab.get("performance_score", 0)
            
            # Compare with our metrics
            comparison = {}
            if our_latest:
                our_lcp = our_latest.field_lcp or our_latest.lab_lcp or 0
                our_fid = our_latest.field_fid or our_latest.lab_fid or 0
                our_cls = our_latest.field_cls or our_latest.lab_cls or 0
                our_inp = our_latest.field_inp or 0
                our_score = our_latest.performance_score or 0
                
                comparison = {
                    "lcp_better": our_lcp < comp_lcp if our_lcp and comp_lcp else None,
                    "fid_better": our_fid < comp_fid if our_fid and comp_fid else None,
                    "cls_better": our_cls < comp_cls if our_cls and comp_cls else None,
                    "inp_better": our_inp < comp_inp if our_inp and comp_inp else None,
                    "overall_better": our_score > comp_score if our_score and comp_score else None,
                    "our_metrics": {
                        "lcp": our_lcp,
                        "fid": our_fid,
                        "cls": our_cls,
                        "inp": our_inp,
                        "performance_score": our_score
                    }
                }
            
            # Save benchmark data
            async with async_session_factory() as db:
                # Check if benchmark exists
                existing_result = await db.execute(
                    select(PerformanceBenchmark).where(
                        and_(
                            PerformanceBenchmark.site_id == site_id,
                            PerformanceBenchmark.competitor_url == competitor_url,
                            PerformanceBenchmark.device_type == device_type
                        )
                    )
                )
                benchmark = existing_result.scalar_one_or_none()
                
                if benchmark:
                    # Update existing
                    benchmark.lcp = comp_lcp
                    benchmark.fid = comp_fid
                    benchmark.cls = comp_cls
                    benchmark.inp = comp_inp
                    benchmark.ttfb = comp_ttfb
                    benchmark.performance_score = comp_score
                    benchmark.lcp_better = comparison.get("lcp_better")
                    benchmark.fid_better = comparison.get("fid_better")
                    benchmark.cls_better = comparison.get("cls_better")
                    benchmark.inp_better = comparison.get("inp_better")
                    benchmark.overall_better = comparison.get("overall_better")
                    benchmark.raw_data = {
                        "lab_data": competitor_lab,
                        "field_data": competitor_field
                    }
                else:
                    # Create new
                    benchmark = PerformanceBenchmark(
                        site_id=site_id,
                        competitor_url=competitor_url,
                        competitor_name=self._extract_domain_name(competitor_url),
                        device_type=device_type,
                        lcp=comp_lcp,
                        fid=comp_fid,
                        cls=comp_cls,
                        inp=comp_inp,
                        ttfb=comp_ttfb,
                        performance_score=comp_score,
                        lcp_better=comparison.get("lcp_better"),
                        fid_better=comparison.get("fid_better"),
                        cls_better=comparison.get("cls_better"),
                        inp_better=comparison.get("inp_better"),
                        overall_better=comparison.get("overall_better"),
                        raw_data={
                            "lab_data": competitor_lab,
                            "field_data": competitor_field
                        }
                    )
                    db.add(benchmark)
                
                await db.commit()
            
            return {
                "competitor": {
                    "url": competitor_url,
                    "name": self._extract_domain_name(competitor_url),
                    "metrics": {
                        "lcp": comp_lcp,
                        "fid": comp_fid,
                        "cls": comp_cls,
                        "inp": comp_inp,
                        "ttfb": comp_ttfb,
                        "performance_score": comp_score
                    },
                    "lab_data": competitor_lab,
                    "field_data": competitor_field
                },
                "comparison": comparison,
                "analysis": self._generate_competitive_insights(comparison, comp_score),
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing competitor {competitor_url}: {e}")
            raise ValueError(f"Failed to analyze competitor: {e}")
    
    async def get_competitive_benchmarks(
        self,
        site_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get all competitive benchmarks for a site.
        
        Args:
            site_id: The site ID
            user_id: The user ID for authorization
            
        Returns:
            List of competitive benchmarks with analysis
        """
        try:
            from app.models.performance import PerformanceBenchmark
            
            async with async_session_factory() as db:
                # Verify site ownership
                result = await db.execute(
                    select(Site).where(Site.id == site_id, Site.user_id == user_id)
                )
                site = result.scalar_one_or_none()
                
                if not site:
                    raise HTTPException(status_code=404, detail="Site not found")
                
                # Get all benchmarks
                benchmarks_result = await db.execute(
                    select(PerformanceBenchmark)
                    .where(PerformanceBenchmark.site_id == site_id)
                    .order_by(PerformanceBenchmark.created_at.desc())
                )
                benchmarks = benchmarks_result.scalars().all()
                
                # Format response
                competitors = []
                for benchmark in benchmarks:
                    competitors.append({
                        "competitor_url": benchmark.competitor_url,
                        "competitor_name": benchmark.competitor_name,
                        "device_type": benchmark.device_type,
                        "metrics": {
                            "lcp": benchmark.lcp,
                            "fid": benchmark.fid,
                            "cls": benchmark.cls,
                            "inp": benchmark.inp,
                            "ttfb": benchmark.ttfb,
                            "performance_score": benchmark.performance_score
                        },
                        "comparison": {
                            "lcp_better": benchmark.lcp_better,
                            "fid_better": benchmark.fid_better,
                            "cls_better": benchmark.cls_better,
                            "inp_better": benchmark.inp_better,
                            "overall_better": benchmark.overall_better
                        },
                        "analyzed_at": benchmark.created_at.isoformat()
                    })
                
                # Calculate summary
                total_competitors = len(competitors)
                better_than_count = sum(1 for c in competitors if c["comparison"]["overall_better"])
                
                return {
                    "site_id": site_id,
                    "competitors": competitors,
                    "summary": {
                        "total_competitors": total_competitors,
                        "better_than_count": better_than_count,
                        "worse_than_count": total_competitors - better_than_count,
                        "performance_rank": better_than_count + 1,  # Our rank among competitors
                        "insights": self._generate_competitive_summary(competitors)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting competitive benchmarks: {e}")
            raise ValueError(f"Failed to get competitive benchmarks: {e}")
    
    def _extract_domain_name(self, url: str) -> str:
        """Extract domain name from URL for display."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def _generate_competitive_insights(
        self, 
        comparison: Dict[str, Any], 
        competitor_score: float
    ) -> List[str]:
        """Generate insights from competitive comparison."""
        insights = []
        
        if not comparison:
            insights.append("No comparison data available. Analyze your site first.")
            return insights
        
        # Overall performance
        if comparison.get("overall_better"):
            insights.append(f"Your site performs better overall (score difference: {comparison['our_metrics']['performance_score'] - competitor_score:.0f} points)")
        else:
            insights.append(f"Competitor performs better overall (score difference: {competitor_score - comparison['our_metrics']['performance_score']:.0f} points)")
        
        # Specific metrics
        metrics_better = sum([
            comparison.get("lcp_better", False),
            comparison.get("fid_better", False),
            comparison.get("cls_better", False),
            comparison.get("inp_better", False)
        ])
        
        if metrics_better >= 3:
            insights.append("You're winning on most Core Web Vitals metrics")
        elif metrics_better <= 1:
            insights.append("Competitor has better Core Web Vitals across most metrics")
        
        # Specific recommendations
        if not comparison.get("lcp_better") and comparison["our_metrics"]["lcp"] > 2.5:
            insights.append("Focus on improving LCP to match competitor performance")
        
        if not comparison.get("cls_better") and comparison["our_metrics"]["cls"] > 0.1:
            insights.append("Reduce layout shifts to compete better")
        
        return insights
    
    def _generate_competitive_summary(self, competitors: List[Dict[str, Any]]) -> List[str]:
        """Generate summary insights from all competitors."""
        insights = []
        
        if not competitors:
            insights.append("No competitors analyzed yet")
            return insights
        
        # Performance ranking
        better_count = sum(1 for c in competitors if c["comparison"]["overall_better"])
        total = len(competitors)
        
        if better_count == total:
            insights.append(f"Excellent! You outperform all {total} analyzed competitors")
        elif better_count >= total * 0.7:
            insights.append(f"Strong performance - better than {better_count}/{total} competitors")
        elif better_count >= total * 0.3:
            insights.append(f"Average performance - better than {better_count}/{total} competitors")
        else:
            insights.append(f"Need improvement - only better than {better_count}/{total} competitors")
        
        # Identify weakest metric
        metric_performance = {
            "lcp": sum(1 for c in competitors if c["comparison"].get("lcp_better", False)),
            "fid": sum(1 for c in competitors if c["comparison"].get("fid_better", False)),
            "cls": sum(1 for c in competitors if c["comparison"].get("cls_better", False)),
            "inp": sum(1 for c in competitors if c["comparison"].get("inp_better", False))
        }
        
        weakest_metric = min(metric_performance.items(), key=lambda x: x[1])
        if weakest_metric[1] < total * 0.5:
            metric_names = {
                "lcp": "Largest Contentful Paint",
                "fid": "First Input Delay",
                "cls": "Cumulative Layout Shift",
                "inp": "Interaction to Next Paint"
            }
            insights.append(f"Focus on improving {metric_names[weakest_metric[0]]} - your weakest metric")
        
        return insights


# Create a singleton instance
cwv_service = CoreWebVitalsService()
