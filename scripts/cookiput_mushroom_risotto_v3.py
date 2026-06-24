#!/usr/bin/env python3
"""
Alternative cookiput script that uses cookies instead of Bearer token for authentication.
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
            
            if response.status_code == 201:
                data = response.json()
                return data.get('recipeId') or data.get('id')
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
        
        # Add a small delay
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
        elif in_method_section:
            if line.startswith('### '):
                # New step header
                if current_step:
                    instructions.append({
                        "type": "STEP",
                        "text": current_step.strip()
                    })
                    current_step = ""
                step_title = line.replace('### ', '').strip()
                current_step = f"{step_title}: "
            elif line.startswith('**') and '**' in line:
                # TM6 instruction line
                tm6_instruction = line.strip('**').strip()
                current_step += f"{tm6_instruction}. "
            elif line.strip():
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
    # Check if cookie is provided
    cookie_value = os.getenv('COOKIDOO_COOKIE')
    if not cookie_value:
        print("Error: COOKIDOO_COOKIE environment variable not set.")
        print("Please set it with your Cookidoo _oauth2_proxy cookie value:")
        print("  export COOKIDOO_COOKIE='your_cookie_value_here'")
        sys.exit(1)
    
    try:
        # Parse the recipe
        print("Parsing mushroom risotto recipe...")
        recipe_data = parse_mushroom_risotto_recipe()
        
        # Create uploader
        uploader = CookidooUploader(cookie_value)
        
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