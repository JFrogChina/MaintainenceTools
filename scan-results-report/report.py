import requests
import json
import argparse
import sys
import time
import subprocess
import os
from tabulate import tabulate
from termcolor import colored
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed

# Handling HTTP errors
def handle_http_error(response, msg):
    return msg

# Function to check authentication
def check_authentication(base_url, auth):
    url = f"{base_url}/artifactory/api/system"
    response = requests.get(url, auth=auth, timeout=5)
    if response.status_code == 401:
        print("Authentication failed: Please check your username and password.")
        sys.exit(1)  # Exit immediately if authentication fails
    print(f"GUI login successfully.")
    return response.ok

# Obtain repository information
def get_repository_info(base_url, repo_name, auth):
    url = f"{base_url}/artifactory/api/repositories/{repo_name}"
    response = requests.get(url, auth=auth, timeout=5)

    if response.status_code == 400 and repo_name.endswith('-cache'):
        repo_name = repo_name[:-6]  # Remove '-cache' suffix
        url = f"{base_url}/artifactory/api/repositories/{repo_name}"
        response = requests.get(url, auth=auth, timeout=5)

    if not response.ok:
        return None, handle_http_error(response, "Failed to get repository info")

    repo_info = response.json()
    if not repo_info.get('xrayIndex', False):
        return None, "The repository is not in the Xray - Index Resource"

    return repo_info, None

# Function to force reindex
def force_reindex(base_url, auth, repo, path, repo_info):
    if repo_info['rclass'] == 'remote':
        repo = repo.replace('-cache', '')
    reindex_payload = {
        "artifacts": [
            {
                "repository": repo,
                "path": path
            }
        ]
    }
    reindex_response = requests.post(f"{base_url}/xray/api/v1/forceReindex", headers={"Content-Type": "application/json"}, data=json.dumps(reindex_payload), auth=auth)
    if not reindex_response.ok:
        return False, handle_http_error(reindex_response, "Failed to force reindex")
    return True, None

# Function to get artifact scan status
    # https://jfrog.com/help/r/xray-rest-apis/artifact-scan-status
    # Xray Since: 3.80.9
def get_scan_status(base_url, auth, repo, path, max_attempts, interval=5):
    status_payload = {
        "repo": repo,
        "path": path
    }
    for attempt in range(max_attempts):
        if attempt > 0:
            time.sleep(interval)

        status_response = requests.post(f"{base_url}/xray/api/v1/artifact/status", headers={"Content-Type": "application/json"}, data=json.dumps(status_payload), auth=auth)
        if status_response.status_code == 404:
            return None, handle_http_error(status_response, "Required Xray > 3.80.9")
        if status_response.status_code != 404 and not status_response.ok:
            return None, handle_http_error(status_response, "Failed to get scan status")

        status_data = status_response.json()
        if "details" in status_data and "sca" in status_data["details"]:
            sca_status = status_data["details"]["sca"]["status"]
            if sca_status == "DONE":
                return status_data, None

    return None, f"Scan status not done: {sca_status}"

# Function to get artifact summary
    # https://jfrog.com/help/r/xray-rest-apis/artifact-summary
def get_summary(base_url, auth, repo, path):
    summary_payload = {
        "paths": [
            f"default/{repo}/{path}"
        ]
    }
    summary_response = requests.post(f"{base_url}/xray/api/v1/summary/artifact", headers={"Content-Type": "application/json"}, data=json.dumps(summary_payload), auth=auth)
    if not summary_response.ok:
        return None, handle_http_error(summary_response, "Failed to get summary")
    return summary_response.json(), None

