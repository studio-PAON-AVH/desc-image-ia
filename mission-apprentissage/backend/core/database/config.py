import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import Boolean, Integer, String, ForeignKey, TIMESTAMP, Index, Enum, Text

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_SSL = os.getenv("POSTGRES_SSL", "disable")
DATABASE_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{POSTGRES_HOST}:5432/{os.getenv('POSTGRES_DB')}"

ssl_arg = False if POSTGRES_SSL == "disable" else POSTGRES_SSL
engine = create_async_engine(
    DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True, connect_args={"ssl": ssl_arg}
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "Users"
    __table_args__ = (Index("idx_users_email", "email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        Enum("user", "admin", name="user_role"), server_default="user"
    )
    created_at: Mapped[str] = mapped_column(TIMESTAMP)
    updated_at: Mapped[str] = mapped_column(TIMESTAMP)
    task = relationship("Task", back_populates="user", lazy="select")
    refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="select")


class RefreshToken(Base):
    __tablename__ = "RefreshTokens"
    __table_args__ = (
        Index("idx_refresh_tokens_token", "token"),
        Index("idx_refresh_tokens_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Users.id"))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    user = relationship("User", back_populates="refresh_tokens", lazy="select")


class Task(Base):
    __tablename__ = "Tasks"
    __table_args__ = (
        Index("idx_tasks_task_id_redis", "task_id_redis"),
        Index("idx_tasks_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id_redis: Mapped[str] = mapped_column(String(255), unique=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("Users.id"))
    status: Mapped[str] = mapped_column(
        Enum("pending", "in_progress", "completed", "failed", name="task_status", default="pending")
    )
    total_images: Mapped[int] = mapped_column(Integer)
    processed_images: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(TIMESTAMP)
    updated_at: Mapped[str] = mapped_column(TIMESTAMP)
    started_at: Mapped[str] = mapped_column(TIMESTAMP)
    completed_at: Mapped[str] = mapped_column(TIMESTAMP)
    user = relationship("User", back_populates="task", lazy="select")
    epubs = relationship("Epub", back_populates="task", lazy="select")
    images = relationship("Images", back_populates="task", lazy="select")


class Epub(Base):
    __tablename__ = "Epubs"
    __table_args__ = (Index("idx_epubs_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("Tasks.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    upload_date: Mapped[str] = mapped_column(TIMESTAMP)
    status: Mapped[str] = mapped_column(
        Enum(
            "uploaded", "processing", "completed", "failed", name="epub_status", default="uploaded"
        )
    )
    created_at: Mapped[str] = mapped_column(TIMESTAMP)
    updated_at: Mapped[str] = mapped_column(TIMESTAMP)
    task = relationship("Task", back_populates="epubs", lazy="select")
    images = relationship("Images", back_populates="epub", lazy="select")


class Images(Base):
    __tablename__ = "Images"
    __table_args__ = (
        Index("idx_images_epub_id", "epub_id"),
        Index("idx_images_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("Tasks.id"))
    epub_id: Mapped[int] = mapped_column(Integer, ForeignKey("Epubs.id"))
    image_file_name: Mapped[str] = mapped_column(String(255))
    image_position_in_epub: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(TIMESTAMP)
    updated_at: Mapped[str] = mapped_column(TIMESTAMP)
    epub = relationship("Epub", back_populates="images", lazy="select")
    task = relationship("Task", back_populates="images", lazy="select")
    description = relationship("ImageDescription", back_populates="image", lazy="select")


class ImageDescription(Base):
    __tablename__ = "ImageDescriptions"
    __table_args__ = (
        Index("idx_image_model", "image_id", "model_ia_id"),
        Index("idx_image_descriptions_image_id", "image_id"),
        Index("idx_image_descriptions_model_ia_id", "model_ia_id"),
        Index("idx_image_descriptions_is_written_by_ai", "is_written_by_ai"),
        Index("idx_image_descriptions_is_written_by_human", "is_written_by_human"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey("Images.id"))
    model_ia_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ModelsIA.id"), nullable=True
    )
    description_text: Mapped[str] = mapped_column(Text)
    is_written_by_ai: Mapped[bool] = mapped_column(default=True)
    is_written_by_human: Mapped[bool] = mapped_column(default=False)
    generated_at: Mapped[str] = mapped_column(TIMESTAMP)
    validated_by_human: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(TIMESTAMP)
    updated_at: Mapped[str] = mapped_column(TIMESTAMP)
    image = relationship("Images", back_populates="description", lazy="select")
    modelIA = relationship("ModelsIA", back_populates="descriptions", lazy="select")


class ModelsIA(Base):
    __tablename__ = "ModelsIA"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP)
    updated_at: Mapped[str] = mapped_column(TIMESTAMP)
    descriptions = relationship("ImageDescription", back_populates="modelIA", lazy="select")


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
