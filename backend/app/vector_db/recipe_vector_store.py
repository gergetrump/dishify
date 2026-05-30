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

from backend.app.models.recipe import RecipeDataPoint


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
        self.vector_size = embedding_model.get_embedding_dimension()

    def create_collection(self, recreate: bool = False) -> None:
        """
        Creates the Qdrant collection.

        If recreate=True, the old collection is deleted and rebuilt.
        Use recreate=True during development, but be careful in production.
        """

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

        # Create payload index on 'raw_ingredients' field for filtering.
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="raw_ingredients",
            field_schema="keyword",
        )

        # Create payload index on 'exclusion_restrictions' for hard filtering.
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
            Ingredients: {", ".join(str(item) for item in recipe.ingredients)}
            Raw ingredients: {", ".join(str(item) for item in recipe.raw_ingredients)}
            Directions: {" ".join(recipe.directions)}
            Source: {recipe.source}
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

            if (
                len(points) >= batch_size
            ):  # Qdrant only accepts ~32 MB per HTTP request.
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

    def retrieve_recipes(
        self,
        query: str,
        top_k: int = 5,
        excluded_ingredients: list[str] | None = None,
    ) -> list[dict]:
        query_vector = self.embedding_model.encode(query).tolist()

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

        recipes: list[dict] = []

        for result in response.points:
            recipes.append(
                {
                    "id": result.id,
                    "score": result.score,
                    "title": result.payload.get("title"),
                    "ingredients": result.payload.get("ingredients"),
                    "raw_ingredients": result.payload.get("raw_ingredients"),
                    "directions": result.payload.get("directions"),
                    "link": result.payload.get("link"),
                    "source": result.payload.get("source"),
                    "ner": result.payload.get("ner"),
                    "exclusion_restrictions": result.payload.get(
                        "exclusion_restrictions"
                    ),
                    "exclusion_restrictions_count": result.payload.get(
                        "exclusion_restrictions_count"
                    ),
                }
            )

        return recipes

    def _recipe_to_embedding_text(self, recipe: RecipeDataPoint) -> str:
        """
        Converts a RecipeDataPoint into text used for semantic embedding.
        This text is not necessarily shown to the user.
        """

        return f"""
                Title: {recipe.title}
                Ingredients: {", ".join(recipe.ingredients)}
                Raw ingredients: {", ".join(recipe.raw_ingredients)}
                Directions: {" ".join(recipe.directions)}
                """.strip()
