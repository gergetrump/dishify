from __future__ import annotations

from dataclasses import asdict
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchAny,
)
from sentence_transformers import SentenceTransformer

from src.models.recipe import RecipeDataPoint


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


    def index_recipes(self, recipes: list[RecipeDataPoint], batch_size: int = 100) -> None:
        points: list[PointStruct] = []

        for idx, recipe in enumerate(recipes):
            text_for_embedding = f"""
            Title: {recipe.title}
            Ingredients: {", ".join(recipe.ingredients)}
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
                    "directions": recipe.directions,
                    "link": recipe.link,
                    "source": recipe.source,
                    "ner": recipe.ner,
                },
            )

            points.append(point)

            if len(points) >= batch_size:  # Qdrant only accepts ~32 MB per HTTP request.
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

        if excluded_ingredients:
            query_filter = Filter(
                must_not=[
                    FieldCondition(
                        key="ner",
                        match=MatchAny(any=excluded_ingredients),
                    )
                ]
            )

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
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
                    "directions": result.payload.get("directions"),
                    "link": result.payload.get("link"),
                    "source": result.payload.get("source"),
                    "ner": result.payload.get("ner"),
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
                Normalized ingredients: {", ".join(recipe.ner)}
                Directions: {" ".join(recipe.directions)}
                """.strip()