import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Category(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "categories"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    __table_args__ = (
        Index(
            "ix_categories_system_slug_unique",
            "slug",
            unique=True,
            postgresql_where=user_id.is_(None),
        ),
        Index(
            "ix_categories_user_slug_unique",
            "user_id",
            "slug",
            unique=True,
            postgresql_where=user_id.is_not(None),
        ),
    )
