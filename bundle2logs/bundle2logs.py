import os
import zipfile
import glob
import shutil
import gzip
import re
import sys
import stat
import json
from datetime import datetime

def extract_node_id_and_service(filename):
    """提取节点ID和服务名"""
    # 格式1: Xray格式 - service/uptime..._jfxx@xxx_service-artXX.zip
    m1 = re.search(r'_(jf\w+)@[^_]+_(.+)-(art\d+)\.zip$', filename)
    if m1:
        node_id = m1.group(3)  # 节点ID: art01, art02
        service_name = m1.group(2)  # 服务名: event, artifactory 等
        return node_id, service_name
    
    # 格式2: Artifactory格式 - access/20250422-1745315574886_jfac@01ht4ha7j4nj61018r1w390nbk_access-art1_normal.zip
    m2 = re.search(r'_jf\w+@[^_]+_(.+)-art(\d+)_normal\.zip$', filename)
    if m2:
        node_id = f"art{m2.group(2)}"  # 节点ID: art1, art2
        service_name = m2.group(1)  # 服务名: access, artifactory 等
        return node_id, service_name
    
    # 格式3: 其他Artifactory格式 - 尝试提取art数字
    m3 = re.search(r'-art(\d+)', filename, re.IGNORECASE)
    if m3:
        node_id = f"art{m3.group(1)}"
        service_name = "unknown"
        return node_id, service_name
    
    # 格式4: Xray格式 - 尝试提取JFGXRAY数字
    m4 = re.search(r'JFGXRAY(\d+)', filename, re.IGNORECASE)
    if m4:
        node_id = f"JFGXRAY{m4.group(1)}"
        service_name = "unknown"
        return node_id, service_name
    
    # 格式5: 当前Xray格式 - 202506301954-jfxr_jfxr_jfxr@01jyzqcswws3qswcqxdpmtm0p2.zip
    m5 = re.search(r'jfxr.*jfxr.*jfxr@([^.]+)', filename, re.IGNORECASE)
    if m5:
        # 对于这种格式，我们无法从文件名提取有意义的节点ID，但可以识别服务类型
        service_name = "xray"
        return None, service_name
    
    # 格式6: 其他无法识别的格式
    return None, "unknown"

def parse_service_manifest(manifest_content):
    """解析service_manifest.json，提取节点和服务信息"""
    try:
        data = json.loads(manifest_content)
        if 'microservices' in data:
            # 提取所有节点名称
            nodes = set()
            services = {}
            
            for service_name, service_info in data['microservices'].items():
                if isinstance(service_info, dict):
                    for node_name in service_info.keys():
                        # 处理不同的节点命名格式
                        if '_normal' in node_name:
                            # Artifactory格式: art1_normal -> art1
                            node_id = node_name.replace('_normal', '')
                            nodes.add(node_id)
                        elif node_name.startswith('jfrog'):
                            # Xray格式: jfrogxap02 -> jfrogxap02
                            node_id = node_name
                            nodes.add(node_id)
                        elif node_name.startswith('art'):
                            # Artifactory格式: art1 -> art1
                            node_id = node_name
                            nodes.add(node_id)
                        else:
                            # 其他格式，直接使用
                            node_id = node_name
                            nodes.add(node_id)
                        
                        if service_name not in services:
                            services[service_name] = []
                        services[service_name].append(node_id)
            
            return list(nodes), services
    except Exception as e:
        print(f"      ⚠️ 解析service_manifest.json失败: {e}")
    
    return [], {}

def get_node_id_from_manifest(service_name, manifest_nodes, manifest_services):
    """从manifest中获取服务对应的节点ID"""
    if service_name in manifest_services and manifest_services[service_name]:
        # 返回第一个可用的节点ID
        return manifest_services[service_name][0]
    elif manifest_nodes:
        # 如果没有明确的服务映射，返回第一个可用节点
        return manifest_nodes[0]
    return None

def preserve_zip_file_attributes(zip_file, zip_name, dst_path):
    """保留zip内部文件的属性（权限、时间戳等）"""
    try:
        # 获取zip内部文件信息
        zip_info = zip_file.getinfo(zip_name)
        
        # 设置时间戳（zip文件存储的是修改时间）
        if zip_info.date_time:
            # 验证时间戳的有效性
            year, month, day, hour, minute, second = zip_info.date_time
            if 1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                timestamp = datetime(year, month, day, hour, minute, second).timestamp()
                os.utime(dst_path, (timestamp, timestamp))
            else:
                print(f"      ⚠️ 跳过无效时间戳: {zip_info.date_time}")
        
        # 设置权限（zip文件可能不存储权限，使用默认值）
        # 对于日志文件，通常设置为644 (rw-r--r--)
        os.chmod(dst_path, 0o644)
        
    except Exception as e:
        print(f"      ⚠️ 保留文件属性失败: {e}")

