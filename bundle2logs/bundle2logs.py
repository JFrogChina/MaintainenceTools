import os
import zipfile
import glob
import shutil
import gzip
import re
import sys

def extract_logs_from_zip(zfile, target_dir):
    try:
        with zipfile.ZipFile(zfile, 'r') as z:
            for name in z.namelist():
                if name.endswith('.zip'):
                    sub_tmp = '__subtmp__'
                    os.makedirs(sub_tmp, exist_ok=True)
                    z.extract(name, sub_tmp)
                    sub_path = os.path.join(sub_tmp, name)
                    m = re.search(r'_([^_]+)_(analysis|indexer|persist|policyenforcer|router|sbom|server)\.zip$', name)
                    subdir = m.group(1) if m else os.path.splitext(os.path.basename(name))[0]
                    outdir = os.path.join(target_dir, subdir)
                    os.makedirs(outdir, exist_ok=True)
                    with zipfile.ZipFile(sub_path, 'r') as z2:
                        for n2 in z2.namelist():
                            if '/logs/' in n2 and (n2.endswith('.log') or n2.endswith('.gz')):
                                dst = os.path.join(outdir, os.path.basename(n2))
                                if not os.path.exists(dst):
                                    with z2.open(n2) as fsrc, open(dst, 'wb') as fdst:
                                        shutil.copyfileobj(fsrc, fdst)
                                    print(f"  解压: {dst}")
                                    if dst.endswith('.gz'):
                                        try:
                                            with gzip.open(dst, 'rb') as f_in, open(dst[:-3], 'wb') as f_out:
                                                shutil.copyfileobj(f_in, f_out)
                                            print(f"  解压gz: {dst[:-3]}")
                                            os.remove(dst)
                                        except Exception as e:
                                            print(f"  解压gz失败: {dst}, {e}")
                    os.remove(sub_path)
                    shutil.rmtree(sub_tmp)
                elif '/logs/' in name and (name.endswith('.log') or name.endswith('.gz')):
                    prefix = os.path.splitext(os.path.basename(zfile))[0]
                    outdir = os.path.join(target_dir, prefix)
                    os.makedirs(outdir, exist_ok=True)
                    dst = os.path.join(outdir, os.path.basename(name))
                    if not os.path.exists(dst):
                        with z.open(name) as fsrc, open(dst, 'wb') as fdst:
                            shutil.copyfileobj(fsrc, fdst)
                        print(f"  解压: {dst}")
                        if dst.endswith('.gz'):
                            try:
                                with gzip.open(dst, 'rb') as f_in, open(dst[:-3], 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                                print(f"  解压gz: {dst[:-3]}")
                                os.remove(dst)
                            except Exception as e:
                                print(f"  解压gz失败: {dst}, {e}")
    except Exception as e:
        print(f"处理 {zfile} 失败: {e}")

def main():
    SRC_DIR = '.'
    DST_XRAY = './xray'
    DST_ART = './artifactory'
    os.makedirs(DST_XRAY, exist_ok=True)
    os.makedirs(DST_ART, exist_ok=True)

    for zfile in glob.glob(os.path.join(SRC_DIR, '*.zip')):
        lower_name = zfile.lower()
        print(f"处理：{zfile}")
        if 'jfxr' in lower_name:
            extract_logs_from_zip(zfile, DST_XRAY)
        elif 'artifactory' in lower_name:
            extract_logs_from_zip(zfile, DST_ART)
        else:
            print(f"  跳过（不是xray或artifactory相关）：{zfile}")

    print("处理完成！日志已整理到 ./xray 和 ./artifactory")

if __name__ == '__main__':
    main()