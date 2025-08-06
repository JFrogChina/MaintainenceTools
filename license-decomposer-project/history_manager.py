import json
import os
import shutil
import base64
import hashlib
from datetime import datetime


class HistoryManager:
    """历史记录管理器 - 管理成功分解记录的保存和加载"""
    
    def __init__(self):
        # 使用用户主目录下的.license_splitter目录存储历史记录
        app_data_dir = os.path.expanduser("~/.license_splitter")
        self.history_dir = os.path.join(app_data_dir, "history")
        self.history_file = os.path.join(self.history_dir, "history.json")
        self.ensure_history_dir()
    
    def ensure_history_dir(self):
        """确保history目录存在"""
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir, exist_ok=True)
    
    def save_success_record(self, original_filepath, password, licenses):
        """保存成功记录，避免重复保存相同的文件+密码组合"""
        try:
            filename = os.path.basename(original_filepath)
            password_encoded = base64.b64encode(password.encode()).decode()
            
            # 检查是否已存在相同的文件名+密码组合
            existing_record = self.find_existing_record(filename, password_encoded)
            
            if existing_record:
                # 存在相同记录：只更新时间戳和许可证数量
                self.update_existing_record(existing_record['id'], licenses)
                return "updated"
            else:
                # 新记录：复制文件并创建记录
                return self.create_new_record(original_filepath, password, licenses)
                
        except Exception as e:
            pass
            return "failed"
    
    def find_existing_record(self, filename, password_encoded):
        """查找是否存在相同的文件名+密码组合"""
        history = self.load_history()
        for record in history.get('records', []):
            if (record['filename'] == filename and 
                record['password'] == password_encoded):
                return record
        return None
    
    def update_existing_record(self, record_id, licenses):
        """更新现有记录的时间戳和许可证数量"""
        history = self.load_history()
        for record in history['records']:
            if record['id'] == record_id:
                record['timestamp'] = datetime.now().isoformat()
                record['license_count'] = len(licenses)
                break
        
        self.save_history(history)
    
    def create_new_record(self, original_filepath, password, licenses):
        """创建新的历史记录"""
        try:
            filename = os.path.basename(original_filepath)
            target_path = os.path.join(self.history_dir, filename)
            
            # 处理文件名冲突（不同密码的同名文件）
            if os.path.exists(target_path):
                # 检查是否是同一个文件（通过内容hash）
                if not self.is_same_file_content(original_filepath, target_path):
                    # 不同内容：重命名新文件
                    name, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{name}_{timestamp}{ext}"
                    target_path = os.path.join(self.history_dir, filename)
            
            # 复制文件到history目录
            shutil.copy2(original_filepath, target_path)
            
            # 创建记录
            record = {
                'id': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'filename': filename,
                'password': base64.b64encode(password.encode()).decode(),
                'timestamp': datetime.now().isoformat(),
                'license_count': len(licenses)
            }
            
            self.append_to_history(record)
            return "created"
            
        except Exception as e:
            pass
            return "failed"
    
    def is_same_file_content(self, file1, file2):
        """比较两个文件内容是否相同"""
        def get_file_hash(filepath):
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        
        try:
            return get_file_hash(file1) == get_file_hash(file2)
        except:
            return False
    
    def load_history(self):
        """加载历史记录"""
        if not os.path.exists(self.history_file):
            return {"records": []}
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            pass
            return {"records": []}
    
    def save_history(self, history_data):
        """保存历史记录到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
            pass
    
    def append_to_history(self, record):
        """追加新记录到历史记录"""
        history = self.load_history()
        history['records'].append(record)
        self.save_history(history)
    
    def get_sorted_history(self):
        """获取按时间排序的历史记录（最新在前）"""
        history = self.load_history()
        records = history.get('records', [])
        
        # 按时间戳降序排序
        return sorted(records, 
                     key=lambda x: x['timestamp'], 
                     reverse=True)
    
    def clear_history(self):
        """清空所有历史记录和文件"""
        try:
            # 删除所有历史文件
            for filename in os.listdir(self.history_dir):
                if filename != "history.json":
                    file_path = os.path.join(self.history_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            
            # 清空JSON记录
            self.save_history({"records": []})
            print("🗑️ 历史记录已清空")
            return True
            
        except Exception as e:
            pass
            return False
    
    def delete_record(self, record_id):
        """删除单个历史记录"""
        try:
            history = self.load_history()
            record_to_delete = None
            
            # 找到要删除的记录
            for record in history['records']:
                if record['id'] == record_id:
                    record_to_delete = record
                    break
            
            if not record_to_delete:
                return False
            
            # 删除文件
            file_path = os.path.join(self.history_dir, record_to_delete['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 从记录中删除
            history['records'] = [r for r in history['records'] if r['id'] != record_id]
            self.save_history(history)
            
            return True
            
        except Exception as e:
            pass
            return False
    
    def get_record_filepath(self, record):
        """获取历史记录对应的文件完整路径"""
        return os.path.join(self.history_dir, record['filename'])
    
    def decode_password(self, record):
        """解码历史记录中的密码"""
        try:
            return base64.b64decode(record['password']).decode()
        except Exception as e:
            pass
            return None
