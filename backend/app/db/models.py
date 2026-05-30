"""SQLAlchemy ORM models."""

from __future__ import annotations

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    ingredients_raw: Mapped[list[str]] = mapped_column(JSON, default=list)
    ingredients_clean: Mapped[list[str]] = mapped_column(JSON, default=list)
    directions: Mapped[list[str]] = mapped_column(JSON, default=list)

    diet: Mapped[str] = mapped_column(String(32), default="omnivore")
    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "ingredients": self.ingredients_clean,
            "directions": self.directions,
            "diet": self.diet,
            "allergens": self.allergens,
        }


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    excluded_ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    diet: Mapped[str | None] = mapped_column(String(32), nullable=True)
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
