#!/usr/bin/env python3
"""
Cookiput script to upload Mushroom Soup recipe to Cookidoo.
"""

import json
import requests
import os
import sys
import time
from typing import Dict, List, Optional

class CookidooUploader:
    def __init__(self, cookie_value: str):
        self.cookie_value = cookie_value
        self.base_url = "https://www.cookidoo.de"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.cookies = {
            "_oauth2_proxy": cookie_value
        }

    def create_recipe_stub(self, recipe_name: str) -> str:
        """Create a new recipe stub and return the recipe ID."""
        url = f"{self.base_url}/created-recipes/de-DE"
        payload = {"recipeName": recipe_name}

        print(f"Attempting to create recipe stub at: {url}")
        print(f"Cookies: {self.cookies}")
        print(f"Payload: {payload}")

        try:
            response = requests.post(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")

            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                recipe_id = data.get('recipeId') or data.get('id') or data.get('recipe_id')
                if not recipe_id:
                    location_header = response.headers.get('Location')
                    if location_header:
                        parts = location_header.split('/')
                        if len(parts) > 0:
                            recipe_id = parts[-1]
                return recipe_id
            else:
                print(f"Response content: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            raise

    def update_recipe_ingredients(self, recipe_id: str, ingredients: List[Dict]) -> None:
        """Update recipe with ingredients."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = {"ingredients": ingredients}

        response = requests.patch(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()

    def update_recipe_instructions(self, recipe_id: str, instructions: List[Dict]) -> None:
        """Update recipe with cooking instructions."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = {"instructions": instructions}

        response = requests.patch(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()

    def update_recipe_metadata(self, recipe_id: str, metadata: Dict) -> None:
        """Update recipe with metadata."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = metadata

        response = requests.patch(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()

    def upload_recipe(self, recipe_data: Dict) -> str:
        """Complete workflow to upload a recipe."""
        print("Creating recipe stub...")
        recipe_id = self.create_recipe_stub(recipe_data['name'])
        print(f"Recipe created with ID: {recipe_id}")

        if not recipe_id:
            raise Exception("Could not extract recipe ID from response")

        time.sleep(1)

        print("Updating ingredients...")
        self.update_recipe_ingredients(recipe_id, recipe_data['ingredients'])

        print("Updating instructions...")
        self.update_recipe_instructions(recipe_id, recipe_data['instructions'])

        print("Updating metadata...")
        self.update_recipe_metadata(recipe_id, recipe_data['metadata'])

        print("Recipe uploaded successfully!")
        return recipe_id

def parse_mushroom_soup_recipe() -> Dict:
    """Parse the mushroom soup recipe from the text file."""
    recipe_name = "Ultimate TM6 Mushroom Soup"
    
    ingredients = [
        {"type": "INGREDIENT", "text": "1 small onion (quartered)"},
        {"type": "INGREDIENT", "text": "1 garlic clove"},
        {"type": "INGREDIENT", "text": "20 g butter or 20 g olive oil"},
        {"type": "INGREDIENT", "text": "200 g baby button mushrooms"},
        {"type": "INGREDIENT", "text": "½ tsp salt"},
        {"type": "INGREDIENT", "text": "30–40 g white wine (optional)"},
        {"type": "INGREDIENT", "text": "600 g water + 1 stock cube"},
        {"type": "INGREDIENT", "text": "20 g Parmigiano Reggiano (cut into 2–3 cm chunks)"},
        {"type": "INGREDIENT", "text": "40–60 g double cream"},
        {"type": "INGREDIENT", "text": "¼ tsp pepper"},
        {"type": "INGREDIENT", "text": "Extra grated Parmigiano (for garnish, optional)"},
        {"type": "INGREDIENT", "text": "Toasted bread or croutons (for serving, optional)"},
    ]

    instructions = [
        {"type": "STEP", "text": "Chop onion & garlic: Add onion (quartered) and garlic clove to TM6 bowl. Mix 5 sec / speed 5. Scrape down sides."},
        {"type": "STEP", "text": "Sauté base: Add butter or olive oil. Cook 3 min / 120°C / speed 1."},
        {"type": "STEP", "text": "Add mushrooms: Add baby button mushrooms and salt. Chop 4 sec / speed 4."},
        {"type": "STEP", "text": "Brown the mushrooms: Cook without measuring cup 10 min / 120°C / reverse / speed 1. If still wet, continue 2 more min / 120°C / reverse / speed 1."},
        {"type": "STEP", "text": "Optional flavor boost: Add white wine. Cook 2 min / 120°C / reverse / speed 1."},
        {"type": "STEP", "text": "Add stock/water: Add water and stock cube. Cook 15 min / 100°C / speed 1."},
        {"type": "STEP", "text": "Optional slow cook: Function Slow Cook, Temperature 80°C, Speed 1, Time 1–2 hours, Measuring cup ON. Gently develops deep flavor and softens mushrooms further."},
        {"type": "STEP", "text": "Grate Parmigiano Reggiano: Add Parmigiano chunks. Grate 10 sec / speed 8. Optional: 2–3 short turbo pulses for harder pieces."},
        {"type": "STEP", "text": "Add cream & Parmesan: Add double cream, grated Parmigiano, and pepper. Mix 10 sec / speed 3."},
        {"type": "STEP", "text": "Emulsify / thicken: Cook 2–3 min / 80°C / reverse / speed 3. Optional: add extra cream or Parmesan for extra silkiness and mix 10 sec / speed 3 / reverse."},
        {"type": "STEP", "text": "Serve & garnish: Drizzle with olive oil, add extra grated Parmigiano, and serve with toasted bread or croutons. Beer pairing tip: stout (dry or milk) complements mushroom umami and creaminess."},
    ]

    metadata = {
        "tools": ["TM6"],
        "totalTime": 3600,  # ~60 minutes total (including optional slow cook)
        "prepTime": 600,    # ~10 minutes prep
        "yield": {
            "value": 2,
            "unitText": "portion"
        },
        "difficulty": "EASY",
        "category": "Starter"
    }

    return {
        "name": recipe_name,
        "ingredients": ingredients,
        "instructions": instructions,
        "metadata": metadata
    }

def main():
    cookie_value = os.getenv('COOKIDOO_COOKIE')
    if not cookie_value:
        print("Error: COOKIDOO_COOKIE environment variable not set.")
        print("Please set it with your Cookidoo _oauth2_proxy cookie value:")
        print("  export COOKIDOO_COOKIE='your_cookie_value_here'")
        sys.exit(1)

    try:
        print("Parsing mushroom soup recipe...")
        recipe_data = parse_mushroom_soup_recipe()

        uploader = CookidooUploader(cookie_value)
        recipe_id = uploader.upload_recipe(recipe_data)

        print(f"\nSuccess! Your Ultimate TM6 Mushroom Soup recipe has been uploaded to Cookidoo.")
        print(f"Recipe ID: {recipe_id}")
        print(f"You can view it at: https://www.cookidoo.de/recipes/recipe/{recipe_id}")

    except Exception as e:
        print(f"Error uploading recipe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
