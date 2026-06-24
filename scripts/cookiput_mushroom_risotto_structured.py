#!/usr/bin/env python3
"""
Enhanced cookiput script that includes structured TM6 parameters for each step.
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
        
        response = requests.post(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get('recipeId') or data.get('id')
    
    def update_recipe_instructions_structured(self, recipe_id: str, instructions: List[Dict]) -> None:
        """Update recipe with structured TM6 instructions including speed, time, temperature, etc."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = {"instructions": instructions}
        
        response = requests.patch(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()
    
    def upload_recipe(self, recipe_data: Dict) -> str:
        """Complete workflow to upload a recipe with structured TM6 parameters."""
        print("Creating recipe stub...")
        recipe_id = self.create_recipe_stub(recipe_data['name'])
        print(f"Recipe created with ID: {recipe_id}")
        
        # Add a small delay
        time.sleep(1)
        
        print("Updating ingredients...")
        self.update_recipe_ingredients(recipe_id, recipe_data['ingredients'])
        
        print("Updating structured instructions...")
        self.update_recipe_instructions_structured(recipe_id, recipe_data['instructions_structured'])
        
        print("Updating metadata...")
        self.update_recipe_metadata(recipe_id, recipe_data['metadata'])
        
        print("Recipe uploaded successfully!")
        return recipe_id
    
    def update_recipe_ingredients(self, recipe_id: str, ingredients: List[Dict]) -> None:
        """Update recipe with ingredients."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = {"ingredients": ingredients}
        
        response = requests.patch(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()
    
    def update_recipe_metadata(self, recipe_id: str, metadata: Dict) -> None:
        """Update recipe with metadata."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = metadata
        
        response = requests.patch(url, headers=self.headers, cookies=self.cookies, json=payload, timeout=10)
        response.raise_for_status()

def parse_mushroom_risotto_recipe_structured() -> Dict:
    """Parse the mushroom risotto recipe from the Markdown file with structured TM6 parameters."""
    with open('/Users/dan/recipes/mushroom-risotto.md', 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Extract recipe name
    recipe_name = lines[0].replace('# ', '').strip()
    
    # Parse ingredients
    ingredients = []
    in_ingredients_section = False
    
    for line in lines:
        if line.startswith('## Ingredients'):
            in_ingredients_section = True
            continue
        elif line.startswith('## Method') or line.startswith('## Notes'):
            break
        elif in_ingredients_section and line.startswith('-'):
            ingredient_text = line.strip('- ').strip()
            if ingredient_text:
                ingredients.append({
                    "type": "INGREDIENT",
                    "text": ingredient_text
                })
    
    # Parse method/steps with structured TM6 parameters
    instructions_structured = []
    
    # Step 1 — Grate the parmesan
    instructions_structured.append({
        "type": "STEP",
        "text": "Add 50g Parmigiano chunks to TM bowl",
        "tm6": {
            "mode": "grate",
            "time": 10,
            "speed": 10,
            "reverse": False,
            "temperature": None
        }
    })
    
    # Step 2 — Chop and brown mushrooms
    instructions_structured.append({
        "type": "STEP",
        "text": "Add 485g mushrooms to TM bowl (quarter any large ones first). Remove. Heat a large pan over high heat with a little butter or oil. Sauté the mushrooms in batches — don't crowd the pan. Cook until well browned, ~5–7 min total. Season lightly. Set aside.",
        "tm6": {
            "mode": "chop",
            "time": 3,
            "speed": 4,
            "reverse": False,
            "temperature": None
        }
    })
    
    # Step 3 — Chop onion and garlic
    instructions_structured.append({
        "type": "STEP",
        "text": "Add to TM bowl: 1 onion (halved), 2 garlic cloves",
        "tm6": {
            "mode": "chop",
            "time": 5,
            "speed": 7,
            "reverse": False,
            "temperature": None
        }
    })
    
    # Step 4 — Saute the base
    instructions_structured.append({
        "type": "STEP",
        "text": "Add 20g butter and 1 tbsp olive oil",
        "tm6": {
            "mode": "cook",
            "time": 180,
            "speed": 1,
            "reverse": False,
            "temperature": 120
        }
    })
    
    # Step 5 — Toast the rice
    instructions_structured.append({
        "type": "STEP",
        "text": "Add 250g risotto rice",
        "tm6": {
            "mode": "cook",
            "time": 120,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": 120
        }
    })
    
    # Step 6 — Deglaze
    instructions_structured.append({
        "type": "STEP",
        "text": "Add 100ml dry white wine",
        "tm6": {
            "mode": "cook",
            "time": 120,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": 100
        }
    })
    
    # Step 7 — Add stock and mushrooms
    instructions_structured.append({
        "type": "STEP",
        "text": "Add to TM bowl: 750ml hot stock (1 chicken stock cube dissolved in 750ml hot water), The browned mushrooms, A few sprigs of fresh thyme leaves",
        "tm6": {
            "mode": "cook",
            "time": 1080,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": 100
        }
    })
    
    # Step 8 — Mantecatura (finishing)
    instructions_structured.append({
        "type": "STEP",
        "text": "Add to TM bowl: 20g butter, Most of the grated Parmigiano (save some for serving)",
        "tm6": {
            "mode": "mix",
            "time": 30,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": None
        }
    })
    
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
        "name": recipe_name,
        "ingredients": ingredients,
        "instructions_structured": instructions_structured,
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
        # Parse the recipe
        print("Parsing mushroom risotto recipe with structured TM6 parameters...")
        recipe_data = parse_mushroom_risotto_recipe_structured()
        
        # Create uploader
        uploader = CookidooUploader(cookie_value)
        
        # Upload the recipe
        recipe_id = uploader.upload_recipe(recipe_data)
        
        print(f"\nSuccess! Your Mushroom Risotto recipe has been uploaded to Cookidoo with structured TM6 parameters.")
        print(f"Recipe ID: {recipe_id}")
        print(f"You can view it at: https://www.cookidoo.de/recipes/recipe/{recipe_id}")
        
    except Exception as e:
        print(f"Error uploading recipe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()