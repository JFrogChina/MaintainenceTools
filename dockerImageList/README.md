# 📦 JFrog Package Version Export Tool

This Python script queries **all packages and their versions** of a specified type (e.g., DOCKER, MAVEN, NPM, PYPI) from the JFrog Metadata GraphQL API and exports them into an Excel file.

---

## 🗂️ Script Workflow (ASCII Flow Diagram)

```
+-------------------------+
|  Start: Parse Arguments |
+-----------+-------------+
            |
            v
+-------------------------------+
| Authenticate with JFrog Token |
+-----------+-------------------+
            |
            v
+-----------------------------+
| Fetch All Packages (GraphQL) |
+-----------+-----------------+
            |
            v
+------------------------------------------+
| For Each Package: Fetch All Versions      |
|                (GraphQL)                 |
+-----------+------------------------------+
            |
            v
+------------------------------------------+
| For Each Version: For Each Repo           |
+-----------+------------------------------+
            |
            v
+--------------------------+
| Get Lead File Path       |
+-----------+--------------+
            |
            v
+---------------------------------------------+
| Query Artifactory REST API for lastDownloaded|
+-----------+---------------------------------+
            |
            v
+--------------------------+
| Collect Version Info     |
+-----------+--------------+
            |
            v
+--------------------------+
| More Versions?           |
+-----+--------------------+
      |Yes                     No
      v                        |
  (loop back)                  v
+--------------------------+
| More Packages?           |
+-----+--------------------+
      |Yes                     No
      v                        |
  (loop back)                  v
+--------------------------+
| Export All Data to Excel |
+-----------+--------------+
            |
            v
+--------------------------+
|           End            |
+--------------------------+
```

---

## 🔧 Installation


```bash

# Create a virtual environment
python3 -m venv ~/my-venv

# Activate the environment
source ~/my-venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

---


### Optional arguments:

| Argument      | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `--token`     | Access token (if not provided, you will be prompted to enter it securely)  |
| `--output`    | Excel output file name (default: `{type}_versions_TIMESTAMP.xlsx`)          |
| `--type`      | Package type: `DOCKER`, `MAVEN`, `NPM`, `PYPI` (default: DOCKER)            |
| `--debug`     | Enable debug logs                                                           |

---

## 🚀 Usage Example

```bash
python3 jfrog_package_exporter.py \
  --url https://abc.jfrog.io --token $ACCESS_TOKEN \
  --output docker_repos.csv --debug --type docker --last-download-top 20
```

### Optional arguments:

| Argument             | Description                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `--token`            | Access token (if not provided, you will be prompted to enter it securely)    |
| `--output`           | Excel or CSV output file name (default: `{type}_versions_TIMESTAMP.xlsx`)    |
| `--type`             | Package type: `DOCKER`, `MAVEN`, `NPM`, `PYPI` (default: DOCKER)            |
| `--last-download-top`| Only fetch `lastDownloaded` for the top N largest versions (default: 0 = off)|
| `--debug`            | Enable debug logs                                                           |

---

## 🧪 Example

```bash
python3 jfrog_package_exporter.py \
  --url https://abc.jfrog.io --token access_token \
  --output docker_repos.csv --debug --type maven
```

---

## 📂 Output

The generated Excel file will contain a sheet named **`Package Versions`**, with the following columns:

- Package Type
- Package Name
- Description
- Package Created / Modified
- Version
- Version Created / Modified
- Version Size (MB)
- Download Count
- Repository Name / Type
- Lead File Path

---

## 🔐 Authentication

Use a [JFrog Access Token](https://jfrog.com/help/r/jfrog-platform-administration-documentation/access-tokens) with permission to query metadata.

---

## 🛠 Maintainer

- Developed by: JFrog China Solution Engineering Team
- License: MIT

## ⚠️ Notes on Rate Limiting and Server Load

When querying the 'Last Downloaded' field for each version via the Artifactory REST API, you may encounter rate limiting or server rejections if too many requests are made in a short period.

- **To avoid rate limiting**, you can uncomment the line `time.sleep(0.05)` in the script to add a short delay between requests:
  ```python
  # time.sleep(0.05)  # Prevent sending requests too quickly and being rate-limited by the server
  ```
- **Reduce the number of workers**: Lower the value of `max_workers` in the ThreadPoolExecutor (e.g., from 4 to 2) to decrease concurrent requests and reduce the chance of server-side rejections.

Adjust these parameters according to your Artifactory server's capacity and your organization's API usage policy.
