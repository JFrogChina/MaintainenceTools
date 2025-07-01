import argparse
import csv
import json
import logging
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.auth import HTTPBasicAuth
from tabulate import tabulate
from tqdm import tqdm
from wcwidth import wcswidth

# Global variable to store current auth for error reporting
CURRENT_AUTH = None


def setup_logger(log_path: str, clear_log: bool) -> logging.Logger:
    """
    Configure and return a logger that writes scan results to a file.
    """
    logger = logging.getLogger("scan_logger")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        mode = 'w' if clear_log else 'a'
        fh = logging.FileHandler(log_path, mode=mode)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger


def handle_http_error(response: requests.Response, message: str):
    """
    Print a descriptive HTTP error, include credentials on 401, and exit.
    """
    status = response.status_code
    text = response.text
    if status == 401:
        if CURRENT_AUTH and hasattr(CURRENT_AUTH, 'username') and hasattr(CURRENT_AUTH, 'password'):
            sys.stderr.write(f"Authentication failed: user={CURRENT_AUTH.username}, password={CURRENT_AUTH.password}\n")
        else:
            sys.stderr.write("Authentication failed: check username/password.\n")
    else:
        sys.stderr.write(f"HTTP Error: {message}. Status: {status}, Response: {text}\n")
    sys.exit(1)


def get_repository_info(session: requests.Session, base_url: str, repo_name: str) -> dict:
    """
    Fetch repository metadata from Artifactory and validate Xray indexing.
    Handles network errors gracefully.
    """
    url = f"{base_url}/artifactory/api/repositories/{repo_name}"
    try:
        resp = session.get(url, timeout=5)
    except requests.RequestException as e:
        sys.stderr.write(f"Network error when retrieving repository info: {e}\n")
        sys.exit(1)
    if resp.status_code == 401:
        handle_http_error(resp, "Unauthorized access when retrieving repository info")
    if not resp.ok:
        handle_http_error(resp, "Failed to retrieve repository info")
    try:
        repo_info = resp.json()
    except ValueError as e:
        sys.stderr.write(f"Failed to parse repository info JSON: {e}\n")
        sys.exit(1)
    if not repo_info.get('xrayIndex', False):
        sys.stderr.write("The repository is not in the Xray Index Resource.\n")
        sys.exit(1)
    return repo_info


def get_file_list(session: requests.Session, base_url: str, repo_name: str, package_type: str) -> list:
    """
    Retrieve and filter the storage listing for files in the repository.
    Handles network errors gracefully.
    """
    url = f"{base_url}/artifactory/api/storage/{repo_name}?list&deep=1&listFolders=0&mdTimestamps=1"
    try:
        resp = session.get(url, timeout=60)
    except requests.RequestException as e:
        sys.stderr.write(f"Network error when retrieving file list: {e}\n")
        sys.exit(1)
    if resp.status_code == 401:
        handle_http_error(resp, "Unauthorized access when retrieving file list")
    if not resp.ok:
        handle_http_error(resp, "Failed to get file list")
    try:
        data = resp.json()
    except ValueError as e:
        sys.stderr.write(f"Failed to parse file list JSON: {e}\n")
        sys.exit(1)
    files = data.get('files', [])
    if not files:
        sys.stderr.write("No index files found in the repository.\n")
        sys.exit(1)
    files = filter_files_by_package_type(files, package_type)
    if not files:
        sys.stderr.write("No index files left after filtering.\n")
        sys.exit(1)
    return files


def filter_files_by_package_type(files: list, package_type: str) -> list:
    """
    Keep only files matching the configured rules for the given package type.
    """
    rules = {
        'cargo': lambda f: (not f['uri'].startswith('/.cargo/')) and (f['uri'].endswith('.crate') or f['uri'].endswith('.tgz') or f['uri'].endswith('.tar.gz')),
        'composer': lambda f: not f['uri'].startswith('/.composer/'),
        'conan': lambda f: (not f['uri'].startswith('/.conan/')) and f['uri'].endswith('conanmanifest.txt'),
        'conda': lambda f: f['uri'].endswith('.conda') or f['uri'].endswith('.tar.bz2'),
        'debian': lambda f: (not f['uri'].startswith('/dists/')) and f['uri'].endswith('.deb'),
        'docker': lambda f: (not f['uri'].startswith('/.jfrog/repository.catalog')) and (not f['uri'].endswith('list.manifest.json')) and f['uri'].endswith('manifest.json'),
        'go': lambda f: f['uri'].endswith('.zip'),
        'gradle': lambda f: (not f['uri'].endswith('.module')) and (not f['uri'].endswith('.pom')) and (not f['uri'].endswith('.xml')),
        'maven': lambda f: (not f['uri'].endswith('.pom')) and (not f['uri'].endswith('.xml')),
        'npm': lambda f: not f['uri'].startswith('/.npm/'),
        'nuget': lambda f: ((not f['uri'].startswith('/.nuGetV3/')) and (not f['uri'].startswith('/.nuget/')) and (f['uri'].endswith('.nupkg') or f['uri'].endswith('.dll') or f['uri'].endswith('.exe'))),
        'pypi': lambda f: not f['uri'].startswith('/.pypi/'),
        'rpm': lambda f: f['uri'].endswith('.rpm'),
        'terraformbackend': lambda f: f['uri'].endswith('state.latest.json'),
        'huggingfaceml': lambda f: f['uri'].endswith('.jfrog_huggingface_model_info.json'),
    }
    if package_type not in rules:
        sys.stderr.write(f"Warning: No filter rules specified for '{package_type}'. All files will be included.\n")
        return files
    return [f for f in files if rules[package_type](f)]


