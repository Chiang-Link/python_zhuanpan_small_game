import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
import time
import json
from datetime import datetime, timedelta
import re

class PlatformSync:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random
        })

    def get_xuexitong_tasks(self, username=None, password=None):
        """
        获取学习通未完成任务
        需要登录凭据或已登录的session
        """
        tasks = []
        
        try:
            # 学习通API接口（需要根据实际情况调整）
            # 这里提供两种方式：API调用和网页爬取
            
            # 方式1：API调用（如果有官方API）
            api_url = "https://api.xuexitong.com/api/v1/tasks/pending"
            
            # 方式2：网页爬取
            login_url = "https://passport2.chaoxing.com/login"
            tasks_url = "https://i.chaoxing.com/base"
            
            # 模拟获取任务数据
            mock_tasks = [
                {
                    'title': '《计算机网络》第三章作业',
                    'description': '完成第三章课后习题1-10题',
                    'platform': '学习通',
                    'deadline': (datetime.now() + timedelta(days=3)).isoformat(),
                    'priority': 'high',
                    'url': 'https://study.chaoxing.com/course/123456',
                    'course': '计算机网络'
                },
                {
                    'title': '《数据结构》期中考试',
                    'description': '线上期中考试，涵盖前五章内容',
                    'platform': '学习通',
                    'deadline': (datetime.now() + timedelta(days=7)).isoformat(),
                    'priority': 'high',
                    'url': 'https://study.chaoxing.com/exam/789012',
                    'course': '数据结构'
                },
                {
                    'title': '《操作系统》视频观看',
                    'description': '观看第五章进程管理视频课程',
                    'platform': '学习通',
                    'deadline': (datetime.now() + timedelta(days=5)).isoformat(),
                    'priority': 'medium',
                    'url': 'https://study.chaoxing.com/video/345678',
                    'course': '操作系统'
                }
            ]
            
            tasks.extend(mock_tasks)
            
        except Exception as e:
            print(f"获取学习通任务失败: {e}")
            
        return tasks

    def get_touge_tasks(self, username=None, password=None):
        """
        获取头歌未完成任务
        头歌(编程实训平台)任务获取
        """
        tasks = []
        
        try:
            # 头歌相关URL
            login_url = "https://www.educoder.net/users/sign_in"
            tasks_url = "https://www.educoder.net/users/my_tasks"
            
            # 模拟获取头歌任务数据
            mock_tasks = [
                {
                    'title': 'Python基础练习 - 循环结构',
                    'description': '完成Python循环结构相关编程练习',
                    'platform': '头歌',
                    'deadline': (datetime.now() + timedelta(days=2)).isoformat(),
                    'priority': 'medium',
                    'url': 'https://www.educoder.net/tasks/456789',
                    'course': 'Python编程基础'
                },
                {
                    'title': '数据结构实验 - 链表操作',
                    'description': '实现单链表的基本操作：插入、删除、查找',
                    'platform': '头歌',
                    'deadline': (datetime.now() + timedelta(days=4)).isoformat(),
                    'priority': 'high',
                    'url': 'https://www.educoder.net/tasks/234567',
                    'course': '数据结构与算法'
                },
                {
                    'title': 'Web开发实训 - HTML/CSS',
                    'description': '完成个人主页的HTML和CSS布局',
                    'platform': '头歌',
                    'deadline': (datetime.now() + timedelta(days=6)).isoformat(),
                    'priority': 'low',
                    'url': 'https://www.educoder.net/tasks/890123',
                    'course': 'Web前端开发'
                }
            ]
            
            tasks.extend(mock_tasks)
            
        except Exception as e:
            print(f"获取头歌任务失败: {e}")
            
        return tasks

    def sync_all_platforms(self, credentials=None):
        """
        同步所有平台的任务
        credentials: 包含各平台登录信息的字典
        """
        all_tasks = []
        
        # 获取学习通任务
        xuexitong_creds = credentials.get('xuexitong') if credentials else None
        xuexitong_tasks = self.get_xuexitong_tasks(
            xuexitong_creds.get('username') if xuexitong_creds else None,
            xuexitong_creds.get('password') if xuexitong_creds else None
        )
        all_tasks.extend(xuexitong_tasks)
        
        # 获取头歌任务
        touge_creds = credentials.get('touge') if credentials else None
        touge_tasks = self.get_touge_tasks(
            touge_creds.get('username') if touge_creds else None,
            touge_creds.get('password') if touge_creds else None
        )
        all_tasks.extend(touge_tasks)
        
        return all_tasks

    def selenium_login_xuexitong(self, username, password):
        """
        使用Selenium登录学习通（用于需要动态登录的情况）
        """
        options = Options()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.get("https://passport2.chaoxing.com/login")
            
            # 等待页面加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "phone"))
            )
            
            # 输入用户名密码
            driver.find_element(By.ID, "phone").send_keys(username)
            driver.find_element(By.ID, "pwd").send_keys(password)
            driver.find_element(By.ID, "loginBtn").click()
            
            # 等待登录成功
            time.sleep(3)
            
            # 获取cookies
            cookies = driver.get_cookies()
            
            driver.quit()
            
            return cookies
            
        except Exception as e:
            print(f"Selenium登录失败: {e}")
            return None

    def parse_deadline(self, deadline_text):
        """
        解析截止时间文本为标准格式
        """
        try:
            # 支持多种时间格式
            patterns = [
                r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2})',
                r'(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{1,2})',
                r'(\d{1,2})天后',
                r'明天|今天'
            ]
            
            current_time = datetime.now()
            
            for pattern in patterns:
                match = re.search(pattern, deadline_text)
                if match:
                    if '天后' in deadline_text:
                        days = int(match.group(1))
                        return (current_time + timedelta(days=days)).isoformat()
                    elif '明天' in deadline_text:
                        return (current_time + timedelta(days=1)).isoformat()
                    elif '今天' in deadline_text:
                        return current_time.isoformat()
                    else:
                        # 处理具体日期时间
                        groups = match.groups()
                        if len(groups) >= 5:
                            year, month, day, hour, minute = groups[:5]
                            return datetime(int(year), int(month), int(day), 
                                          int(hour), int(minute)).isoformat()
                        elif len(groups) >= 4:
                            month, day, hour, minute = groups[:4]
                            return datetime(current_time.year, int(month), int(day),
                                          int(hour), int(minute)).isoformat()
            
            return None
            
        except Exception as e:
            print(f"解析截止时间失败: {e}")
            return None

# 配置类
class PlatformConfig:
    def __init__(self):
        self.config_file = 'platform_config.json'
        self.load_config()

    def load_config(self):
        """加载平台配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except:
            self.config = {
                'platforms': {
                    'xuexitong': {
                        'enabled': True,
                        'auto_sync': True,
                        'sync_interval': 3600,  # 1小时
                        'credentials': None
                    },
                    'touge': {
                        'enabled': True,
                        'auto_sync': True,
                        'sync_interval': 3600,
                        'credentials': None
                    }
                },
                'last_sync': None
            }

    def save_config(self):
        """保存平台配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def update_credentials(self, platform, username, password):
        """更新平台凭据"""
        if platform in self.config['platforms']:
            self.config['platforms'][platform]['credentials'] = {
                'username': username,
                'password': password
            }
            self.save_config()

    def get_platform_config(self, platform):
        """获取平台配置"""
        return self.config['platforms'].get(platform, {})
