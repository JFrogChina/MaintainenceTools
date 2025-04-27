# 查看仓库是否设置JAS扫描
import requests
import json
from requests.auth import HTTPBasicAuth

# JFrog Xray API URL
XRAy_API_URL = "https://demo.jfrogchina.com/xray/api/v1"
USERNAME = "xxxx"  # JFrog  用户名
PASSWORD = "xxxx"  # JFrog \ 密码（或使用 API 密钥代替）

# HTTP 请求头
HEADERS = {
    "Content-Type": "application/json"
}

# 1. 获取仓库索引配置
def get_indexing_configuration():
    url = f"{XRAy_API_URL}/binMgr/default/repos"
    response = requests.get(url, headers=HEADERS, auth=HTTPBasicAuth(USERNAME, PASSWORD))

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching indexing configuration: {response.status_code}")
        return None

# 2. 获取仓库配置（包括漏洞上下文分析等）
def get_repository_configuration(repo_name):
    url = f"{XRAy_API_URL}/repos_config/{repo_name}"
    params = {"repo_name": repo_name}
    response = requests.get(url, headers=HEADERS, params=params, auth=HTTPBasicAuth(USERNAME, PASSWORD))

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching repository configuration for {repo_name}: {response.status_code}")
        return None

# 3. 过滤仓库并获取所需配置
#def get_filtered_repo_configurations(type_filter, pkg_type_filter):
def get_filtered_repo_configurations(type_filters, pkg_type_filters):

    indexing_data = get_indexing_configuration()

    if not indexing_data:
        return []

    # 根据 type 和 pkg_type 过滤仓库
    indexed_repos = indexing_data.get("indexed_repos", [])
    filtered_repos = [
        repo for repo in indexed_repos
        #if repo["type"] == type_filter and repo["pkg_type"] == pkg_type_filter
        if repo["type"] in type_filters and repo["pkg_type"] in pkg_type_filters

    ]

    # 获取每个仓库的配置
    repo_configurations = []

    for repo in filtered_repos:
        repo_name = repo["name"]
        repo_config_data = get_repository_configuration(repo_name)

        if repo_config_data:
            repo_configurations.append({
                "repo_name": repo_name,
                "retention_in_days": repo_config_data.get("repo_config", {}).get("retention_in_days"),
                # 确保 vuln_contextual_analysis 是布尔值
                "vuln_contextual_analysis": bool(repo_config_data.get("repo_config", {}).get("vuln_contextual_analysis", False)),
                "exposures": repo_config_data.get("repo_config", {}).get("exposures")
            })

    return repo_configurations

# 4. 主程序
def main():
    # 设置过滤条件 local | remote
    #type_filter = "local"  # 过滤仓库类型，可以根据需求修改
    type_filters = ["local", "remote"]
    # Contextual Analysis - Supported Repositories: Docker | Maven | Gradle | npm
    #   https://jfrog.com/help/r/jfrog-security-documentation/vulnerability-contextual-analysis 
    # Exposures - Supports following package types: Docker | OCI | Maven | npm | Pypi
    #   https://jfrog.com/help/r/jfrog-security-documentation/exposures-scans
    #pkg_type_filter = "Pypi"  # 过滤包类型，可以根据需求修改
    pkg_type_filters = ["Docker", "Maven", "Gradle", "npm", "OCI", "Pypi"]

    # 获取符合条件的仓库配置
    #repo_configs = get_filtered_repo_configurations(type_filter, pkg_type_filter)
    repo_configs = get_filtered_repo_configurations(type_filters, pkg_type_filters)

    # 按字母排序 repo_name
    if repo_configs:
        repo_configs_sorted = sorted(repo_configs, key=lambda x: x["repo_name"])

        # 输出表头
        print(f"{'repo_name':<48} {'retention'} {'vuln_contextual_analysis'} {'exposures':<25}")  # 格式化表头对齐

        for config in repo_configs_sorted:
            repo_name = config["repo_name"]
            retention_in_days = config["retention_in_days"]
            vuln_contextual_analysis = config["vuln_contextual_analysis"]
            exposures = config["exposures"]

            # 使用格式化输出确保每列对齐
            print(f"{repo_name:<48} {retention_in_days:<9} {vuln_contextual_analysis!s:<24} {exposures}")  # 左对齐并限制列宽

    else:
        print("No repositories found with the given filters.")

if __name__ == "__main__":
    main()
