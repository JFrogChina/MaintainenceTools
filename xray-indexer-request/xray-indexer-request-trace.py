import os
import re
from collections import defaultdict
from datetime import datetime


def find_index_requests(log_dir):
    # EVENT
    pattern_created = re.compile(r'Got indexing message: created')
    pattern_build = re.compile(r'Got indexing message: build')
    pattern_rb = re.compile(r'Got indexing message: release-bundle')
    # forceReindex - 需要同时包含 forceReindex 和 Scan status record updated for
    force_reindex_pattern = re.compile(r'forceReindex.*Scan status record updated for')
    results = set()
    
    # 只扫描特定的日志文件
    target_files = []
    for root, _, files in os.walk(log_dir):
        for fname in files:
            if fname.endswith('.log'):
                # 只匹配 xray-server-service 相关的日志文件
                # 排除 metrics, error, stack 等其他类型的日志
                if (fname == 'xray-server-service.log' or 
                    (fname.startswith('xray-server-service-') and 
                     not any(x in fname for x in ['metrics', 'error', 'stack', 'request', 'traefik']) and
                     fname.endswith('.log'))):
                    target_files.append(os.path.join(root, fname))
    
    for path in target_files:
        with open(path, encoding='utf-8', errors='ignore') as f:
            for line in f:
                if pattern_created.search(line) or pattern_build.search(line) or pattern_rb.search(line) or force_reindex_pattern.search(line):
                    results.add(line.strip())
    return list(results)

def classify_line(line):
    if 'forceReindex' in line:
        return 'forceReindex'
    elif 'Got indexing message: release-bundle' in line:
        return 'release-bundle'
    elif 'Got indexing message: build' in line:
        return 'build'
    elif 'Got indexing message:' in line:
        return 'created'
    else:
        return 'other'

def extract_timestamp(line):
    # 假设日志行以 ISO 格式时间开头
    m = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)Z', line)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S.%f")
        except Exception:
            pass
    return datetime.min  # 没有时间戳的行排到最后

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='查找 Xray index 请求')
    parser.add_argument("log_dir", help="日志目录路径")
    parser.add_argument("--head", type=int, default=2, help="显示前N条结果 (默认: 20)")
    parser.add_argument("--output", default="requests.log", help="输出日志文件名 (默认: requests.log)")
    
    args = parser.parse_args()
    
    log_dir = args.log_dir
    index_lines = find_index_requests(log_dir)
    
    type_counter = {'created': 0, 'build': 0, 'release-bundle': 0, 'forceReindex': 0}
    classified_lines = []

    for line in index_lines:
        t = classify_line(line)
        if t in type_counter:
            type_counter[t] += 1
        classified_lines.append((t, line))

    # 总请求数 = len(classified_lines)
    # 各类型数量 = type_counter['created'] 等
    
    # 按时间倒序排序
    classified_lines.sort(key=lambda x: extract_timestamp(x[1]), reverse=True)

    # 分组
    grouped_lines = defaultdict(list)
    for t, line in classified_lines:
        grouped_lines[t].append(line)

    # 保存结果到日志文件
    with open(args.output, 'w', encoding='utf-8') as f:
        # 写入统计摘要
        f.write(f"# Xray Index 请求统计摘要\n")
        f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 日志目录: {log_dir}\n")
        f.write(f"# 总请求数: {len(index_lines)}\n")
        f.write(f"# EVENT 请求总数: {type_counter['created'] + type_counter['build'] + type_counter['release-bundle']} 条\n")
        f.write(f"#   - created: {type_counter['created']} 条\n")
        f.write(f"#   - build: {type_counter['build']} 条\n")
        f.write(f"#   - release-bundle: {type_counter['release-bundle']} 条\n")
        f.write(f"# forceReindex 请求: {type_counter['forceReindex']} 条\n")
        f.write(f"# {'='*80}\n\n")
        
        # 写入所有结果，按分类分组
        for t in ['forceReindex', 'release-bundle', 'build', 'created']:
            lines = grouped_lines.get(t, [])
            if not lines:
                continue
            f.write(f"\n# ==== {t} ({len(lines)} 条) ====\n")
            for i, line in enumerate(lines, 1):
                f.write(f"{i:4d}. {line}\n")
    
    # 显示统计摘要
    print(f"共找到 {len(index_lines)} 条 index 请求")
    print(f"EVENT 请求总数: {type_counter['created'] + type_counter['build'] + type_counter['release-bundle']} 条")
    print(f"  - created: {type_counter['created']} 条")
    print(f"  - build: {type_counter['build']} 条")
    print(f"  - release-bundle: {type_counter['release-bundle']} 条")
    print(f"forceReindex 请求: {type_counter['forceReindex']} 条")
    print(f"结果已保存到: {args.output}")
    
    # 显示前N条结果
    if index_lines:
        print(f"\n显示前 {min(args.head, len(index_lines))} 条:")
        for t in ['forceReindex', 'release-bundle', 'build', 'created']:
            lines = grouped_lines.get(t, [])
            if not lines:
                continue
            print(f"\n==== {t}（{len(lines)} 条）====")
            for i, line in enumerate(lines[:args.head], 1):
                print(f"{i:3d}. {line}")
            if len(lines) > args.head:
                print(f"... 还有 {len(lines) - args.head} 条未显示")
        
        if len(index_lines) > args.head:
            print(f"\n... 还有 {len(index_lines) - args.head} 条未显示")
            print(f"查看完整结果: cat {args.output}")
            print(f"查看更多结果: head -{args.head + 10} {args.output}")