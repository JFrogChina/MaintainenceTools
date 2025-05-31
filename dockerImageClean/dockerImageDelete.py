import requests
import json
import urllib3
import os
import argparse
import getpass
import sys
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Delete Docker images from Artifactory based on keywords')
parser.add_argument('--artifactory-url', type=str, required=True, help='Artifactory URL (e.g., https://abc.jfrog.io/artifactory)')
parser.add_argument('--username', type=str, required=True, help='Artifactory username')
parser.add_argument('--repo', type=str, default='docker-local', help='Repository name (default: docker-local)')
parser.add_argument('--keyword', type=str, required=True, help='Keyword to match in image path or name')
parser.add_argument('--dry-run', action='store_true', help='Enable dry run mode (no actual deletion)')
parser.add_argument('--verbose', action='store_true', help='Show detailed information in dry run mode')
args = parser.parse_args()

# Set Artifactory configuration from command line arguments
ARTIFACTORY_URL = args.artifactory_url
USERNAME = args.username
# Get password securely
PASSWORD = getpass.getpass('Enter Artifactory password: ')
REPO = args.repo
KEYWORD = args.keyword

# Validate Artifactory URL format
if not ARTIFACTORY_URL.startswith(('http://', 'https://')):
    print("❌ Error: Artifactory URL must start with http:// or https://")
    sys.exit(1)

if not ARTIFACTORY_URL.endswith('/artifactory'):
    print("❌ Error: Artifactory URL must end with /artifactory")
    sys.exit(1)

# Print configuration info
print("\nArtifactory Configuration:")
print(f"URL: {ARTIFACTORY_URL}")
print(f"Username: {USERNAME}")
print("Password: ********")
print(f"Repository: {REPO}")
print(f"Keyword: {KEYWORD}")
print(f"Mode: {'Dry Run' if args.dry_run else 'Delete'}")
if args.dry_run and args.verbose:
    print("Verbose mode: Enabled")

# Build AQL query to find images
query = f"""
items.find(
    {{
        "repo": "{REPO}",
        "type": "file",
        "path": {{"$match": "*{KEYWORD}*"}}
    }}
).include("repo","path","name","size","created","modified","created_by","modified_by")
"""

# Send AQL request
url = f"{ARTIFACTORY_URL}/api/search/aql"
print(f"\nSearching for images matching keyword '{KEYWORD}'...")
try:
    response = requests.post(url, auth=(USERNAME, PASSWORD), data=query, verify=False)
    
    # Check for authentication errors
    if response.status_code == 401:
        print("❌ Error: Authentication failed")
        print("Please check your username and password.")
        sys.exit(1)
    elif response.status_code == 403:
        print("❌ Error: Access forbidden")
        print("Please check your permissions in Artifactory.")
        sys.exit(1)
    
    # Check for other HTTP errors
    response.raise_for_status()
    
except requests.exceptions.ConnectionError:
    print("❌ Error: Could not connect to Artifactory")
    print("Please check your Artifactory URL and network connection.")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"❌ Error connecting to Artifactory: {str(e)}")
    print("Please check your Artifactory URL, username, and password.")
    sys.exit(1)

# Parse results
try:
    results = response.json()
except json.JSONDecodeError:
    print("❌ Error: Invalid JSON response from Artifactory")
    print("Response content:", response.text)
    sys.exit(1)

images = results.get("results", [])
if not images:
    print("✅ No images found matching the keyword")
    sys.exit(0)

# Print found images
print(f"\nFound {len(images)} images matching keyword '{KEYWORD}':")
total_size_bytes = 0
for image in images:
    path = image.get("path", "")
    name = image.get("name", "")
    size = image.get("size", 0)
    total_size_bytes += size
    
    if args.dry_run and args.verbose:
        created = image.get("created", "")
        modified = image.get("modified", "")
        created_by = image.get("created_by", "")
        modified_by = image.get("modified_by", "")
        
        print(f"\nImage: {REPO}/{path}/{name}")
        print(f"  Size: {round(size/1024/1024, 2)} MB")
        print(f"  Created: {created}")
        print(f"  Modified: {modified}")
        print(f"  Created by: {created_by}")
        print(f"  Modified by: {modified_by}")
        print(f"  Delete URL: {ARTIFACTORY_URL}/{REPO}/{path}/{name}")
    else:
        print(f"\nImage: {REPO}/{path}/{name}")
        print(f"  Size: {round(size/1024/1024, 2)} MB")

# Print summary
total_size_mb = round(total_size_bytes / 1024 / 1024, 2)
total_size_gb = round(total_size_mb / 1024, 2)
print(f"\nTotal size: {total_size_mb} MB ({total_size_gb} GB)")

# Ask for confirmation if not in dry run mode
if not args.dry_run:
    confirm = input(f"\n⚠️  Are you sure you want to delete these {len(images)} images? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled")
        sys.exit(0)

# Delete images
print("\nDeleting images...")
deleted_count = 0
failed_count = 0

for image in images:
    path = image.get("path", "")
    name = image.get("name", "")
    full_path = f"{path}/{name}" if path else name
    
    if args.dry_run:
        if args.verbose:
            print(f"Would delete: {REPO}/{full_path}")
            print(f"  URL: {ARTIFACTORY_URL}/{REPO}/{full_path}")
            print(f"  Size: {round(image.get('size', 0)/1024/1024, 2)} MB")
        else:
            print(f"Would delete: {REPO}/{full_path}")
        deleted_count += 1
        continue
    
    try:
        delete_url = f"{ARTIFACTORY_URL}/{REPO}/{full_path}"
        response = requests.delete(delete_url, auth=(USERNAME, PASSWORD), verify=False)
        
        if response.status_code == 204:
            print(f"✅ Deleted: {REPO}/{full_path}")
            deleted_count += 1
        else:
            print(f"❌ Failed to delete {REPO}/{full_path}: {response.status_code} {response.text}")
            failed_count += 1
            
    except Exception as e:
        print(f"❌ Error deleting {REPO}/{full_path}: {str(e)}")
        failed_count += 1

# Print final summary
print(f"\nSummary:")
print(f"Total images found: {len(images)}")
print(f"Successfully deleted: {deleted_count}")
print(f"Failed to delete: {failed_count}")
print(f"Total size: {total_size_mb} MB ({total_size_gb} GB)")

if args.dry_run:
    print("\n⚠️  This was a dry run. No images were actually deleted.")
    if args.verbose:
        print("\nDetailed information:")
        print(f"Repository: {REPO}")
        print(f"Keyword: {KEYWORD}")
        print(f"Total images: {len(images)}")
        print(f"Total size: {total_size_mb} MB ({total_size_gb} GB)")
        print(f"Average size: {round(total_size_mb/len(images), 2)} MB per image") 