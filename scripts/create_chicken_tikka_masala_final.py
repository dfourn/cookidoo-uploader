#!/usr/bin/env python3
"""
Final version: Chicken Tikka Masala recipe with TM6 parameters prominently displayed in instruction text.
This ensures the TM6 settings are visible when viewing the recipe online.
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
        """Update recipe with enhanced text formatting for TM6 parameters."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        
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

def create_chicken_tikka_masala_final() -> Dict:
    """Create chicken tikka masala with TM6 parameters prominently displayed in instruction text."""
    
    ingredients = [
        {"type": "INGREDIENT", "text": "650g chicken breast fillets, cut into bite-size chunks"},
        {"type": "INGREDIENT", "text": "3 tbsp natural yogurt"},
        {"type": "INGREDIENT", "text": "1 tsp garam masala"},
        {"type": "INGREDIENT", "text": "1 tsp tikka curry powder"},
        {"type": "INGREDIENT", "text": "Salt & pepper"},
        {"type": "INGREDIENT", "text": "2 onions, halved"},
        {"type": "INGREDIENT", "text": "3 garlic cloves"},
        {"type": "INGREDIENT", "text": "1 thumb-sized piece fresh ginger, peeled"},
        {"type": "INGREDIENT", "text": "1 tbsp olive oil"},
        {"type": "INGREDIENT", "text": "1 tin chopped tomatoes (400g)"},
        {"type": "INGREDIENT", "text": "1 tin coconut milk (400ml)"},
        {"type": "INGREDIENT", "text": "1 tbsp tomato puree"},
        {"type": "INGREDIENT", "text": "2 tsp tikka curry powder"},
        {"type": "INGREDIENT", "text": "1 tsp garam masala"},
        {"type": "INGREDIENT", "text": "1 tsp ground cumin"},
        {"type": "INGREDIENT", "text": "1 tsp ground coriander"},
        {"type": "INGREDIENT", "text": "1/2 tsp turmeric"},
        {"type": "INGREDIENT", "text": "Splash of Elmlea double cream"},
        {"type": "INGREDIENT", "text": "Basmati rice"},
        {"type": "INGREDIENT", "text": "Fresh coriander, chopped"},
        {"type": "INGREDIENT", "text": "Squeeze of lemon"}
    ]
    
    # Enhanced instructions with TM6 parameters prominently displayed in text
    instructions = [
        {
            "type": "STEP",
            "text": "**TM6: MARINATE** - 30 sec / Soft Stir\nMix together: 650g chicken breast, cut into bite-size chunks, 3 tbsp natural yogurt, 1 tsp garam masala, 1 tsp tikka curry powder, pinch of salt"
        },
        {
            "type": "STEP",
            "text": "**TM6: CHOP** - 5 sec / Speed 7\nAdd to TM bowl: 2 onions (halved), 3 garlic cloves, 1 thumb-sized piece fresh ginger, peeled"
        },
        {
            "type": "STEP",
            "text": "**TM6: SAUTÉ** - 5 min / 120°C / Speed 1\nAdd 1 tbsp olive oil"
        },
        {
            "type": "STEP",
            "text": "**TM6: SPICES** - 2 min / 120°C / Speed 1\nAdd to TM bowl: 2 tsp tikka curry powder, 1 tsp garam masala, 1 tsp ground cumin, 1 tsp ground coriander, 1/2 tsp turmeric, 1 tbsp tomato puree"
        },
        {
            "type": "STEP",
            "text": "**TM6: SIMMER** - 15 min / 100°C / Reverse / Speed 1\nAdd to TM bowl: 1 tin chopped tomatoes (400g), 1 tin coconut milk (400ml)"
        },
        {
            "type": "STEP",
            "text": "**TM6: BLEND** - 10 sec / Speed 5-7\nBlend (optional, for smoother sauce)"
        },
        {
            "type": "STEP",
            "text": "**TM6: COOK CHICKEN** - 20 min / 100°C / Reverse / Speed Soft Stir\nAdd marinated chicken pieces to the sauce"
        },
        {
            "type": "STEP",
            "text": "**TM6: FINISH** - 30 sec / Soft Stir\nStir in a splash of Elmlea double cream. Taste and adjust salt."
        }
    ]
    
    metadata = {
        "tools": ["TM6"],
        "totalTime": 3600,
        "prepTime": 1800,
        "yield": {"value": 2, "unitText": "portion"},
        "difficulty": "MEDIUM",
        "category": "Main Course"
    }
    
    return {
        "name": "Chicken Tikka Masala (TM6) - 2 Portions - FINAL",
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
        print("Creating final chicken tikka masala recipe with visible TM6 parameters...")
        recipe_data = create_chicken_tikka_masala_final()
        
        uploader = CookidooUploader(cookie_value)
        recipe_id = uploader.create_recipe_stub(recipe_data['name'])
        print(f"New recipe created with ID: {recipe_id}")
        
        uploader.update_recipe_full(recipe_id, recipe_data)
        
        print(f"\n✓ Success! Final Chicken Tikka Masala recipe created with visible TM6 parameters.")
        print(f"Recipe ID: {recipe_id}")
        print(f"View it at: https://www.cookidoo.de/recipes/recipe/{recipe_id}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()