#!/usr/bin/env python3
"""
Enhanced cookiput script for uploading Mushroom Risotto to Cookidoo.
Includes better error handling, debugging, and alternative API endpoints.
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
        # Try multiple base URLs that Cookidoo might use
        self.base_urls = [
            "https://www.cookidoo.de",
            "https://api.cookidoo.de",
            "https://cookidoo.de"
        ]
        self.headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    
    def find_working_endpoint(self) -> str:
        """Try different endpoints to find one that works."""
        for base_url in self.base_urls:
            try:
                url = f"{base_url}/created-recipes/de-DE"
                response = requests.head(url, headers=self.headers, timeout=5)
                if response.status_code == 200 or response.status_code == 401 or response.status_code == 403:
                    print(f"Found working base URL: {base_url}")
                    return base_url
            except Exception as e:
                print(f"Failed to connect to {base_url}: {e}")
                continue
        raise Exception("No working Cookidoo endpoint found")
    
    def create_recipe_stub(self, recipe_name: str, base_url: str) -> str:
        """Create a new recipe stub and return the recipe ID."""
        url = f"{base_url}/created-recipes/de-DE"
        payload = {"recipeName": recipe_name}
        
        print(f"Attempting to create recipe stub at: {url}")
        print(f"Headers: {self.headers}")
        print(f"Payload: {payload}")
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 201 or response.status_code == 200:
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
    
    def update_recipe_ingredients(self, recipe_id: str, ingredients: List[Dict], base_url: str) -> None:
        """Update recipe with ingredients."""
        url = f"{base_url}/created-recipes/de-DE/{recipe_id}"
        payload = {"ingredients": ingredients}
        
        response = requests.patch(url, headers=self.headers, json=payload, timeout=10)
        response.raise_for_status()
    
    def update_recipe_instructions(self, recipe_id: str, instructions: List[Dict], base_url: str) -> None:
        """Update recipe with cooking instructions."""
        url = f"{base_url}/created-recipes/de-DE/{recipe_id}"
        payload = {"instructions": instructions}
        
        response = requests.patch(url, headers=self.headers, json=payload, timeout=10)
        response.raise_for_status()
    
    def update_recipe_metadata(self, recipe_id: str, metadata: Dict, base_url: str) -> None:
        """Update recipe with metadata."""
        url = f"{base_url}/created-recipes/de-DE/{recipe_id}"
        payload = metadata
        
        response = requests.patch(url, headers=self.headers, json=payload, timeout=10)
        response.raise_for_status()
    
    def upload_recipe(self, recipe_data: Dict) -> str:
        """Complete workflow to upload a recipe."""
        # Find working endpoint
        base_url = self.find_working_endpoint()
        
        print("Creating recipe stub...")
        recipe_id = self.create_recipe_stub(recipe_data['name'], base_url)
        print(f"Recipe created with ID: {recipe_id}")
        
        # Add a small delay
        time.sleep(1)
        
        print("Updating ingredients...")
        self.update_recipe_ingredients(recipe_id, recipe_data['ingredients'], base_url)
        
        print("Updating instructions...")
        self.update_recipe_instructions(recipe_id, recipe_data['instructions'], base_url)
        
        print("Updating metadata...")
        self.update_recipe_metadata(recipe_id, recipe_data['metadata'], base_url)
        
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
    # Check if JWT token is provided
    jwt_token = os.getenv('COOKIDOO_JWT')
    if not jwt_token:
        print("Error: COOKIDOO_JWT environment variable not set.")
        print("Please set it with your Cookidoo JWT token:")
        print("  export COOKIDOO_JWT=your_jwt_token_here")
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