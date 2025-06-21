# Docker Image List Tool

A Python script to help identify and manage unused Docker images in Artifactory.

## 📋 Prerequisites

- Python 3.6 or higher
- Required packages: requests, pandas, openpyxl, urllib3

## 🔧 Installation

```bash
# Create a virtual environment
python3 -m venv ~/my-venv

# Activate it
source ~/my-venv/bin/activate

pip install -r requirements.txt
```

## 🛠️ Usage

### 1. List Unused Images

```bash
python dockerImageList.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "your-username" \
  --repo "docker-local" \
  --days 30 \
  --max-repos 5
```

#### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--artifactory-url` | Yes | - | Artifactory URL (must end with /artifactory) |
| `--username` | Yes | - | Artifactory username |
| `--repo` | No | docker-local | Repository name |
| `--days` | No | 30 | Days to look back for downloads |
| `--output` | No | auto-generated | Output Excel file name |
|--max-repos	| No	|unlimited|	Max number of repositories to scan (only used if --repo is not specified)
## 📊 Output

The script generates:
1. Console output with image details and summary
2. Excel report with:
   - Image metadata (size, dates, creators)
   - Download statistics
   - Checksums (SHA1, MD5, SHA256)

### Example Output

```
Artifactory Configuration:
URL: https://abc.jfrog.io/artifactory
Username: admin
Password: ********

Scanning alpha-docker-qa-local (10/10)
   📄 Found 5 manifest.json files in alpha-docker-qa-local
    🔄 Processing 1/5: alpha-docker-qa-local/docker-app/179
    🔄 Processing 2/5: alpha-docker-qa-local/example-project-app/sha256:14f9d68673b075c2e58f5f4d8761de9f58558df6d3e63135e08f1d99eff72f5b
    🔄 Processing 3/5: alpha-docker-qa-local/example-project-app/sha256:c8fba29372664d4eb18d89b0fbd8a8e8b46eca8e904e04e58a7e7ffa2c149ad2
    🔄 Processing 4/5: alpha-docker-qa-local/reactappimage/89
    🔄 Processing 5/5: alpha-docker-qa-local/reactappimage/90

✅ Report exported to: docker_images_report_20240315_123456.xlsx

```

### Note
If you don't specify the max-repo parameter, all the repositories will be listed.
For 4K images it will take 3 hour to finish.

## ⚠️ Error Handling

Common errors and solutions:
- Authentication failed: Check username and password
- Invalid URL: URL must start with http(s):// and end with /artifactory
- Connection error: Check network and Artifactory URL
- Invalid response: Check Artifactory server status 