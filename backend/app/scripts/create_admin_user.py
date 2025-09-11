#!/usr/bin/env python3
"""
Admin User Creation Script for Voltex SEO Decision Superiority Engine

This script creates a superuser account in the database. It can be used for:
- Initial setup of the application
- Creating additional admin users
- Password reset for existing admin users

Usage:
    python create_admin_user.py
    python create_admin_user.py --email admin@example.com --password securepass123
    python create_admin_user.py --interactive
    python create_admin_user.py --reset-password admin@example.com
"""

import asyncio
import argparse
import getpass
import logging
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
# Import the base module to register all models with SQLAlchemy
from app.db import base  # noqa: F401
from app.models.user import User
from app.auth.core.security import pwd_context
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AdminUserManager:
    """Manages admin user creation and management."""
    
    def __init__(self):
        self.session: Optional[AsyncSession] = None
    
    async def __aenter__(self):
        self.session = async_session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_user_exists(self, email: str) -> Optional[User]:
        """Check if a user with the given email exists."""
        try:
            result = await self.session.execute(
                select(User).filter(User.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error checking if user exists: {e}")
            return None
    
    async def create_admin_user(
        self, 
        email: str, 
        password: str, 
        full_name: str = "Voltex Admin",
        company: str = "Voltex",
        position: str = "Administrator",
        force_update: bool = False
    ) -> bool:
        """
        Creates or updates an admin user in the database.
        
        Args:
            email: User's email address
            password: User's password (will be hashed)
            full_name: User's full name
            company: User's company
            position: User's position
            force_update: If True, update existing user's password and details
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if user already exists
            existing_user = await self.check_user_exists(email)
            
            if existing_user:
                if not force_update:
                    logger.warning(f"User '{email}' already exists. Use --force to update.")
                    return False
                
                # Update existing user
                logger.info(f"Updating existing user: {email}")
                existing_user.hashed_password = pwd_context.hash(password)
                existing_user.full_name = full_name
                existing_user.company = company
                existing_user.position = position
                existing_user.is_superuser = True
                existing_user.is_active = True
                existing_user.updated_at = datetime.utcnow()
                existing_user.password_last_changed = datetime.utcnow()
                
                await self.session.commit()
                logger.info(f"Successfully updated admin user: {email}")
                return True
            
            # Create new admin user
            logger.info(f"Creating new admin user: {email}")
            
            # Hash the password
            hashed_password = pwd_context.hash(password)
            
            # Create the new admin user with all required fields
            new_admin = User(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                company=company,
                company_name=company,  # For auth service compatibility
                position=position,
                is_superuser=True,
                is_active=True,
                subscription_plan="enterprise",  # Give admin enterprise access
                subscription_status="active",
                subscription_start_date=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                password_last_changed=datetime.utcnow()
            )
            
            self.session.add(new_admin)
            await self.session.commit()
            
            logger.info(f"✅ Successfully created admin user: {email}")
            logger.info(f"   Full Name: {full_name}")
            logger.info(f"   Company: {company}")
            logger.info(f"   Position: {position}")
            logger.info(f"   Superuser: Yes")
            logger.info(f"   Active: Yes")
            logger.info(f"   Subscription: Enterprise")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating/updating admin user: {e}", exc_info=True)
            await self.session.rollback()
            return False
    
    async def reset_user_password(self, email: str, new_password: str) -> bool:
        """
        Reset a user's password.
        
        Args:
            email: User's email address
            new_password: New password (will be hashed)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user = await self.check_user_exists(email)
            
            if not user:
                logger.error(f"❌ User '{email}' not found.")
                return False
            
            # Update password
            user.hashed_password = pwd_context.hash(new_password)
            user.password_last_changed = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            
            await self.session.commit()
            logger.info(f"✅ Successfully reset password for user: {email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error resetting password: {e}", exc_info=True)
            await self.session.rollback()
            return False
    
    async def list_admin_users(self) -> None:
        """List all admin users in the database."""
        try:
            result = await self.session.execute(
                select(User).filter(User.is_superuser == True)
            )
            admin_users = result.scalars().all()
            
            if not admin_users:
                logger.info("No admin users found in the database.")
                return
            
            logger.info(f"Found {len(admin_users)} admin user(s):")
            for user in admin_users:
                status = "🟢 Active" if user.is_active else "🔴 Inactive"
                logger.info(f"  • {user.email} ({user.full_name}) - {status}")
                
        except Exception as e:
            logger.error(f"❌ Error listing admin users: {e}", exc_info=True)


def validate_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    return True, ""


def get_user_input(prompt: str, secret: bool = False) -> str:
    """Get user input with optional secret mode."""
    if secret:
        return getpass.getpass(prompt)
    return input(prompt).strip()


async def interactive_mode() -> None:
    """Run the script in interactive mode."""
    print("\n🚀 Voltex Admin User Creation - Interactive Mode")
    print("=" * 50)
    
    # Get email
    while True:
        email = get_user_input("Enter admin email: ").strip()
        if not email:
            print("❌ Email is required.")
            continue
        if not validate_email(email):
            print("❌ Please enter a valid email address.")
            continue
        break
    
    # Get password
    while True:
        password = get_user_input("Enter admin password: ", secret=True)
        if not password:
            print("❌ Password is required.")
            continue
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            print(f"❌ {error_msg}")
            continue
        
        confirm_password = get_user_input("Confirm admin password: ", secret=True)
        if password != confirm_password:
            print("❌ Passwords do not match.")
            continue
        break
    
    # Get additional details
    full_name = get_user_input("Enter full name (optional): ").strip() or "Voltex Admin"
    company = get_user_input("Enter company (optional): ").strip() or "Voltex"
    position = get_user_input("Enter position (optional): ").strip() or "Administrator"
    
    # Check if user exists
    async with AdminUserManager() as manager:
        existing_user = await manager.check_user_exists(email)
        
        if existing_user:
            print(f"\n⚠️  User '{email}' already exists.")
            update = get_user_input("Do you want to update this user? (y/N): ").strip().lower()
            if update not in ['y', 'yes']:
                print("Operation cancelled.")
                return
            force_update = True
        else:
            force_update = False
        
        # Create/update user
        success = await manager.create_admin_user(
            email=email,
            password=password,
            full_name=full_name,
            company=company,
            position=position,
            force_update=force_update
        )
        
        if success:
            print("\n✅ Admin user created/updated successfully!")
        else:
            print("\n❌ Failed to create/update admin user.")


async def main():
    """Main function to handle command-line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Create or manage admin users for Voltex SEO Decision Superiority Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_admin_user.py                    # Use default settings
  python create_admin_user.py --interactive      # Interactive mode
  python create_admin_user.py --email admin@example.com --password securepass123
  python create_admin_user.py --reset-password admin@example.com
  python create_admin_user.py --list             # List all admin users
        """
    )
    
    parser.add_argument(
        "--email",
        help="Admin user email address"
    )
    parser.add_argument(
        "--password",
        help="Admin user password"
    )
    parser.add_argument(
        "--full-name",
        default="Voltex Admin",
        help="Admin user full name (default: Voltex Admin)"
    )
    parser.add_argument(
        "--company",
        default="Voltex",
        help="Admin user company (default: Voltex)"
    )
    parser.add_argument(
        "--position",
        default="Administrator",
        help="Admin user position (default: Administrator)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--reset-password",
        metavar="EMAIL",
        help="Reset password for existing user"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all admin users"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update existing user"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.reset_password and not validate_email(args.reset_password):
        logger.error("❌ Invalid email address for password reset.")
        sys.exit(1)
    
    if args.email and not validate_password(args.password or ""):
        logger.error("❌ Invalid password provided.")
        sys.exit(1)
    
    try:
        async with AdminUserManager() as manager:
            # Handle different modes
            if args.list:
                await manager.list_admin_users()
                return
            
            if args.reset_password:
                if not args.password:
                    password = get_user_input("Enter new password: ", secret=True)
                else:
                    password = args.password
                
                is_valid, error_msg = validate_password(password)
                if not is_valid:
                    logger.error(f"❌ {error_msg}")
                    sys.exit(1)
                
                success = await manager.reset_user_password(args.reset_password, password)
                sys.exit(0 if success else 1)
            
            if args.interactive:
                await interactive_mode()
                return
            
            # Default mode or command-line arguments
            email = args.email or settings.FIRST_SUPERUSER_EMAIL
            password = args.password or settings.FIRST_SUPERUSER_PASSWORD
            
            logger.info(f"Creating admin user with email: {email}")
            
            success = await manager.create_admin_user(
                email=email,
                password=password,
                full_name=args.full_name,
                company=args.company,
                position=args.position,
                force_update=args.force
            )
            
            if success:
                logger.info("✅ Admin user creation completed successfully!")
                sys.exit(0)
            else:
                logger.error("❌ Admin user creation failed!")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("\n⚠️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
