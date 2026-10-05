from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="employee",
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class WorkProcess(Base):
    __tablename__ = "work_processes"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    source_document: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    prerequisites: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(24), default="ready", nullable=False)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    steps: Mapped[list["WorkStep"]] = relationship(
        back_populates="process",
        cascade="all, delete-orphan",
        order_by="WorkStep.step_number"
    )


class WorkStep(Base):
    __tablename__ = "work_steps"

    id: Mapped[int] = mapped_column(primary_key=True)

    process_id: Mapped[int] = mapped_column(
        ForeignKey("work_processes.id"),
        nullable=False
    )

    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    source_document: Mapped[str | None] = mapped_column(String(300), nullable=True)

    process: Mapped["WorkProcess"] = relationship(
        back_populates="steps"
    )

    __table_args__ = (
        UniqueConstraint(
            "process_id",
            "step_number",
            name="uq_process_step_number"
        ),
    )


class EmployeeProgress(Base):
    __tablename__ = "employee_progress"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    step_id: Mapped[int] = mapped_column(
        ForeignKey("work_steps.id"),
        nullable=False
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "step_id",
            name="uq_employee_step"
        ),
    )
