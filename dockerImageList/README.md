
# 📦 JFrog Package Version Export Tool

This Python script queries **all packages and their versions** of a specified type (e.g., DOCKER, MAVEN, NPM, PYPI) from the JFrog Metadata GraphQL API and exports them into an Excel file.

---

## 🔧 Installation


Create a `requirements.txt` file with:

```txt
requests
pandas
openpyxl
```

```bash

# Create a virtual environment
python3 -m venv ~/my-venv

# Activate the environment
source ~/my-venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```



---

## 🚀 Usage

```bash
python3 jfrog_package_exporter.py \
  --url https://abc.jfrog.io --token access_token \
  --output docker_repos.csv --debug --type docker
```

### Optional arguments:

| Argument      | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `--token`     | Access token (if not provided, you will be prompted to enter it securely)  |
| `--output`    | Excel output file name (default: `{type}_versions_TIMESTAMP.xlsx`)          |
| `--type`      | Package type: `DOCKER`, `MAVEN`, `NPM`, `PYPI` (default: DOCKER)            |
| `--debug`     | Enable debug logs                                                           |

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
