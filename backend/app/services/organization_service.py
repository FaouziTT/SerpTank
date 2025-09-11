# In app/services/organization_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from slugify import slugify  # You may need to install this: pip install python-slugify

from app.models.organization import Organization, OrganizationMember, MemberRole, OrganizationStatus
from app.schemas.organization import OrganizationCreate
from app.models.user import User # Assuming user model is here

class OrganizationService:
    async def create_organization_with_owner(
        self,
        db: AsyncSession,
        *,
        obj_in: OrganizationCreate,
        owner_id: int
    ) -> Organization:
        """
        Creates a new organization and assigns the provided user as the owner.
        """
        # Check if the user already owns an organization with the same name
        existing_org_query = select(Organization).join(OrganizationMember).where(
            OrganizationMember.user_id == owner_id,
            Organization.name == obj_in.name,
            OrganizationMember.role == MemberRole.OWNER
        )
        existing_org_result = await db.execute(existing_org_query)
        if existing_org_result.scalar_one_or_none():
            raise ValueError(f"You already own an organization named '{obj_in.name}'.")

        # Create the new Organization object
        new_organization = Organization(
            name=obj_in.name,
            slug=slugify(obj_in.name), # Generate a URL-safe slug
            description=obj_in.description,
            website_url=getattr(obj_in, 'website_url', None),
            industry=getattr(obj_in, 'industry', None),
            status=OrganizationStatus.ACTIVE,
            settings=obj_in.settings or {}
        )
        db.add(new_organization)
        await db.flush()  # This assigns the UUID to new_organization.id

        # Create the OrganizationMember link to make the user the OWNER
        new_member = OrganizationMember(
            organization_id=new_organization.id,
            user_id=owner_id,
            role=MemberRole.OWNER,
            status="active"
        )
        db.add(new_member)

        # Commit all changes to the database
        await db.commit()
        await db.refresh(new_organization)

        return new_organization

# Create a single instance of the service to be used across the application
organization_service = OrganizationService()