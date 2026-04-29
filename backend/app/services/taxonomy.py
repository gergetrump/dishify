"""Cheap diet + allergen inference from a list of clean ingredient names.

This isn't medical-grade -- it's a pragmatic keyword classifier good enough
for the recommender. False positives (over-restricting) are preferred over
false negatives (leaking an allergen).
"""

from __future__ import annotations

from typing import Iterable, List


_MEAT_TOKENS: set[str] = {
	"beef", "steak", "veal", "venison", "lamb", "mutton", "goat",
	"pork", "ham", "bacon", "sausage", "pancetta", "prosciutto", "chorizo", "salami",
	"chicken", "poultry", "turkey", "duck", "goose", "quail",
	"liver", "tripe", "gelatin", "lard", "tallow", "anchovy", "anchovies",
}

_SEAFOOD_TOKENS: set[str] = {
	"fish", "salmon", "tuna", "cod", "halibut", "trout", "sardine", "sardines",
	"mackerel", "tilapia", "snapper", "bass", "haddock", "sole",
	"shrimp", "prawn", "lobster", "crab", "crayfish", "scallop", "scallops",
	"mussel", "mussels", "clam", "clams", "oyster", "oysters", "squid", "octopus",
	"calamari", "caviar", "roe",
}

_DAIRY_TOKENS: set[str] = {
	"milk", "cream", "butter", "cheese", "cheddar", "mozzarella", "parmesan",
	"parmigiano", "ricotta", "yogurt", "yoghurt", "ghee", "kefir", "buttermilk",
	"whey", "casein",
}

_EGG_TOKENS: set[str] = {"egg", "eggs", "yolk", "yolks", "egg white", "egg whites"}
_HONEY_TOKENS: set[str] = {"honey"}

_ALLERGEN_GROUPS: dict[str, set[str]] = {
	"peanuts": {"peanut", "peanuts", "peanut butter", "groundnut"},
	"tree_nuts": {
		"almond", "almonds", "walnut", "walnuts", "pecan", "pecans",
		"cashew", "cashews", "hazelnut", "hazelnuts", "pistachio", "pistachios",
		"macadamia", "brazil nut", "pine nut", "pine nuts", "nuts",
	},
	"gluten": {
		"wheat", "flour", "bread", "pasta", "noodle", "noodles",
		"barley", "rye", "spelt", "couscous", "semolina", "bulgur", "farina",
		"breadcrumbs", "cracker", "crackers",
	},
	"dairy": _DAIRY_TOKENS,
	"eggs": _EGG_TOKENS,
	"soy": {"soy", "soya", "tofu", "tempeh", "edamame", "miso", "soy sauce"},
	"fish": {
		"fish", "salmon", "tuna", "cod", "halibut", "trout", "sardine",
		"sardines", "mackerel", "tilapia", "snapper", "bass", "haddock",
		"sole", "anchovy", "anchovies",
	},
	"shellfish": {
		"shrimp", "prawn", "lobster", "crab", "crayfish", "scallop", "scallops",
		"mussel", "mussels", "clam", "clams", "oyster", "oysters",
		"squid", "octopus", "calamari",
	},
	"sesame": {"sesame", "tahini"},
}


def _ingredient_corpus(ingredients: Iterable[str]) -> str:
	return " ".join(str(item).lower() for item in ingredients if item)


def infer_diet(ingredients: Iterable[str]) -> str:
	"""Return ``vegan`` | ``vegetarian`` | ``omnivore``."""

	corpus = _ingredient_corpus(ingredients)
	tokens = set(corpus.split())

	def has_any(group: set[str]) -> bool:
		for term in group:
			if " " in term:
				if term in corpus:
					return True
			elif term in tokens:
				return True
		return False

	if has_any(_MEAT_TOKENS) or has_any(_SEAFOOD_TOKENS):
		return "omnivore"
	if has_any(_DAIRY_TOKENS) or has_any(_EGG_TOKENS) or has_any(_HONEY_TOKENS):
		return "vegetarian"
	return "vegan"


def infer_allergens(ingredients: Iterable[str]) -> List[str]:
	"""Return the allergen group names the recipe contains."""

	corpus = _ingredient_corpus(ingredients)
	tokens = set(corpus.split())

	hits: list[str] = []
	for group_name, terms in _ALLERGEN_GROUPS.items():
		for term in terms:
			if " " in term:
				if term in corpus:
					hits.append(group_name)
					break
			elif term in tokens:
				hits.append(group_name)
				break
	return sorted(set(hits))
