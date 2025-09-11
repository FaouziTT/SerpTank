"""
Domain Verification API endpoints.

This module provides endpoints for domain verification and management,
allowing users to prove ownership of their websites.
"""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.db.session import get_db
from app.models.user import User
from app.services.domain_verification import domain_verification_service

router = APIRouter()
logger = logging.getLogger(__name__)


class DomainVerificationRequest(BaseModel):
    """Request model for domain verification."""
    domain: str = Field(..., description="Domain to verify (e.g., example.com or www.example.com)")
    method: str = Field(..., description="Verification method: html_file, dns_record, or meta_tag")


class DomainVerificationResponse(BaseModel):
    """Response model for domain verification initiation."""
    domain_id: int = Field(..., description="Domain ID")
    domain: str = Field(..., description="Full domain name")
    method: str = Field(..., description="Verification method")
    token: str = Field(..., description="Verification token")
    instructions: Dict[str, Any] = Field(..., description="Verification instructions")
    status: str = Field(..., description="Verification status")


class DomainVerifyRequest(BaseModel):
    """Request model for verifying a domain."""
    domain_id: int = Field(..., description="Domain ID to verify")


class DomainVerifyResponse(BaseModel):
    """Response model for domain verification result."""
    success: bool = Field(..., description="Whether verification was successful")
    message: str = Field(..., description="Verification result message")
    domain: str = Field(None, description="Verified domain")
    verified_at: str = Field(None, description="Verification timestamp")
    check_count: int = Field(None, description="Number of verification attempts")


class DomainListResponse(BaseModel):
    """Response model for user's domains list."""
    domains: List[Dict[str, Any]] = Field(..., description="List of user's domains")
    total_domains: int = Field(..., description="Total number of domains")
    verified_domains: int = Field(..., description="Number of verified domains")


@router.post("/verify/initiate", response_model=DomainVerificationResponse)
async def initiate_domain_verification(
    request: DomainVerificationRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DomainVerificationResponse:
    """
    Initiate domain verification process.
    
    Starts the verification process for a domain using the specified method.
    Returns instructions for completing the verification.
    """
    try:
        result = await domain_verification_service.initiate_verification(
            db=db,
            user_id=current_user.id,
            domain=request.domain,
            method=request.method
        )
        
        return DomainVerificationResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error initiating domain verification for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate domain verification: {str(e)}"
        )


@router.post("/verify/complete", response_model=DomainVerifyResponse)
async def complete_domain_verification(
    request: DomainVerifyRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DomainVerifyResponse:
    """
    Complete domain verification.
    
    Checks if the user has completed the verification setup
    (uploaded file, added DNS record, or meta tag) and verifies the domain.
    """
    try:
        result = await domain_verification_service.verify_domain(
            db=db,
            domain_id=request.domain_id,
            user_id=current_user.id
        )
        
        return DomainVerifyResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error completing domain verification for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete domain verification: {str(e)}"
        )


@router.get("/list", response_model=DomainListResponse)
async def get_user_domains(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DomainListResponse:
    """
    Get list of user's domains and their verification status.
    
    Returns all domains associated with the user, including verification
    status, methods used, and timestamps.
    """
    try:
        domains = await domain_verification_service.get_user_domains(
            db=db,
            user_id=current_user.id
        )
        
        verified_count = sum(1 for domain in domains if domain["is_verified"])
        
        return DomainListResponse(
            domains=domains,
            total_domains=len(domains),
            verified_domains=verified_count
        )
        
    except Exception as e:
        logger.error(f"Error getting domains for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get domains: {str(e)}"
        )


@router.delete("/delete/{domain_id}")
async def delete_domain(
    domain_id: int,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete a domain verification.
    
    Removes a domain from the user's list. This cannot be undone.
    """
    try:
        success = await domain_verification_service.delete_domain(
            db=db,
            domain_id=domain_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domain not found"
            )
        
        return {"message": "Domain deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting domain {domain_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete domain: {str(e)}"
        )


@router.get("/methods")
async def get_verification_methods() -> Dict[str, Any]:
    """
    Get available domain verification methods and their descriptions.
    
    Returns information about each verification method to help users
    choose the best option for their setup.
    """
    return {
        "methods": [
            {
                "id": "html_file",
                "name": "HTML File Upload",
                "description": "Upload a verification file to your website root directory",
                "difficulty": "Easy",
                "requirements": [
                    "Access to upload files to your website",
                    "Website accessible via HTTPS"
                ],
                "time_to_verify": "Immediate"
            },
            {
                "id": "dns_record",
                "name": "DNS TXT Record",
                "description": "Add a TXT record to your domain's DNS settings",
                "difficulty": "Medium",
                "requirements": [
                    "Access to your domain's DNS management panel",
                    "Knowledge of DNS record management"
                ],
                "time_to_verify": "Up to 24 hours (DNS propagation)"
            },
            {
                "id": "meta_tag",
                "name": "HTML Meta Tag",
                "description": "Add a meta tag to your website's homepage",
                "difficulty": "Easy",
                "requirements": [
                    "Access to edit your website's HTML",
                    "Ability to modify the <head> section"
                ],
                "time_to_verify": "Immediate"
            }
        ],
        "recommendations": {
            "html_file": "Best for most users - quick and easy",
            "dns_record": "Best for technical users or when you can't modify website files",
            "meta_tag": "Best when you have easy access to edit your homepage HTML"
        }
    }


@router.get("/status/{domain_id}")
async def get_domain_verification_status(
    domain_id: int,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed verification status for a specific domain.
    
    Returns current status, verification method, attempts, and
    troubleshooting information if verification failed.
    """
    try:
        domains = await domain_verification_service.get_user_domains(
            db=db,
            user_id=current_user.id
        )
        
        domain = next((d for d in domains if d["id"] == domain_id), None)
        
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domain not found"
            )
        
        # Add troubleshooting info for failed verifications
        troubleshooting = []
        if domain["status"] == "failed":
            if domain["verification_method"] == "html_file":
                troubleshooting = [
                    "Ensure the verification file is uploaded to the correct location",
                    "Check that your website is accessible via HTTPS",
                    "Verify the file content matches exactly (no extra spaces or characters)",
                    "Make sure your server returns the file with correct MIME type"
                ]
            elif domain["verification_method"] == "dns_record":
                troubleshooting = [
                    "Verify the TXT record was added correctly",
                    "Wait for DNS propagation (can take up to 24 hours)",
                    "Check the record value matches exactly",
                    "Ensure there are no quotes around the record value"
                ]
            elif domain["verification_method"] == "meta_tag":
                troubleshooting = [
                    "Ensure the meta tag is in the <head> section of your homepage",
                    "Check that the meta tag content matches exactly",
                    "Verify your homepage is accessible via HTTPS",
                    "Make sure the meta tag wasn't modified by your CMS"
                ]
        
        return {
            **domain,
            "troubleshooting": troubleshooting
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting domain status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get domain status: {str(e)}"
        )
