# Docker Image List Tool

A Python script to help identify and manage unused Docker images in Artifactory.

## 📋 Prerequisites

- Python 3.6 or higher
- Required packages: requests, pandas, openpyxl, urllib3

## 🔧 Installation

```bash
pip install -r requirements.txt
```

## 🛠️ Usage

### 1. List Unused Images

```bash
python dockerImageList.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "your-username" \
  --repo "docker-local" \
  --days 30
```

#### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--artifactory-url` | Yes | - | Artifactory URL (must end with /artifactory) |
| `--username` | Yes | - | Artifactory username |
| `--repo` | No | docker-local | Repository name |
| `--days` | No | 30 | Days to look back for downloads |
| `--output` | No | auto-generated | Output Excel file name |

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

Found 3 images:

Image: docker-local/app1/v1.0.0/image.tar
  Tag: v1.0.0
  Size: 256.5 MB
  Created: 2024-01-01T10:00:00.000Z
  Downloads: 0
  Last Downloaded: Never
  SHA256: abc123...

Image: docker-local/app2/v2.0.0/image.tar
  Tag: v2.0.0
  Size: 512.8 MB
  Created: 2024-01-15T15:30:00.000Z
  Downloads: 0
  Last Downloaded: Never
  SHA256: def456...

Summary:
Total images found: 3
Total size: 769.3 MB (0.75 GB)

✅ Report exported to: docker_images_report_20240315_123456.xlsx

Top 10 largest images:
app2/v2.0.0/image.tar: 512.8 MB
app1/v1.0.0/image.tar: 256.5 MB
```

## ⚠️ Error Handling

Common errors and solutions:
- Authentication failed: Check username and password
- Invalid URL: URL must start with http(s):// and end with /artifactory
- Connection error: Check network and Artifactory URL
- Invalid response: Check Artifactory server status 