import requests
import json
import argparse
import getpass
import pandas as pd
from datetime import datetime
import urllib3
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 解析参数
parser = argparse.ArgumentParser(description="Query all Docker packages and versions from JFrog Metadata API and export to CSV.")
parser.add_argument('--url', required=True, help='JFrog base URL, e.g., https://abc.jfrog.io')
parser.add_argument('--token', help='Access token (or input securely)')
parser.add_argument('--output', default=None, help='CSV output file name')
parser.add_argument('--repo', help='Filter to only include repositories containing this substring')
parser.add_argument('--debug', action='store_true', help='Enable debug logs')
parser.add_argument('--threads', type=int, default=20, help='Number of concurrent threads (default: 6)')
args = parser.parse_args()

token = args.token or getpass.getpass('Enter JFrog access token: ')
graphql_url = f"{args.url.rstrip('/')}/metadata/api/v1/query"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

def log(msg):
    if args.debug:
        print(msg)

def get_all_packages():
    packages = []
    cursor = None
    while True:
        query = {
            "query": """
            query ($first: Int, $after: ID) {
              packages(
                filter: { name: "*", packageTypeIn: [DOCKER] },
                first: $first,
                after: $after,
                orderBy: { field: NAME, direction: DESC }
              ) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                edges {
                  node {
                    id
                    name
                    description
                    created
                    modified
                    versionsCount
                  }
                }
              }
            }
            """,
            "variables": {
                "first": 100,
                "after": cursor
            }
        }
        log(f"📦 Fetching packages after cursor: {cursor}")
        resp = requests.post(graphql_url, headers=headers, json=query, verify=False)
        resp.raise_for_status()
        data = resp.json()
        page = data.get("data", {}).get("packages", {})
        edges = page.get("edges", [])
        for edge in edges:
            packages.append(edge["node"])
        if not page.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = page["pageInfo"]["endCursor"]
    return packages

def get_all_versions(package):
    versions = []
    cursor = None
    while True:
        query = {
            "query": """
            query ($filter: VersionFilter!, $first: Int, $after: ID) {
              versions(filter: $filter, first: $first, after: $after, orderBy: { field: NAME_SEMVER, direction: DESC }) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                edges {
                  node {
                    name
                    created
                    modified
                    size
                    stats { downloadCount }
                    repos { name type leadFilePath }
                  }
                }
              }
            }
            """,
            "variables": {
                "filter": {
                    "packageId": package['id'],
                    "ignorePreRelease": False,
                    "ignoreNonLeadFiles": True
                },
                "first": 100,
                "after": cursor
            }
        }
        log(f"🔍 Fetching versions for {package['name']} cursor: {cursor}")
        resp = requests.post(graphql_url, headers=headers, json=query, verify=False)
        resp.raise_for_status()
        data = resp.json()
        page = data.get("data", {}).get("versions", {})
        edges = page.get("edges", [])
        for edge in edges:
            versions.append(edge["node"])
        if not page.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = page["pageInfo"]["endCursor"]
    return package, versions

def process_package(package):
    try:
        pkg, versions = get_all_versions(package)
        rows = []
        for v in versions:
            base = {
                "Package Name": pkg["name"],
                "Description": pkg.get("description", ""),
                "Package Created": pkg.get("created", ""),
                "Package Modified": pkg.get("modified", ""),
                "Versions Count": pkg.get("versionsCount", 0),
                "Version": v.get("name", ""),
                "Version Created": v.get("created", ""),
                "Version Modified": v.get("modified", ""),
                "Download Count": v.get("stats", {}).get("downloadCount", 0),
            }
            try:
                size_bytes = int(v.get("size", 0))
                base["Version Size (MB)"] = round(size_bytes / 1024 / 1024, 2)
            except:
                base["Version Size (MB)"] = 0

            repos = v.get("repos", [])
            if repos:
                for r in repos:
                    if args.repo and args.repo.lower() not in r.get("name", "").lower():
                        continue
                    row = base.copy()
                    row["Repository Name"] = r.get("name", "")
                    row["Repo Type"] = r.get("type", "")
                    row["Lead File Path"] = r.get("leadFilePath", "")
                    rows.append(row)
            elif not args.repo:
                row = base.copy()
                row["Repository Name"] = ""
                row["Repo Type"] = ""
                row["Lead File Path"] = ""
                rows.append(row)
        return rows
    except Exception as e:
        print(f"❌ Failed to process package {package['name']}: {e}")
        return []

# Main logic
all_packages = get_all_packages()
total = len(all_packages)
print(f"📦 Total Docker packages found: {total}")

all_rows = []
with ThreadPoolExecutor(max_workers=args.threads) as executor:
    future_to_package = {executor.submit(process_package, pkg): idx for idx, pkg in enumerate(all_packages)}
    for i, future in enumerate(as_completed(future_to_package), 1):
        percent = round((i / total) * 100, 1)
        print(f"➡️ Progress: {i}/{total} ({percent}%)")
        all_rows.extend(future.result())

# Output to CSV
if not all_rows:
    print("⚠️ No data to export.")
    exit(0)

df = pd.DataFrame(all_rows)
df.sort_values(by="Version Size (MB)", ascending=False, inplace=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"{os.path.splitext(args.output)[0] if args.output else 'docker_versions'}_{timestamp}.csv"
df.to_csv(filename, index=False)

print(f"\n✅ Exported {len(df)} version rows to {filename}")
