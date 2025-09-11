"""
Domain Verification Service

This service handles domain verification for users to prove ownership
of their websites. Supports multiple verification methods:
- HTML file upload
- DNS TXT record
- HTML meta tag
"""
import asyncio
import hashlib
import logging
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import re

import httpx
import dns.resolver
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.domain import Domain
from app.models.user import User

logger = logging.getLogger(__name__)


class DomainVerificationService:
    """Handle domain verification for users."""
    
    VERIFICATION_METHODS = ["html_file", "dns_record", "meta_tag"]
    VERIFICATION_TIMEOUT = 10  # seconds
    
    def __init__(self):
        self.http_client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.http_client = httpx.AsyncClient(timeout=self.VERIFICATION_TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.http_client:
            await self.http_client.aclose()
    
    def _normalize_domain(self, domain: str) -> Tuple[str, str, str]:
        """
        Normalize domain input and extract components.
        
        Args:
            domain: Domain string (e.g., "https://www.example.com" or "example.com")
            
        Returns:
            Tuple of (base_domain, subdomain, full_domain)
        """
        # Remove protocol if present
        if domain.startswith(('http://', 'https://')):
            parsed = urlparse(domain)
            domain = parsed.netloc
        
        # Split domain parts
        parts = domain.lower().split('.')
        
        if len(parts) < 2:
            raise ValueError("Invalid domain format")
        
        # Handle common subdomains
        if len(parts) >= 3 and parts[0] in ['www', 'blog', 'shop', 'app']:
            subdomain = parts[0]
            base_domain = '.'.join(parts[1:])
        else:
            subdomain = None
            base_domain = domain
        
        full_domain = domain
        
        return base_domain, subdomain, full_domain
    
    def _generate_verification_token(self) -> str:
        """Generate a unique verification token."""
        return secrets.token_urlsafe(32)
    
    def _generate_verification_value(self, method: str, domain: str, token: str) -> str:
        """
        Generate verification value based on method.
        
        Args:
            method: Verification method
            domain: Domain being verified
            token: Verification token
            
        Returns:
            Verification value (file content, DNS record value, or meta tag content)
        """
        if method == "html_file":
            return f"voltex-domain-verification: {token}"
        
        elif method == "dns_record":
            return f"voltex-verification={token}"
        
        elif method == "meta_tag":
            return f'<meta name="voltex-site-verification" content="{token}" />'
        
        else:
            raise ValueError(f"Unknown verification method: {method}")
    
    async def initiate_verification(
        self, 
        db: AsyncSession, 
        user_id: int, 
        domain: str, 
        method: str
    ) -> Dict:
        """
        Initiate domain verification process.
        
        Args:
            db: Database session
            user_id: User ID
            domain: Domain to verify
            method: Verification method
            
        Returns:
            Verification instructions
        """
        if method not in self.VERIFICATION_METHODS:
            raise ValueError(f"Invalid verification method. Choose from: {', '.join(self.VERIFICATION_METHODS)}")
        
        # Normalize domain
        base_domain, subdomain, full_domain = self._normalize_domain(domain)
        
        # Check if domain already exists for user
        result = await db.execute(
            select(Domain).where(
                Domain.user_id == user_id,
                Domain.full_domain == full_domain
            )
        )
        existing_domain = result.scalar_one_or_none()
        
        if existing_domain and existing_domain.is_verified:
            raise ValueError("Domain is already verified")
        
        # Generate verification token and value
        token = self._generate_verification_token()
        verification_value = self._generate_verification_value(method, full_domain, token)
        
        # Create or update domain record
        if existing_domain:
            domain_obj = existing_domain
            domain_obj.verification_method = method
            domain_obj.verification_token = token
            domain_obj.verification_value = verification_value
            domain_obj.status = "pending"
            domain_obj.is_verified = False
        else:
            domain_obj = Domain(
                user_id=user_id,
                domain=base_domain,
                subdomain=subdomain,
                full_domain=full_domain,
                verification_method=method,
                verification_token=token,
                verification_value=verification_value,
                status="pending"
            )
            db.add(domain_obj)
        
        await db.commit()
        await db.refresh(domain_obj)
        
        # Generate instructions based on method
        instructions = self._get_verification_instructions(method, full_domain, token, verification_value)
        
        logger.info(f"Initiated {method} verification for domain {full_domain} for user {user_id}")
        
        return {
            "domain_id": domain_obj.id,
            "domain": full_domain,
            "method": method,
            "token": token,
            "instructions": instructions,
            "status": "pending"
        }
    
    def _get_verification_instructions(self, method: str, domain: str, token: str, value: str) -> Dict:
        """Get verification instructions for the user."""
        if method == "html_file":
            return {
                "method": "HTML File Upload",
                "steps": [
                    f"Create a file named 'voltex-verification-{token}.txt'",
                    f"Add this content to the file: {value}",
                    f"Upload the file to your website root: https://{domain}/voltex-verification-{token}.txt",
                    "Click 'Verify' to complete the process"
                ],
                "verification_url": f"https://{domain}/voltex-verification-{token}.txt",
                "file_content": value
            }
        
        elif method == "dns_record":
            return {
                "method": "DNS TXT Record",
                "steps": [
                    "Go to your domain's DNS management panel",
                    f"Create a new TXT record for '{domain}'",
                    f"Set the value to: {value}",
                    "Save the DNS record and wait for propagation (up to 24 hours)",
                    "Click 'Verify' to complete the process"
                ],
                "record_type": "TXT",
                "record_name": domain,
                "record_value": value
            }
        
        elif method == "meta_tag":
            return {
                "method": "HTML Meta Tag",
                "steps": [
                    "Add this meta tag to the <head> section of your homepage",
                    f"Meta tag: {value}",
                    "Save and publish your homepage",
                    "Click 'Verify' to complete the process"
                ],
                "meta_tag": value,
                "verification_url": f"https://{domain}/"
            }
        
        return {}
    
    async def verify_domain(self, db: AsyncSession, domain_id: int, user_id: int) -> Dict:
        """
        Verify a domain using the configured method.
        
        Args:
            db: Database session
            domain_id: Domain ID
            user_id: User ID (for security)
            
        Returns:
            Verification result
        """
        # Get domain record
        result = await db.execute(
            select(Domain).where(
                Domain.id == domain_id,
                Domain.user_id == user_id
            )
        )
        domain_obj = result.scalar_one_or_none()
        
        if not domain_obj:
            raise ValueError("Domain not found")
        
        if domain_obj.is_verified:
            return {
                "success": True,
                "message": "Domain is already verified",
                "verified_at": domain_obj.verified_at
            }
        
        # Increment check count
        domain_obj.check_count += 1
        domain_obj.last_checked = datetime.now()
        
        try:
            # Perform verification based on method
            if domain_obj.verification_method == "html_file":
                success = await self._verify_html_file(domain_obj)
            elif domain_obj.verification_method == "dns_record":
                success = await self._verify_dns_record(domain_obj)
            elif domain_obj.verification_method == "meta_tag":
                success = await self._verify_meta_tag(domain_obj)
            else:
                raise ValueError(f"Unknown verification method: {domain_obj.verification_method}")
            
            if success:
                domain_obj.is_verified = True
                domain_obj.status = "verified"
                domain_obj.verified_at = datetime.now()
                
                await db.commit()
                
                logger.info(f"Successfully verified domain {domain_obj.full_domain} for user {user_id}")
                
                return {
                    "success": True,
                    "message": "Domain verified successfully",
                    "domain": domain_obj.full_domain,
                    "verified_at": domain_obj.verified_at
                }
            else:
                domain_obj.status = "failed"
                await db.commit()
                
                return {
                    "success": False,
                    "message": "Domain verification failed. Please check your setup and try again.",
                    "check_count": domain_obj.check_count
                }
                
        except Exception as e:
            logger.error(f"Error verifying domain {domain_obj.full_domain}: {e}")
            domain_obj.status = "failed"
            await db.commit()
            
            return {
                "success": False,
                "message": f"Verification error: {str(e)}",
                "check_count": domain_obj.check_count
            }
    
    async def _verify_html_file(self, domain_obj: Domain) -> bool:
        """Verify domain using HTML file method."""
        verification_url = f"https://{domain_obj.full_domain}/voltex-verification-{domain_obj.verification_token}.txt"
        
        try:
            if not self.http_client:
                async with httpx.AsyncClient(timeout=self.VERIFICATION_TIMEOUT) as client:
                    response = await client.get(verification_url)
            else:
                response = await self.http_client.get(verification_url)
            
            if response.status_code == 200:
                content = response.text.strip()
                expected_content = domain_obj.verification_value
                return content == expected_content
            
            return False
            
        except Exception as e:
            logger.warning(f"HTML file verification failed for {domain_obj.full_domain}: {e}")
            return False
    
    async def _verify_dns_record(self, domain_obj: Domain) -> bool:
        """Verify domain using DNS TXT record method."""
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.VERIFICATION_TIMEOUT
            
            answers = resolver.resolve(domain_obj.full_domain, 'TXT')
            
            expected_value = domain_obj.verification_value
            
            for answer in answers:
                txt_record = answer.to_text().strip('"')
                if txt_record == expected_value:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"DNS verification failed for {domain_obj.full_domain}: {e}")
            return False
    
    async def _verify_meta_tag(self, domain_obj: Domain) -> bool:
        """Verify domain using HTML meta tag method."""
        verification_url = f"https://{domain_obj.full_domain}/"
        
        try:
            if not self.http_client:
                async with httpx.AsyncClient(timeout=self.VERIFICATION_TIMEOUT) as client:
                    response = await client.get(verification_url)
            else:
                response = await self.http_client.get(verification_url)
            
            if response.status_code == 200:
                html_content = response.text
                
                # Extract meta tag content
                meta_pattern = r'<meta[^>]*name=["\']voltex-site-verification["\'][^>]*content=["\']([^"\']+)["\'][^>]*>'
                match = re.search(meta_pattern, html_content, re.IGNORECASE)
                
                if match:
                    meta_content = match.group(1)
                    return meta_content == domain_obj.verification_token
            
            return False
            
        except Exception as e:
            logger.warning(f"Meta tag verification failed for {domain_obj.full_domain}: {e}")
            return False
    
    async def get_user_domains(self, db: AsyncSession, user_id: int) -> List[Dict]:
        """Get all domains for a user."""
        result = await db.execute(
            select(Domain).where(Domain.user_id == user_id).order_by(Domain.created_at.desc())
        )
        domains = result.scalars().all()
        
        domain_list = []
        for domain in domains:
            domain_list.append({
                "id": domain.id,
                "domain": domain.full_domain,
                "base_domain": domain.domain,
                "subdomain": domain.subdomain,
                "is_verified": domain.is_verified,
                "verification_method": domain.verification_method,
                "status": domain.status,
                "verified_at": domain.verified_at.isoformat() if domain.verified_at else None,
                "created_at": domain.created_at.isoformat(),
                "last_checked": domain.last_checked.isoformat() if domain.last_checked else None,
                "check_count": domain.check_count,
                "in_search_console": domain.in_search_console,
                "in_analytics": domain.in_analytics
            })
        
        return domain_list
    
    async def delete_domain(self, db: AsyncSession, domain_id: int, user_id: int) -> bool:
        """Delete a domain verification."""
        result = await db.execute(
            select(Domain).where(
                Domain.id == domain_id,
                Domain.user_id == user_id
            )
        )
        domain_obj = result.scalar_one_or_none()
        
        if not domain_obj:
            return False
        
        await db.delete(domain_obj)
        await db.commit()
        
        logger.info(f"Deleted domain {domain_obj.full_domain} for user {user_id}")
        return True


# Global domain verification service
domain_verification_service = DomainVerificationService()
