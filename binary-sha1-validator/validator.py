#!/usr/bin/env python3
"""
Binary SHA1 Validator
JFrog Artifactory 制品SHA1校验工具

功能：检查Artifactory底层存储中文件名和SHA1值是否一致
优势：相比shell脚本，Python实现效率更高，错误处理更完善
"""

import os
import sys
import hashlib
import argparse
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Optional
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
    """SHA1校验器"""
    
    def __init__(self, base_dir: str, thread_num: int = 4):
        self.base_dir = Path(base_dir)
        self.thread_num = thread_num
        self.results = {
            'valid': 0,
            'invalid': 0,
            'errors': 0,
            'total': 0
        }
        self.error_files = []
        
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
    
    def find_artifact_files(self, start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[Path]:
        """查找制品文件"""
        files = []
        try:
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file() and self.is_sha1_filename(file_path.name):
                    # 如果指定了时间范围，检查文件修改时间
                    if start_time and end_time:
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                        end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
                        if start_dt <= mtime <= end_dt:
                            files.append(file_path)
                    else:
                        files.append(file_path)
                        
        except Exception as e:
            logger.error(f"查找文件失败: {e}")
            
        return files
    
    def validate_files_parallel(self, files: List[Path]) -> None:
        """并行验证文件"""
        logger.info(f"开始验证 {len(files)} 个文件，使用 {self.thread_num} 个线程")
        
        with ThreadPoolExecutor(max_workers=self.thread_num) as executor:
            # 提交所有任务
            future_to_file = {executor.submit(self.validate_file, file_path): file_path 
                            for file_path in files}
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    is_valid, message = future.result()
                    self.results['total'] += 1
                    
                    if is_valid:
                        self.results['valid'] += 1
                        logger.debug(f"✅ {file_path.name}: {message}")
                    else:
                        self.results['invalid'] += 1
                        self.error_files.append((str(file_path), message))
                        logger.warning(f"❌ {file_path.name}: {message}")
                        
                except Exception as e:
                    self.results['errors'] += 1
                    logger.error(f"验证异常 {file_path}: {e}")
    
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
  
  # 指定线程数
  python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore --threads 8
  
  # 指定时间范围
  python3 validator.py /opt/jfrog/artifactory/var/data/artifactory/filestore --start-time "2024-01-01 00:00" --end-time "2024-01-31 23:59"
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
        '--start-time',
        help='开始时间 (格式: YYYY-MM-DD HH:MM)'
    )
    parser.add_argument(
        '--end-time',
        help='结束时间 (格式: YYYY-MM-DD HH:MM)'
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
    validator = SHA1Validator(args.base_dir, args.threads)
    
    try:
        # 查找文件
        logger.info(f"正在查找制品文件...")
        files = validator.find_artifact_files(args.start_time, args.end_time)
        
        if not files:
            logger.warning("未找到任何制品文件")
            sys.exit(0)
        
        logger.info(f"找到 {len(files)} 个制品文件")
        
        # 验证文件
        validator.validate_files_parallel(files)
        
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
        logger.info("用户中断操作")
        sys.exit(130)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 