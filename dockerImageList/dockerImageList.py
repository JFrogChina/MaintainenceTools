import requests
import json
import urllib3
import os
import argparse
import pandas as pd
from datetime import datetime, timedelta
import getpass
import sys

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Query Docker images from Artifactory')
parser.add_argument('--days', type=int, default=30, help='Number of days to look back for downloads (default: 30)')
parser.add_argument('--repo', type=str, help='Repository name to search in (default: all repositories)')
parser.add_argument('--artifactory-url', type=str, required=True, help='Artifactory URL (e.g., https://abc.jfrog.io/artifactory)')
parser.add_argument('--username', type=str, required=True, help='Artifactory username')
parser.add_argument('--output', type=str, help='Output Excel file name (default: docker_images_report_YYYYMMDD_HHMMSS.xlsx)')
parser.add_argument('--max-repos', type=int, default=None, help='Maximum number of repositories to search (default: unlimited)')
args = parser.parse_args()

# Set Artifactory configuration
ARTIFACTORY_URL = args.artifactory_url
USERNAME = args.username
PASSWORD = getpass.getpass('Enter Artifactory password: ')
REPO = args.repo

if not ARTIFACTORY_URL.startswith(('http://', 'https://')):
    print("❌ Error: Artifactory URL must start with http:// or https://")
    sys.exit(1)

if not ARTIFACTORY_URL.endswith('/artifactory'):
    print("❌ Error: Artifactory URL must end with /artifactory")
    sys.exit(1)

print("\nArtifactory Configuration:")
print(f"URL: {ARTIFACTORY_URL}")
print(f"Username: {USERNAME}")
print("Password: ********")

def get_all_repositories():
    url = f"{ARTIFACTORY_URL}/api/repositories"
    try:
        response = requests.get(url, auth=(USERNAME, PASSWORD), verify=False)
        response.raise_for_status()
        repos = response.json()
        docker_repos = [repo['key'] for repo in repos if repo.get('packageType') == 'Docker']
        return docker_repos
    except Exception as e:
        print(f"❌ Error fetching repositories: {str(e)}")
        sys.exit(1)

def search_repository(repo, cutoff_time):
    query = f"""
items.find({{
    "repo": "{repo}",
    "type": "file",
    "$and": [
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
.include("property.key","property.value","repo","path","name","created","modified","updated","created_by","modified_by",
        "type","size","actual_sha1","original_sha1","actual_md5","original_md5","sha256","stat.downloads","stat.downloaded")
.limit(500)
"""
    url = f"{ARTIFACTORY_URL}/api/search/aql"
    try:
        response = requests.post(url, auth=(USERNAME, PASSWORD), data=query, verify=False)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        print(f"❌ Error searching repository {repo}: {str(e)}")
        return []

# Get target repositories
repositories = [REPO] if REPO else get_all_repositories()
if not repositories:
    print("❌ No Docker repositories found.")
    sys.exit(1)

# Apply max-repo limit
if args.max_repos:
    repositories = repositories[:args.max_repos]
    print(f"\n🔢 Limiting to first {args.max_repos} repositories.")

print(f"\n🔍 Searching in repositories: {', '.join(repositories)}")

cutoff_time = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

all_images = []
for repo in repositories:
    print(f"\n📦 Searching repository: {repo}")
    images = search_repository(repo, cutoff_time)
    all_images.extend(images)

if not all_images:
    print("✅ No unused images found.")
    sys.exit(0)

print(f"\n🧊 Found {len(all_images)} unused images.")
excel_data = []
total_size_bytes = 0

for image in all_images:
    if not isinstance(image, dict):
        continue

    repo = image.get("repo", "")
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
    tag = path.split('/')[-1] if path else ""

    properties = {}
    for prop in image.get("properties", []):
        if "key" in prop and "value" in prop:
            properties[prop["key"]] = prop["value"]

    total_size_bytes += size

    excel_data.append({
        "Repository": repo,
        "Path": path,
        "Tag": tag,
        "Name": name,
        "Size (MB)": round(size / 1024 / 1024, 2),
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

total_size_mb = round(total_size_bytes / 1024 / 1024, 2)
total_size_gb = round(total_size_mb / 1024, 2)

print(f"\n📊 Summary:")
print(f"Total images: {len(all_images)}")
print(f"Total size: {total_size_mb} MB ({total_size_gb} GB)")

# Export to Excel
if excel_data:
    try:
        df = pd.DataFrame(excel_data)
        df.sort_values(by='Size (MB)', ascending=False, inplace=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = args.output or f"docker_images_report_{timestamp}.xlsx"
        if not excel_filename.endswith('.xlsx'):
            excel_filename += '.xlsx'
        df.to_excel(excel_filename, index=False, engine='openpyxl')
        print(f"\n✅ Report saved to: {excel_filename}")
    except Exception as e:
        print(f"❌ Error exporting Excel: {str(e)}")
