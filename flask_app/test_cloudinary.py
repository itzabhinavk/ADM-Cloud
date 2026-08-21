#!/usr/bin/env python
import os
from dotenv import load_dotenv

load_dotenv()

import cloudinary
import cloudinary.api

cfg = {
    "CLOUDINARY_CLOUD_NAME": os.environ.get("CLOUDINARY_CLOUD_NAME"),
    "CLOUDINARY_API_KEY": os.environ.get("CLOUDINARY_API_KEY"),
    "CLOUDINARY_API_SECRET": os.environ.get("CLOUDINARY_API_SECRET"),
}

print("Configuration loaded:")
print(f"  Cloud Name: {cfg['CLOUDINARY_CLOUD_NAME']}")
print(f"  API Key: {cfg['CLOUDINARY_API_KEY']}")
print(f"  API Secret: {cfg['CLOUDINARY_API_SECRET'][:10]}...")

try:
    cloudinary.config(
        cloud_name=cfg["CLOUDINARY_CLOUD_NAME"],
        api_key=cfg["CLOUDINARY_API_KEY"],
        api_secret=cfg["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    print("\n✅ Cloudinary configuration set successfully!")
    
    # Test with a simple API call
    result = cloudinary.api.resources(max_results=1, type='upload')
    print(f"✅ Cloudinary API connection working!")
    print(f"   Total resources in account: {result.get('total_count', 0)}")
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