def annotate_support(files: list, support_rules: dict) -> list:
    """
    Annotate each file with a boolean 'support' flag determined by support_rules.
    """
    extensions_map = {}
    for rule in support_rules.get('supported_package_types', []):
        for ext in rule.get('extensions', []):
            extensions_map[ext['extension']] = True
    for f in files:
        f['support'] = any(f['uri'].endswith(ext) for ext in extensions_map)
    return files


def get_scan_status(session: requests.Session, base_url: str, repo_name: str, package_type: str, f: dict, auth: HTTPBasicAuth, rclass: str, max_retries: int = 3) -> dict:
    """
    Try up to max_retries to retrieve scan status from Xray for a given file.
    If repository class is 'remote', append '-cache' to repo_name.
    """
    effective_repo = repo_name + '-cache' if rclass == 'remote' else repo_name
    url = f"{base_url}/xray/api/v1/scan/status/artifact"
    data = {
        'repository_pkg_type': package_type,
        'path': f"{effective_repo}{f['uri']}",
        'sha256': f.get('sha2')
    }
    attempt = 0
    while attempt < max_retries:
        try:
            resp = session.post(url, json=data, auth=auth, timeout=5)
        except requests.RequestException as e:
            logging.getLogger('scan_logger').error(f"Network error scanning {f['uri']}: {e}")
            return {'uri': f['uri'], 'status': 'ERROR'}
        if resp.status_code == 401:
            handle_http_error(resp, "Unauthorized access when retrieving scan status")
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            logging.getLogger('scan_logger').error(f"HTTP error scanning {f['uri']}: {e}")
            return {'uri': f['uri'], 'status': 'ERROR'}
        try:
            status_json = resp.json()
        except ValueError as e:
            logging.getLogger('scan_logger').error(f"Failed to parse scan status JSON for {f['uri']}: {e}")
            return {'uri': f['uri'], 'status': 'ERROR'}
        return {'uri': f['uri'], 'status': status_json.get('status', 'N/A')}
    logging.getLogger('scan_logger').error(f"Failed to get scan status for {f['uri']} after {max_retries} attempts.")
    return {'uri': f['uri'], 'status': 'ERROR'}


def force_reindex(session: requests.Session, base_url: str, repo_name: str, f: dict, auth: HTTPBasicAuth, rclass: str) -> bool:
    """
    Force reindex a single artifact via Xray's API.
    If repository class is 'remote', append '-cache' to repo_name.
    """
    effective_repo = repo_name + '-cache' if rclass == 'remote' else repo_name
    url = f"{base_url}/xray/api/v1/forceReindex"
    payload = {
        'artifacts': [
            {
                'repository': effective_repo,
                'path': f['uri']
            }
        ]
    }
    try:
        resp = session.post(url, json=payload, auth=auth, timeout=10)
    except requests.RequestException as e:
        logging.getLogger('scan_logger').error(f"Network error forcing reindex {f['uri']}: {e}")
        return False
    if resp.status_code == 401:
        handle_http_error(resp, "Unauthorized access when forcing reindex")
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        logging.getLogger('scan_logger').error(f"HTTP error forcing reindex {f['uri']}: {e}")
        return False
    return True


def process_files(session: requests.Session, base_url: str, repo_name: str, package_type: str, files: list,
                  auth: HTTPBasicAuth, rclass: str, threads: int, forcereindex: bool) -> list:
    """
    Concurrently scan supported files, optionally force reindex, and collect results for all files.
    Returns a list of all files with updated 'status'.
    """
    supported_files = [f for f in files if f.get('support')]
    total = len(supported_files)

    progress = tqdm(total=total, desc="Scanning/Indexing")
    status_map = {}

    def handle_file(f):
        if forcereindex:
            force_reindex(session, base_url, repo_name, f, auth, rclass)
        return get_scan_status(session, base_url, repo_name, package_type, f, auth, rclass)

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(handle_file, f): f for f in supported_files}
        for future in as_completed(futures):
            res = future.result()
            status_map[res['uri']] = res['status']
            progress.update(1)
    progress.close()

    all_results = []
    for f in files:
        if f.get('support'):
            f['status'] = status_map.get(f['uri'], 'N/A')
        else:
            f['status'] = 'not scanned'
        all_results.append(f)
    return all_results


