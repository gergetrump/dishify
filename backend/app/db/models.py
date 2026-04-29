"""SQLAlchemy ORM models.

The dataset doesn't carry diet/allergen labels, so they're inferred at load
time and stored alongside the original fields. Keeping ``ingredients_clean``
(the dataset's NER list) as a separate JSON list makes hard filtering and
ingredient overlap scoring trivial.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Recipe(Base):
	__tablename__ = "recipes"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	title: Mapped[str] = mapped_column(String(512))
	link: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
	source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

	ingredients_raw: Mapped[List[str]] = mapped_column(JSON, default=list)
	ingredients_clean: Mapped[List[str]] = mapped_column(JSON, default=list)
	directions: Mapped[List[str]] = mapped_column(JSON, default=list)

	diet: Mapped[str] = mapped_column(String(32), default="omnivore")
	allergens: Mapped[List[str]] = mapped_column(JSON, default=list)

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
