import asyncio
import unittest
from typing import Any

from src.tools.recipes import register_recipe_tools


class CaptureMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorator(function):
            self.tools[function.__name__] = function
            return function
        return decorator


class FakeClient:
    def __init__(self):
        self.calls = []
        self.recipe = {"slug": "test-recipe", "name": "Test recipe", "tags": [], "recipeCategory": []}

    async def post(self, path, body) -> Any:
        self.calls.append(("post", path, body))
        if path == "/parser/ingredients":
            return [{"quantity": 2.5, "unit": {"name": "cup"}}]
        return {"slug": "test-recipe", "name": body["name"]}

    async def get(self, path, params=None):
        self.calls.append(("get", path, params))
        return dict(self.recipe)

    async def put(self, path, body):
        self.calls.append(("put", path, body))
        self.recipe = dict(body)
        return dict(body)


class StringSlugClient(FakeClient):
    async def post(self, path, body) -> Any:
        self.calls.append(("post", path, body))
        if path == "/parser/ingredients":
            return [{"quantity": 2.5, "unit": {"name": "cup"}}]
        return "test-recipe"


class RecipeOrganizerTests(unittest.TestCase):
    def setUp(self):
        self.mcp = CaptureMCP()
        self.client = FakeClient()
        register_recipe_tools(self.mcp, self.client)

    def test_update_recipe_forwards_organizers_and_preserves_empty_lists(self):
        result = asyncio.run(self.mcp.tools["update_recipe"](
            slug="test-recipe",
            tags=[],
            recipeCategory=[],
        ))

        method, path, body = self.client.calls[-1]
        self.assertEqual((method, path), ("put", "/recipes/test-recipe"))
        self.assertEqual(body["tags"], [])
        self.assertEqual(body["recipeCategory"], [])
        self.assertEqual(result["tags"], [])
        self.assertEqual(result["recipeCategory"], [])

    def test_create_recipe_applies_organizers_after_creation(self):
        tags = [{"id": "tag-id", "name": "Dessert", "slug": "dessert"}]
        categories = [{"id": "category-id", "name": "Cakes", "slug": "cakes"}]

        result = asyncio.run(self.mcp.tools["create_recipe"](
            name="Test recipe",
            tags=tags,
            recipeCategory=categories,
        ))

        self.assertEqual(self.client.calls[0], ("post", "/recipes", {"name": "Test recipe"}))
        self.assertEqual(self.client.calls[1][0:2], ("get", "/recipes/test-recipe"))
        method, path, body = self.client.calls[2]
        self.assertEqual((method, path), ("put", "/recipes/test-recipe"))
        self.assertEqual(body["tags"], tags)
        self.assertEqual(body["recipeCategory"], categories)
        self.assertEqual(result["tags"], tags)
        self.assertEqual(result["recipeCategory"], categories)

    def test_create_recipe_accepts_string_slug_response(self):
        mcp = CaptureMCP()
        client = StringSlugClient()
        register_recipe_tools(mcp, client)  # type: ignore[arg-type]
        tags = [{"id": "tag-id", "name": "Dessert", "slug": "dessert"}]
        categories = [{"id": "category-id", "name": "Cakes", "slug": "cakes"}]

        result = asyncio.run(mcp.tools["create_recipe"](
            name="Test recipe",
            tags=tags,
            recipeCategory=categories,
        ))

        self.assertEqual(client.calls[1][0:2], ("get", "/recipes/test-recipe"))
        self.assertEqual(client.calls[2][0:2], ("put", "/recipes/test-recipe"))
        self.assertEqual(result["tags"], tags)
        self.assertEqual(result["recipeCategory"], categories)

    def test_parse_ingredients_wraps_list_in_declared_object(self):
        result = asyncio.run(self.mcp.tools["parse_ingredients"](
            ingredients=["2 1/2 cups flour"],
        ))

        self.assertEqual(
            result,
            {"ingredients": [{"quantity": 2.5, "unit": {"name": "cup"}}]},
        )
        self.assertIn(
            (
                "post",
                "/parser/ingredients",
                {"parser": "nlp", "ingredients": ["2 1/2 cups flour"]},
            ),
            self.client.calls,
        )


if __name__ == "__main__":
    unittest.main()
