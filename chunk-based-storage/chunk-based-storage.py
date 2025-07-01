import hashlib
import os
from pathlib import Path
import pandas as pd
import argparse
import re
from collections import defaultdict
import random

# -----------------------------
# 🔧 CLI 参数解析
# -----------------------------
def parse_chunk_size(s):
    s = s.strip().upper()
    match = re.match(r"(\d+)(B|KB|MB|GB)?", s)
    if not match:
        raise argparse.ArgumentTypeError("Invalid chunk size format")
    num, unit = match.groups()
    multiplier = {
        None: 1,
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3
    }[unit]
    size = int(num) * multiplier
    if size < 1:
        raise argparse.ArgumentTypeError("Chunk size must be >= 1 byte")
    return size

parser = argparse.ArgumentParser(description="Deduplication check for chunked files")
parser.add_argument("--chunk-size", default="64KB", type=parse_chunk_size,
                    help="Chunk size, e.g., 512KB, 1MB, 2048 (bytes)")
parser.add_argument("--dir", default="logs", help="Directory to scan (default: ./logs)")
args = parser.parse_args()

CHUNK_SIZE = args.chunk_size
LOGS_DIR = args.dir

print(f"🔧 Chunk size: {CHUNK_SIZE} bytes")
print(f"📂 Scanning directory: {LOGS_DIR}")

# -----------------------------
# 📁 遍历文件
# -----------------------------
log_files = sorted(Path(LOGS_DIR).rglob("*"))
log_files = [f for f in log_files if f.is_file()]

if not log_files:
    print(f"❌ No files found in '{LOGS_DIR}'")
    exit(1)

print(f"📁 Found {len(log_files)} files.")

# -----------------------------
# 🧮 分片并计算 SHA1
# -----------------------------
all_hashes = []
file_hash_info = []

def split_and_hash(file_path):
    hashes = []
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha1 = hashlib.sha1(chunk).hexdigest()
            hashes.append(sha1)
    return hashes

for log_file in log_files:
    hashes = split_and_hash(log_file)
    all_hashes.extend(hashes)
    file_hash_info.append({
        "file": str(log_file),
        "chunks": len(hashes)
    })

# -----------------------------
# 📊 去重率统计
# -----------------------------
total_chunks = len(all_hashes)
unique_chunks = len(set(all_hashes))
duplicate_chunks = total_chunks - unique_chunks
dedup_ratio = round((duplicate_chunks / total_chunks) * 100, 2) if total_chunks > 0 else 0.0

# -----------------------------
# 📄 每文件 chunk 数量
# -----------------------------
print("\n📄 Per-File Chunk Count:")
df_files = pd.DataFrame(file_hash_info)
print(df_files.to_string(index=False))

# -----------------------------
# 📊 总体统计
# -----------------------------
print("\n📊 === Overall Deduplication Summary ===")
print(f"Total Chunks          : {total_chunks}")
print(f"Unique Chunks         : {unique_chunks}")
print(f"Duplicate Chunks      : {duplicate_chunks}")
print(f"Deduplication Ratio   : {dedup_ratio}%")
