#!/usr/bin/env python3
import argparse
import hashlib
import sys
from typing import Tuple

def generate_file_with_checksum(prefix: str) -> Tuple[str, str]:
    """
    生成一个文件，使其内容以 prefix 开头，并且文件内容的 SHA-1 校验和（hex）也以相同的 prefix 开头。

    :param prefix: 2 个十六进制字符，例如 "a1"。
    :return: (生成的文件名, 对应的 SHA-1 校验和)
    """
    prefix = prefix.lower()
    # 校验：必须是 2 个十六进制字符
    if len(prefix) != 2 or any(c not in "0123456789abcdef" for c in prefix):
        raise ValueError("参数 prefix 必须是 2 个十六进制字符（0-9, a-f）。")

    base = prefix.encode("utf-8")
    suffix = 0

    # 不断尝试在 base 后面追加数字后缀，直到 SHA-1(hex) 前两位 == prefix
    while True:
        candidate = base + str(suffix).encode("utf-8")
        digest = hashlib.sha1(candidate).hexdigest()
        if digest.startswith(prefix):
            break
        suffix += 1

    file_name = f"file_with_{prefix}.txt"
    with open(file_name, "wb") as f:
        f.write(candidate)

    return file_name, digest

def main():
    parser = argparse.ArgumentParser(
        description="生成一个文件，内容以给定前缀开头，且其 SHA-1 校验和(hex)的前两位也等于该前缀。"
    )
    parser.add_argument(
        "prefix",
        metavar="PREFIX",
        help="2 个十六进制字符，用作内容和 checksum 的前缀（如 '0f'）。"
    )
    args = parser.parse_args()

    try:
        file_name, checksum = generate_file_with_checksum(args.prefix)
    except ValueError as err:
        print(f"参数错误：{err}", file=sys.stderr)
        sys.exit(1)

    print(f"✔ 生成文件：{file_name}")
    print(f"✔ SHA-1 checksum：{checksum}")

if __name__ == "__main__":
    main()

