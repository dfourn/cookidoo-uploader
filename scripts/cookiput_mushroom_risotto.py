#!/usr/bin/env python3
"""
Custom cookiput script to upload Mushroom Risotto recipe to Cookidoo.
Converts the TM6 Markdown recipe format to Cookidoo's JSON format.
"""

import json
import requests
import os
import sys
import time
from typing import Dict, List, Optional

class CookidooUploader:
    def __init__(self, jwt_token: str):
        self.jwt_token = jwt_token
        self.base_url = "https://www.cookidoo.de"
        self.headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def create_recipe_stub(self, recipe_name: str) -> str:
        """Create a new recipe stub and return the recipe ID."""
        url = f"{self.base_url}/created-recipes/de-DE"
        payload = {"recipeName": recipe_name}
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get('recipeId')
    
    def update_recipe_ingredients(self, recipe_id: str, ingredients: List[Dict]) -> None:
        """Update recipe with ingredients."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = {"ingredients": ingredients}
        
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
    
    def update_recipe_instructions(self, recipe_id: str, instructions: List[Dict]) -> None:
        """Update recipe with cooking instructions."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = {"instructions": instructions}
        
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
    
    def update_recipe_metadata(self, recipe_id: str, metadata: Dict) -> None:
        """Update recipe with metadata (tools, time, yield, etc.)."""
        url = f"{self.base_url}/created-recipes/de-DE/{recipe_id}"
        payload = metadata
        
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
    
    def upload_recipe(self, recipe_data: Dict) -> str:
        """Complete workflow to upload a recipe."""
        print("Creating recipe stub...")
        recipe_id = self.create_recipe_stub(recipe_data['name'])
        print(f"Recipe created with ID: {recipe_id}")
        
        # Add a small delay to ensure the recipe is created
        time.sleep(1)
        
        print("Updating ingredients...")
        self.update_recipe_ingredients(recipe_id, recipe_data['ingredients'])
        
        print("Updating instructions...")
        self.update_recipe_instructions(recipe_id, recipe_data['instructions'])
        
        print("Updating metadata...")
        self.update_recipe_metadata(recipe_id, recipe_data['metadata'])
        
        print("Recipe uploaded successfully!")
        return recipe_id

def parse_mushroom_risotto_recipe() -> Dict:
    """Parse the mushroom risotto recipe from the Markdown file."""
    # Since we're in the same directory, we can read the file directly
    with open('/Users/dan/recipes/mushroom-risotto.md', 'r') as f:
        content = f.read()
    
    # Extract recipe name
    lines = content.split('\n')
    recipe_name = lines[0].replace('# ', '').strip()
    
    # Parse ingredients section
    ingredients = []
    in_ingredients_section = False
    ingredient_lines = []
    
    for line in lines:
        if line.startswith('## Ingredients'):
            in_ingredients_section = True
            continue
        elif line.startswith('## Method') or line.startswith('## Notes'):
            break
        elif in_ingredients_section and line.strip() and not line.startswith('-'):
            continue
        elif in_ingredients_section and line.startswith('-'):
            ingredient_lines.append(line.strip('- ').strip())
    
    # Format ingredients for Cookidoo
    for ingredient in ingredient_lines:
        if ingredient:  # Skip empty lines
            ingredients.append({
                "type": "INGREDIENT",
                "text": ingredient
            })
    
    # Parse method/steps
    instructions = []
    in_method_section = False
    current_step = ""
    
    for line in lines:
        if line.startswith('## Method'):
            in_method_section = True
            continue
        elif line.startswith('## ') and in_method_section:
            break
        elif in_method_section and line.startswith('### '):
            # New step header
            if current_step:
                instructions.append({
                    "type": "STEP",
                    "text": current_step.strip()
                })
                current_step = ""
            step_title = line.replace('### ', '').strip()
            current_step = f"{step_title}: "
        elif in_method_section and line.startswith('**') and '**' in line:
            # TM6 instruction line (e.g., **Chop: 5 sec / Speed 4**)
            tm6_instruction = line.strip('**').strip()
            current_step += f"{tm6_instruction}. "
        elif in_method_section and line.strip():
            # Regular text in step
            current_step += f"{line.strip()} "
    
    # Add the last step
    if current_step:
        instructions.append({
            "type": "STEP",
            "text": current_step.strip()
        })
    
    # Metadata
    metadata = {
        "tools": ["TM6"],
        "totalTime": 2400,  # ~40 minutes total
        "prepTime": 600,    # ~10 minutes prep
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
        "instructions": instructions,
        "metadata": metadata
    }

def main():
    # Check if JWT token is provided
    jwt_token = os.getenv('COOKIDOO_JWT')
    if not jwt_token:
        print("Error: COOKIDOO_JWT environment variable not set.")
        print("Please set it with your Cookidoo JWT token:")
        print("  export COOKIDOO_JWT=your_jwt_token_here")
        print("You can get the JWT from your browser's cookies (_oauth2_proxy cookie) after logging into Cookidoo.")
        sys.exit(1)
    
    try:
        # Parse the recipe
        print("Parsing mushroom risotto recipe...")
        recipe_data = parse_mushroom_risotto_recipe()
        
        # Create uploader
        uploader = CookidooUploader(jwt_token)
        
        # Upload the recipe
        recipe_id = uploader.upload_recipe(recipe_data)
        
        print(f"\nSuccess! Your Mushroom Risotto recipe has been uploaded to Cookidoo.")
        print(f"Recipe ID: {recipe_id}")
        print(f"You can view it at: https://www.cookidoo.de/recipes/recipe/{recipe_id}")
        
    except Exception as e:
        print(f"Error uploading recipe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()