def extract_logs_from_zip(zfile, target_dir):
    extracted_count = 0
    manifest_nodes = []
    manifest_services = {}
    
    try:
        with zipfile.ZipFile(zfile, 'r') as z:
            zip_files = [name for name in z.namelist() if name.endswith('.zip')]
            print(f"  发现 {len(zip_files)} 个内部zip文件")
            
            # 首先尝试读取service_manifest.json
            for name in z.namelist():
                if name.endswith('service_manifest.json'):
                    print(f"    📋 发现服务清单文件: {name}")
                    try:
                        with z.open(name) as f:
                            manifest_content = f.read().decode('utf-8')
                            manifest_nodes, manifest_services = parse_service_manifest(manifest_content)
                            if manifest_nodes:
                                print(f"      ✅ 解析到节点: {', '.join(manifest_nodes)}")
                            break
                    except Exception as e:
                        print(f"      ⚠️ 读取service_manifest.json失败: {e}")
            
            # 按节点ID分组
            node_files = {}
            
            for name in z.namelist():
                if name.endswith('.zip'):
                    sub_tmp = '__subtmp__'
                    os.makedirs(sub_tmp, exist_ok=True)
                    z.extract(name, sub_tmp)
                    sub_path = os.path.join(sub_tmp, name)
                    
                    # 优先使用manifest中的节点信息
                    node_id, service_name = extract_node_id_and_service(name)
                    
                    # 如果manifest解析成功，强制使用manifest中的节点ID
                    if manifest_nodes:
                        # 不再使用从文件名提取的节点ID，直接使用manifest中的第一个节点
                        node_id = manifest_nodes[0]
                        print(f"    [{service_name or 'unknown'}] -> 节点: {node_id} (使用manifest)")
                    elif node_id:
                        # 只有在没有manifest信息时才使用文件名提取的节点ID
                        print(f"    [{service_name or 'unknown'}] -> 节点: {node_id} (从文件名)")
                    else:
                        print(f"    [error] 无法识别节点ID: {name}")
                        continue
                    
                    if node_id:
                        print(f"    [{service_name or 'unknown'}] -> 节点: {node_id}")
                        
                        if node_id not in node_files:
                            node_files[node_id] = []
                        node_files[node_id].append((sub_path, service_name))
                    else:
                        print(f"    [error] 无法识别节点ID: {name}")
                        continue
                    
                    # 处理每个内部zip文件
                    with zipfile.ZipFile(sub_path, 'r') as z2:
                        for n2 in z2.namelist():
                            if '/logs/' in n2 and (n2.endswith('.log') or n2.endswith('.gz')):
                                base_name = os.path.basename(n2)
                                
                                # 创建节点目录
                                node_dir = os.path.join(target_dir, node_id)
                                os.makedirs(node_dir, exist_ok=True)
                                
                                # 处理文件名冲突：如果文件已存在，添加服务前缀
                                dst = os.path.join(node_dir, base_name)
                                if os.path.exists(dst) and service_name and service_name != "unknown":
                                    name_parts = os.path.splitext(base_name)
                                    dst = os.path.join(node_dir, f"{service_name}_{name_parts[0]}{name_parts[1]}")
                                elif os.path.exists(dst):
                                    # 如果service_name为None或unknown，使用时间戳避免冲突
                                    name_parts = os.path.splitext(base_name)
                                    timestamp = str(int(datetime.now().timestamp()))[-6:]  # 使用时间戳后6位
                                    dst = os.path.join(node_dir, f"{name_parts[0]}_{timestamp}{name_parts[1]}")
                                
                                if not os.path.exists(dst):
                                    with z2.open(n2) as fsrc, open(dst, 'wb') as fdst:
                                        shutil.copyfileobj(fsrc, fdst)
                                    
                                    # 保留zip内部文件的属性
                                    preserve_zip_file_attributes(z2, n2, dst)
                                    
                                    print(f"      + {os.path.basename(dst)}")
                                    extracted_count += 1
                                    
                                    if dst.endswith('.gz'):
                                        try:
                                            unzipped_dst = dst[:-3]
                                            with gzip.open(dst, 'rb') as f_in, open(unzipped_dst, 'wb') as f_out:
                                                shutil.copyfileobj(f_in, f_out)
                                            
                                            # 保留解压后文件的属性（使用原始gz文件的时间）
                                            preserve_zip_file_attributes(z2, n2, unzipped_dst)
                                            
                                            print(f"      + {os.path.basename(unzipped_dst)} (解压)")
                                            os.remove(dst)
                                        except Exception as e:
                                            print(f"      ! 解压gz失败: {os.path.basename(dst)}")
                                else:
                                    print(f"      - {os.path.basename(dst)} (跳过，已存在)")
                    
                    os.remove(sub_path)
                    shutil.rmtree(sub_tmp)
                elif '/logs/' in name and (name.endswith('.log') or name.endswith('.gz')):
                    # 直接日志文件，尝试从文件名提取节点ID
                    node_id, _ = extract_node_id_and_service(os.path.basename(zfile))
                    if not node_id and manifest_nodes:
                        # 如果无法从文件名提取，尝试从manifest获取
                        node_id = get_node_id_from_manifest("unknown", manifest_nodes, manifest_services)
                    
                    if node_id:
                        node_dir = os.path.join(target_dir, node_id)
                        os.makedirs(node_dir, exist_ok=True)
                        
                        dst = os.path.join(node_dir, os.path.basename(name))
                        if not os.path.exists(dst):
                            with z.open(name) as fsrc, open(dst, 'wb') as fdst:
                                shutil.copyfileobj(fsrc, fdst)
                            
                            # 保留zip内部文件的属性
                            preserve_zip_file_attributes(z, name, dst)
                            
                            print(f"      + {os.path.basename(dst)}")
                            extracted_count += 1
                            
                            if dst.endswith('.gz'):
                                try:
                                    unzipped_dst = dst[:-3]
                                    with gzip.open(dst, 'rb') as f_in, open(unzipped_dst, 'wb') as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                                    
                                    # 保留解压后文件的属性
                                    preserve_zip_file_attributes(z, name, unzipped_dst)
                                    
                                    print(f"      + {os.path.basename(unzipped_dst)} (解压)")
                                    os.remove(dst)
                                except Exception as e:
                                    print(f"      ! 解压gz失败: {os.path.basename(dst)}")
                
                # 提取service_manifest.json文件
                elif name.endswith('service_manifest.json'):
                    print(f"    📋 发现服务清单文件: {name}")
                    
                    # 只复制到根目录，避免重复
                    dst = os.path.join(target_dir, 'service_manifest.json')
                    if not os.path.exists(dst):
                        with z.open(name) as fsrc, open(dst, 'wb') as fdst:
                            shutil.copyfileobj(fsrc, fdst)
                        
                        # 保留zip内部文件的属性
                        preserve_zip_file_attributes(z, name, dst)
                        
                        print(f"      + service_manifest.json (根目录)")
                        extracted_count += 1
                    else:
                        print(f"      - service_manifest.json (跳过，已存在)")
    except Exception as e:
        print(f"处理 {zfile} 失败: {e}")
    
    return extracted_count

