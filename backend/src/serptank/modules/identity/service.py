"""Authentication use cases.

Security properties enforced here (docs/execution-plan.md §5.1):

* **No account enumeration.** Registration and "forgot password" always return the
  same response; login spends equal time for unknown emails (dummy hash) and uses one
  generic error message.
* **Email verification** is required before password sign-in.
* **MFA.** After a correct password, users with MFA get an ``mfa_pending`` session that
  can only complete the second factor; the session is rotated on completion.
* **Session hygiene.** Sessions rotate on login, MFA, password change and re-auth;
  password reset and change revoke the user's other sessions.
* **Audit.** Every security-relevant event is written to the append-only audit log.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.audit import record_audit_event
from serptank.core.db import bind_identity
from serptank.core.email import OutgoingEmail
from serptank.core.errors import AppError, AuthenticationRequiredError, ConflictError
from serptank.modules.identity import mfa
from serptank.modules.identity.deps import IdentityServices
from serptank.modules.identity.email_tokens import consume_email_token, issue_email_token
from serptank.modules.identity.google import GoogleIdentity, GoogleSignInError
from serptank.modules.identity.models import EmailTokenPurpose, MfaTotp, User, WebAuthnCredential
from serptank.modules.identity.passwords import WeakPasswordError, validate_password
from serptank.modules.identity.sessions import SessionData

logger = structlog.get_logger(__name__)

GENERIC_LOGIN_ERROR = "Incorrect email or password."


class InvalidCredentialsError(AppError):
    status = 401
    code = "invalid_credentials"
    title = "Sign-in failed"


class EmailNotVerifiedError(AppError):
    status = 403
    code = "email_not_verified"
    title = "Email address not verified"


class InvalidTokenError(AppError):
    status = 400
    code = "invalid_token"
    title = "Invalid or expired link"


class InvalidMfaCodeError(AppError):
    status = 401
    code = "invalid_mfa_code"
    title = "Invalid authentication code"


@dataclass
class ClientInfo:
    ip: str | None
    user_agent: str | None


@dataclass
class LoginResult:
    token: str
    session: SessionData
    user: User
    mfa_required: bool
    mfa_methods: list[str]


class AuthService:
    def __init__(self, db: AsyncSession, identity: IdentityServices) -> None:
        self.db = db
        self.ids = identity
        self.settings = identity.settings
        self._pepper = identity.settings.api_key_pepper.get_secret_value()

    # ------------------------------------------------------------------ helpers
    def _link(self, path: str, token: str) -> str:
        return f"{self.settings.public_origin.rstrip('/')}{path}?token={token}"

    async def _user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower(), User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def _check_new_password(self, password: str, user: User | None, email: str) -> None:
        context = (email.split("@", 1)[0], *(user.full_name.split() if user else ()))
        await validate_password(
            password,
            min_length=self.settings.password_min_length,
            breach_checker=self.ids.breach_checker,
            context=context,
        )

    async def mfa_methods(self, user: User) -> list[str]:
        methods: list[str] = []
        totp = await self.db.get(MfaTotp, user.id)
        if totp is not None and totp.confirmed_at is not None:
            methods += ["totp", "recovery_code"]
        passkeys = await self.db.execute(
            select(func.count()).where(WebAuthnCredential.user_id == user.id)
        )
        if passkeys.scalar_one():
            methods.append("passkey")
        return methods

    # ------------------------------------------------------------- registration
    async def register(self, email: str, password: str, full_name: str, client: ClientInfo) -> None:
        """Create an account and email a verification link. Never reveals existence."""
        email = email.strip().lower()
        existing = await self._user_by_email(email)
        if existing is not None:
            await self.ids.email.send(
                OutgoingEmail(
                    to=email,
                    subject="Someone tried to create a SerpTank account with your email",
                    text=(
                        "An account already exists for this address. If this was you, sign in "
                        "or reset your password. If not, you can ignore this email."
                    ),
                )
            )
            return
        await self._check_new_password(password, None, email)
        user = User(
            email=email,
            full_name=full_name.strip(),
            password_hash=self.ids.hasher.hash(password),
            password_changed_at=datetime.now(UTC),
        )
        self.db.add(user)
        await self.db.flush()
        await bind_identity(self.db, user_id=user.id)
        token = await issue_email_token(
            self.db, user.id, EmailTokenPurpose.VERIFY_EMAIL, self._pepper
        )
        record_audit_event(
            self.db, "user.registered", actor_user_id=user.id, user_agent=client.user_agent
        )
        await self.db.commit()
        await self.ids.email.send(
            OutgoingEmail(
                to=email,
                subject="Verify your SerpTank email address",
                text=f"Confirm your email address: {self._link('/verify-email', token)}\n"
                "This link expires in 48 hours.",
            )
        )

    async def verify_email(self, token: str) -> None:
        user_id = await consume_email_token(
            self.db, token, EmailTokenPurpose.VERIFY_EMAIL, self._pepper
        )
        if user_id is None:
            raise InvalidTokenError("This verification link is invalid or has expired.")
        await bind_identity(self.db, user_id=user_id)
        user = await self.db.get(User, user_id)
        if user is None:
            raise InvalidTokenError("This verification link is invalid or has expired.")
        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)
        record_audit_event(self.db, "user.email_verified", actor_user_id=user.id)
        await self.db.commit()

    async def resend_verification(self, email: str) -> None:
        user = await self._user_by_email(email)
        if user is None or user.email_verified_at is not None:
            return
        await bind_identity(self.db, user_id=user.id)
        token = await issue_email_token(
            self.db, user.id, EmailTokenPurpose.VERIFY_EMAIL, self._pepper
        )
        await self.db.commit()
        await self.ids.email.send(
            OutgoingEmail(
                to=user.email,
                subject="Verify your SerpTank email address",
                text=f"Confirm your email address: {self._link('/verify-email', token)}",
            )
        )

    # -------------------------------------------------------------------- login
    async def login(
        self,
        email: str,
        password: str,
        *,
        remember: bool,
        captcha_token: str | None,
        client: ClientInfo,
    ) -> LoginResult:
        email = email.strip().lower()
        await self.ids.throttle.before_attempt(email, client.ip or "unknown", captcha_token)
        user = await self._user_by_email(email)
        if user is None or not user.password_hash:
            self.ids.hasher.dummy_verify(password)
            await self.ids.throttle.record_failure(email)
            raise InvalidCredentialsError(GENERIC_LOGIN_ERROR)
        valid, upgraded_hash = self.ids.hasher.verify(password, user.password_hash)
        await bind_identity(self.db, user_id=user.id)
        if not valid or not user.is_active:
            await self.ids.throttle.record_failure(email)
            record_audit_event(
                self.db, "auth.login_failed", actor_user_id=user.id, user_agent=client.user_agent
            )
            await self.db.commit()
            raise InvalidCredentialsError(GENERIC_LOGIN_ERROR)
        if user.email_verified_at is None:
            raise EmailNotVerifiedError("Check your inbox for the verification link.")
        await self.ids.throttle.record_success(email)
        if upgraded_hash:
            user.password_hash = upgraded_hash
        methods = await self.mfa_methods(user)
        mfa_required = user.mfa_enabled and bool(methods)
        token, data = await self.ids.store.create(
            user.id,
            remember=remember,
            mfa_pending=mfa_required,
            auth_methods=["password"],
            ip=client.ip,
            user_agent=client.user_agent,
        )
        if not mfa_required:
            user.last_login_at = datetime.now(UTC)
        record_audit_event(
            self.db,
            "auth.mfa_challenge" if mfa_required else "auth.login",
            actor_user_id=user.id,
            user_agent=client.user_agent,
            details={"method": "password"},
        )
        await self.db.commit()
        return LoginResult(token, data, user, mfa_required, methods if mfa_required else [])

    async def complete_mfa(
        self,
        user: User,
        session: SessionData,
        *,
        code: str | None,
        recovery_code: str | None,
        client: ClientInfo,
    ) -> tuple[str, SessionData]:
        method = await self._verify_second_factor(user, code, recovery_code)
        if method is None:
            record_audit_event(
                self.db, "auth.mfa_failed", actor_user_id=user.id, user_agent=client.user_agent
            )
            await self.db.commit()
            raise InvalidMfaCodeError("The code is incorrect or has already been used.")
        token, data = await self.ids.store.rotate(
            session,
            mfa_pending=False,
            auth_methods=[*session.auth_methods, method],
            reauth_at=time.time(),
        )
        user.last_login_at = datetime.now(UTC)
        record_audit_event(
            self.db,
            "auth.login",
            actor_user_id=user.id,
            user_agent=client.user_agent,
            details={"method": f"password+{method}"},
        )
        await self.db.commit()
        return token, data

    async def _verify_second_factor(
        self, user: User, code: str | None, recovery_code: str | None
    ) -> str | None:
        if code and await mfa.verify_totp(self.db, self.ids.keyring, user.id, code):
            return "totp"
        if recovery_code and await mfa.use_recovery_code(
            self.db, user.id, recovery_code, self._pepper
        ):
            record_audit_event(self.db, "auth.recovery_code_used", actor_user_id=user.id)
            return "recovery_code"
        return None

    async def reauthenticate(
        self, user: User, session: SessionData, *, password: str | None, code: str | None
    ) -> tuple[str, SessionData]:
        ok = False
        if password and user.password_hash:
            ok, _ = self.ids.hasher.verify(password, user.password_hash)
        if not ok and code:
            ok = await mfa.verify_totp(self.db, self.ids.keyring, user.id, code)
        if not ok:
            record_audit_event(self.db, "auth.reauth_failed", actor_user_id=user.id)
            await self.db.commit()
            raise InvalidCredentialsError("Could not confirm your identity.")
        token, data = await self.ids.store.rotate(session, reauth_at=time.time())
        record_audit_event(self.db, "auth.reauthenticated", actor_user_id=user.id)
        await self.db.commit()
        return token, data

    # ----------------------------------------------------------------- passwords
    async def forgot_password(self, email: str) -> None:
        user = await self._user_by_email(email)
        if user is None or not user.is_active:
            return
        await bind_identity(self.db, user_id=user.id)
        token = await issue_email_token(
            self.db, user.id, EmailTokenPurpose.RESET_PASSWORD, self._pepper
        )
        record_audit_event(self.db, "auth.password_reset_requested", actor_user_id=user.id)
        await self.db.commit()
        await self.ids.email.send(
            OutgoingEmail(
                to=user.email,
                subject="Reset your SerpTank password",
                text=f"Reset your password: {self._link('/reset-password', token)}\n"
                "This link expires in 30 minutes. If you did not ask for this, ignore it.",
            )
        )

    async def reset_password(self, token: str, new_password: str) -> None:
        user_id = await consume_email_token(
            self.db, token, EmailTokenPurpose.RESET_PASSWORD, self._pepper
        )
        if user_id is None:
            raise InvalidTokenError("This reset link is invalid or has expired.")
        await bind_identity(self.db, user_id=user_id)
        user = await self.db.get(User, user_id)
        if user is None:
            raise InvalidTokenError("This reset link is invalid or has expired.")
        try:
            await self._check_new_password(new_password, user, user.email)
        except WeakPasswordError:
            await self.db.rollback()  # keep the token usable for a second attempt
            raise
        user.password_hash = self.ids.hasher.hash(new_password)
        user.password_changed_at = datetime.now(UTC)
        # Possession of the mailbox proves the address.
        user.email_verified_at = user.email_verified_at or datetime.now(UTC)
        record_audit_event(self.db, "auth.password_reset", actor_user_id=user.id)
        await self.db.commit()
        await self.ids.store.revoke_all(user.id)
        await self.ids.email.send(
            OutgoingEmail(
                to=user.email,
                subject="Your SerpTank password was changed",
                text="Your password was reset and all sessions were signed out. If this was "
                "not you, contact support immediately.",
            )
        )

    async def change_password(
        self, user: User, session: SessionData, current: str, new: str
    ) -> tuple[str, SessionData]:
        if user.password_hash:
            valid, _ = self.ids.hasher.verify(current, user.password_hash)
            if not valid:
                raise InvalidCredentialsError("Your current password is incorrect.")
        elif not session.recently_reauthenticated(self.settings.reauth_window_s):
            raise AuthenticationRequiredError("Re-authenticate before setting a password.")
        await self._check_new_password(new, user, user.email)
        user.password_hash = self.ids.hasher.hash(new)
        user.password_changed_at = datetime.now(UTC)
        record_audit_event(self.db, "auth.password_changed", actor_user_id=user.id)
        await self.db.commit()
        token, data = await self.ids.store.rotate(session, reauth_at=time.time())
        await self.ids.store.revoke_all(user.id, except_key=data.key)
        return token, data

    # --------------------------------------------------------------- Google SSO
    async def google_sign_in(self, identity: GoogleIdentity, client: ClientInfo) -> LoginResult:
        result = await self.db.execute(
            select(User).where(User.google_subject == identity.subject, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user is None:
            if await self._user_by_email(identity.email) is not None:
                # Never auto-link by email: that would let anyone controlling a Google
                # account with a matching address take over an existing account.
                raise GoogleSignInError(
                    "An account with this email already exists. Sign in with your password "
                    "and link Google from your security settings."
                )
            user = User(
                email=identity.email,
                full_name=identity.name,
                google_subject=identity.subject,
                email_verified_at=datetime.now(UTC),
            )
            self.db.add(user)
            await self.db.flush()
            await bind_identity(self.db, user_id=user.id)
            record_audit_event(
                self.db, "user.registered", actor_user_id=user.id, details={"method": "google"}
            )
        await bind_identity(self.db, user_id=user.id)
        if not user.is_active:
            raise GoogleSignInError("This account is disabled.")
        methods = await self.mfa_methods(user)
        mfa_required = user.mfa_enabled and bool(methods)
        token, data = await self.ids.store.create(
            user.id,
            mfa_pending=mfa_required,
            auth_methods=["google"],
            ip=client.ip,
            user_agent=client.user_agent,
        )
        if not mfa_required:
            user.last_login_at = datetime.now(UTC)
        record_audit_event(
            self.db,
            "auth.mfa_challenge" if mfa_required else "auth.login",
            actor_user_id=user.id,
            user_agent=client.user_agent,
            details={"method": "google"},
        )
        await self.db.commit()
        return LoginResult(token, data, user, mfa_required, methods if mfa_required else [])

    async def link_google(self, user: User, identity: GoogleIdentity) -> None:
        taken = await self.db.execute(
            select(User.id).where(User.google_subject == identity.subject, User.id != user.id)
        )
        if taken.scalar_one_or_none() is not None:
            raise ConflictError("This Google account is linked to another SerpTank account.")
        user.google_subject = identity.subject
        record_audit_event(self.db, "auth.google_linked", actor_user_id=user.id)
        await self.db.commit()

    async def unlink_google(self, user: User) -> None:
        if not user.password_hash and not await self.mfa_methods(user):
            raise ConflictError("Set a password or add a passkey before unlinking Google.")
        user.google_subject = None
        record_audit_event(self.db, "auth.google_unlinked", actor_user_id=user.id)
        await self.db.commit()

    # ---------------------------------------------------------------- passkeys
    async def passkey_sign_in(
        self, user_id: uuid.UUID, remember: bool, client: ClientInfo
    ) -> LoginResult:
        user = await self.db.get(User, user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise InvalidCredentialsError("This passkey cannot be used to sign in.")
        # A user-verified passkey is itself multi-factor (possession + biometric/PIN).
        token, data = await self.ids.store.create(
            user.id,
            remember=remember,
            auth_methods=["passkey"],
            ip=client.ip,
            user_agent=client.user_agent,
        )
        user.last_login_at = datetime.now(UTC)
        record_audit_event(
            self.db,
            "auth.login",
            actor_user_id=user.id,
            user_agent=client.user_agent,
            details={"method": "passkey"},
        )
        await self.db.commit()
        return LoginResult(token, data, user, False, [])
