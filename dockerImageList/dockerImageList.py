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

parser = argparse.ArgumentParser(description='Query Docker images from Artifactory and calculate their total sizes.')
parser.add_argument('--days', type=int, help='Only include images not downloaded in the last N days (optional)')
parser.add_argument('--repo', type=str, help='Docker repository to analyze')
parser.add_argument('--artifactory-url', type=str, required=True, help='Artifactory URL (e.g., https://example.jfrog.io/artifactory)')
parser.add_argument('--username', type=str, required=True, help='Artifactory username')
parser.add_argument('--output', type=str, help='Output Excel file name (optional)')
parser.add_argument('--max-repos', type=int, default=None, help='Limit the number of repositories to process')
args = parser.parse_args()

ARTIFACTORY_URL = args.artifactory_url
USERNAME = args.username
PASSWORD = getpass.getpass('Enter Artifactory password: ')
REPO = args.repo

if not ARTIFACTORY_URL.endswith('/artifactory'):
    print("❌ Error: Artifactory URL must end with /artifactory")
    sys.exit(1)

def get_docker_repos():
    url = f"{ARTIFACTORY_URL}/api/repositories?type=local"
    try:
        r = requests.get(url, auth=(USERNAME, PASSWORD), verify=False)
        r.raise_for_status()
        data = r.json()
        print("📋 All local Docker repositories:")
        for repo in data:
            if repo.get("packageType") == "Docker":
                print(f"  - {repo.get('key')}")
        return [repo["key"] for repo in data if repo.get("packageType") == "Docker"]
    except Exception as e:
        print(f"❌ Failed to get repositories: {e}")
        sys.exit(1)

def find_manifest_paths(repo):
    query = f"""
items.find({{
    "repo": "{repo}",
    "name": "manifest.json",
    "type": "file"
}})
.include("repo", "path", "name", "created", "modified", "updated", "created_by", "modified_by", "sha256")
"""
    url = f"{ARTIFACTORY_URL}/api/search/aql"
    try:
        r = requests.post(url, auth=(USERNAME, PASSWORD), data=query, verify=False)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as e:
        print(f"❌ Error fetching manifest.json paths in repo {repo}: {e}")
        return []

def get_total_size(repo, path_prefix):
    query = f"""
items.find({{
    "repo": "{repo}",
    "path": {{"$match": "{path_prefix}*"}},
    "type": "file"
}})
.include("size")
"""
    url = f"{ARTIFACTORY_URL}/api/search/aql"
    try:
        r = requests.post(url, auth=(USERNAME, PASSWORD), data=query, verify=False)
        r.raise_for_status()
        items = r.json().get("results", [])
        return sum(i.get("size", 0) for i in items)
    except Exception as e:
        print(f"❌ Failed to calculate size for {repo}/{path_prefix}: {e}")
        return 0

def get_manifest_stats(repo, path):
    url = f"{ARTIFACTORY_URL}/api/storage/{repo}/{path}/manifest.json?stats"
    try:
        r = requests.get(url, auth=(USERNAME, PASSWORD), verify=False)
        if r.status_code == 404:
            print(f"⚠️ Manifest not found for {repo}/{path}, skipping.")
            return 0, "Never"
        r.raise_for_status()
        data = r.json()
        count = data.get("downloadCount", 0)
        ts = data.get("lastDownloaded")
        last_downloaded = (
            datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")
            if ts else "Never"
        )
        return count, last_downloaded
    except Exception as e:
        print(f"⚠️ Failed to fetch manifest stats for {repo}/{path}: {e}")
        return 0, "Never"

# Start analysis
repos = [REPO] if REPO else get_docker_repos()
if args.max_repos:
    repos = repos[:args.max_repos]

print(f"\n🔍 Repositories to scan: {repos}\n")
results = []
cutoff = datetime.utcnow() - timedelta(days=args.days) if args.days else None

for repo_idx, repo in enumerate(repos, start=1):
    print(f"📦 Scanning {repo} ({repo_idx}/{len(repos)})")
    manifests = find_manifest_paths(repo)
    total = len(manifests)
    print(f"   📄 Found {total} manifest.json files in {repo}")
    for idx, m in enumerate(manifests, start=1):
        print(f"    🔄 Processing {idx}/{total}: {repo}/{m.get('path')}")
        path = m.get("path", "")
        downloads, last_downloaded = get_manifest_stats(repo, path)

        if args.days and last_downloaded != "Never":
            try:
                dl_date = datetime.strptime(last_downloaded, "%Y-%m-%dT%H:%M:%SZ")
                if dl_date > cutoff:
                    continue
            except:
                pass

        size = get_total_size(repo, path)
        results.append({
            "Repository": repo,
            "Path": path,
            "Tag": path.split("/")[-1],
            "Size (MB)": round(size / 1024 / 1024, 2),
            "Created": m.get("created"),
            "Modified": m.get("modified"),
            "Updated": m.get("updated"),
            "Created By": m.get("created_by"),
            "Modified By": m.get("modified_by"),
            "SHA256": m.get("sha256"),
            "Downloads": downloads,
            "Last Downloaded": last_downloaded
        })

if not results:
    print("\n✅ No images matched the criteria.")
    sys.exit(0)

df = pd.DataFrame(results)
df.sort_values(by="Size (MB)", ascending=False, inplace=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_name = args.output or f"docker_image_report_{timestamp}.xlsx"
df.to_excel(output_name, index=False, engine="openpyxl")

print(f"\n✅ Report saved to {output_name}")