# Function to process each line
def get_result_gui(base_url, auth, repositorypath, cve, aim, max_attempts):
    repo, path = repositorypath.split('/', 1)
    aim = aim.lower()

    try:
        repo_info, error = get_repository_info(base_url, repo, auth)
        if error:
            return [repositorypath, cve, aim, "error", error]
        
        reindex_success, error = force_reindex(base_url, auth, repo, path, repo_info)
        if not reindex_success:
            return [repositorypath, cve, aim, "error", error]

        scan_status, error = get_scan_status(base_url, auth, repo, path, max_attempts)
        if error:
            return [repositorypath, cve, aim, "error", error]

        summary_response, error = get_summary(base_url, auth, repo, path)
        if error:
            return [repositorypath, cve, aim, "error", error]

        save_get_summary = "logs/.tmpresult-gui.json"
        os.makedirs(os.path.dirname(save_get_summary), exist_ok=True)
        with open(save_get_summary, 'w') as tmp_file:
            json.dump(summary_response, tmp_file)

        artifacts = summary_response.get("artifacts", [])
        result = "false"
        if artifacts:
            issues = artifacts[0].get("issues", [])
            for issue in issues:
                cve_list = issue.get("cves", [])
                if any(cve_item.get("cve") == cve for cve_item in cve_list):
                    result = "true"
                    break
        else:
            print("No artifacts found in the summary response.")
        return [repositorypath, cve, aim, result, ""]
    except Exception as e:
        print(f"Failed to get summary for {repositorypath}. Error: {e}")
        return [repositorypath, cve, aim, "error", str(e)]

# Function to configure JFrog CLI
def configure_jfrog_cli(server_id, url, user, password):
    try:
        config_cmd = f"JFROG_CLI_AVOID_NEW_VERSION_WARNING=true jf c add {server_id} --url={url} --user={user} --password={password} --interactive=false --overwrite=true"
        subprocess.run(config_cmd, shell=True, check=True)
        print("JFrog CLI configured successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure JFrog CLI: {str(e)}")
        exit(1)
    subprocess.run(f"JFROG_CLI_AVOID_NEW_VERSION_WARNING=true jf c use {server_id}", shell=True, check=True)
    subprocess.run(f"JFROG_CLI_AVOID_NEW_VERSION_WARNING=true jf rt ping", shell=True, check=True)

# Function to download files using JFrog CLI
def download_files_jf(repositorypath, artifacts_dir, base_url, auth, cve, aim):
    repo, path = repositorypath.split('/', 1)
    try:
        os.makedirs(artifacts_dir, exist_ok=True)
        # if file not exist
        repo_info, error = get_repository_info(base_url, repo, auth)
        if error:
            return [repositorypath, cve, aim, "error", error]
        if repo_info['rclass'] == 'remote':
            repo = repo.replace('-cache', '')
        download_cmd = f"jf rt curl -XGET {repo}/{path} -O --output-dir {artifacts_dir}"
        with open(os.devnull, 'wb') as devnull:
            subprocess.run(download_cmd, shell=True, check=True, stdout=devnull, stderr=devnull)
        return os.path.join(artifacts_dir, os.path.basename(path))
    except subprocess.CalledProcessError as e:
        print(f"Download failed for {repo}/{path}: {str(e)}")
        return None

# Function to scan files using JFrog CLI
def get_result_cli(repositorypath, artifacts_dir, cve):
    file = os.path.basename(repositorypath)
    filepath = os.path.join(artifacts_dir, file)
    
    try:
        scan_cmd = f"jf scan {filepath} --format=json"
        scan_output = subprocess.run(scan_cmd, shell=True, check=True, capture_output=True, text=True)
        scan_results = json.loads(scan_output.stdout)
        
        if not isinstance(scan_results, list) or not scan_results:
            raise ValueError("Unable to filter results")
        
        vulnerabilities = scan_results[0].get("vulnerabilities", [])
        cli_result = "false"
        if not vulnerabilities:
            return cli_result, None
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict):
                cli_result = "false"
                continue
            
            cve_list = vulnerability.get("cves", [])
            if any(cve_item.get("cve") == cve for cve_item in cve_list):
                cli_result = "true"
                break
            else:
                cli_result = "false"
        
        return cli_result, None
    
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.strip()
        if "[Error] path does not exist" in stderr_output:
            error_message = "File not exist"
        elif "failed to index file" in stderr_output:
            error_message = "Failed to index"
        else:
            error_message = f"Failed with {e.stderr.strip()}"
        return "error", str(error_message)
    
    except json.JSONDecodeError as e:
        return "error", f"JSON decode error: {str(e)}"
    except Exception as e:
        return "error", str(e)

