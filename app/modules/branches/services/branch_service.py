"""Branch service."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.branches.models.branch import Branch
from app.modules.branches.repositories.branch_repository import BranchRepository
from app.services.audit_service import AuditService

DEFAULT_BRANCH_CODE = "MAIN"


class BranchCreateSchema(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=150)
    address: str | None = None
    phone: str | None = None
    is_default: bool = False

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Kod majburiy.")
        return cleaned

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Nom majburiy.")
        return cleaned

    @field_validator("address", "phone", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class BranchUpdateSchema(BranchCreateSchema):
    is_active: bool = True


class BranchService:
    """CRUD for company branches."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._branches = BranchRepository(session)
        self._audit = AuditService(session)

    def ensure_default(self, company_id: int, *, actor_id: int | None = None) -> Branch:
        existing = self._branches.get_default(company_id)
        if existing is not None:
            return existing
        by_code = self._branches.get_by_code(company_id, DEFAULT_BRANCH_CODE)
        if by_code is not None:
            by_code.is_default = True
            by_code.is_active = True
            return self._branches.save(by_code)
        branch = Branch(
            company_id=company_id,
            code=DEFAULT_BRANCH_CODE,
            name="Asosiy filial",
            is_default=True,
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return self._branches.add(branch)

    def list_branches(self, company_id: int) -> list[Branch]:
        self.ensure_default(company_id)
        return self._branches.list_active(company_id)

    def get_branch(self, branch_id: int) -> Branch:
        branch = self._branches.get_by_id(branch_id)
        if branch is None:
            raise NotFoundError("Filial topilmadi.", entity="Branch")
        return branch

    def create_branch(
        self,
        company_id: int,
        payload: BranchCreateSchema,
        *,
        actor_id: int | None = None,
    ) -> Branch:
        if self._branches.get_by_code(company_id, payload.code) is not None:
            raise ConflictError(f"Kod band: {payload.code}")
        if payload.is_default:
            self._clear_default(company_id)
        branch = Branch(
            company_id=company_id,
            code=payload.code,
            name=payload.name,
            address=payload.address,
            phone=payload.phone,
            is_default=payload.is_default,
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._branches.add(branch)
        self._audit.record(
            "branch_created",
            actor_id=actor_id,
            entity_type="Branch",
            entity_id=branch.id,
            entity_uuid=branch.uuid,
            message=branch.code,
        )
        return branch

    def update_branch(
        self,
        branch_id: int,
        payload: BranchUpdateSchema,
        *,
        actor_id: int | None = None,
    ) -> Branch:
        branch = self.get_branch(branch_id)
        other = self._branches.get_by_code(branch.company_id, payload.code)
        if other is not None and other.id != branch.id:
            raise ConflictError(f"Kod band: {payload.code}")
        if payload.is_default:
            self._clear_default(branch.company_id)
        if not payload.is_active and branch.is_default:
            raise ValidationError("Asosiy filialni nofaol qilib boʻlmaydi.")
        branch.code = payload.code
        branch.name = payload.name
        branch.address = payload.address
        branch.phone = payload.phone
        branch.is_default = payload.is_default
        branch.is_active = payload.is_active
        branch.updated_by = actor_id
        self._branches.save(branch)
        self._audit.record(
            "branch_updated",
            actor_id=actor_id,
            entity_type="Branch",
            entity_id=branch.id,
            entity_uuid=branch.uuid,
        )
        return branch

    def soft_delete_branch(self, branch_id: int, *, actor_id: int | None = None) -> None:
        branch = self.get_branch(branch_id)
        if branch.is_default:
            raise ValidationError("Asosiy filialni oʻchirib boʻlmaydi.")
        branch.soft_delete(actor_id=actor_id)
        self._branches.save(branch)
        self._audit.record(
            "branch_deleted",
            actor_id=actor_id,
            entity_type="Branch",
            entity_id=branch.id,
            entity_uuid=branch.uuid,
        )

    def _clear_default(self, company_id: int) -> None:
        for branch in self._branches.list_active(company_id):
            if branch.is_default:
                branch.is_default = False
                self._branches.save(branch)
