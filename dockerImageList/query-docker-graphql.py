import requests
import json
import argparse
import getpass
import pandas as pd
from datetime import datetime
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 参数
parser = argparse.ArgumentParser(description="Query Docker packages from JFrog Metadata API and export to CSV.")
parser.add_argument('--url', required=True, help='JFrog base URL, e.g., https://soleng.jfrog.io')
parser.add_argument('--token', help='Access token (or input securely)')
parser.add_argument('--output', default=None, help='CSV output file name')
parser.add_argument('--debug', action='store_true', help='Enable debug logs')
args = parser.parse_args()

# 获取 Token
token = args.token or getpass.getpass('Enter JFrog access token: ')
graphql_url = f"{args.url.rstrip('/')}/metadata/api/v1/query"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

# 构造分页查询
def build_query(after_cursor=None):
    return {
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
                name
                description
                created
                modified
                versionsCount
                versions {
                  name
                  size
                  created
                  modified
                  stats {
                    downloadCount
                  }
                  repos {
                    name
                    type
                    leadFilePath
                  }
                }
              }
            }
          }
        }
        """,
        "variables": {
            "first": 100,
            "after": after_cursor
        }
    }

# 查询循环
results = []
cursor = None
total_packages = 0

while True:
    query = build_query(after_cursor=cursor)
    if args.debug:
        print(f"📡 Querying after cursor: {cursor}")
        print(json.dumps(query, indent=2))

    try:
        response = requests.post(graphql_url, headers=headers, json=query, verify=False)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        try:
            print(f"📄 Raw response:\n{response.text}")
        except:
            pass
        break

    page = data.get("data", {}).get("packages", {})
    edges = page.get("edges", [])
    page_info = page.get("pageInfo", {})
    has_next = page_info.get("hasNextPage", False)
    cursor = page_info.get("endCursor")

    if args.debug:
        print(f"📦 Page fetched: {len(edges)} packages")

    for edge in edges:
        node = edge["node"]
        versions = node.get("versions", [])
        for v in versions:
            base = {
                "Package Name": node["name"],
                "Description": node.get("description", ""),
                "Package Created": node.get("created", ""),
                "Package Modified": node.get("modified", ""),
                "Versions Count": node.get("versionsCount", 0),
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
                    row = base.copy()
                    row["Repository Name"] = r.get("name", "")
                    row["Repo Type"] = r.get("type", "")
                    row["Lead File Path"] = r.get("leadFilePath", "")
                    results.append(row)
            else:
                row = base.copy()
                row["Repository Name"] = ""
                row["Repo Type"] = ""
                row["Lead File Path"] = ""
                results.append(row)

        total_packages += 1

    if not has_next:
        break

# 写入 CSV，按 Version Size (MB) 倒序
df = pd.DataFrame(results)
df.sort_values(by="Version Size (MB)", ascending=False, inplace=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"{os.path.splitext(args.output)[0] if args.output else 'docker_packages'}_{timestamp}.csv"
df.to_csv(filename, index=False)
print(f"\n✅ Exported {len(df)} rows from {total_packages} Docker packages to {filename}")
