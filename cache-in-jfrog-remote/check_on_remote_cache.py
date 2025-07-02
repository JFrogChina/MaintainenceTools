import requests
import os
import sys
import argparse
import io
import multiprocessing
import time
from queue import Empty
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor

def get_auth_headers():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("[ERROR] 环境变量 HF_TOKEN 未设置，无法认证 Artifactory。", file=sys.stderr)
        sys.exit(1)
    return {"Authorization": f"Bearer {token}"}

def get_files_from_artifactory_api(repo_id, revision, artifactory_base, timeout=20, debug=False, repo_type="model"):
    """
    获取 Artifactory 代理仓库下指定模型或数据集的所有文件列表
    repo_type: "model" 或 "dataset"
    """
    if repo_type == "dataset":
        api_url = f"{artifactory_base}/api/datasets/{repo_id}/revision/{revision}"
    else:
        api_url = f"{artifactory_base}/api/models/{repo_id}/revision/{revision}"
    headers = get_auth_headers()
    if debug:
        print(f"[DEBUG] 获取文件列表: {api_url}")
    resp = requests.get(api_url, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise Exception(f"获取文件列表失败: {resp.status_code} {resp.text}")
    data = resp.json()
    return data.get("siblings", [])

def print_model_result(repo_type, repo_id, revision, model_output_lines, completed_count=None, total_count=None):
    print(f"\n🔍 {repo_type}: {repo_id}@{revision}")
    print("-" * 60)
    cached, not_cached, error = 0, 0, 0
    for line in model_output_lines:
        print(line, end="")
        if "\033[32mCACHED\033[0m" in line:
            cached += 1
        elif "\033[35mNOT CACHED\033[0m" in line:
            not_cached += 1
        elif "\033[31mERROR" in line:
            error += 1
    print(f"\n统计: \033[32mCACHED {cached}\033[0m, \033[35mNOT CACHED {not_cached}\033[0m, \033[31mERROR {error}\033[0m")
    if completed_count is not None and total_count is not None:
        print(f"✅ {repo_type} {repo_id}@{revision} 处理完成 ({completed_count}/{total_count})")
    print("------------------------------------------------------------")

def file_head_check_and_queue(repo_id, revision, artifactory_base, f, headers, file_timeout, queue, repo_type="model"):
    filename = f['rfilename'] if isinstance(f, dict) and 'rfilename' in f else str(f)
    if repo_type == "dataset":
        url = f"{artifactory_base}/datasets/{repo_id}/resolve/{revision}/{filename}"
    else:
        url = f"{artifactory_base}/{repo_id}/resolve/{revision}/{filename}"
    try:
        resp = requests.head(url, headers=headers, timeout=file_timeout)
        if resp.status_code == 200:
            status = "CACHED"
        elif resp.status_code == 404:
            status = "NOT CACHED"
        else:
            status = f"ERROR {resp.status_code}"
    except requests.exceptions.Timeout:
        status = "NOT CACHED"
    except Exception as e:
        status = f"ERROR {e}"
    if status == "NOT CACHED":
        colored_status = "\033[35mNOT CACHED\033[0m"  # 紫色
    elif status == "CACHED":
        colored_status = "\033[32mCACHED\033[0m"      # 绿色
    else:
        colored_status = f"\033[31m{status}\033[0m"   # 红色（错误）
    output_line = f"{filename:<40} | {colored_status:>10}\n"
    queue.put(output_line)

def cache_from_remote_worker(repo_id, revision, artifactory_base, timeout, debug, file_workers, file_timeout, queue, repo_type="model"):
    import threading
    files = get_files_from_artifactory_api(repo_id, revision, artifactory_base, timeout, debug, repo_type)
    queue.put(f"[{repo_id}@{revision}] 共{len(files)}个文件，将检测 Artifactory 代理缓存：\n")
    queue.put(f"__FILE_COUNT__:{len(files)}")
    headers = get_auth_headers()
    threads = []
    for f in files:
        t = threading.Thread(target=file_head_check_and_queue, args=(repo_id, revision, artifactory_base, f, headers, file_timeout, queue, repo_type))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    queue.put("__MODEL_DONE__")

def cache_from_remote_with_timeout(repo_id, revision, artifactory_base, timeout=20, debug=False, file_workers=12, file_timeout=5, silent=False, repo_type="model"):
    from multiprocessing import Process, Queue
    from queue import Empty
    import time
    output = ""
    queue = Queue()
    p = Process(target=cache_from_remote_worker, args=(repo_id, revision, artifactory_base, timeout, debug, file_workers, file_timeout, queue, repo_type))
    p.start()
    start_time = time.time()
    model_done = False
    file_count = None
    files_received = 0
    while not model_done and (time.time() - start_time) <= timeout:
        try:
            msg = queue.get(timeout=0.2)
            if msg == "__MODEL_DONE__":
                model_done = True
            elif msg.startswith("__FILE_COUNT__:"):
                file_count = int(msg.split(":", 1)[1])
            else:
                if not silent:
                    print(msg, end="")
                output += msg
                if " | " in msg and not msg.startswith("[") and not msg.startswith("[ERROR]"):
                    files_received += 1
                    if file_count is not None and files_received >= file_count:
                        model_done = True
                        p.terminate()
                        break
        except Empty:
            if not p.is_alive():
                break
            pass
    if model_done and file_count is not None and files_received >= file_count:
        p.terminate()
        p.kill()
        return output
    while True:
        try:
            msg = queue.get_nowait()
            if msg != "__MODEL_DONE__" and not msg.startswith("__FILE_COUNT__:"):
                if not silent:
                    print(msg, end="")
                output += msg
        except Empty:
            break
    if not model_done:
        p.terminate()
        p.join()
        timeout_msg = f"[TIMEOUT] {repo_id}@{revision} 检测超时（>{timeout}s）\n"
        if not silent:
            print(timeout_msg, end="")
        output += timeout_msg
    else:
        p.join()
    return output

def parse_checklist_file(filename):
    tasks = []
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                repo_type, repo_id, revision = parts
                if repo_type not in ("model", "dataset"):
                    print(f"[WARN] 未知类型: {repo_type}, 默认按 model 处理")
                    repo_type = "model"
                tasks.append((repo_type, repo_id, revision))
            elif len(parts) == 2:
                # 兼容老格式
                repo_id, revision = parts
                tasks.append(("model", repo_id, revision))
            else:
                print(f"[WARN] 格式不正确: {line}")
    return tasks

def batch_from_file_concurrent(models_file, artifactory_base, timeout=20, debug=False, workers=2, file_workers=12, file_timeout=5):
    tasks = parse_checklist_file(models_file)
    print(f"开始并发处理 {len(tasks)} 个条目，并发数: {workers}")
    from functools import partial
    from concurrent.futures import as_completed, ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_task = {
            executor.submit(
                cache_from_remote_with_timeout,
                repo_id, revision, artifactory_base, timeout, debug, file_workers, file_timeout, True, repo_type
            ): (repo_type, repo_id, revision)
            for repo_type, repo_id, revision in tasks
        }
        completed_count = 0
        total_count = len(tasks)
        for future in as_completed(future_to_task):
            repo_type, repo_id, revision = future_to_task[future]
            try:
                result = future.result(timeout=timeout + 5)
                completed_count += 1
                model_output_lines = result.splitlines(keepends=True)
                print_model_result(repo_type, repo_id, revision, model_output_lines, completed_count, total_count)
            except Exception as e:
                completed_count += 1
                print(f"\n🔍 {repo_type}: {repo_id}@{revision}")
                print("-" * 60)
                print(f"❌ {repo_type} {repo_id}@{revision} 处理失败: {e}\n")
                print("------")
                print(f"❌ {repo_type} {repo_id}@{revision} 处理失败 ({completed_count}/{total_count})")
        print(f"\n🎉 所有 {len(tasks)} 个条目处理完成！")

def batch_from_file(models_file, artifactory_base, timeout=20, debug=False, workers=2, file_workers=12, file_timeout=5):
    tasks = parse_checklist_file(models_file)
    total_count = len(tasks)
    for idx, (repo_type, repo_id, revision) in enumerate(tasks, 1):
        print(f"\n开始处理{repo_type}: {repo_id}@{revision}")
        result = cache_from_remote_with_timeout(repo_id, revision, artifactory_base, timeout, debug, file_workers, file_timeout, repo_type=repo_type)
        model_output_lines = result.splitlines(keepends=True)
        print_model_result(repo_type, repo_id, revision, model_output_lines, idx, total_count)

if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    # 重定向输出到文件
    class Logger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, 'w', encoding='utf-8')
            
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
            self.log.flush()
            
        def flush(self):
            self.terminal.flush()
            self.log.flush()
    
    # 设置日志文件
    log_filename = "head.log"
    sys.stdout = Logger(log_filename)
    
    # 写入日志头部信息
    print(f"# Artifactory 代理缓存检测日志")
    print(f"# 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# 命令: {' '.join(sys.argv)}")
    print("=" * 80)
    
    parser = argparse.ArgumentParser(description="检测 Artifactory 代理缓存状态，支持批量和并发，严格超时，模型内文件多线程，实时输出")
    parser.add_argument("--models", type=str, default=None, help="模型列表文件，每行: repo_id,revision")
    parser.add_argument("--timeout", type=int, default=15, help="每个模型检测的最大超时（秒）")
    parser.add_argument("--debug", action="store_true", help="打印 API 原始内容")
    parser.add_argument("--registry", type=str, default="http://localhost:8082/artifactory/api/huggingfaceml/huggingfaceml-remote", help="Artifactory 代理基础URL")
    parser.add_argument("--workers", type=int, default=1, help="并发进程数（模型级并发），workers<=1为单线程，workers>1为并发模式")
    parser.add_argument("--file-workers", type=int, default=10, help="每个模型内部文件并发数")
    parser.add_argument("--file-timeout", type=int, default=5, help="每个文件 HEAD 检查超时（秒）")
    args = parser.parse_args()

    try:
        if args.models:
            if args.workers > 1:
                print(f"🚀 使用并发版本处理，并发数: {args.workers}")
                batch_from_file_concurrent(args.models, args.registry, timeout=args.timeout, debug=args.debug, workers=args.workers, file_workers=args.file_workers, file_timeout=args.file_timeout)
            else:
                print("🐌 使用单线程版本处理")
                batch_from_file(args.models, args.registry, timeout=args.timeout, debug=args.debug, workers=args.workers, file_workers=args.file_workers, file_timeout=args.file_timeout)
        else:
            # 单模型测试（1.2G）
            repo_id = "LiheYoung/depth_anything_vitl14"
            revision = "973948530e4e4f4afd6d1913f670d9f96071dcaa"
            cache_from_remote_with_timeout(repo_id, revision, args.registry, timeout=args.timeout, debug=args.debug, file_workers=args.file_workers, file_timeout=args.file_timeout)
    finally:
        # 写入日志尾部信息
        print("=" * 80)
        print(f"# 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"# 日志已保存到: {log_filename}")
        
        # 恢复标准输出
        sys.stdout.log.close()
        sys.stdout = sys.stdout.terminal