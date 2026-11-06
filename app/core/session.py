"""Desktop session state."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.users.models.user import User


@dataclass
class DesktopSession:
    """Authenticated desktop session."""

    user: User
    token: str
    active_branch_id: int | None = field(default=None)

    @property
    def user_id(self) -> int:
        return self.user.id

    @property
    def display_name(self) -> str:
        return self.user.full_name
