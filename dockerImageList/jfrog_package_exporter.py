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

# 参数解析
parser = argparse.ArgumentParser(description="Query all packages and versions from JFrog Metadata API and export to Excel.")
parser.add_argument('--url', required=True, help='JFrog base URL, e.g., https://abc.jfrog.io')
parser.add_argument('--token', help='Access token (or input securely)')
parser.add_argument('--output', default=None, help='Excel output file name')
parser.add_argument('--repo', help='Filter results to only include repositories containing this substring')
parser.add_argument('--type', default='DOCKER', help='Package type (e.g., DOCKER, MAVEN, NPM, PYPI)')
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

# 获取所有包
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

# 获取指定包的所有版本
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
            }
            try:
                size_bytes = int(v.get("size", 0))
                base["Version Size (MB)"] = round(size_bytes / 1024 / 1024, 2)
            except:
                base["Version Size (MB)"] = 0

            matched_repo = False
            for r in v.get("repos", []):
                repo_name = r.get("name", "")
                if args.repo and args.repo.lower() not in repo_name.lower():
                    continue
                matched_repo = True
                row = base.copy()
                row["Repository Name"] = repo_name
                row["Repo Type"] = r.get("type", "")
                row["Lead File Path"] = r.get("leadFilePath", "")
                all_rows.append(row)

            if not matched_repo and not args.repo:
                row = base.copy()
                row["Repository Name"] = ""
                row["Repo Type"] = ""
                row["Lead File Path"] = ""
                all_rows.append(row)

# 导出 Excel
df = pd.DataFrame(all_rows)
df.sort_values(by="Version Size (MB)", ascending=False, inplace=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"{os.path.splitext(args.output)[0] if args.output else package_type.lower() + '_versions'}_{timestamp}.xlsx"

with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name="Package Versions", index=False)

print(f"\n✅ Exported {len(df)} version rows from {len(all_packages)} {package_type} packages to {filename}")
