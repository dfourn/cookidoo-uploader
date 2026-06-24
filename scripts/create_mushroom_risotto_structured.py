#!/usr/bin/env python3
"""
Create a completely new mushroom risotto recipe from scratch with proper TM6 structured fields.
"""

import json
import requests
import os
import sys
import time

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
        """Create a new recipe stub."""
        url = f"{self.base_url}/created-recipes/de-DE"
        payload = {"recipeName": recipe_name}
        
        response = requests.post(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get('recipeId') or data.get('id')
    
    def update_recipe_full(self, recipe_id: str, recipe_data: Dict) -> None:
        """Update recipe with all structured data including TM6 parameters."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        
        # The full recipe data with structured TM6 parameters
        payload = {
            "name": recipe_data['name'],
            "ingredients": recipe_data['ingredients'],
            "instructions": recipe_data['instructions'],
            "tools": recipe_data['metadata']['tools'],
            "totalTime": recipe_data['metadata']['totalTime'],
            "prepTime": recipe_data['metadata']['prepTime'],
            "yield": recipe_data['metadata']['yield'],
            "difficulty": recipe_data['metadata'].get('difficulty', 'MEDIUM'),
            "category": recipe_data['metadata'].get('category', 'Main Course')
        }
        
        response = requests.patch(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()

def create_structured_mushroom_risotto_recipe() -> Dict:
    """Create a mushroom risotto recipe with proper TM6 structured fields for each step."""
    
    # Ingredients
    ingredients = [
        {"type": "INGREDIENT", "text": "250g Carnaroli risotto rice"},
        {"type": "INGREDIENT", "text": "485g chestnut mushrooms, cleaned"},
        {"type": "INGREDIENT", "text": "1 onion, halved"},
        {"type": "INGREDIENT", "text": "2 garlic cloves"},
        {"type": "INGREDIENT", "text": "50g Parmigiano Reggiano, cut into chunks"},
        {"type": "INGREDIENT", "text": "40g unsalted butter (split: 20g + 20g)"},
        {"type": "INGREDIENT", "text": "1 tbsp olive oil"},
        {"type": "INGREDIENT", "text": "100ml dry white wine"},
        {"type": "INGREDIENT", "text": "750ml hot water + 1 chicken stock cube (dissolved)"},
        {"type": "INGREDIENT", "text": "Fresh thyme leaves (a few sprigs)"},
        {"type": "INGREDIENT", "text": "Salt & pepper"}
    ]
    
    # Structured instructions with TM6 parameters as top-level fields
    instructions = [
        {
            "type": "STEP",
            "text": "Add 50g Parmigiano chunks to TM bowl",
            "mode": "grate",
            "time": 10,
            "speed": 10,
            "reverse": False
        },
        {
            "type": "STEP",
            "text": "Add 485g mushrooms to TM bowl (quarter any large ones first). Remove. Heat a large pan over high heat with a little butter or oil. Sauté the mushrooms in batches — don't crowd the pan. Cook until well browned, ~5–7 min total. Season lightly. Set aside.",
            "mode": "chop",
            "time": 3,
            "speed": 4,
            "reverse": False
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 1 onion (halved), 2 garlic cloves",
            "mode": "chop",
            "time": 5,
            "speed": 7,
            "reverse": False
        },
        {
            "type": "STEP",
            "text": "Add 20g butter and 1 tbsp olive oil",
            "mode": "cook",
            "time": 180,
            "speed": 1,
            "reverse": False,
            "temperature": 120
        },
        {
            "type": "STEP",
            "text": "Add 250g risotto rice",
            "mode": "cook",
            "time": 120,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": 120
        },
        {
            "type": "STEP",
            "text": "Add 100ml dry white wine",
            "mode": "cook",
            "time": 120,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": 100
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 750ml hot stock (1 chicken stock cube dissolved in 750ml hot water), The browned mushrooms, A few sprigs of fresh thyme leaves",
            "mode": "cook",
            "time": 1080,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": 100
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 20g butter, Most of the grated Parmigiano (save some for serving)",
            "mode": "mix",
            "time": 30,
            "speed": "Soft Stir",
            "reverse": True
        }
    ]
    
    # Metadata
    metadata = {
        "tools": ["TM6"],
        "totalTime": 2400,
        "prepTime": 600,
        "yield": {
            "value": 2,
            "unitText": "portion"
        },
        "difficulty": "MEDIUM",
        "category": "Main Course"
    }
    
    return {
        "name": "Mushroom Risotto (TM6)",
        "ingredients": ingredients,
        "instructions": instructions,
        "metadata": metadata
    }

def main():
    # Check if cookie is provided
    cookie_value = os.getenv('COOKIDOO_COOKIE')
    if not cookie_value:
        print("Error: COOKIDOO_COOKIE environment variable not set.")
        print("Please set it with your Cookidoo _oauth2_proxy cookie value:")
        print("  export COOKIDOO_COOKIE='your_cookie_value_here'")
        sys.exit(1)
    
    try:
        # Create structured recipe data
        print("Creating structured mushroom risotto recipe...")
        recipe_data = create_structured_mushroom_risotto_recipe()
        
        # Create uploader
        uploader = CookidooUploader(cookie_value)
        
        # Create new recipe stub
        print("Creating new recipe stub...")
        recipe_id = uploader.create_recipe_stub(recipe_data['name'])
        print(f"New recipe created with ID: {recipe_id}")
        
        # Update with full structured data
        print("Updating with structured TM6 parameters...")
        uploader.update_recipe_full(recipe_id, recipe_data)
        
        print(f"\n✓ Success! New Mushroom Risotto recipe created with structured TM6 parameters.")
        print(f"Recipe ID: {recipe_id}")
        print(f"View it at: https://www.cookidoo.de/recipes/recipe/{recipe_id}")
        
    except Exception as e:
        print(f"Error creating recipe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()