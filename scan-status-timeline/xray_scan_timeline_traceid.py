import re
import os
import sys
from datetime import datetime

def extract_time(line):
    m = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)Z', line)
    if m:
        # 精确到毫秒
        dt = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
        ms = int(m.group(2)[:3].ljust(3, '0'))  # 取前三位，不足补0
        return dt.replace(microsecond=ms*1000)
    return None

def find_trace_ids(log_dir, artifact):
    # artifact为完整文件名，严格匹配
    trace_ids = set()
    for root, _, files in os.walk(log_dir):
        for fname in files:
            if not fname.endswith('.log'):
                continue
            path = os.path.join(root, fname)
            with open(path, encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if artifact in line:
                        for m in re.findall(r'\[([a-f0-9]{16})\]', line):
                            trace_ids.add(m)
    return list(trace_ids)

def find_all_lines_by_trace_id(log_dir, trace_id):
    lines = []
    bracket_trace_id = f'[{trace_id}]'
    # 只保留这些关键字相关的业务日志
    keep_keywords = ['index', 'persist', 'analysis', 'ca', 'exposure', 'scan', 'worker', 'cve_applicability', 'exposures_service']
    for root, _, files in os.walk(log_dir):
        for fname in files:
            if not fname.endswith('.log'):
                continue
            path = os.path.join(root, fname)
            with open(path, encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if bracket_trace_id in line:
                        # 只保留含关键字的业务行
                        if any(kw in line for kw in keep_keywords):
                            lines.append(line.strip())
    return lines

def parse_timeline(lines, artifact, debug_mode=False):
    result = {}
    debug_status = {}

    # 定义各阶段关键字
    phase_keys = {
        'indexer_start':   ("index_worker", "Start processing msg"),
        'indexer_end':     ("index_worker", "has completed to process message"),
        'persist_start':   ("persist_worker", "is processing message from persist"),
        'persist_end':     ("persist_worker", "has completed to process message"),
        'analysis_start':  ("analysis_worker", "processing msg for artifact"),
        'analysis_end':    ("analysis_worker", "has completed to analyze the component"),
        'ca_start':        ("cve_applicability_service", "Starting CheckApplicability for url"),
        'ca_end':          None,
        'exposure_start':  ("exposures_service", "Exposures scan started after SCA scan"),
        'exposure_end':    None,
    }

    ca_end_patterns = [
        ("contextual_analysis", "from status: SCANNING to status: DONE", "DONE"),
        ("contextual_analysis", "from status: SCANNING to status: FAILED", "FAILED"),
        ("scan_build_or_rb", "Build not scanned for CA. All artifacts were skipped", "SKIP"),
        ("cve_applicability_service", "Package type Pypi is not supported", "SKIP"),
        ("cve_applicability_service", "No vulnerable components found for applicability scan", "SKIP"),

    ]
    exposure_end_patterns = [
        ("exposures", "from status: SCANNING to status: DONE", "DONE"),
        ("exposures_execution_worker", "Job failed", "FAILED"),
        ("scan_status_service", "from status: SCANNING to status: FAILED", "FAILED"),
        ("exposures_service", "Handling job failure", "FAILED"),
        ("exposures_service", "Exposures scan is enabled but no categories were selected for scan. Scan aborted", "ABORTED"),
    ]
    # 匹配各阶段时间    
    for key, val in phase_keys.items():
        if isinstance(val, list):  # 多种模式
            for sub1, sub2 in val:
                for line in reversed(lines) if key.endswith('_end') else lines:
                    if sub1 in line and sub2 in line:
                        t = extract_time(line)
                        if t:
                            result[key] = t
                            break
                if key in result:
                    break
        elif key == 'ca_end':
            for sub1, sub2, status in ca_end_patterns:
                for line in reversed(lines):
                    if re.search(re.escape(sub1), line) and re.search(re.escape(sub2), line):
                        t = extract_time(line)
                        if t:
                            result[key] = t
                            result[f"{key}_status"] = status
                            break
                if key in result:
                    break
            # 如果没有找到匹配，添加调试信息（仅在debug模式下）
            if key not in result and debug_mode:
                print(f"DEBUG: ca_end not found. Checking patterns:")
                for sub1, sub2, status in ca_end_patterns:
                    print(f"  Pattern: '{sub1}' and '{sub2}'")
                    found_sub1 = False
                    for line in reversed(lines):
                        if re.search(re.escape(sub1), line):
                            found_sub1 = True
                            print(f"    Found '{sub1}' in: {line}")
                            if re.search(re.escape(sub2), line):
                                print(f"    Also found '{sub2}' in same line")
                                t = extract_time(line)
                                print(f"    extract_time result: {t}")
                                if t:
                                    print(f"    Time extracted: {t}")
                                    result[key] = t
                                    result[f"{key}_status"] = status
                                    break
                            else:
                                print(f"    But '{sub2}' NOT found in same line")
                    if not found_sub1:
                        print(f"    '{sub1}' not found in any line")
                    if key in result:
                        break
        elif key == 'exposure_end':
            for sub1, sub2, status in exposure_end_patterns:
                for line in reversed(lines):
                    if sub1 in line and sub2 in line:
                        t = extract_time(line)
                        if t:
                            result[key] = t
                            result[f"{key}_status"] = status
                            break
                if key in result:
                    break
        elif val is not None:
            sub1, sub2 = val
            for line in reversed(lines) if key.endswith('_end') else lines:
                if sub1 in line and sub2 in line:
                    t = extract_time(line)
                    if t:
                        result[key] = t
                        break
    # 收集debug状态，倒序查找含ERROR/FAIL/WARN等行
    keywords = {
        'indexer': ["index", "error", "fail", "warn"],
        'persist': ["persist", "error", "fail", "warn"],
        'analysis': ["analysis", "error", "fail", "warn"],
        'ca': ["ca", "applicability", "error", "fail", "warn"],
        'exposure': ["exposure", "error", "fail", "warn"],
    }
    for phase in ['indexer', 'persist', 'analysis', 'ca', 'exposure']:
        phase_lines = [l for l in lines if phase in l.lower()]
        # 查找含关键错误字的日志行
        for l in reversed(phase_lines):
            if any(k in l.lower() for k in ["fail", "error", "warn", "skip", "missing", "retry"]):
                debug_status[phase] = l.strip()[-120:]  # 末尾截断
                break
        else:
            debug_status[phase] = "INCOMPLETE"

    return result, debug_status


def show(result, debug_status=None):
    print(f"| 阶段      | 起始时间                 | 结束时间                 | 耗时/状态     |")
    print(f"|-----------|--------------------------|--------------------------|--------------|")
    for phase in ['indexer', 'persist', 'analysis', 'ca', 'exposure']:
        s = result.get(f"{phase}_start")
        e = result.get(f"{phase}_end")
        status_key = f"{phase}_end_status"
        if s and e:
            status = result.get(status_key)
            # 统一处理状态字符串
            if status == "FAILED":
                state_str = "FAILED"
            elif status == "SKIP":
                state_str = "SKIP"
            elif status == "ABORTED":
                state_str = "ABORTED"
            else:
                state_str = ""
            delta = e - s
            total_seconds = delta.total_seconds()
            ms = int((total_seconds - int(total_seconds)) * 1000)
            h = int(total_seconds // 3600)
            m = int((total_seconds % 3600) // 60)
            sec = int(total_seconds % 60)
            if state_str:
                print(f"| {phase:9} | {s} | {e} | {h}:{m:02d}:{sec:02d}.{ms:03d} {state_str} |")
            else:
                print(f"| {phase:9} | {s} | {e} | {h}:{m:02d}:{sec:02d}.{ms:03d} |")
        elif s and not e:
            status = (debug_status.get(phase, '') if debug_status else '').lower()
            if any(k in status for k in ['fail', 'failed']):
                state = 'FAILED'
            elif any(k in status for k in ['warn', 'skip', 'not found']):
                state = 'WARNING'
            elif 'abort' in status:
                state = 'ABORTED'
            else:
                state = 'INCOMPLETE'
            print(f"| {phase:9} | {s} | {'-'*21} | {state:10} |")
        else:
            print(f"| {phase:9} | {'-'*21} | {'-'*21} | {'':12} |") 


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("logdir", help="日志主目录（如xray/）")
    parser.add_argument("artifact", help="artifact相关关键词（如sha256片段或jar文件名等）")
    parser.add_argument("--debug", action="store_true", help="写debug.log并打印分析行")
    args = parser.parse_args()

    trace_ids = find_trace_ids(args.logdir, args.artifact)
    print("All trace ids:", trace_ids)
    if not trace_ids:
        print("未找到trace id")
        sys.exit(1)
    for trace_id in trace_ids:
        lines = find_all_lines_by_trace_id(args.logdir, trace_id)
        result, debug_status = parse_timeline(lines, args.artifact, args.debug)
        # 判断是否有任何阶段有时间
        if not any(result.get(f"{phase}_start") or result.get(f"{phase}_end") for phase in ['indexer', 'persist', 'analysis', 'ca', 'exposure']):
            print(f"# Trace ID: {trace_id} skipped (no scan-related business lines found, e.g. curation/router/policyenforcer)")
            continue
        print(f"# Trace ID: {trace_id}")
        if args.debug:
            debug_filename = f"debug_{trace_id}.log"
            # 按时间排序
            sorted_lines = sorted(lines, key=lambda l: extract_time(l) or datetime.min)
            with open(debug_filename, "w", encoding="utf-8") as f:
                for l in sorted_lines:
                    f.write(l + "\n")
            print(f"已写入 {debug_filename}")
        show(result, debug_status)

