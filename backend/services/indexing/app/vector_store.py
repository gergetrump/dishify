from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from app.models.recipe import RecipeDataPoint


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
