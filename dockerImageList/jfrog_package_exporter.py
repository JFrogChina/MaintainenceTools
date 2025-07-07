# Final optimized code: Only fetch lastDownloaded for top N largest versions
import requests
import json
import argparse
import getpass
import pandas as pd
from datetime import datetime
import urllib3
import os
import concurrent.futures
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Argument parsing
parser = argparse.ArgumentParser(description="Query JFrog packages and export to Excel or CSV.")
parser.add_argument('--url', required=True, help='JFrog base URL, e.g., https://abc.jfrog.io')
parser.add_argument('--token', help='Access token (or input securely)')
parser.add_argument('--output', default=None, help='Output Excel or CSV file name')
parser.add_argument('--repo', help='Filter results to only include repositories containing this substring')
parser.add_argument('--type', default='DOCKER', help='Package type (e.g., DOCKER, MAVEN, NPM, PYPI)')
parser.add_argument('--last-download-top', type=int, default=0, help='Top N largest versions to fetch lastDownloaded')
parser.add_argument('--debug', action='store_true', help='Enable debug logs')
args = parser.parse_args()

package_type = args.type.upper()
if package_type not in ['DOCKER', 'MAVEN', 'NPM', 'PYPI']:
    raise ValueError("Unsupported package type: {}".format(package_type))

token = args.token or getpass.getpass('Enter JFrog access token: ')
graphql_url = f"{args.url.rstrip('/')}/metadata/api/v1/query"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

def log(msg):
    if args.debug:
        print(msg)

def decode_cursor(cursor):
    try:
        return base64.b64decode(cursor).decode()
    except Exception:
        return cursor

def get_all_packages():
    packages = []
    cursor = None
    while True:
        query = {
            "query": """
            query ($first: Int, $after: ID, $type: PackageType!) {
              packages(
                filter: { name: "*", packageTypeIn: [$type] },
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
                "after": cursor,
                "type": package_type
            }
        }
        log(f"📦 Fetching packages after cursor: {decode_cursor(cursor) if cursor else 'None'}")
        resp = requests.post(graphql_url, headers=headers, json=query, verify=False)
        resp.raise_for_status()
        data = resp.json()
        page = data.get("data", {}).get("packages", {})
        for edge in page.get("edges", []):
            packages.append(edge["node"])
        if not page.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = page["pageInfo"]["endCursor"]
    return packages

def get_all_versions(package):
    versions = []
    package_id = package["id"]
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
                    "packageId": package_id,
                    "ignorePreRelease": False,
                    "ignoreNonLeadFiles": True
                },
                "first": 100,
                "after": cursor
            }
        }
        log(f"🔍 Fetching versions for {package['name']} cursor: {decode_cursor(cursor) if cursor else 'None'}")
        resp = requests.post(graphql_url, headers=headers, json=query, verify=False)
        resp.raise_for_status()
        data = resp.json()
        page = data.get("data", {}).get("versions", {})
        for edge in page.get("edges", []):
            versions.append(edge["node"])
        if not page.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = page["pageInfo"]["endCursor"]
    return package, versions

def get_last_downloaded(base_url, repo, lead_file_path, token):
    if not repo or not lead_file_path:
        return ""
    url = f"{base_url.rstrip('/')}/artifactory/api/storage/{repo}/{lead_file_path}?stats"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        if resp.status_code == 404:
            return "Never"
        resp.raise_for_status()
        data = resp.json()
        ts = data.get("lastDownloaded")
        if ts:
            try:
                dt = datetime.fromtimestamp(int(ts) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                return dt
            except Exception:
                return str(ts)
        return "Never"
    except Exception:
        return ""

# 主流程
all_packages = get_all_packages()
log(f"📦 Total {package_type} packages found: {len(all_packages)}")

all_rows = []

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(get_all_versions, pkg): pkg for pkg in all_packages}
    for idx, future in enumerate(concurrent.futures.as_completed(futures), 1):
        pkg, versions = future.result()
        percent = round(idx / len(all_packages) * 100, 1)
        log(f"➡️ ({idx}/{len(all_packages)} | {percent}%) Processed {pkg['name']} with {len(versions)} versions")

        for v in versions:
            base = {
                "Package Type": package_type,
                "Package Name": pkg["name"],
                "Description": pkg.get("description", ""),
                "Package Created": pkg.get("created", ""),
                "Package Modified": pkg.get("modified", ""),
                "Versions Count": pkg.get("versionsCount", 0),
                "Version": v.get("name", ""),
                "Version Created": v.get("created", ""),
                "Version Modified": v.get("modified", ""),
                "Download Count": v.get("stats", {}).get("downloadCount", 0),
                "Last Downloaded": ""
            }
            try:
                size_bytes = int(v.get("size", 0))
                base["Version Size (MB)"] = round(size_bytes / 1024 / 1024, 2)
            except:
                base["Version Size (MB)"] = 0

            matched_repo = False
            for r in v.get("repos", []):
                repo_name = r.get("name", "")
                lead_file_path = r.get("leadFilePath", "")
                if args.repo and args.repo.lower() not in repo_name.lower():
                    continue
                matched_repo = True
                row = base.copy()
                row["Repository Name"] = repo_name
                row["Repo Type"] = r.get("type", "")
                row["Lead File Path"] = lead_file_path
                row["Last Downloaded"] = ""  # placeholder only
                all_rows.append(row)

            if not matched_repo and not args.repo:
                row = base.copy()
                row["Repository Name"] = ""
                row["Repo Type"] = ""
                row["Lead File Path"] = ""
                row["Last Downloaded"] = ""
                all_rows.append(row)

# 获取前 N 个最大版本的 lastDownloaded（如果设置了）
if args.last_download_top > 0:
    print(f"📊 Fetching lastDownloaded info for top {args.last_download_top} largest versions...")
    all_rows.sort(key=lambda x: x.get("Version Size (MB)", 0), reverse=True)
    for row in all_rows[:args.last_download_top]:
        repo = row.get("Repository Name", "")
        path = row.get("Lead File Path", "")
        if repo and path:
            print(f"🕵️ Fetching lastDownloaded for: {repo}/{path}")
            row["Last Downloaded"] = get_last_downloaded(args.url, repo, path, token)

# 导出为 Excel 或 CSV
df = pd.DataFrame(all_rows)
df.sort_values(by="Version Size (MB)", ascending=False, inplace=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"{os.path.splitext(args.output)[0] if args.output else package_type.lower() + '_versions'}_{timestamp}"

if filename.endswith(".csv"):
    df.to_csv(filename, index=False)
else:
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Package Versions", index=False)

print(f"\n✅ Exported {len(df)} version rows from {len(all_packages)} {package_type} packages to {filename}")
