"""
Google Analytics 4 Data API Service

This service provides functionality to interact with Google Analytics 4 Data API
for retrieving analytics data, revenue metrics, and conversion tracking.
"""
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import httpx
import json
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleAnalytics4Service:
    """Service for Google Analytics 4 Data API integration."""
    
    def __init__(self, property_id: Optional[str] = None, access_token: Optional[str] = None):
        self.api_key = settings.GOOGLE_ANALYTICS_API_KEY
        self.property_id = property_id or settings.GOOGLE_ANALYTICS_PROPERTY_ID  # Use project-specific or fallback
        self.service_account_file = settings.GOOGLE_APPLICATION_CREDENTIALS
        self.base_url = "https://analyticsdata.googleapis.com/v1beta"
        self.access_token = access_token  # OAuth access token
        self.management_api_url = "https://analyticsadmin.googleapis.com/v1beta"
        
    def is_configured(self, property_id: Optional[str] = None) -> bool:
        """Check if GA4 is properly configured for a specific property."""
        # Use provided property_id or instance property_id
        prop_id = property_id or self.property_id
        # Support both API key and service account authentication
        has_api_key = bool(self.api_key and prop_id)
        has_service_account = bool(self.service_account_file and prop_id)
        return has_api_key or has_service_account
    
    async def get_revenue_metrics(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        dimensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get revenue and conversion metrics from GA4.
        
        Args:
            start_date: Start date for the report (YYYY-MM-DD or nDaysAgo)
            end_date: End date for the report (YYYY-MM-DD or today)
            dimensions: Additional dimensions to include
            
        Returns:
            Revenue metrics and conversion data
            
        Raises:
            ValueError: If GA4 is not configured
            httpx.HTTPError: If API request fails
        """
        if not self.is_configured():
            raise ValueError("Google Analytics 4 is not configured. Please set GOOGLE_ANALYTICS_API_KEY and GOOGLE_ANALYTICS_PROPERTY_ID in your environment variables.")
        
        try:
            # Build the request payload
            request_data = {
                "dimensions": [
                    {"name": "date"},
                    {"name": "source"},
                    {"name": "medium"}
                ],
                "metrics": [
                    {"name": "totalRevenue"},
                    {"name": "conversions"},
                    {"name": "sessions"},
                    {"name": "activeUsers"},
                    {"name": "purchaseRevenue"},
                    {"name": "ecommercePurchases"}
                ],
                "dateRanges": [{
                    "startDate": start_date,
                    "endDate": end_date
                }]
            }
            
            # Add custom dimensions if provided
            if dimensions:
                for dim in dimensions:
                    request_data["dimensions"].append({"name": dim})
            
            headers = {
                "Authorization": f"Bearer {self.access_token or self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/properties/{self.property_id}:runReport",
                    headers=headers,
                    json=request_data
                )
                response.raise_for_status()
                
                data = response.json()
                return self._process_revenue_metrics(data)
                
        except httpx.HTTPError as e:
            logger.error(f"GA4 API HTTP error: {e}")
            raise ValueError(f"Failed to fetch revenue metrics from Google Analytics 4: {e}")
        except Exception as e:
            logger.error(f"GA4 revenue metrics error: {e}")
            raise ValueError(f"Unexpected error fetching revenue metrics: {e}")
    
    async def get_traffic_analytics(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "today"
    ) -> Dict[str, Any]:
        """
        Get traffic analytics from GA4.
        
        Args:
            start_date: Start date for the report
            end_date: End date for the report
            
        Returns:
            Traffic analytics data
            
        Raises:
            ValueError: If GA4 is not configured
            httpx.HTTPError: If API request fails
        """
        if not self.is_configured():
            raise ValueError("Google Analytics 4 is not configured. Please set GOOGLE_ANALYTICS_API_KEY and GOOGLE_ANALYTICS_PROPERTY_ID in your environment variables.")
        
        try:
            request_data = {
                "dimensions": [
                    {"name": "date"},
                    {"name": "pagePath"},
                    {"name": "source"},
                    {"name": "medium"},
                    {"name": "deviceCategory"}
                ],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "activeUsers"},
                    {"name": "screenPageViews"},
                    {"name": "bounceRate"},
                    {"name": "averageSessionDuration"},
                    {"name": "engagementRate"}
                ],
                "dateRanges": [{
                    "startDate": start_date,
                    "endDate": end_date
                }],
                "orderBys": [{
                    "metric": {"metricName": "sessions"},
                    "desc": True
                }],
                "limit": 100
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token or self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/properties/{self.property_id}:runReport",
                    headers=headers,
                    json=request_data
                )
                response.raise_for_status()
                
                data = response.json()
                return self._process_traffic_analytics(data)
                
        except httpx.HTTPError as e:
            logger.error(f"GA4 API HTTP error: {e}")
            raise ValueError(f"Failed to fetch traffic analytics from Google Analytics 4: {e}")
        except Exception as e:
            logger.error(f"GA4 traffic analytics error: {e}")
            raise ValueError(f"Unexpected error fetching traffic analytics: {e}")
    
    async def get_conversion_funnel(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "today"
    ) -> Dict[str, Any]:
        """
        Get conversion funnel data from GA4.
        
        Args:
            start_date: Start date for the report
            end_date: End date for the report
            
        Returns:
            Conversion funnel analysis
            
        Raises:
            ValueError: If GA4 is not configured
            httpx.HTTPError: If API request fails
        """
        if not self.is_configured():
            raise ValueError("Google Analytics 4 is not configured. Please set GOOGLE_ANALYTICS_API_KEY and GOOGLE_ANALYTICS_PROPERTY_ID in your environment variables.")
        
        try:
            request_data = {
                "dimensions": [
                    {"name": "eventName"},
                    {"name": "source"},
                    {"name": "medium"}
                ],
                "metrics": [
                    {"name": "eventCount"},
                    {"name": "conversions"},
                    {"name": "totalRevenue"}
                ],
                "dateRanges": [{
                    "startDate": start_date,
                    "endDate": end_date
                }],
                "dimensionFilter": {
                    "filter": {
                        "fieldName": "eventName",
                        "inListFilter": {
                            "values": [
                                "page_view",
                                "view_item",
                                "add_to_cart",
                                "begin_checkout",
                                "purchase"
                            ]
                        }
                    }
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token or self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/properties/{self.property_id}:runReport",
                    headers=headers,
                    json=request_data
                )
                response.raise_for_status()
                
                data = response.json()
                return self._process_conversion_funnel(data)
                
        except httpx.HTTPError as e:
            logger.error(f"GA4 API HTTP error: {e}")
            raise ValueError(f"Failed to fetch conversion funnel from Google Analytics 4: {e}")
        except Exception as e:
            logger.error(f"GA4 conversion funnel error: {e}")
            raise ValueError(f"Unexpected error fetching conversion funnel: {e}")
    
    async def get_organic_performance(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "today"
    ) -> Dict[str, Any]:
        """
        Get organic search performance from GA4.
        
        Args:
            start_date: Start date for the report
            end_date: End date for the report
            
        Returns:
            Organic search performance data
            
        Raises:
            ValueError: If GA4 is not configured
            httpx.HTTPError: If API request fails
        """
        if not self.is_configured():
            raise ValueError("Google Analytics 4 is not configured. Please set GOOGLE_ANALYTICS_API_KEY and GOOGLE_ANALYTICS_PROPERTY_ID in your environment variables.")
        
        try:
            request_data = {
                "dimensions": [
                    {"name": "date"},
                    {"name": "pagePath"},
                    {"name": "source"},
                    {"name": "medium"}
                ],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "activeUsers"},
                    {"name": "screenPageViews"},
                    {"name": "totalRevenue"},
                    {"name": "conversions"}
                ],
                "dateRanges": [{
                    "startDate": start_date,
                    "endDate": end_date
                }],
                "dimensionFilter": {
                    "filter": {
                        "fieldName": "source",
                        "stringFilter": {
                            "matchType": "EXACT",
                            "value": "google"
                        }
                    }
                },
                "orderBys": [{
                    "metric": {"metricName": "sessions"},
                    "desc": True
                }],
                "limit": 50
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token or self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/properties/{self.property_id}:runReport",
                    headers=headers,
                    json=request_data
                )
                response.raise_for_status()
                
                data = response.json()
                return self._process_organic_performance(data)
                
        except httpx.HTTPError as e:
            logger.error(f"GA4 API HTTP error: {e}")
            raise ValueError(f"Failed to fetch organic performance from Google Analytics 4: {e}")
        except Exception as e:
            logger.error(f"GA4 organic performance error: {e}")
            raise ValueError(f"Unexpected error fetching organic performance: {e}")
    
    def _process_revenue_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GA4 revenue metrics response."""
        
        rows = data.get("rows", [])
        total_revenue = 0
        total_conversions = 0
        total_sessions = 0
        
        daily_data = []
        source_data = {}
        
        for row in rows:
            dims = [dv.get("value", "") for dv in row.get("dimensionValues", [])]
            metrics = [mv.get("value", "0") for mv in row.get("metricValues", [])]
            
            if len(dims) >= 3 and len(metrics) >= 6:
                date, source, medium = dims[0], dims[1], dims[2]
                revenue, conversions, sessions, users, purchase_revenue, purchases = metrics
                
                # Convert strings to numbers
                revenue = float(revenue) if revenue else 0
                conversions = int(float(conversions)) if conversions else 0
                sessions = int(float(sessions)) if sessions else 0
                
                total_revenue += revenue
                total_conversions += conversions
                total_sessions += sessions
                
                # Group by source
                source_key = f"{source}/{medium}"
                if source_key not in source_data:
                    source_data[source_key] = {
                        "revenue": 0,
                        "conversions": 0,
                        "sessions": 0
                    }
                
                source_data[source_key]["revenue"] += revenue
                source_data[source_key]["conversions"] += conversions
                source_data[source_key]["sessions"] += sessions
                
                daily_data.append({
                    "date": date,
                    "revenue": revenue,
                    "conversions": conversions,
                    "sessions": sessions
                })
        
        return {
            "total_revenue": total_revenue,
            "total_conversions": total_conversions,
            "total_sessions": total_sessions,
            "conversion_rate": (total_conversions / total_sessions * 100) if total_sessions > 0 else 0,
            "revenue_per_session": total_revenue / total_sessions if total_sessions > 0 else 0,
            "daily_data": daily_data,
            "source_breakdown": source_data,
            "currency": data.get("metadata", {}).get("currencyCode", "USD"),
            "timezone": data.get("metadata", {}).get("timeZone", "UTC")
        }
    
    def _process_traffic_analytics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GA4 traffic analytics response."""
        
        rows = data.get("rows", [])
        total_sessions = 0
        total_users = 0
        total_pageviews = 0
        
        page_performance = {}
        device_breakdown = {"desktop": 0, "mobile": 0, "tablet": 0}
        
        for row in rows:
            dims = [dv.get("value", "") for dv in row.get("dimensionValues", [])]
            metrics = [mv.get("value", "0") for mv in row.get("metricValues", [])]
            
            if len(dims) >= 5 and len(metrics) >= 6:
                date, page_path, source, medium, device = dims
                sessions, users, pageviews, bounce_rate, avg_duration, engagement = metrics
                
                # Convert strings to numbers
                sessions = int(float(sessions)) if sessions else 0
                users = int(float(users)) if users else 0
                pageviews = int(float(pageviews)) if pageviews else 0
                
                total_sessions += sessions
                total_users += users
                total_pageviews += pageviews
                
                # Track device breakdown
                device_lower = device.lower()
                if device_lower in device_breakdown:
                    device_breakdown[device_lower] += sessions
                
                # Track page performance
                if page_path not in page_performance:
                    page_performance[page_path] = {
                        "sessions": 0,
                        "users": 0,
                        "pageviews": 0
                    }
                
                page_performance[page_path]["sessions"] += sessions
                page_performance[page_path]["users"] += users
                page_performance[page_path]["pageviews"] += pageviews
        
        # Get top pages
        top_pages = sorted(
            page_performance.items(),
            key=lambda x: x[1]["sessions"],
            reverse=True
        )[:10]
        
        return {
            "total_sessions": total_sessions,
            "total_users": total_users,
            "total_pageviews": total_pageviews,
            "device_breakdown": device_breakdown,
            "top_pages": [{"path": path, **data} for path, data in top_pages],
            "pages_analyzed": len(page_performance)
        }
    
    def _process_conversion_funnel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GA4 conversion funnel response."""
        
        rows = data.get("rows", [])
        funnel_steps = {
            "page_view": {"count": 0, "revenue": 0},
            "view_item": {"count": 0, "revenue": 0},
            "add_to_cart": {"count": 0, "revenue": 0},
            "begin_checkout": {"count": 0, "revenue": 0},
            "purchase": {"count": 0, "revenue": 0}
        }
        
        for row in rows:
            dims = [dv.get("value", "") for dv in row.get("dimensionValues", [])]
            metrics = [mv.get("value", "0") for mv in row.get("metricValues", [])]
            
            if len(dims) >= 3 and len(metrics) >= 3:
                event_name, source, medium = dims
                event_count, conversions, revenue = metrics
                
                event_count = int(float(event_count)) if event_count else 0
                revenue = float(revenue) if revenue else 0
                
                if event_name in funnel_steps:
                    funnel_steps[event_name]["count"] += event_count
                    funnel_steps[event_name]["revenue"] += revenue
        
        # Calculate conversion rates
        page_views = funnel_steps["page_view"]["count"]
        conversion_rates = {}
        
        if page_views > 0:
            for step, data in funnel_steps.items():
                if step != "page_view":
                    conversion_rates[step] = (data["count"] / page_views) * 100
        
        return {
            "funnel_steps": funnel_steps,
            "conversion_rates": conversion_rates,
            "total_page_views": page_views,
            "final_conversion_rate": conversion_rates.get("purchase", 0)
        }
    
    def _process_organic_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GA4 organic performance response."""
        
        rows = data.get("rows", [])
        total_clicks = 0
        total_impressions = 0
        total_revenue = 0
        
        page_performance = []
        
        for row in rows:
            dims = [dv.get("value", "") for dv in row.get("dimensionValues", [])]
            metrics = [mv.get("value", "0") for mv in row.get("metricValues", [])]
            
            if len(dims) >= 3 and len(metrics) >= 6:
                date, page_path, landing_page = dims
                clicks, impressions, ctr, sessions, conversions, revenue = metrics
                
                # Convert strings to numbers
                clicks = int(float(clicks)) if clicks else 0
                impressions = int(float(impressions)) if impressions else 0
                ctr = float(ctr) if ctr else 0
                revenue = float(revenue) if revenue else 0
                
                total_clicks += clicks
                total_impressions += impressions
                total_revenue += revenue
                
                page_performance.append({
                    "page_path": page_path,
                    "clicks": clicks,
                    "impressions": impressions,
                    "ctr": ctr,
                    "revenue": revenue
                })
        
        overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "overall_ctr": overall_ctr,
            "total_organic_revenue": total_revenue,
            "page_performance": page_performance[:20],  # Top 20 pages
            "pages_analyzed": len(page_performance)
        }
    
    async def get_roi_metrics(
        self,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        campaign_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate ROI metrics for SEO and marketing campaigns.
        
        Args:
            start_date: Start date for the report
            end_date: End date for the report
            campaign_source: Optional filter by campaign source
            
        Returns:
            ROI metrics and attribution data
        """
        if not self.is_configured():
            raise ValueError("Google Analytics 4 is not configured.")
        
        try:
            # Build dimensions and filters
            dimensions = [
                {"name": "date"},
                {"name": "source"},
                {"name": "medium"},
                {"name": "campaign"},
                {"name": "landingPagePlusQueryString"}
            ]
            
            dimension_filter = None
            if campaign_source:
                dimension_filter = {
                    "filter": {
                        "fieldName": "source",
                        "stringFilter": {
                            "matchType": "CONTAINS",
                            "value": campaign_source
                        }
                    }
                }
            
            request_data = {
                "dimensions": dimensions,
                "metrics": [
                    {"name": "totalRevenue"},
                    {"name": "conversions"},
                    {"name": "sessions"},
                    {"name": "activeUsers"},
                    {"name": "newUsers"},
                    {"name": "purchaseRevenue"},
                    {"name": "adCost"},  # If available
                    {"name": "returnOnAdSpend"}  # If available
                ],
                "dateRanges": [{
                    "startDate": start_date,
                    "endDate": end_date
                }],
                "orderBys": [{
                    "metric": {"metricName": "totalRevenue"},
                    "desc": True
                }],
                "limit": 500
            }
            
            if dimension_filter:
                request_data["dimensionFilter"] = dimension_filter
            
            headers = {
                "Authorization": f"Bearer {self.access_token or self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/properties/{self.property_id}:runReport",
                    headers=headers,
                    json=request_data
                )
                response.raise_for_status()
                
                data = response.json()
                return self._process_roi_metrics(data)
                
        except Exception as e:
            logger.error(f"GA4 ROI metrics error: {e}")
            raise ValueError(f"Failed to fetch ROI metrics: {e}")
    
    def _process_roi_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GA4 ROI metrics response."""
        rows = data.get("rows", [])
        
        # Initialize tracking variables
        total_revenue = 0
        total_cost = 0
        total_conversions = 0
        total_sessions = 0
        
        campaign_data = {}
        landing_page_data = {}
        source_medium_data = {}
        
        for row in rows:
            dims = [dv.get("value", "") for dv in row.get("dimensionValues", [])]
            metrics = [mv.get("value", "0") for mv in row.get("metricValues", [])]
            
            if len(dims) >= 5 and len(metrics) >= 8:
                date, source, medium, campaign, landing_page = dims
                revenue, conversions, sessions, users, new_users, purchase_revenue, ad_cost, roas = metrics
                
                # Convert to numbers
                revenue = float(revenue) if revenue else 0
                conversions = int(float(conversions)) if conversions else 0
                sessions = int(float(sessions)) if sessions else 0
                ad_cost = float(ad_cost) if ad_cost else 0
                
                total_revenue += revenue
                total_cost += ad_cost
                total_conversions += conversions
                total_sessions += sessions
                
                # Track by campaign
                campaign_key = campaign or "(not set)"
                if campaign_key not in campaign_data:
                    campaign_data[campaign_key] = {
                        "revenue": 0,
                        "cost": 0,
                        "conversions": 0,
                        "sessions": 0,
                        "roi": 0
                    }
                
                campaign_data[campaign_key]["revenue"] += revenue
                campaign_data[campaign_key]["cost"] += ad_cost
                campaign_data[campaign_key]["conversions"] += conversions
                campaign_data[campaign_key]["sessions"] += sessions
                
                # Track by source/medium
                source_medium_key = f"{source}/{medium}"
                if source_medium_key not in source_medium_data:
                    source_medium_data[source_medium_key] = {
                        "revenue": 0,
                        "conversions": 0,
                        "sessions": 0
                    }
                
                source_medium_data[source_medium_key]["revenue"] += revenue
                source_medium_data[source_medium_key]["conversions"] += conversions
                source_medium_data[source_medium_key]["sessions"] += sessions
                
                # Track by landing page
                if landing_page and revenue > 0:
                    if landing_page not in landing_page_data:
                        landing_page_data[landing_page] = {
                            "revenue": 0,
                            "conversions": 0,
                            "sessions": 0
                        }
                    
                    landing_page_data[landing_page]["revenue"] += revenue
                    landing_page_data[landing_page]["conversions"] += conversions
                    landing_page_data[landing_page]["sessions"] += sessions
        
        # Calculate ROI for campaigns
        for campaign_key, data in campaign_data.items():
            if data["cost"] > 0:
                data["roi"] = ((data["revenue"] - data["cost"]) / data["cost"]) * 100
            else:
                data["roi"] = float('inf') if data["revenue"] > 0 else 0
        
        # Sort campaigns by revenue
        top_campaigns = sorted(
            campaign_data.items(),
            key=lambda x: x[1]["revenue"],
            reverse=True
        )[:10]
        
        # Sort landing pages by revenue
        top_landing_pages = sorted(
            landing_page_data.items(),
            key=lambda x: x[1]["revenue"],
            reverse=True
        )[:10]
        
        # Calculate overall ROI
        overall_roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else (float('inf') if total_revenue > 0 else 0)
        
        return {
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_cost": round(total_cost, 2),
                "total_profit": round(total_revenue - total_cost, 2),
                "overall_roi": round(overall_roi, 2) if overall_roi != float('inf') else "∞",
                "total_conversions": total_conversions,
                "total_sessions": total_sessions,
                "conversion_rate": round((total_conversions / total_sessions * 100), 2) if total_sessions > 0 else 0,
                "average_order_value": round(total_revenue / total_conversions, 2) if total_conversions > 0 else 0
            },
            "top_campaigns": [
                {"campaign": name, **data} for name, data in top_campaigns
            ],
            "top_landing_pages": [
                {"page": page, **data} for page, data in top_landing_pages
            ],
            "source_medium_breakdown": source_medium_data,
            "currency": data.get("metadata", {}).get("currencyCode", "USD")
        }
    
    async def get_ga4_properties(self) -> List[Dict[str, Any]]:
        """
        Get list of GA4 properties the user has access to.
        
        Returns:
            List of GA4 properties
        """
        if not self.access_token:
            raise ValueError("OAuth access token required for this operation")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.management_api_url}/accounts",
                    headers=headers
                )
                
                if response.status_code == 404:
                    # Try the data API endpoint
                    response = await client.get(
                        f"{self.base_url}/properties",
                        headers=headers
                    )
                
                response.raise_for_status()
                data = response.json()
                
                properties = []
                
                # If we got accounts, list properties for each
                if "accounts" in data:
                    for account in data.get("accounts", []):
                        account_name = account.get("name", "")
                        
                        # Get properties for this account
                        props_response = await client.get(
                            f"{self.management_api_url}/{account_name}/properties",
                            headers=headers
                        )
                        
                        if props_response.status_code == 200:
                            props_data = props_response.json()
                            for prop in props_data.get("properties", []):
                                properties.append({
                                    "property_id": prop.get("name", "").split("/")[-1],
                                    "display_name": prop.get("displayName", ""),
                                    "account": account.get("displayName", ""),
                                    "time_zone": prop.get("timeZone", "UTC"),
                                    "currency_code": prop.get("currencyCode", "USD")
                                })
                
                # Direct properties list
                elif "properties" in data:
                    for prop in data.get("properties", []):
                        properties.append({
                            "property_id": prop.get("name", "").split("/")[-1],
                            "display_name": prop.get("displayName", prop.get("name", "")),
                            "time_zone": prop.get("timeZone", "UTC"),
                            "currency_code": prop.get("currencyCode", "USD")
                        })
                
                return properties
                
        except Exception as e:
            logger.error(f"Failed to get GA4 properties: {e}")
            raise ValueError(f"Failed to retrieve GA4 properties: {e}")


# Create service instance
ga4_service = GoogleAnalytics4Service()
