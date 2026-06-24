#!/usr/bin/env python3
"""
Create a completely new chicken tikka masala recipe from scratch for 2 portions with proper TM6 structured fields.
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

def create_chicken_tikka_masala_2portions() -> Dict:
    """Create chicken tikka masala recipe for exactly 2 portions with proper TM6 structured fields."""
    
    # Ingredients for 2 portions (as specified in the recipe: "Serves 2 generously")
    ingredients = [
        # Marinade
        {"type": "INGREDIENT", "text": "650g chicken breast fillets, cut into bite-size chunks"},
        {"type": "INGREDIENT", "text": "3 tbsp natural yogurt"},
        {"type": "INGREDIENT", "text": "1 tsp garam masala"},
        {"type": "INGREDIENT", "text": "1 tsp tikka curry powder"},
        {"type": "INGREDIENT", "text": "Salt & pepper"},
        
        # Sauce
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
        
        # To serve
        {"type": "INGREDIENT", "text": "Basmati rice"},
        {"type": "INGREDIENT", "text": "Fresh coriander, chopped"},
        {"type": "INGREDIENT", "text": "Squeeze of lemon"}
    ]
    
    # Structured instructions with TM6 parameters
    instructions = [
        {
            "type": "STEP",
            "text": "Mix together: 650g chicken breast, cut into bite-size chunks, 3 tbsp natural yogurt, 1 tsp garam masala, 1 tsp tikka curry powder, pinch of salt",
            "mode": "mix",
            "time": 30,
            "speed": "Soft Stir",
            "reverse": False
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 2 onions (halved), 3 garlic cloves, 1 thumb-sized piece fresh ginger, peeled",
            "mode": "chop",
            "time": 5,
            "speed": 7,
            "reverse": False
        },
        {
            "type": "STEP",
            "text": "Add 1 tbsp olive oil",
            "mode": "cook",
            "time": 300,
            "speed": 1,
            "reverse": False,
            "temperature": 120
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 2 tsp tikka curry powder, 1 tsp garam masala, 1 tsp ground cumin, 1 tsp ground coriander, 1/2 tsp turmeric, 1 tbsp tomato puree",
            "mode": "cook",
            "time": 120,
            "speed": 1,
            "reverse": False,
            "temperature": 120
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 1 tin chopped tomatoes (400g), 1 tin coconut milk (400ml)",
            "mode": "cook",
            "time": 900,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": 100
        },
        {
            "type": "STEP",
            "text": "Blend (optional, for smoother sauce)",
            "mode": "blend",
            "time": 10,
            "speed": 5,
            "reverse": False
        },
        {
            "type": "STEP",
            "text": "Add marinated chicken pieces to the sauce",
            "mode": "cook",
            "time": 1200,
            "speed": "Soft Stir",
            "reverse": True,
            "temperature": 100
        },
        {
            "type": "STEP",
            "text": "Stir in a splash of Elmlea double cream. Taste and adjust salt.",
            "mode": "mix",
            "time": 30,
            "speed": "Soft Stir",
            "reverse": False
        }
    ]
    
    # Metadata
    metadata = {
        "tools": ["TM6"],
        "totalTime": 3600,  # ~60 minutes total (including marinating time)
        "prepTime": 1800,   # ~30 minutes prep (marinating + prep)
        "yield": {
            "value": 2,
            "unitText": "portion"
        },
        "difficulty": "MEDIUM",
        "category": "Main Course"
    }
    
    return {
        "name": "Chicken Tikka Masala (TM6) - 2 Portions",
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
        print("Creating chicken tikka masala recipe for 2 portions...")
        recipe_data = create_chicken_tikka_masala_2portions()
        
        # Create uploader
        uploader = CookidooUploader(cookie_value)
        
        # Create new recipe stub
        print("Creating new recipe stub...")
        recipe_id = uploader.create_recipe_stub(recipe_data['name'])
        print(f"New recipe created with ID: {recipe_id}")
        
        # Update with full structured data
        print("Updating with structured TM6 parameters...")
        uploader.update_recipe_full(recipe_id, recipe_data)
        
        print(f"\n✓ Success! New Chicken Tikka Masala recipe created for 2 portions with structured TM6 parameters.")
        print(f"Recipe ID: {recipe_id}")
        print(f"View it at: https://www.cookidoo.de/recipes/recipe/{recipe_id}")
        
    except Exception as e:
        print(f"Error creating recipe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()