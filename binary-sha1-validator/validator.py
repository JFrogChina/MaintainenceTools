#!/usr/bin/env python3
"""
Binary SHA1 Validator
JFrog Artifactory 制品SHA1校验工具

功能：检查Artifactory底层存储中文件名和SHA1值是否一致
优势：相比shell脚本，Python实现效率更高，错误处理更完善
优化：支持流式处理、分批处理和断点续传，适合处理大量文件
"""

import os
import sys
import json
import hashlib
import argparse
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Optional, Generator
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('checksum_validation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SHA1Validator:
    """SHA1校验器 - 优化版本，支持大量文件处理"""
    
    def __init__(self, base_dir: str, thread_num: int = 4, batch_size: int = 10000):
        self.base_dir = Path(base_dir)
        self.thread_num = thread_num
        self.batch_size = batch_size
        self.results = {
            'valid': 0,
            'invalid': 0,
            'errors': 0,
            'total': 0
        }
        self.error_files = []
        self.processed_files = set()  # 记录已处理的文件，支持断点续传
        self.lock = threading.Lock()  # 线程安全锁
        self.last_batch_count = 0  # 记录上次的批次计数，支持断点续传
        
    def calculate_sha1(self, file_path: Path) -> str:
        """计算文件的SHA1值"""
        try:
            sha1_hash = hashlib.sha1()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha1_hash.update(chunk)
            return sha1_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算SHA1失败 {file_path}: {e}")
            return ""
    
    def is_sha1_filename(self, filename: str) -> bool:
        """检查文件名是否为SHA1格式（40位十六进制）"""
        return len(filename) == 40 and all(c in '0123456789abcdefABCDEF' for c in filename)
    
    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """验证单个文件的SHA1"""
        try:
            filename = file_path.name
            if not self.is_sha1_filename(filename):
                return False, f"文件名不是SHA1格式: {filename}"
            
            calculated_sha1 = self.calculate_sha1(file_path)
            if not calculated_sha1:
                return False, f"无法计算SHA1: {filename}"
            
            if calculated_sha1.lower() == filename.lower():
                return True, "SHA1匹配"
            else:
                return False, f"SHA1不匹配: 期望={filename}, 实际={calculated_sha1}"
                
        except Exception as e:
            return False, f"验证失败: {e}"
    
    def find_artifact_files_generator(self, start_time: Optional[str] = None, end_time: Optional[str] = None) -> Generator[Path, None, None]:
        """生成器方式查找文件，支持时间过滤，避免内存占用"""
        try:
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file() and self.is_sha1_filename(file_path.name):
                    # 如果指定了时间范围，检查文件修改时间
                    if start_time and end_time:
                        try:
                            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
                            if not (start_dt <= mtime <= end_dt):
                                continue
                        except Exception:
                            continue  # 跳过无法获取时间的文件
                    
                    yield file_path
                        
        except Exception as e:
            logger.error(f"查找文件失败: {e}")
    
    def process_batch(self, batch: List[Path]) -> Dict[str, int]:
        """处理一批文件"""
        batch_results = {'valid': 0, 'invalid': 0, 'errors': 0}
        
        with ThreadPoolExecutor(max_workers=self.thread_num) as executor:
            # 提交所有任务
            future_to_file = {executor.submit(self.validate_file, file_path): file_path 
                            for file_path in batch}
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    is_valid, message = future.result()
                    
                    with self.lock:
                        self.results['total'] += 1
                        
                        if is_valid:
                            batch_results['valid'] += 1
                            self.results['valid'] += 1
                            logger.debug(f"✅ {file_path.name}: {message}")
                        else:
                            batch_results['invalid'] += 1
                            self.results['invalid'] += 1
                            self.error_files.append((str(file_path), message))
                            logger.warning(f"❌ {file_path.name}: {message}")
                        
                        # 记录已处理文件
                        self.processed_files.add(str(file_path))
                        
                except Exception as e:
                    batch_results['errors'] += 1
                    self.results['errors'] += 1
                    logger.error(f"验证异常 {file_path}: {e}")
        
        return batch_results
    
    def validate_files_streaming(self, start_time: Optional[str] = None, end_time: Optional[str] = None) -> None:
        """流式处理所有文件，支持分批处理和断点续传"""
        logger.info(f"开始流式验证，批次大小: {self.batch_size}, 线程数: {self.thread_num}")
        
        batch = []
        batch_count = self.last_batch_count  # 从上次的批次计数继续
        
        for file_path in self.find_artifact_files_generator(start_time, end_time):
            # 跳过已处理的文件（断点续传）
            if str(file_path) in self.processed_files:
                continue
                
            batch.append(file_path)
            
            # 达到批次大小时处理
            if len(batch) >= self.batch_size:
                batch_count += 1
                logger.info(f"处理第 {batch_count} 批，文件数: {len(batch)}")
                
                batch_results = self.process_batch(batch)
                self._log_batch_progress(batch_count, batch_results)
                
                # 立即更新批次计数，确保中断时能正确保存
                self.last_batch_count = batch_count
                
                batch = []  # 清空批次
        
        # 处理最后一批
        if batch:
            batch_count += 1
            logger.info(f"处理最后一批，文件数: {len(batch)}")
            batch_results = self.process_batch(batch)
            self._log_batch_progress(batch_count, batch_results)
            
            # 更新最后的批次计数
            self.last_batch_count = batch_count
        
        # 如果还有未处理的文件，更新为下一个批次
        if batch:
            self.last_batch_count = batch_count + 1
        
        logger.info("所有批次处理完成")
    
    def _log_batch_progress(self, batch_num: int, batch_results: Dict[str, int]) -> None:
        """记录批次进度"""
        # 统一格式：批次进度 + 总体进度
        total_processed = self.results['total']
        
        # 批次进度（简洁）
        logger.info(f"✅ 批次 {batch_num} | 文件: {batch_results['valid'] + batch_results['invalid'] + batch_results['errors']} | "
                   f"通过: {batch_results['valid']} | 失败: {batch_results['invalid']} | 错误: {batch_results['errors']}")
        
        # 总体进度（每批次都显示，格式统一）
        logger.info(f"📊 总计: {total_processed} 文件 | "
                   f"通过: {self.results['valid']} | 失败: {self.results['invalid']} | 错误: {self.results['errors']}")
    
    def save_progress(self, filename: str = 'progress.json') -> None:
        """保存进度，支持断点续传"""
        progress_data = {
            'processed_files': list(self.processed_files),
            'results': self.results,
            'error_files': self.error_files,
            'last_batch_count': self.last_batch_count,  # 保存批次计数
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"进度已保存到 {filename}")
    
    def load_progress(self, filename: str = 'progress.json') -> bool:
        """加载进度，支持断点续传"""
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                
                self.processed_files = set(progress_data.get('processed_files', []))
                self.results = progress_data.get('results', self.results)
                self.error_files = progress_data.get('error_files', [])
                self.last_batch_count = progress_data.get('last_batch_count', 0) # 加载批次计数
                
                logger.info(f"已加载进度: {len(self.processed_files)} 个文件已处理")
                return True
            except Exception as e:
                logger.warning(f"加载进度失败: {e}")
                return False
        return False
    
    def generate_report(self) -> str:
        """生成验证报告"""
        report = []
        report.append("=" * 60)
        report.append("Binary SHA1 验证报告")
        report.append("=" * 60)
        report.append(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"基础目录: {self.base_dir}")
        report.append(f"总文件数: {self.results['total']}")
        report.append(f"验证通过: {self.results['valid']}")
        report.append(f"验证失败: {self.results['invalid']}")
        report.append(f"处理错误: {self.results['errors']}")
        report.append("")
        
        if self.error_files:
            report.append("❌ 验证失败的文件:")
            report.append("-" * 40)
            for file_path, error_msg in self.error_files:
                report.append(f"文件: {file_path}")
                report.append(f"错误: {error_msg}")
                report.append("")
        
        return "\n".join(report)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Binary SHA1 Validator - JFrog Artifactory制品SHA1校验工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 验证所有文件
  python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore
  
  # 指定线程数和批次大小
  python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore --threads 8 --batch-size 20000
  
  # 指定时间范围
  python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore --start-time "2024-01-01 00:00" --end-time "2024-01-31 23:59"
  
  # 从上次进度继续
  python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore --resume
        """
    )
    
    parser.add_argument(
        'base_dir',
        help='Artifactory filestore基础目录路径'
    )
    parser.add_argument(
        '--threads', '-t',
        type=int,
        default=4,
        help='并发线程数 (默认: 4)'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=10000,
        help='批次大小 (默认: 10000)'
    )
    parser.add_argument(
        '--start-time',
        help='开始时间 (格式: YYYY-MM-DD HH:MM)'
    )
    parser.add_argument(
        '--end-time',
        help='结束时间 (格式: YYYY-MM-DD HH:MM)'
    )
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        help='从上次进度继续'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 检查目录是否存在
    if not os.path.exists(args.base_dir):
        logger.error(f"目录不存在: {args.base_dir}")
        sys.exit(1)
    
    # 创建验证器
    validator = SHA1Validator(args.base_dir, args.threads, args.batch_size)
    
    # 自动检测并加载进度（断点续传）
    if validator.load_progress():
        logger.info("检测到上次进度，自动继续...")
    else:
        logger.info("开始新的验证任务...")
    
    try:
        # 流式处理
        validator.validate_files_streaming(args.start_time, args.end_time)
        
        # 保存最终进度
        validator.save_progress()
        
        # 生成报告
        report = validator.generate_report()
        print(report)
        
        # 保存报告到文件
        with open('validation_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info("验证完成，报告已保存到 validation_report.txt")
        
        # 返回适当的退出码
        if validator.results['invalid'] > 0 or validator.results['errors'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("用户中断，保存进度...")
        # 中断时保存当前批次计数
        validator.save_progress()
        sys.exit(130)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 