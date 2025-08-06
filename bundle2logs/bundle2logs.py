import os
import zipfile
import glob
import shutil
import gzip
import re
import sys

def extract_logs_from_zip(zfile, target_dir):
    extracted_count = 0
    try:
        with zipfile.ZipFile(zfile, 'r') as z:
            zip_files = [name for name in z.namelist() if name.endswith('.zip')]
            print(f"  发现 {len(zip_files)} 个内部zip文件")
            for name in z.namelist():
                if name.endswith('.zip'):
                    sub_tmp = '__subtmp__'
                    os.makedirs(sub_tmp, exist_ok=True)
                    z.extract(name, sub_tmp)
                    sub_path = os.path.join(sub_tmp, name)
                    # 提取节点ID和服务名
                    # 实际格式: service/uptime..._jfxx@xxx_service-artXX.zip
                    m1 = re.search(r'_(jf\w+)@[^_]+_(.+)-(art\d+)\.zip$', name)
                    
                    if m1:
                        subdir = m1.group(3)  # 节点ID: art01, art02
                        service_name = m1.group(2)  # 服务名: event, artifactory 等
                        print(f"    [{service_name}] -> 节点: {subdir}")
                    else:
                        # fallback: 使用文件名
                        subdir = os.path.splitext(os.path.basename(name))[0]
                        service_name = "unknown"
                        print(f"    [fallback] -> 目录: {subdir}")
                    outdir = os.path.join(target_dir, subdir)
                    os.makedirs(outdir, exist_ok=True)
                    with zipfile.ZipFile(sub_path, 'r') as z2:
                        for n2 in z2.namelist():
                            if '/logs/' in n2 and (n2.endswith('.log') or n2.endswith('.gz')):
                                base_name = os.path.basename(n2)
                                
                                # 处理文件名冲突：如果文件已存在，添加服务前缀
                                dst = os.path.join(outdir, base_name)
                                if os.path.exists(dst) and service_name != "unknown":
                                    name_parts = os.path.splitext(base_name)
                                    dst = os.path.join(outdir, f"{service_name}_{name_parts[0]}{name_parts[1]}")
                                
                                if not os.path.exists(dst):
                                    with z2.open(n2) as fsrc, open(dst, 'wb') as fdst:
                                        shutil.copyfileobj(fsrc, fdst)
                                    print(f"      + {os.path.basename(dst)}")
                                    extracted_count += 1
                                    
                                    if dst.endswith('.gz'):
                                        try:
                                            unzipped_dst = dst[:-3]
                                            with gzip.open(dst, 'rb') as f_in, open(unzipped_dst, 'wb') as f_out:
                                                shutil.copyfileobj(f_in, f_out)
                                            print(f"      + {os.path.basename(unzipped_dst)} (解压)")
                                            os.remove(dst)
                                        except Exception as e:
                                            print(f"      ! 解压gz失败: {os.path.basename(dst)}")
                                else:
                                    print(f"      - {os.path.basename(dst)} (跳过，已存在)")
                    os.remove(sub_path)
                    shutil.rmtree(sub_tmp)
                elif '/logs/' in name and (name.endswith('.log') or name.endswith('.gz')):
                    prefix = os.path.splitext(os.path.basename(zfile))[0]
                    print(f"    直接日志文件: {name} -> 目录: {prefix}")
                    outdir = os.path.join(target_dir, prefix)
                    os.makedirs(outdir, exist_ok=True)
                    dst = os.path.join(outdir, os.path.basename(name))
                    if not os.path.exists(dst):
                        with z.open(name) as fsrc, open(dst, 'wb') as fdst:
                            shutil.copyfileobj(fsrc, fdst)
                        print(f"      + {os.path.basename(dst)}")
                        extracted_count += 1
                        if dst.endswith('.gz'):
                            try:
                                unzipped_dst = dst[:-3]
                                with gzip.open(dst, 'rb') as f_in, open(unzipped_dst, 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                                print(f"      + {os.path.basename(unzipped_dst)} (解压)")
                                os.remove(dst)
                            except Exception as e:
                                print(f"      ! 解压gz失败: {os.path.basename(dst)}")
    except Exception as e:
        print(f"处理 {zfile} 失败: {e}")
    
    return extracted_count

def main():
    """
    支持的文件名模式:
    - Xray: 包含 'jfxr' 或 'xray' 的文件
    - Artifactory: 包含 'artifactory', 'jfrt', 或 'jfrog' 的文件
    """
    SRC_DIR = '.'
    DST_XRAY = './xray'
    DST_ART = './artifactory'
    os.makedirs(DST_XRAY, exist_ok=True)
    os.makedirs(DST_ART, exist_ok=True)

    total_extracted = 0
    processed_files = 0
    
    for zfile in glob.glob(os.path.join(SRC_DIR, '*.zip')):
        lower_name = zfile.lower()
        print(f"\n📦 处理：{os.path.basename(zfile)}")
        
        if 'jfxr' in lower_name or 'xray' in lower_name:
            count = extract_logs_from_zip(zfile, DST_XRAY)
            total_extracted += count
            processed_files += 1
        elif 'artifactory' in lower_name or 'jfrt' in lower_name or 'jfrog' in lower_name:
            count = extract_logs_from_zip(zfile, DST_ART)
            total_extracted += count
            processed_files += 1
        else:
            print(f"  ⏭️  跳过（不是JFrog相关产品）")

    print(f"\n✅ 处理完成！")
    print(f"📊 统计信息:")
    print(f"   - 处理的bundle文件: {processed_files}")
    print(f"   - 提取的日志文件: {total_extracted}")
    print(f"   - 输出目录: ./xray 和 ./artifactory")

if __name__ == '__main__':
    main()