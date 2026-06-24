#!/usr/bin/env python3
"""
Script to update the existing mushroom risotto recipe with structured TM6 parameters.
"""

import json
import requests
import os
import sys
import time

def update_recipe_with_structured_steps(recipe_id: str, cookie_value: str):
    """Update existing recipe with structured TM6 parameters for each step."""
    
    base_url = "https://www.cookidoo.de"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    cookies = {
        "_oauth2_proxy": cookie_value
    }
    
    # Structured TM6 instructions
    structured_instructions = [
        {
            "type": "STEP",
            "text": "Add 50g Parmigiano chunks to TM bowl",
            "tm6": {
                "mode": "grate",
                "time": 10,
                "speed": 10,
                "reverse": False
            }
        },
        {
            "type": "STEP",
            "text": "Add 485g mushrooms to TM bowl (quarter any large ones first). Remove. Heat a large pan over high heat with a little butter or oil. Sauté the mushrooms in batches — don't crowd the pan. Cook until well browned, ~5–7 min total. Season lightly. Set aside.",
            "tm6": {
                "mode": "chop",
                "time": 3,
                "speed": 4,
                "reverse": False
            }
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 1 onion (halved), 2 garlic cloves",
            "tm6": {
                "mode": "chop",
                "time": 5,
                "speed": 7,
                "reverse": False
            }
        },
        {
            "type": "STEP",
            "text": "Add 20g butter and 1 tbsp olive oil",
            "tm6": {
                "mode": "cook",
                "time": 180,
                "speed": 1,
                "reverse": False,
                "temperature": 120
            }
        },
        {
            "type": "STEP",
            "text": "Add 250g risotto rice",
            "tm6": {
                "mode": "cook",
                "time": 120,
                "speed": "Soft Stir",
                "reverse": True,
                "temperature": 120
            }
        },
        {
            "type": "STEP",
            "text": "Add 100ml dry white wine",
            "tm6": {
                "mode": "cook",
                "time": 120,
                "speed": "Soft Stir",
                "reverse": True,
                "temperature": 100
            }
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 750ml hot stock (1 chicken stock cube dissolved in 750ml hot water), The browned mushrooms, A few sprigs of fresh thyme leaves",
            "tm6": {
                "mode": "cook",
                "time": 1080,
                "speed": "Soft Stir",
                "reverse": True,
                "temperature": 100
            }
        },
        {
            "type": "STEP",
            "text": "Add to TM bowl: 20g butter, Most of the grated Parmigiano (save some for serving)",
            "tm6": {
                "mode": "mix",
                "time": 30,
                "speed": "Soft Stir",
                "reverse": True
            }
        }
    ]
    
    # Update instructions
    url = f"{base_url}/created-recipes/de-DE/{recipe_id}"
    payload = {"instructions": structured_instructions}
    
    print(f"Updating recipe {recipe_id} with structured TM6 parameters...")
    response = requests.patch(url, headers=headers, cookies=cookies, json=payload, timeout=10)
    
    if response.status_code == 200:
        print("✓ Successfully updated recipe with structured TM6 parameters!")
        print("The recipe now includes speed, time, temperature, and reverse settings for each step.")
    else:
        print(f"✗ Failed to update recipe. Status: {response.status_code}")
        print(f"Response: {response.text}")
        raise Exception(f"Update failed: {response.status_code}")

def main():
    # Get recipe ID and cookie
    recipe_id = "01KJJEP6HVX2KY6Z5ANKYGAHNN"  # From our successful upload
    cookie_value = os.getenv('COOKIDOO_COOKIE')
    
    if not cookie_value:
        print("Error: COOKIDOO_COOKIE environment variable not set.")
        print("Please set it with your Cookidoo _oauth2_proxy cookie value:")
        print("  export COOKIDOO_COOKIE='your_cookie_value_here'")
        sys.exit(1)
    
    try:
        update_recipe_with_structured_steps(recipe_id, cookie_value)
        print(f"\nYour mushroom risotto recipe has been updated with structured TM6 parameters!")
        print(f"View it at: https://www.cookidoo.de/recipes/recipe/{recipe_id}")
        
    except Exception as e:
        print(f"Error updating recipe: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()