import requests
import json
import urllib3
import os
import argparse
import pandas as pd
from datetime import datetime, timedelta
import getpass

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Query Docker images from Artifactory')
parser.add_argument('--days', type=int, default=30, help='Number of days to look back for downloads (default: 30)')
parser.add_argument('--repo', type=str, default='docker-local', help='Repository name to search in (default: docker-local)')
parser.add_argument('--artifactory-url', type=str, required=True, help='Artifactory URL (e.g., https://abc.jfrog.io/artifactory)')
parser.add_argument('--username', type=str, required=True, help='Artifactory username')
parser.add_argument('--output', type=str, help='Output Excel file name (default: docker_images_report_YYYYMMDD_HHMMSS.xlsx)')
args = parser.parse_args()

# Set Artifactory configuration from command line arguments
ARTIFACTORY_URL = args.artifactory_url
USERNAME = args.username
# Get password securely
PASSWORD = getpass.getpass('Enter Artifactory password: ')
REPO = args.repo

# Validate Artifactory URL format
if not ARTIFACTORY_URL.startswith(('http://', 'https://')):
    print("❌ Error: Artifactory URL must start with http:// or https://")
    exit(1)

if not ARTIFACTORY_URL.endswith('/artifactory'):
    print("❌ Error: Artifactory URL must end with /artifactory")
    exit(1)

# Print configuration info
print("\nArtifactory Configuration:")
print(f"URL: {ARTIFACTORY_URL}")
print(f"Username: {USERNAME}")
print("Password: ********")

# Calculate cutoff time
cutoff_time = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

# AQL query for Docker images
query = f"""
items.find( 
{{
        "repo": {{"$eq": "{REPO}"}},
        "$and": [
            {{"type":"file"}},
            {{
                "$and": [
                    {{"path": {{"$match": "**"}}}}
                ]
            }},
            {{
                "$or": [
                    {{"stat.downloads": 0}},
                    {{"stat.downloads": null}}
                ]
            }},
            {{
                "$or": [
                    {{"stat.downloaded": {{"$lt": "{cutoff_time}"}}}},
                    {{"stat.downloaded": null}}
                ]
            }}
        ]
    }})
.include("property.key","property.value","repo","path","name","created","modified","updated","created_by","modified_by","type","size","id","type","repo","path","name","depth","created","created_by","modified","modified_by","updated","size","actual_sha1","original_sha1","actual_md5","original_md5","sha256","stat.downloads","stat.downloaded").
limit(500)
"""

# Send AQL request
url = f"{ARTIFACTORY_URL}/api/search/aql"
print(f"\nDEBUG: Sending AQL query: {query}")
try:
    response = requests.post(url, auth=(USERNAME, PASSWORD), data=query, verify=False)
    response.raise_for_status()  # Raise an exception for bad status codes
except requests.exceptions.RequestException as e:
    print(f"❌ Error connecting to Artifactory: {str(e)}")
    print("Please check your Artifactory URL, username, and password.")
    exit(1)

if response.status_code != 200:
    print(f"❌ Failed to get image information: {response.text}")
    print("Please check your Artifactory URL, username, and password.")
    exit(1)

# Parse results
try:
    results = response.json()
except json.JSONDecodeError:
    print("❌ Error: Invalid JSON response from Artifactory")
    print("Response content:", response.text)
    exit(1)

images = results.get("results", [])
print(f"DEBUG: Query response: {json.dumps(results, indent=2)}")

if not images:
    print("✅ No images found")
    exit(0)

print(f"\nFound {len(images)} images:")
total_size_bytes = 0
excel_data = []

# Process each image
for image in images:
    path = image.get("path", "")
    name = image.get("name", "")
    size = image.get("size", 0)
    created = image.get("created", "")
    modified = image.get("modified", "")
    updated = image.get("updated", "")
    created_by = image.get("created_by", "")
    modified_by = image.get("modified_by", "")
    actual_sha1 = image.get("actual_sha1", "")
    original_sha1 = image.get("original_sha1", "")
    actual_md5 = image.get("actual_md5", "")
    original_md5 = image.get("original_md5", "")
    sha256 = image.get("sha256", "")
    downloads = image.get("stat", {}).get("downloads", 0)
    last_downloaded = image.get("stat", {}).get("downloaded", "Never")
    
    # Extract tag from path
    tag = path.split('/')[-1] if path else ""
    
    # Get properties
    properties = {}
    for prop in image.get("properties", []):
        key = prop.get("key")
        value = prop.get("value")
        if key and value:
            properties[key] = value
    
    print(f"\nDEBUG: Processing file: {path}/{name}")
    print(f"DEBUG: File info: {json.dumps(image, indent=2)}")
    
    total_size_bytes += size
    
    # Print to console
    print(f"\nImage: {REPO}/{path}/{name}")
    print(f"  Tag: {tag}")
    print(f"  Size: {round(size/1024/1024, 2)} MB")
    print(f"  Created: {created}")
    print(f"  Modified: {modified}")
    print(f"  Updated: {updated}")
    print(f"  Created by: {created_by}")
    print(f"  Modified by: {modified_by}")
    print(f"  Downloads: {downloads}")
    print(f"  Last Downloaded: {last_downloaded}")
    print(f"  SHA1: {actual_sha1}")
    print(f"  Original SHA1: {original_sha1}")
    print(f"  MD5: {actual_md5}")
    print(f"  Original MD5: {original_md5}")
    print(f"  SHA256: {sha256}")
    print("  Properties:")
    for key, value in properties.items():
        print(f"    {key}: {value}")
    
    # Add to Excel data
    excel_data.append({
        "Repository": REPO,
        "Path": path,
        "Tag": tag,
        "Name": name,
        "Size (MB)": round(size/1024/1024, 2),
        "Created": created,
        "Modified": modified,
        "Updated": updated,
        "Created By": created_by,
        "Modified By": modified_by,
        "Downloads": downloads,
        "Last Downloaded": last_downloaded,
        "SHA1": actual_sha1,
        "Original SHA1": original_sha1,
        "MD5": actual_md5,
        "Original MD5": original_md5,
        "SHA256": sha256
    })

# Total size summary
total_size_mb = round(total_size_bytes / 1024 / 1024, 2)
total_size_gb = round(total_size_mb / 1024, 2)

print(f"\nSummary:")
print(f"Total images found: {len(images)}")
print(f"Total size: {total_size_mb} MB ({total_size_gb} GB)")

# Export to Excel
if excel_data:
    df = pd.DataFrame(excel_data)
    
    # Sort by size in descending order
    df = df.sort_values(by='Size (MB)', ascending=False)
    
    # Generate filename with timestamp if not specified
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"docker_images_report_{timestamp}.xlsx"
    else:
        excel_filename = args.output if args.output.endswith('.xlsx') else f"{args.output}.xlsx"
    
    # Export to Excel
    df.to_excel(excel_filename, index=False, engine='openpyxl')
    print(f"\n✅ Report exported to: {excel_filename}")
    
    # Print top 10 largest images
    print("\nTop 10 largest images:")
    for _, row in df.head(10).iterrows():
        print(f"{row['Path']}/{row['Name']}: {row['Size (MB)']} MB") 