# Function to process each line in parallel
def process_line(line, base_url, auth, artifacts_dir, max_attempts):
    repositorypath, cve, aim = line.strip().split()
    
    download_result = download_files_jf(repositorypath, artifacts_dir, base_url, auth, cve, aim)
    log_entry = get_result_gui(base_url, auth, repositorypath, cve, aim, max_attempts)
    
    if download_result:
        cli_result, cli_error = get_result_cli(repositorypath, artifacts_dir, cve)
        if cli_error:
            log_entry.extend(["error", cli_error])
        else:
            log_entry.extend([cli_result, ""])
    else:
        log_entry.extend(["error", "Failed to download file"])

    return log_entry

# Main function
def main():
    default_base_url = "http://127.0.0.1:8082"
    default_username = "admin"
    default_password = "password"
    default_log_file = "scan_result.log"
    default_retry = 2
    default_save_artifacts_folder = "artifacts/"

    parser = argparse.ArgumentParser(description="Artifact scan")
    parser.add_argument('repositorypath', type=str, nargs='?', default='', help='The Repository Path of the Artifact')
    parser.add_argument('cve', type=str, nargs='?', default='', help='CVE with the Artifact')
    parser.add_argument('aim', type=str, nargs='?', default='', help='true or false')
    parser.add_argument('--base_url', type=str, default=default_base_url, help=f'The base URL for the Artifactory instance (default: {default_base_url})')
    parser.add_argument('--username', type=str, default=default_username, help='Artifactory username')
    parser.add_argument('--password', type=str, default=default_password, help='Artifactory password')
    parser.add_argument('--log', type=str, default=default_log_file, help='Save the result to log')
    parser.add_argument('-f', '--file', type=str, help='File containing parameters for the scan')
    parser.add_argument('--retry', default=default_retry, type=int, help='Retry time of get scan status')
    parser.add_argument('--folder', default=default_save_artifacts_folder, help='Save downloaded artifacts by JFrog CLI')

    args = parser.parse_args()

    base_url = args.base_url
    username = args.username
    password = args.password
    log_file = args.log
    max_attempts = args.retry
    params_file = args.file
    artifacts_dir = args.folder

    auth = HTTPBasicAuth(username, password)

    # Validate username and password
    try:
        check_authentication(base_url, auth)
    except Exception as e:
        print(f"Authentication failed: {e}")
        exit(1)
    configure_jfrog_cli('abc', base_url, username, password)

    if params_file:
        with open(params_file, 'r') as file:
            lines = file.readlines()
    elif len(sys.argv) in [3, 4]:
        args.aim = 'true'
        lines = [f"{args.repositorypath} {args.cve} {args.aim}"]
    else:
        print("Usage: python report.py <repository_path>/<artifact_path> <CVE> <intention> or provide a file with -f <file>")
        sys.exit(1)

    # Process lines in parallel
    logs = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_line, line, base_url, auth, artifacts_dir, max_attempts) for line in lines]
        for future in as_completed(futures):
            logs.append(future.result())

    headers = ["Repository Path", "CVEs", "Intention", "GUI", "GUI - Error", "CLI", "CLI - Error"]
    table = []

    for log in logs:
        path, cve, intention, gui_result, gui_error, cli_result, cli_error = log
        if str(intention).lower() == gui_result and str(intention).lower() == cli_result:
            intention = colored(intention, 'green')
        else:
            intention = colored(intention, 'red')
        table.append([path, cve, intention, gui_result, gui_error, cli_result, cli_error])

    colalign = ("left", "center", "center", "center", "left", "center", "left")
    print(tabulate(table, headers, tablefmt="grid", colalign=colalign))

    with open(log_file, "w") as log_file:
        log_file.write(tabulate(table, headers, tablefmt="grid", colalign=colalign))

if __name__ == "__main__":
    main()