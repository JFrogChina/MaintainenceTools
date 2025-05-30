import requests
import json
from datetime import datetime, timedelta
import urllib3
import os
import pandas as pd
import argparse

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Find Docker manifest files not downloaded within a specified time period.')
parser.add_argument('--days', type=int, default=1,
                    help='Number of days to look back (default: 1)')
parser.add_argument('--hours', type=int, default=0,
                    help='Number of hours to look back (default: 0)')
args = parser.parse_args()

# Read configuration from environment variables
ARTIFACTORY_URL = os.getenv('ARTIFACTORY_URL', 'https://demo.jfrogchina.com/artifactory')
REPO = os.getenv('ARTIFACTORY_REPO', 'docker-local')  # Target Docker repository
USERNAME = os.getenv('ARTIFACTORY_USERNAME')
PASSWORD = os.getenv('ARTIFACTORY_PASSWORD')

# Check required environment variables
if not all([USERNAME, PASSWORD]):
    print("❌ Error: Please set required environment variables ARTIFACTORY_USERNAME and ARTIFACTORY_PASSWORD")
    exit(1)

# Calculate time period
time_period = timedelta(days=args.days, hours=args.hours)
cutoff_time = (datetime.now() - time_period).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

# Format time period for display
time_period_str = []
if args.days > 0:
    time_period_str.append(f"{args.days} day{'s' if args.days != 1 else ''}")
if args.hours > 0:
    time_period_str.append(f"{args.hours} hour{'s' if args.hours != 1 else ''}")
time_period_display = " and ".join(time_period_str)

# AQL query to get Docker images
aql_query = f"""
items.find({{
  "repo": "{REPO}",
  "$and": [
    {{
      "$or": [
        {{"name": {{"$eq": "manifest.json"}}}},
        {{"name": {{"$eq": "list.manifest.json"}}}}
      ]
    }},
    {{
      "$or": [
        {{"property.key": "docker.repoName"}},
        {{"property.key": "docker.repoName", "property.value": "library/*"}}
      ]
    }},
    {{
      "$or": [
        {{"stat.downloaded": {{"$lt": "{cutoff_time}"}}}},
        {{"stat.downloaded": null}}
      ]
    }}
  ]
}}).include("property.key","property.value","repo","path","name","created","modified","updated","created_by","modified_by","type","size","id","type","repo","path","name","depth","created","created_by","modified","modified_by","updated","size","actual_sha1","original_sha1","actual_md5","original_md5","sha256").
limit(1500)"""

# Send AQL request
url = f"{ARTIFACTORY_URL}/api/search/aql"
response = requests.post(url, auth=(USERNAME, PASSWORD), data=aql_query, verify=False)

if response.status_code != 200:
    print("❌ AQL query failed:", response.text)
    exit(1)

# Parse results
results = response.json()
items = results.get("results", [])

print(f"\n🎯 Docker manifest files not downloaded in the past {time_period_display} (Total: {len(items)}):\n")

# Prepare data for Excel
excel_data = []

for item in items:
    repo = item["repo"]
    path = item["path"]
    name = item["name"]
    
    # Get docker.repoName and docker.tag.name from properties
    docker_repo = "Unknown"
    docker_tag = "Unknown"
    if "properties" in item:
        for prop in item["properties"]:
            if prop.get("key") == "docker.repoName":
                docker_repo = prop.get("value", "Unknown")
            elif prop.get("key") == "docker.tag.name":
                docker_tag = prop.get("value", "Unknown")
    
    # Get the image path (directory containing the manifest)
    image_path = os.path.dirname(path)
    
    # Query for all files in the same directory to calculate total size
    size_query = f"""
    items.find({{
        "repo": "{repo}",
        "path": "{image_path}"
    }}).include("name", "size")
    """
    
    print(f"\nDebug - Size query for {repo}/{image_path}:")
    print(size_query)
    
    size_response = requests.post(url, auth=(USERNAME, PASSWORD), data=size_query, verify=False)
    if size_response.status_code == 200:
        size_results = size_response.json()
        files = size_results.get("results", [])
        print(f"Found {len(files)} files:")
        for file in files:
            print(f"  - {file.get('name')}: {file.get('size', 0)} bytes")
        
        total_size_bytes = sum(item.get("size", 0) for item in files)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
        print(f"Total size: {total_size_mb} MB")
    else:
        print(f"Failed to get size information: {size_response.text}")
        total_size_mb = 0
    
    last_downloaded = item.get("stat", {}).get("downloaded", "Never")
    
    # Print to console
    print(f"\n{repo}/{path}/{name} (Docker Repo: {docker_repo}, Tag: {docker_tag}, Size: {total_size_mb} MB, Last Downloaded: {last_downloaded})")
    
    # Add to Excel data
    excel_data.append({
        "Repository": repo,
        "Path": path,
        "File Name": name,
        "Docker Repository": docker_repo,
        "Docker Tag": docker_tag,
        "Last Downloaded": last_downloaded,
        "Created": item.get("created", ""),
        "Modified": item.get("modified", ""),
        "Size (MB)": total_size_mb,
        "Created By": item.get("created_by", ""),
        "Modified By": item.get("modified_by", "")
    })

# Create DataFrame and export to Excel
if excel_data:
    df = pd.DataFrame(excel_data)
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"docker_manifest_report_{timestamp}.xlsx"
    
    # Export to Excel
    df.to_excel(excel_filename, index=False, engine='openpyxl')
    print(f"\n✅ Report exported to: {excel_filename}")

