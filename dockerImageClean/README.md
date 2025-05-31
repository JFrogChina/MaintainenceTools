# Docker Image Cleanup Tool

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
python dockerImageClean.py \
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

### 2. Delete Images by Keyword

```bash
# Preview what would be deleted (dry run mode)
python dockerImageDelete.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "your-username" \
  --repo "docker-local" \
  --keyword "test" \
  --dry-run

# Preview with detailed information
python dockerImageDelete.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "your-username" \
  --repo "docker-local" \
  --keyword "test" \
  --dry-run \
  --verbose

# Actually delete images
python dockerImageDelete.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "your-username" \
  --repo "docker-local" \
  --keyword "test"
```

#### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--artifactory-url` | Yes | - | Artifactory URL (must end with /artifactory) |
| `--username` | Yes | - | Artifactory username |
| `--repo` | No | docker-local | Repository name |
| `--keyword` | Yes | - | Keyword to match in image path or name |
| `--dry-run` | No | False | Enable dry run mode (no actual deletion) |
| `--verbose` | No | False | Show detailed information in dry run mode |

## 📊 Output

### List Images Output

The script generates:
1. Console output with image details and summary
2. Excel report with:
   - Image metadata (size, dates, creators)
   - Download statistics
   - Checksums (SHA1, MD5, SHA256)

#### Example Output

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

### Delete Images Output

The script shows:
1. Configuration information
2. List of images matching the keyword
3. Total size of matching images
4. Confirmation prompt (unless in dry-run mode)
5. Deletion progress and results

#### Example Output (Normal Mode)

```
Artifactory Configuration:
URL: https://abc.jfrog.io/artifactory
Username: admin
Password: ********
Repository: docker-local
Keyword: test
Mode: Delete

Searching for images matching keyword 'test'...

Found 2 images matching keyword 'test':

Image: docker-local/test-app/v1.0.0/image.tar
  Size: 256.5 MB

Image: docker-local/test-app/v2.0.0/image.tar
  Size: 512.8 MB

Total size: 769.3 MB (0.75 GB)

⚠️  Are you sure you want to delete these 2 images? (yes/no): yes

Deleting images...
✅ Deleted: docker-local/test-app/v1.0.0/image.tar
✅ Deleted: docker-local/test-app/v2.0.0/image.tar

Summary:
Total images found: 2
Successfully deleted: 2
Failed to delete: 0
Total size: 769.3 MB (0.75 GB)
```

#### Example Output (Dry Run with Verbose Mode)

```
Artifactory Configuration:
URL: https://abc.jfrog.io/artifactory
Username: admin
Password: ********
Repository: docker-local
Keyword: test
Mode: Dry Run
Verbose mode: Enabled

Searching for images matching keyword 'test'...

Found 2 images matching keyword 'test':

Image: docker-local/test-app/v1.0.0/image.tar
  Size: 256.5 MB
  Created: 2024-01-01T10:00:00.000Z
  Modified: 2024-01-15T15:30:00.000Z
  Created by: admin
  Modified by: admin
  Delete URL: https://abc.jfrog.io/artifactory/docker-local/test-app/v1.0.0/image.tar

Image: docker-local/test-app/v2.0.0/image.tar
  Size: 512.8 MB
  Created: 2024-01-15T15:30:00.000Z
  Modified: 2024-01-15T15:30:00.000Z
  Created by: admin
  Modified by: admin
  Delete URL: https://abc.jfrog.io/artifactory/docker-local/test-app/v2.0.0/image.tar

Total size: 769.3 MB (0.75 GB)

Would delete: docker-local/test-app/v1.0.0/image.tar
  URL: https://abc.jfrog.io/artifactory/docker-local/test-app/v1.0.0/image.tar
  Size: 256.5 MB

Would delete: docker-local/test-app/v2.0.0/image.tar
  URL: https://abc.jfrog.io/artifactory/docker-local/test-app/v2.0.0/image.tar
  Size: 512.8 MB

Summary:
Total images found: 2
Successfully deleted: 2
Failed to delete: 0
Total size: 769.3 MB (0.75 GB)

⚠️  This was a dry run. No images were actually deleted.

Detailed information:
Repository: docker-local
Keyword: test
Total images: 2
Total size: 769.3 MB (0.75 GB)
Average size: 384.65 MB per image
```

## ⚠️ Error Handling

Common errors and solutions:
- Authentication failed: Check username and password
- Invalid URL: URL must start with http(s):// and end with /artifactory
- Connection error: Check network and Artifactory URL
- Invalid response: Check Artifactory server status

## 🔍 Delete Images Documentation

### Overview

The `dockerImageDelete.py` script helps you safely delete Docker images from Artifactory based on keywords. It includes a dry run mode to preview changes before actual deletion.

### Usage

1. **Preview Changes (Dry Run)**
   ```bash
   python dockerImageDelete.py \
     --artifactory-url "https://abc.jfrog.io/artifactory" \
     --username "your-username" \
     --repo "docker-local" \
     --keyword "test" \
     --dry-run
   ```

2. **Preview with Details**
   ```bash
   python dockerImageDelete.py \
     --artifactory-url "https://abc.jfrog.io/artifactory" \
     --username "your-username" \
     --repo "docker-local" \
     --keyword "test" \
     --dry-run \
     --verbose
   ```

3. **Delete Images**
   ```bash
   python dockerImageDelete.py \
     --artifactory-url "https://abc.jfrog.io/artifactory" \
     --username "your-username" \
     --repo "docker-local" \
     --keyword "test"
   ```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--artifactory-url` | Yes | - | Artifactory URL (must end with /artifactory) |
| `--username` | Yes | - | Artifactory username |
| `--repo` | No | docker-local | Repository name |
| `--keyword` | Yes | - | Keyword to match in image path or name |
| `--dry-run` | No | False | Preview changes without deleting |
| `--verbose` | No | False | Show detailed image information |

### Best Practices

1. Always use `--dry-run` first to verify what will be deleted
2. Use `--verbose` to see detailed information about each image
3. Double-check the repository name and keyword
4. Back up important images before deletion 