#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JFrog Support Bundle 日志提取工具
简化版本：保持核心功能，减少复杂性，保留时间戳
"""

import os
import zipfile
import gzip
import shutil
import glob
import json
import re
import subprocess
from datetime import datetime

def extract_node_from_zipname(zip_name, service_manifest_data=None):
    """从zip文件名中提取节点ID，基于service_manifest.json的节点信息"""
    try:
        if not service_manifest_data or 'microservices' not in service_manifest_data:
            return 'unknown'
        
        filename = os.path.basename(zip_name)
        microservices = service_manifest_data['microservices']
        
        # 遍历所有服务，找到匹配的节点
        for service_name, nodes in microservices.items():
            if isinstance(nodes, dict):
                for node_name in nodes.keys():
                    # 检查zip文件名是否包含这个节点名
                    if node_name in filename:
                        return node_name
        
        # 如果没有找到匹配的节点，返回unknown
        return 'unknown'
        
    except Exception as e:
        print(f"      ⚠️ 提取节点名失败: {e}")
        return 'unknown'

def preserve_file_attributes(zip_info, target_file):
    """保留文件的原始时间戳和权限"""
    try:
        # 设置文件时间戳
        if zip_info.date_time:
            year, month, day, hour, minute, second = zip_info.date_time
            
            # 验证时间戳的有效性
            if (1 <= month <= 12 and 1 <= day <= 31 and 
                0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                timestamp = datetime(year, month, day, hour, minute, second).timestamp()
                os.utime(target_file, (timestamp, timestamp))
            # 去掉无效时间戳的警告信息
        
        # 设置文件权限
        if zip_info.external_attr:
            mode = zip_info.external_attr >> 16
            if mode & 0o777:  # 确保权限位有效
                os.chmod(target_file, mode & 0o777)
                
    except Exception as e:
        print(f"      ⚠️ 保留文件属性失败: {e}")

def create_file_with_timestamp(zip_info, target_file, inner_zip=None, filename=None):
    """创建文件时直接使用正确的时间戳"""
    try:
        # 创建目录
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        
        # 如果是从内部zip提取
        if inner_zip and filename:
            with inner_zip.open(filename) as fsrc, open(target_file, 'wb') as fdst:
                shutil.copyfileobj(fsrc, fdst)
        # 如果是从外部zip提取
        else:
            # 这里应该不会用到，但保留以防万一
            pass
        
        # 设置时间戳（在文件创建后立即设置）
        if zip_info and zip_info.date_time:
            year, month, day, hour, minute, second = zip_info.date_time
            
            # 验证时间戳的有效性
            if (1 <= month <= 12 and 1 <= day <= 31 and 
                0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                timestamp = datetime(year, month, day, hour, minute, second).timestamp()
                os.utime(target_file, (timestamp, timestamp))
            # 去掉无效时间戳的警告信息
        
        # 设置文件权限
        if zip_info and zip_info.external_attr:
            mode = zip_info.external_attr >> 16
            if mode & 0o777:  # 确保权限位有效
                os.chmod(target_file, mode & 0o777)
                
    except Exception as e:
        print(f"      ⚠️ 创建文件失败: {e}")
        raise

def extract_logs_from_zip(zip_file, target_dir, service_manifest_data=None):
	"""从zip文件中提取日志文件"""
	extracted_count = 0
	processed_files = set()  # 用于去重
	
	try:
		with zipfile.ZipFile(zip_file, 'r') as zfile:
			# 查找内部zip文件
			zip_files = [f for f in zfile.namelist() if f.endswith('.zip')]
			
			if zip_files:
				# 处理内部zip文件（静默模式）
				for zip_name in zip_files:
					node_id = extract_node_from_zipname(zip_name, service_manifest_data)
					
					# 如果无法提取到有效的节点名，跳过该文件
					if node_id == 'unknown':
						continue
					
					# 创建节点目录
					node_dir = os.path.join(target_dir, node_id)
					os.makedirs(node_dir, exist_ok=True)
					
					try:
						with zfile.open(zip_name) as zip_data:
							with zipfile.ZipFile(zip_data, 'r') as inner_zip:
								for file_info in inner_zip.infolist():
									if file_info.filename.endswith('.log') or file_info.filename.endswith('.log.gz'):
										# 去重检查
										file_key = file_info.filename
										if file_key in processed_files:
											continue
										processed_files.add(file_key)
										
										# 直接使用文件名，不创建服务子目录
										filename = os.path.basename(file_info.filename)
										
										# 创建目标文件路径：直接放在节点目录下
										dst_file = os.path.join(node_dir, filename)
										
										# 解压日志文件
										if file_info.filename.endswith('.log.gz'):
											# 处理压缩日志
											with inner_zip.open(file_info.filename) as gz_file:
												with gzip.open(gz_file, 'rt') as gz:
													content = gz.read()
													# 去掉.gz后缀
													dst_file = dst_file[:-3]
													with open(dst_file, 'w', encoding='utf-8') as f:
														f.write(content)
										else:
											# 处理普通日志
											with inner_zip.open(file_info.filename) as src_file:
												with open(dst_file, 'wb') as dst_file_obj:
													shutil.copyfileobj(src_file, dst_file_obj)
										
										# 设置时间戳和权限
										create_file_with_timestamp(file_info, dst_file, inner_zip=inner_zip, filename=file_info.filename)
										
										extracted_count += 1
					except Exception:
						# 静默跳过单个内部zip错误
						continue
	except Exception as e:
		print(f"    ❌ 处理zip文件失败: {e}")
	
	return extracted_count

def get_bundle_type(service_manifest_path):
    """从service_manifest.json中获取bundle类型"""
    try:
        with open(service_manifest_path, 'r') as f:
            data = json.load(f)
            service_type = data.get('service_type', 'unknown')
            return service_type
    except Exception as e:
        print(f"    ⚠️ 无法读取bundle类型: {e}")
        return 'unknown'

def get_output_directory(bundle_type):
    """根据bundle类型确定输出目录"""
    if bundle_type == 'jfxr':
        return './xray'
    elif bundle_type == 'jfrt':
        return './artifactory'
    else:
        return './unknown'  # 默认使用artifactory目录

def main():
    """主函数"""
    # 极简输出：每个bundle一行，总结一行
    # 查找所有zip文件
    zip_files = [f for f in os.listdir('.') if f.endswith('.zip')]
    
    if not zip_files:
        print("❌ 未找到zip文件")
        return
    
    total_extracted = 0
    
    for zip_file in zip_files:
        # 读取service_manifest.json来确定bundle类型
        bundle_type = 'unknown'
        service_manifest_data = None
        try:
            with zipfile.ZipFile(zip_file, 'r') as z:
                if 'service_manifest.json' in z.namelist():
                    with z.open('service_manifest.json') as f:
                        data = json.load(f)
                        bundle_type = data.get('service_type', 'unknown')
                        service_manifest_data = data
                        # 复制service_manifest.json到输出目录（静默）
                        target_dir = get_output_directory(bundle_type)
                        os.makedirs(target_dir, exist_ok=True)
                        dst = os.path.join(target_dir, 'service_manifest.json')
                        with z.open('service_manifest.json') as fsrc, open(dst, 'wb') as fdst:
                            shutil.copyfileobj(fsrc, fdst)
                        zip_info = z.getinfo('service_manifest.json')
                        preserve_file_attributes(zip_info, dst)
        except Exception:
            # 静默
            pass
        
        target_dir = get_output_directory(bundle_type)
        os.makedirs(target_dir, exist_ok=True)
        
        extracted = extract_logs_from_zip(zip_file, target_dir, service_manifest_data)
        total_extracted += extracted
        
        # 极简每个bundle输出
        print(f"✅ {os.path.basename(zip_file)} -> {target_dir} | 文件: {extracted}")
    
    # 极简汇总
    print(f"✅ 总计 | bundles: {len(zip_files)} | files: {total_extracted}")

if __name__ == "__main__":
    main()