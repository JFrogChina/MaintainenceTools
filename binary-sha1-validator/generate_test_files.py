#!/usr/bin/env python3
"""
Test File Generator for Binary SHA1 Validator
生成测试文件，模拟 Artifactory 存储结构

功能：生成指定数量的测试文件，文件名为其内容的SHA1值
目录结构：按SHA1前2位创建子目录，如 99/9932ed218041489c2292a8d625db9053498bf23b
支持：--false 参数生成错误文件（文件名 ≠ 内容SHA1）
"""

import os
import sys
import random
import hashlib
import argparse
import string
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_file_generation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TestFileGenerator:
    """测试文件生成器"""
    
    def __init__(self, base_dir: str, count: int = 10000, min_size: int = 100, max_size: int = 1000):
        self.base_dir = Path(base_dir)
        self.count = count
        self.min_size = min_size
        self.max_size = max_size
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'directories_created': set(),
            'errors': 0,
            'false_files': []  # 记录错误文件信息
        }
        
    def create_directory_structure(self, sha1_hash: str) -> Path:
        """根据SHA1创建目录结构"""
        try:
            # 取前2位作为一级目录
            first_two = sha1_hash[:2]
            # 完整SHA1作为文件名
            full_sha1 = sha1_hash
            
            # 创建目录路径
            dir_path = self.base_dir / first_two
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # 记录创建的目录
            self.stats['directories_created'].add(first_two)
            
            return dir_path / full_sha1
            
        except Exception as e:
            logger.error(f"创建目录失败 {sha1_hash}: {e}")
            raise
    
    def generate_random_content(self, size: int) -> str:
        """生成指定大小的随机内容"""
        # 使用字母、数字和特殊字符，增加内容的随机性
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choices(chars, k=size))
    
    def generate_test_file(self, generate_false: bool = False) -> Tuple[str, int]:
        """生成单个测试文件，返回SHA1和文件大小"""
        try:
            # 生成随机大小
            file_size = random.randint(self.min_size, self.max_size)
            
            # 生成随机内容
            content = self.generate_random_content(file_size)
            
            # 计算实际SHA1
            actual_sha1 = hashlib.sha1(content.encode('utf-8')).hexdigest()
            
            if generate_false:
                # 生成错误文件：文件名 ≠ 内容SHA1
                # 通过修改内容生成一个不同的SHA1作为文件名
                while True:
                    modified_content = content + str(random.randint(1000, 9999))
                    false_sha1 = hashlib.sha1(modified_content.encode('utf-8')).hexdigest()
                    if false_sha1 != actual_sha1:
                        break
                
                # 使用错误的SHA1创建目录结构
                file_path = self.create_directory_structure(false_sha1)
                
                # 记录错误文件信息
                self.stats['false_files'].append({
                    'filename': false_sha1,
                    'actual_sha1': actual_sha1,
                    'size': file_size
                })
                
                # 保存原始内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return false_sha1, file_size
            else:
                # 生成正常文件：文件名 = 内容SHA1
                file_path = self.create_directory_structure(actual_sha1)
                
                # 保存文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return actual_sha1, file_size
            
        except Exception as e:
            logger.error(f"生成测试文件失败: {e}")
            self.stats['errors'] += 1
            raise
    
    def generate_all_files(self, generate_false: bool = False) -> None:
        """生成所有测试文件"""
        if generate_false:
            logger.info("生成模式: 错误文件（文件名 ≠ 内容SHA1）")
        else:
            logger.info("生成模式: 正常文件（文件名 = 内容SHA1）")
            
        logger.info(f"开始生成测试文件...")
        logger.info(f"目标目录: {self.base_dir}")
        logger.info(f"文件数量: {self.count}")
        logger.info(f"文件大小: {self.min_size}-{self.max_size} bytes")
        logger.info("-" * 60)
        
        start_time = datetime.now()
        
        for i in range(1, self.count + 1):
            try:
                sha1_hash, file_size = self.generate_test_file(generate_false)
                
                self.stats['total_files'] += 1
                self.stats['total_size'] += file_size
                
                # 显示进度
                if i % 1000 == 0 or i == self.count:
                    progress = (i / self.count) * 100
                    logger.info(f"✅ 已生成: {i}/{self.count} ({progress:.1f}%)")
                
                # 详细模式显示每个文件
                if logger.isEnabledFor(logging.DEBUG):
                    if generate_false:
                        logger.debug(f"生成错误文件: {sha1_hash} (大小: {file_size} bytes)")
                    else:
                        logger.debug(f"生成正常文件: {sha1_hash} (大小: {file_size} bytes)")
                        
            except Exception as e:
                logger.error(f"生成第 {i} 个文件失败: {e}")
                continue
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # 显示完成信息
        self._show_completion_info(duration, generate_false)
    
    def _show_completion_info(self, duration, generate_false: bool) -> None:
        """显示完成信息"""
        logger.info("=" * 60)
        logger.info("🎉 测试文件生成完成！")
        logger.info("=" * 60)
        
        # 基本统计
        logger.info(f"📊 统计信息:")
        logger.info(f"   - 总文件数: {self.stats['total_files']:,}")
        logger.info(f"   - 文件类型: {'错误文件' if generate_false else '正常文件'}")
        if generate_false:
            logger.info(f"   - 错误文件详情: 文件名 ≠ 内容SHA1")
        else:
            logger.info(f"   - 验证结果: 应该全部通过验证")
        logger.info(f"   - 目录数量: {len(self.stats['directories_created'])} (00-ff)")
        logger.info(f"   - 平均文件大小: {self.stats['total_size'] // self.stats['total_files']} bytes")
        logger.info(f"   - 总大小: {self.stats['total_size'] / (1024*1024):.2f} MB")
        logger.info(f"   - 错误数量: {self.stats['errors']}")
        logger.info(f"   - 耗时: {duration}")
        
        # 目录分布
        if self.stats['directories_created']:
            sorted_dirs = sorted(self.stats['directories_created'])
            logger.info(f"   - 目录分布: {', '.join(sorted_dirs[:10])}{'...' if len(sorted_dirs) > 10 else ''}")
        
        # 保存错误文件信息
        if generate_false and self.stats['false_files']:
            self._save_false_files_info()
        
        logger.info("=" * 60)
    
    def _save_false_files_info(self) -> None:
        """保存错误文件信息到JSON文件"""
        try:
            import json
            false_files_data = {
                'generation_time': datetime.now().isoformat(),
                'total_files': len(self.stats['false_files']),
                'false_files': self.stats['false_files']
            }
            
            with open('false_files.json', 'w', encoding='utf-8') as f:
                json.dump(false_files_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"错误文件信息已保存到 false_files.json")
        except Exception as e:
            logger.warning(f"保存错误文件信息失败: {e}")
    
    def cleanup(self) -> None:
        """清理生成的测试文件（危险操作）"""
        if not self.base_dir.exists():
            logger.warning("目标目录不存在，无需清理")
            return
        
        try:
            import shutil
            shutil.rmtree(self.base_dir)
            logger.info(f"已清理目录: {self.base_dir}")
        except Exception as e:
            logger.error(f"清理失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Test File Generator - 为Binary SHA1 Validator生成测试文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 生成1万个正常测试文件（默认）
  python3 generate_test_files.py /opt/jfrog/artifactory/var/data/artifactory/filestore/
  
  # 生成1万个错误测试文件（文件名 ≠ 内容SHA1）
  python3 generate_test_files.py /opt/jfrog/artifactory/var/data/artifactory/filestore/ --false
  
  # 指定文件数量和大小范围
  python3 generate_test_files.py /path/to/test/dir --count 5000 --min-size 200 --max-size 800
  
  # 详细模式
  python3 generate_test_files.py /path/to/test/dir --verbose
  
  # 清理测试文件（危险操作）
  python3 generate_test_files.py /path/to/test/dir --cleanup
        """
    )
    
    parser.add_argument(
        'base_dir',
        help='测试文件生成的基础目录路径'
    )
    parser.add_argument(
        '--count', '-c',
        type=int,
        default=10000,
        help='生成的文件数量 (默认: 10000)'
    )
    parser.add_argument(
        '--min-size',
        type=int,
        default=100,
        help='文件最小大小(bytes) (默认: 100)'
    )
    parser.add_argument(
        '--max-size',
        type=int,
        default=1000,
        help='文件最大大小(bytes) (默认: 1000)'
    )
    parser.add_argument(
        '--false',
        action='store_true',
        help='生成错误文件（文件名 ≠ 内容SHA1）'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='清理生成的测试文件（危险操作）'
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
    
    # 检查参数有效性
    if args.min_size >= args.max_size:
        logger.error("最小文件大小必须小于最大文件大小")
        sys.exit(1)
    
    if args.count <= 0:
        logger.error("文件数量必须大于0")
        sys.exit(1)
    
    # 创建生成器
    generator = TestFileGenerator(
        args.base_dir,
        args.count,
        args.min_size,
        args.max_size
    )
    
    try:
        if args.cleanup:
            # 清理模式
            confirm = input(f"确定要删除目录 {args.base_dir} 及其所有内容吗？(输入 'yes' 确认): ")
            if confirm.lower() == 'yes':
                generator.cleanup()
            else:
                logger.info("取消清理操作")
        else:
            # 生成模式
            generator.generate_all_files(args.false)
            
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(130)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 