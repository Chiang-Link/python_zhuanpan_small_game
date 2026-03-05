from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import threading
import time
from platform_sync import PlatformSync, PlatformConfig

app = Flask(__name__)
CORS(app)


# 数据存储文件
DATA_FILE = 'tasks.json'

class TaskManager:
    def __init__(self):
        self.tasks = self.load_tasks()
        self.reminder_thread = None
        self.sync_thread = None
        self.platform_sync = PlatformSync()
        self.platform_config = PlatformConfig()
        self.start_reminder_check()
        self.start_auto_sync()

    def load_tasks(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_tasks(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

    def add_task(self, title, description="", priority="medium", deadline="", platform="手动添加", url="", course=""):
        # 检查是否已存在相同的任务
        existing_task = self.find_existing_task(title, platform)
        if existing_task:
            return existing_task
        
        task = {
            'id': int(time.time() * 1000),
            'title': title,
            'description': description,
            'priority': priority,
            'deadline': deadline,
            'completed': False,
            'created_at': datetime.now().isoformat(),
            'platform': platform,
            'url': url,
            'course': course
        }
        self.tasks.insert(0, task)
        self.save_tasks()
        return task

    def find_existing_task(self, title, platform):
        """查找是否已存在相同标题和平台的任务"""
        for task in self.tasks:
            if (task['title'] == title and 
                task.get('platform') == platform and 
                not task['completed']):
                return task
        return None

    def toggle_task(self, task_id):
        for task in self.tasks:
            if task['id'] == task_id:
                task['completed'] = not task['completed']
                if task['completed']:
                    task['completed_at'] = datetime.now().isoformat()
                else:
                    task.pop('completed_at', None)
                self.save_tasks()
                return task
        return None

    def delete_task(self, task_id):
        for i, task in enumerate(self.tasks):
            if task['id'] == task_id:
                deleted_task = self.tasks.pop(i)
                self.save_tasks()
                return deleted_task
        return None

    def get_tasks(self, filter_type='all'):
        if filter_type == 'completed':
            return [task for task in self.tasks if task['completed']]
        elif filter_type == 'pending':
            return [task for task in self.tasks if not task['completed']]
        return self.tasks

    def get_statistics(self):
        total = len(self.tasks)
        completed = len([task for task in self.tasks if task['completed']])
        pending = total - completed
        rate = round((completed / total) * 100) if total > 0 else 0
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'rate': rate
        }

    def sync_platform_tasks(self, platforms=None):
        """同步平台任务"""
        try:
            credentials = {}
            if platforms:
                for platform in platforms:
                    config = self.platform_config.get_platform_config(platform)
                    if config.get('credentials'):
                        credentials[platform] = config['credentials']
            
            sync_tasks = self.platform_sync.sync_all_platforms(credentials)
            added_tasks = []
            
            for task_data in sync_tasks:
                # 确定优先级
                priority = task_data.get('priority', 'medium')
                
                # 添加到任务列表
                new_task = self.add_task(
                    title=task_data['title'],
                    description=task_data.get('description', ''),
                    priority=priority,
                    deadline=task_data.get('deadline', ''),
                    platform=task_data.get('platform', '未知平台'),
                    url=task_data.get('url', ''),
                    course=task_data.get('course', '')
                )
                
                if new_task:
                    added_tasks.append(new_task)
            
            # 更新最后同步时间
            self.platform_config.config['last_sync'] = datetime.now().isoformat()
            self.platform_config.save_config()
            
            return {
                'success': True,
                'added_count': len(added_tasks),
                'tasks': added_tasks
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def update_platform_credentials(self, platform, username, password):
        """更新平台凭据"""
        try:
            self.platform_config.update_credentials(platform, username, password)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_platform_status(self):
        """获取平台状态"""
        status = {}
        for platform_name, config in self.platform_config.config['platforms'].items():
            status[platform_name] = {
                'enabled': config.get('enabled', False),
                'auto_sync': config.get('auto_sync', False),
                'has_credentials': bool(config.get('credentials')),
                'last_sync': self.platform_config.config.get('last_sync')
            }
        return status

    def check_reminders(self):
        now = datetime.now()
        reminders = []
        
        for task in self.tasks:
            if task['completed'] or not task['deadline']:
                continue
                
            try:
                deadline = datetime.fromisoformat(task['deadline'].replace('Z', '+00:00'))
                time_diff = deadline - now
                
                if time_diff.total_seconds() > 0 and time_diff.total_seconds() <= 3600:
                    hours = int(time_diff.total_seconds() // 3600)
                    minutes = int((time_diff.total_seconds() % 3600) // 60)
                    
                    platform_info = f" [{task.get('platform', '')}]" if task.get('platform') else ""
                    
                    if hours == 0 and minutes <= 5:
                        reminders.append({
                            'type': 'urgent',
                            'title': '紧急提醒',
                            'message': f'任务"{task["title"]}"{platform_info}将在{minutes}分钟后到期！'
                        })
                    elif hours == 0:
                        reminders.append({
                            'type': 'normal',
                            'title': '提醒',
                            'message': f'任务"{task["title"]}"{platform_info}将在{minutes}分钟后到期'
                        })
                    else:
                        reminders.append({
                            'type': 'normal',
                            'title': '提醒',
                            'message': f'任务"{task["title"]}"{platform_info}将在{hours}小时后到期'
                        })
                elif time_diff.total_seconds() <= 0:
                    overdue_hours = abs(int(time_diff.total_seconds() // 3600))
                    if overdue_hours <= 1:
                        platform_info = f" [{task.get('platform', '')}]" if task.get('platform') else ""
                        reminders.append({
                            'type': 'overdue',
                            'title': '逾期提醒',
                            'message': f'任务"{task["title"]}"{platform_info}已逾期，请尽快完成！'
                        })
            except:
                continue
                
        return reminders

    def start_reminder_check(self):
        def reminder_loop():
            while True:
                time.sleep(60)  # 每分钟检查一次
                self.check_reminders()
        
        if not self.reminder_thread:
            self.reminder_thread = threading.Thread(target=reminder_loop, daemon=True)
            self.reminder_thread.start()

    def start_auto_sync(self):
        """启动自动同步"""
        def auto_sync_loop():
            while True:
                try:
                    # 检查是否需要自动同步
                    for platform_name, config in self.platform_config.config['platforms'].items():
                        if config.get('enabled') and config.get('auto_sync'):
                            # 每小时同步一次
                            time.sleep(3600)
                            self.sync_platform_tasks([platform_name])
                except Exception as e:
                    print(f"自动同步失败: {e}")
                    time.sleep(300)  # 出错后5分钟后重试
        
        if not self.sync_thread:
            self.sync_thread = threading.Thread(target=auto_sync_loop, daemon=True)
            self.sync_thread.start()

# 初始化任务管理器
task_manager = TaskManager()

# API路由
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/styles.css')
def styles():
    return send_from_directory('.', 'styles.css')

@app.route('/script.js')
def script():
    return send_from_directory('.', 'script.js')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    filter_type = request.args.get('filter', 'all')
    tasks = task_manager.get_tasks(filter_type)
    return jsonify(tasks)

# 移除手动添加任务的API，专注于自动同步
@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    task = task_manager.toggle_task(task_id)
    if task:
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = task_manager.delete_task(task_id)
    if task:
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    stats = task_manager.get_statistics()
    return jsonify(stats)

@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    reminders = task_manager.check_reminders()
    return jsonify(reminders)

# 平台同步相关API
@app.route('/api/sync/platforms', methods=['POST'])
def sync_platforms():
    data = request.get_json()
    platforms = data.get('platforms', ['xuexitong', 'touge'])
    result = task_manager.sync_platform_tasks(platforms)
    return jsonify(result)

@app.route('/api/platform/credentials', methods=['POST'])
def update_platform_credentials():
    data = request.get_json()
    platform = data.get('platform')
    username = data.get('username')
    password = data.get('password')
    
    if not all([platform, username, password]):
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = task_manager.update_platform_credentials(platform, username, password)
    return jsonify(result)

@app.route('/api/platform/status', methods=['GET'])
def get_platform_status():
    status = task_manager.get_platform_status()
    return jsonify(status)

@app.route('/api/platform/config', methods=['GET'])
def get_platform_config():
    return jsonify(task_manager.platform_config.config)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)