def save_results(scan_results: list, repo_name: str, start: float, end: float,
                 logger: logging.Logger, print_lines: int, out_format: str, output_path: str) -> None:
    """
    Log summary, print table, and write to file in requested format.
    """
    table_rows = [[f['uri'], f.get('support', False), f.get('status', 'N/A')] for f in scan_results]
    col_widths = [max(wcswidth(str(row[i])) for row in table_rows) for i in range(len(table_rows[0]))]
    formatted = [[str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)] for row in table_rows]
    formatted.sort(key=lambda r: (r[2], r[1] != 'True', r[0]))

    counts = Counter(f['status'] for f in scan_results)
    elapsed = end - start
    logger.info(f"[{repo_name}] Potential files: {len(scan_results)}, Status Counts: {counts}")
    print(f"[Repo ] [{repo_name}] Potential files: {len(scan_results)}, Status Counts: {counts}")
    logger.info(f"[Sum  ] Total time: {elapsed:.2f} sec")
    print(f"[Sum  ] Total time: {elapsed:.2f} sec")

    if len(formatted) > print_lines:
        print(tabulate(formatted[:print_lines], headers=["File Path", "Support", "Status"], tablefmt="grid"))
        print(f"\n[Warn ] ... additional rows logged in {output_path}\n")
    else:
        print(tabulate(formatted, headers=["File Path", "Support", "Status"], tablefmt="grid"))

    if out_format == 'csv':
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["File Path", "Support", "Status"]) 
            for row in formatted:
                writer.writerow(row)
    elif out_format == 'json':
        with open(output_path, 'w') as jf:
            json.dump([{  
                'uri': f['uri'],
                'support': f.get('support', False),
                'status': f.get('status', 'N/A')
            } for f in scan_results], jf, indent=4)  
    elif out_format == 'table':
        logger.info(tabulate(formatted, headers=["File Path", "Support", "Status"], tablefmt="grid"))
    else:
        sys.stderr.write("[Warn ] Unknown format. Defaulting to table.\n")
        logger.info(tabulate(formatted, headers=["File Path", "Support", "Status"], tablefmt="grid"))

def main():
    parser = argparse.ArgumentParser(description="Scan Artifactory repository via Xray index/status and optionally force reindex.")
    parser.add_argument('reponame', help='Name of the repository')
    parser.add_argument('--base_url', default='http://localhost:8082', help='Base URL for Artifactory and Xray')
    parser.add_argument('--pkg_support', default='Xray_pkg_support.json', help='JSON file defining supported package types')
    parser.add_argument('--username', default='admin', help='Artifactory username')
    parser.add_argument('--password', default='password', help='Artifactory password')
    parser.add_argument('--scan_result_save', default='scan_details.file', help='Path to save scan results')
    parser.add_argument('--print_lines', type=int, default=10, help='Number of rows to print in console')
    parser.add_argument('--format', default='table', choices=['table', 'csv', 'json'], help='Output format')
    parser.add_argument('--clear_log', action='store_true', default=True, help='Clear previous log file (default: overwrite)')
    parser.add_argument('--threads', type=int, default=50, help='Threads for concurrent API calls')
    parser.add_argument('--forcereindex', action='store_true', help='Force reindex each artifact before scanning')
    args = parser.parse_args()

    global CURRENT_AUTH
    CURRENT_AUTH = HTTPBasicAuth(args.username, args.password)
    auth = CURRENT_AUTH

    session = requests.Session()
    session.auth = auth

    logger = setup_logger(args.scan_result_save, args.clear_log)

    try:
        with open(args.pkg_support, 'r') as sf:
            pkg_support_rules = json.load(sf)
    except (IOError, json.JSONDecodeError) as e:
        sys.stderr.write(f"Failed to load package support file: {e}\n")
        sys.exit(1)

    repo_info = get_repository_info(session, args.base_url, args.reponame)
    pkg_type = repo_info.get('packageType')
    rclass = repo_info.get('rclass')
    files = get_file_list(session, args.base_url, args.reponame, pkg_type)
    files = annotate_support(files, pkg_support_rules)

    start_time = time.time()
    results = process_files(session, args.base_url, args.reponame,
                             pkg_type, files, auth, rclass, args.threads, args.forcereindex)
    end_time = time.time()

    save_results(results, args.reponame, start_time, end_time,
                 logger, args.print_lines, args.format, args.scan_result_save)


if __name__ == '__main__':
    main()