def detect_bundle_type(zip_file):
    """检测zip包的类型（Xray或Artifactory）"""
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            # 检查是否包含service_manifest.json
            if 'service_manifest.json' in z.namelist():
                # 读取并解析manifest
                with z.open('service_manifest.json') as f:
                    manifest_content = f.read().decode('utf-8')
                    data = json.loads(manifest_content)
                    
                    # 根据manifest内容判断类型
                    if 'service_type' in data:
                        return data['service_type']  # 'jfxr' 或 'jfrt'
                    elif 'microservices' in data:
                        # 通过服务类型判断
                        services = list(data['microservices'].keys())
                        if any(s in ['analysis', 'indexer', 'persist'] for s in services):
                            return 'jfxr'  # Xray服务
                        elif any(s in ['access', 'artifactory', 'router'] for s in services):
                            return 'jfrt'  # Artifactory服务
        return 'unknown'
    except Exception as e:
        return 'unknown'

def main():
    """
    支持的文件名模式:
    - 自动检测: 基于zip包内容和service_manifest.json判断类型
    - 不再依赖文件名关键词
    """
    SRC_DIR = '.'
    DST_XRAY = './xray'
    DST_ART = './artifactory'
    
    # 获取所有zip文件
    zip_files = glob.glob(os.path.join(SRC_DIR, '*.zip'))
    
    # 根据内容自动检测bundle类型
    xray_files = []
    art_files = []
    
    for zip_file in zip_files:
        bundle_type = detect_bundle_type(zip_file)
        if bundle_type == 'jfxr':
            xray_files.append(zip_file)
            print(f"🔍 检测到Xray bundle: {os.path.basename(zip_file)}")
        elif bundle_type == 'jfrt':
            art_files.append(zip_file)
            print(f"🔍 检测到Artifactory bundle: {os.path.basename(zip_file)}")
        else:
            print(f"⚠️ 无法识别的bundle类型: {os.path.basename(zip_file)}")
    
    total_extracted = 0
    processed_files = 0
    
    # 处理Xray文件
    for zfile in xray_files:
        print(f"\n📦 处理Xray bundle：{os.path.basename(zfile)}")
        os.makedirs(DST_XRAY, exist_ok=True)
        count = extract_logs_from_zip(zfile, DST_XRAY)
        total_extracted += count
        processed_files += 1
    
    # 处理Artifactory文件
    for zfile in art_files:
        print(f"\n📦 处理Artifactory bundle：{os.path.basename(zfile)}")
        os.makedirs(DST_ART, exist_ok=True)
        count = extract_logs_from_zip(zfile, DST_ART)
        total_extracted += count
        processed_files += 1

    print(f"\n✅ 处理完成！")
    print(f"📊 统计信息:")
    print(f"   - 处理的bundle文件: {processed_files}")
    print(f"   - 提取的日志文件: {total_extracted}")
    
    if xray_files:
        print(f"   - Xray输出目录: {DST_XRAY}")
    if art_files:
        print(f"   - Artifactory输出目录: {DST_ART}")

if __name__ == '__main__':
    main()