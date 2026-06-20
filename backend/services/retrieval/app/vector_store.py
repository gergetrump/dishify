from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import (
	Distance,
	FieldCondition,
	Filter,
	MatchAny,
	PointStruct,
	VectorParams,
)
from sentence_transformers import SentenceTransformer

from app.models.recipe import RecipeDataPoint
from dishify_contracts import ParsedIngredientModel, RetrievedRecipe


class RecipeVectorStore:
	def __init__(
		self,
		qdrant_client: QdrantClient,
		embedding_model: SentenceTransformer,
		collection_name: str = "recipes",
	):
		self.client = qdrant_client
		self.embedding_model = embedding_model
		self.collection_name = collection_name
		if hasattr(embedding_model, "get_sentence_embedding_dimension"):
			self.vector_size = embedding_model.get_sentence_embedding_dimension()
		else:
			self.vector_size = embedding_model.get_embedding_dimension()

	def create_collection(self, recreate: bool = False) -> None:
		if recreate:
			self.client.recreate_collection(
				collection_name=self.collection_name,
				vectors_config=VectorParams(
					size=self.vector_size,
					distance=Distance.COSINE,
				),
			)
		else:
			self.client.create_collection(
				collection_name=self.collection_name,
				vectors_config=VectorParams(
					size=self.vector_size,
					distance=Distance.COSINE,
				),
			)

		self.client.create_payload_index(
			collection_name=self.collection_name,
			field_name="raw_ingredients",
			field_schema="keyword",
		)
		self.client.create_payload_index(
			collection_name=self.collection_name,
			field_name="exclusion_restrictions",
			field_schema="keyword",
		)

	def index_recipes(
		self, recipes: list[RecipeDataPoint], batch_size: int = 100
	) -> None:
		points: list[PointStruct] = []

		for idx, recipe in enumerate(recipes):
			text_for_embedding = f"""
            Title: {recipe.title}
            Title: {recipe.title}
            Raw ingredients: {", ".join(str(item) for item in recipe.raw_ingredients)}
            """

			vector = self.embedding_model.encode(text_for_embedding).tolist()

			point = PointStruct(
				id=idx,
				vector=vector,
				payload={
					"title": recipe.title,
					"ingredients": recipe.ingredients,
					"parsed_ingredients": [
						{
							"name": ingredient.name,
							"quantity": ingredient.quantity,
							"unit": ingredient.unit,
							"raw_text": ingredient.raw_text,
						}
						for ingredient in recipe.parsed_ingredients
					],
					"raw_ingredients": recipe.raw_ingredients,
					"directions": recipe.directions,
					"link": recipe.link,
					"source": recipe.source,
					"ner": recipe.ner,
					"exclusion_restrictions": recipe.exclusion_restrictions,
					"exclusion_restrictions_count": recipe.exclusion_restrictions_count,
				},
			)

			points.append(point)

			if len(points) >= batch_size:
				self.client.upsert(
					collection_name=self.collection_name,
					points=points,
				)
				points = []

		if points:
			self.client.upsert(
				collection_name=self.collection_name,
				points=points,
			)

	@staticmethod
	def _normalize_ingredient_names(values: list[object] | None) -> list[str]:
		if not values:
			return []

		names: list[str] = []
		for item in values:
			if item is None:
				continue
			if isinstance(item, str):
				name = item
			elif isinstance(item, dict):
				name = item.get("name") or item.get("raw_text") or ""
			else:
				name = getattr(item, "name", "") or getattr(item, "raw_text", "")
			name = str(name).strip()
			if name:
				names.append(name)
		return names

	def build_query_text(
		self, query: str, available_ingredients: list[object] | None = None
	) -> str:
		names = self._normalize_ingredient_names(available_ingredients)
		if not names:
			return f"Query: {query}"
		return f"Query: {query}\nAvailable ingredients: {', '.join(names)}"

	def retrieve_recipes(
		self,
		query: str,
		top_k: int = 5,
		excluded_ingredients: list[str] | None = None,
		available_ingredients: list[object] | None = None,
	) -> list[RetrievedRecipe]:
		query_text = self.build_query_text(query, available_ingredients)
		query_vector = self.embedding_model.encode(query_text).tolist()

		query_filter = None
		excluded_norm = [
			item.strip().lower() for item in (excluded_ingredients or []) if item
		]

		if excluded_norm:
			query_filter = Filter(
				must_not=[
					FieldCondition(
						key="exclusion_restrictions",
						match=MatchAny(any=excluded_norm),
					)
				]
			)

		response = self.client.query_points(
			collection_name=self.collection_name,
			query=query_vector,
			limit=top_k,
			query_filter=query_filter,
			with_payload=True,
		)

		recipes: list[RetrievedRecipe] = []
		for result in response.points:
			parsed_raw = result.payload.get("parsed_ingredients") or []
			parsed_ingredients = [
				ParsedIngredientModel(**item) if isinstance(item, dict) else item
				for item in parsed_raw
			]
			recipes.append(
				RetrievedRecipe(
					id=int(result.id),
					score=float(result.score or 0),
					title=result.payload.get("title"),
					ingredients=result.payload.get("ingredients"),
					raw_ingredients=result.payload.get("raw_ingredients"),
					parsed_ingredients=parsed_ingredients,
					directions=result.payload.get("directions"),
					link=result.payload.get("link"),
					source=result.payload.get("source"),
					ner=result.payload.get("ner"),
					exclusion_restrictions=result.payload.get("exclusion_restrictions"),
					exclusion_restrictions_count=result.payload.get(
						"exclusion_restrictions_count"
					),
				)
			)

		return recipes

	def collection_exists(self) -> bool:
		try:
			collections = self.client.get_collections().collections
			return any(c.name == self.collection_name for c in collections)
		except Exception:
			return False
