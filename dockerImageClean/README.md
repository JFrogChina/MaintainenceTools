# Docker Image Cleanup Tool

A Python script to help identify and manage unused Docker images in Artifactory. This tool generates detailed reports of Docker images that haven't been downloaded within a specified time period.

## 🚀 Features

- Query Docker images from Artifactory repository
- Filter images based on last download date
- Generate detailed Excel reports with image information
- Sort images by size to identify largest unused images
- Secure password handling
- Support for custom repository names
- Detailed console output with image statistics

## 📋 Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - requests
  - pandas
  - openpyxl
  - urllib3

## 🔧 Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd dockerImageClean
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## 🛠️ Usage

### Basic Usage

```bash
python dockerImageClean.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "your-username" \
  --repo "docker-local" \
  --days 30
```

### Command Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--artifactory-url` | Yes | - | Artifactory server URL (must end with /artifactory) |
| `--username` | Yes | - | Artifactory username |
| `--repo` | No | docker-local | Repository name to search in |
| `--days` | No | 30 | Number of days to look back for downloads. Images that have not been downloaded in the last N days will be included in the report. If not specified, all images will be shown (limited to 500). |
| `--output` | No | auto-generated | Output Excel file name |

### Examples

1. Query images not downloaded in the last 30 days:
```bash
python dockerImageClean.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "admin" \
  --repo "docker-local" \
  --days 30
```

2. Query images with custom output file:
```bash
python dockerImageClean.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "admin" \
  --repo "docker-local" \
  --output "my_report.xlsx"
```

3. Query all images (limited to 500):
```bash
python dockerImageClean.py \
  --artifactory-url "https://abc.jfrog.io/artifactory" \
  --username "admin" \
  --repo "docker-local"
```

## 📊 Output

### Console Output
- Configuration information
- List of found images with details
- Summary statistics
- Top 10 largest images

### Excel Report
The generated Excel report includes the following information for each image:
- Repository
- Path
- Tag
- Name
- Size (MB)
- Created date
- Modified date
- Updated date
- Created by
- Modified by
- Download count
- Last downloaded date
- SHA1
- Original SHA1
- MD5
- Original MD5
- SHA256

## 🔒 Security

- Password is securely handled using Python's `getpass` module
- SSL verification warnings are disabled for development environments
- No credentials are stored or logged

## ⚠️ Error Handling

The script includes error handling for:
- Invalid Artifactory URL format
- Authentication failures
- Connection issues
- Invalid JSON responses
- Missing required parameters

### Common Error Messages

1. Authentication Failure:
```
❌ Error connecting to Artifactory: 401 Unauthorized
Please check your Artifactory URL, username, and password.
```

2. Invalid URL Format:
```
❌ Error: Artifactory URL must start with http:// or https://
❌ Error: Artifactory URL must end with /artifactory
```

3. Connection Issues:
```
❌ Error connecting to Artifactory: Connection refused
Please check your Artifactory URL, username, and password.
```

4. Invalid Response:
```
❌ Error: Invalid JSON response from Artifactory
Response content: [error details]
```

## 📝 Notes

- The script uses AQL (Artifactory Query Language) to search for images
- Results are limited to 500 images per query
- Excel reports are sorted by image size in descending order
- Default repository name is 'docker-local'
- If authentication fails, the script will exit with status code 1
- Invalid responses from Artifactory will be displayed in the error message

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 