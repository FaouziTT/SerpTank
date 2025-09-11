"""Request signing and verification for API security."""

import hashlib
import hmac
import time
import secrets
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode

from fastapi import Request, HTTPException, status
from pydantic import BaseModel

from app.auth.core.config import get_settings


class SignatureConfig(BaseModel):
    """Configuration for request signing."""
    secret_key: str
    algorithm: str = "sha256"
    include_timestamp: bool = True
    timestamp_tolerance: int = 300  # 5 minutes in seconds
    include_nonce: bool = True


class RequestSigner:
    """Handles request signing and verification."""
    
    def __init__(self, config: SignatureConfig):
        self.config = config
        self._algorithm = getattr(hashlib, config.algorithm)
    
    def sign_request(
        self,
        method: str,
        url: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        timestamp: Optional[int] = None,
        nonce: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sign a request and return signature components."""
        if self.config.include_timestamp and timestamp is None:
            timestamp = int(time.time())
        
        if self.config.include_nonce and nonce is None:
            nonce = secrets.token_hex(16)
        
        # Create canonical string
        canonical_string = self._create_canonical_string(
            method, url, body, headers, timestamp, nonce
        )
        
        # Generate signature
        signature = self._generate_signature(canonical_string)
        
        return {
            "signature": signature,
            "timestamp": timestamp,
            "nonce": nonce
        }
    
    def verify_signature(
        self,
        signature: str,
        method: str,
        url: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        timestamp: Optional[int] = None,
        nonce: Optional[str] = None
    ) -> bool:
        """Verify a request signature."""
        # Check timestamp if included
        if self.config.include_timestamp and timestamp:
            current_time = int(time.time())
            if abs(current_time - timestamp) > self.config.timestamp_tolerance:
                return False
        
        # Recreate canonical string
        canonical_string = self._create_canonical_string(
            method, url, body, headers, timestamp, nonce
        )
        
        # Generate expected signature
        expected_signature = self._generate_signature(canonical_string)
        
        # Constant-time comparison
        return hmac.compare_digest(signature, expected_signature)
    
    def _create_canonical_string(
        self,
        method: str,
        url: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        timestamp: Optional[int] = None,
        nonce: Optional[str] = None
    ) -> str:
        """Create canonical string for signing."""
        parts = [
            method.upper(),
            self._normalize_url(url)
        ]
        
        if timestamp is not None:
            parts.append(str(timestamp))
        
        if nonce is not None:
            parts.append(nonce)
        
        if headers:
            header_string = self._canonicalize_headers(headers)
            if header_string:
                parts.append(header_string)
        
        if body:
            body_hash = self._algorithm(body).hexdigest()
            parts.append(body_hash)
        
        return "\n".join(parts)
    
    def _generate_signature(self, canonical_string: str) -> str:
        """Generate HMAC signature."""
        signature = hmac.new(
            self.config.secret_key.encode(),
            canonical_string.encode(),
            self._algorithm
        )
        return signature.hexdigest()
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent signing."""
        parsed = urlparse(url)
        
        # Sort query parameters
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            sorted_params = sorted(params.items())
            query_string = urlencode(
                [(k, v) for k, vals in sorted_params for v in vals],
                doseq=True
            )
            url = url.replace(parsed.query, query_string)
        
        return url
    
    def _canonicalize_headers(self, headers: Dict[str, str]) -> str:
        """Canonicalize headers for signing."""
        # Only include specific headers
        signed_headers = {
            "content-type",
            "content-length",
            "host",
            "x-api-version"
        }
        
        canonical_headers = []
        for key, value in sorted(headers.items()):
            if key.lower() in signed_headers:
                canonical_headers.append(f"{key.lower()}:{value.strip()}")
        
        return "\n".join(canonical_headers)


class SignatureMiddleware:
    """Middleware to verify request signatures."""
    
    def __init__(self, signer: RequestSigner, exclude_paths: Optional[set] = None):
        self.signer = signer
        self.exclude_paths = exclude_paths or {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
    
    async def __call__(self, request: Request, call_next):
        """Verify request signature if required."""
        # Skip verification for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract signature headers
        signature = request.headers.get("X-Request-Signature")
        timestamp_str = request.headers.get("X-Request-Timestamp")
        nonce = request.headers.get("X-Request-Nonce")
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing request signature"
            )
        
        # Parse timestamp
        timestamp = None
        if timestamp_str:
            try:
                timestamp = int(timestamp_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid timestamp format"
                )
        
        # Read body for verification
        body = await request.body()
        
        # Reconstruct headers
        headers = dict(request.headers)
        
        # Verify signature
        is_valid = self.signer.verify_signature(
            signature=signature,
            method=request.method,
            url=str(request.url),
            body=body if body else None,
            headers=headers,
            timestamp=timestamp,
            nonce=nonce
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid request signature"
            )
        
        # Continue with request
        return await call_next(request)


def create_request_signer() -> Optional[RequestSigner]:
    """Create request signer from settings."""
    settings = get_settings()
    
    # Only enable in production or when explicitly configured
    if not settings.enable_request_signing:
        return None
    
    if not settings.signing_secret_key:
        raise ValueError("Request signing enabled but no secret key configured")
    
    config = SignatureConfig(
        secret_key=settings.signing_secret_key,
        algorithm=settings.signing_algorithm,
        include_timestamp=True,
        timestamp_tolerance=300,  # 5 minutes
        include_nonce=True
    )
    
    return RequestSigner(config)


# Dependency for request signature verification
async def verify_request_signature(request: Request):
    """Verify request signature for protected endpoints."""
    signer = create_request_signer()
    
    if not signer:
        # Signing not enabled
        return
    
    # Extract signature headers
    signature = request.headers.get("X-Request-Signature")
    timestamp_str = request.headers.get("X-Request-Timestamp")
    nonce = request.headers.get("X-Request-Nonce")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing request signature"
        )
    
    # Parse timestamp
    timestamp = None
    if timestamp_str:
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp format"
            )
    
    # Read body
    body = await request.body()
    
    # Verify
    is_valid = signer.verify_signature(
        signature=signature,
        method=request.method,
        url=str(request.url),
        body=body if body else None,
        headers=dict(request.headers),
        timestamp=timestamp,
        nonce=nonce
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid request signature"
        )