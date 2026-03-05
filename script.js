class TaskManager {
    constructor() {
        this.tasks = [];
        this.currentFilter = 'all';
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadTasks();
        this.loadPlatformStatus();
        this.startReminderCheck();
        // 页面加载时自动同步一次
        this.autoSyncOnLoad();
    }

    bindEvents() {
        // 过滤按钮事件
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setFilter(e.target.dataset.filter);
            });
        });

        // 同步按钮事件
        const syncAllBtn = document.getElementById('syncAllBtn');
        const syncXuexitongBtn = document.getElementById('syncXuexitongBtn');
        const syncTougeBtn = document.getElementById('syncTougeBtn');

        if (syncAllBtn) {
            syncAllBtn.addEventListener('click', (e) => {
                this.syncPlatforms(['xuexitong', 'touge'], e.target);
            });
        }

        if (syncXuexitongBtn) {
            syncXuexitongBtn.addEventListener('click', (e) => {
                this.syncPlatforms(['xuexitong'], e.target);
            });
        }

        if (syncTougeBtn) {
            syncTougeBtn.addEventListener('click', (e) => {
                this.syncPlatforms(['touge'], e.target);
            });
        }
    }

    async autoSyncOnLoad() {
        // 页面加载时自动同步所有平台
        console.log('页面加载，开始自动同步...');
        await this.syncPlatforms(['xuexitong', 'touge'], null, true);
    }

    async loadTasks() {
        try {
            const response = await fetch('/api/tasks');
            this.tasks = await response.json();
            this.renderTasks();
            this.updateStatistics();
        } catch (error) {
            console.error('加载任务失败:', error);
            this.showNotification('错误', '加载任务失败，请检查网络连接');
        }
    }

    async loadPlatformStatus() {
        try {
            const response = await fetch('/api/platform/status');
            const status = await response.json();
            this.renderPlatformStatus(status);
        } catch (error) {
            console.error('加载平台状态失败:', error);
        }
    }

    renderPlatformStatus(status) {
        const statusContent = document.getElementById('statusContent');
        let html = '';
        
        for (const [platform, info] of Object.entries(status)) {
            const platformName = platform === 'xuexitong' ? '学习通' : '头歌';
            const statusClass = info.enabled ? 'status-enabled' : 'status-disabled';
            const credentialStatus = info.has_credentials ? '✅ 已配置' : '❌ 未配置';
            const lastSync = info.last_sync ? 
                new Date(info.last_sync).toLocaleString('zh-CN') : '从未同步';
            
            html += `
                <div class="status-item">
                    <div>
                        <span class="status-indicator ${statusClass}"></span>
                        <strong>${platformName}</strong>
                    </div>
                    <div>
                        <span>${credentialStatus}</span> | 
                        <span>最后同步: ${lastSync}</span>
                    </div>
                </div>
            `;
        }
        
        statusContent.innerHTML = html;
    }

    async syncPlatforms(platforms, buttonElement, isAutoSync = false) {
        // 如果是自动同步，不修改按钮状态
        if (!isAutoSync && buttonElement) {
            const syncBtn = buttonElement;
            const originalText = syncBtn.textContent;
            syncBtn.textContent = '同步中...';
            syncBtn.disabled = true;
        }

        try {
            console.log(`开始同步平台: ${platforms.join(', ')}`);
            const response = await fetch('/api/sync/platforms', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ platforms })
            });

            const result = await response.json();
            console.log('同步结果:', result);
            
            if (result.success) {
                const message = isAutoSync ? 
                    `自动同步完成，添加了 ${result.added_count} 个新任务` : 
                    `已添加 ${result.added_count} 个新任务`;
                this.showNotification('同步成功', message);
                this.loadTasks(); // 重新加载任务列表
                this.loadPlatformStatus(); // 更新平台状态
            } else {
                const message = isAutoSync ? 
                    '自动同步失败: ' + (result.error || '同步过程中出现错误') :
                    result.error || '同步过程中出现错误';
                this.showNotification('同步失败', message);
            }
        } catch (error) {
            console.error('同步失败:', error);
            const message = isAutoSync ? '自动同步网络错误' : '网络错误，请重试';
            this.showNotification('同步失败', message);
        } finally {
            // 如果不是自动同步，恢复按钮状态
            if (!isAutoSync && buttonElement) {
                const syncBtn = buttonElement;
                syncBtn.textContent = syncBtn.textContent.replace('同步中...', '同步所有平台');
                syncBtn.disabled = false;
            }
        }
    }

    async saveCredentials(platform) {
        const usernameInput = document.getElementById(`${platform}Username`);
        const passwordInput = document.getElementById(`${platform}Password`);
        
        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();
        
        if (!username || !password) {
            this.showNotification('错误', '请输入完整的用户名和密码');
            return;
        }

        try {
            const response = await fetch('/api/platform/credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ platform, username, password })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('成功', '凭据保存成功');
                usernameInput.value = '';
                passwordInput.value = '';
                this.loadPlatformStatus(); // 更新平台状态
            } else {
                this.showNotification('保存失败', result.error || '保存凭据时出现错误');
            }
        } catch (error) {
            console.error('保存凭据失败:', error);
            this.showNotification('保存失败', '网络错误，请重试');
        }
    }

    // 移除手动添加任务功能，专注于自动同步
    async toggleTask(id) {
        try {
            const response = await fetch(`/api/tasks/${id}/toggle`, {
                method: 'POST'
            });

            if (response.ok) {
                const updatedTask = await response.json();
                const taskIndex = this.tasks.findIndex(t => t.id === id);
                if (taskIndex !== -1) {
                    this.tasks[taskIndex] = updatedTask;
                    if (updatedTask.completed) {
                        this.showNotification('任务完成', `恭喜完成任务：${updatedTask.title}`);
                    }
                    this.renderTasks();
                    this.updateStatistics();
                }
            } else {
                throw new Error('更新任务失败');
            }
        } catch (error) {
            console.error('切换任务状态失败:', error);
            this.showNotification('错误', '更新任务失败，请重试');
        }
    }

    async deleteTask(id) {
        const task = this.tasks.find(t => t.id === id);
        if (!task) return;

        if (confirm(`确定要删除任务"${task.title}"吗？`)) {
            try {
                const response = await fetch(`/api/tasks/${id}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    this.tasks = this.tasks.filter(t => t.id !== id);
                    this.renderTasks();
                    this.updateStatistics();
                    this.showNotification('删除成功', `任务"${task.title}"已删除`);
                } else {
                    throw new Error('删除任务失败');
                }
            } catch (error) {
                console.error('删除任务失败:', error);
                this.showNotification('错误', '删除任务失败，请重试');
            }
        }
    }

    setFilter(filter) {
        this.currentFilter = filter;
        
        // 更新按钮状态
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });
        
        this.renderTasks();
    }

    getFilteredTasks() {
        switch (this.currentFilter) {
            case 'completed':
                return this.tasks.filter(task => task.completed);
            case 'pending':
                return this.tasks.filter(task => !task.completed);
            default:
                return this.tasks;
        }
    }

    renderTasks() {
        const container = document.getElementById('taskContainer');
        const filteredTasks = this.getFilteredTasks();

        if (filteredTasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>暂无任务</h3>
                    <p>点击上方添加新任务或同步平台任务开始管理您的待办事项</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filteredTasks.map(task => this.createTaskHTML(task)).join('');
    }

    createTaskHTML(task) {
        const priorityClass = `${task.priority}-priority`;
        const completedClass = task.completed ? 'completed' : '';
        const priorityText = {
            high: '高',
            medium: '中',
            low: '低'
        }[task.priority];

        const deadlineText = task.deadline ? 
            new Date(task.deadline).toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }) : '无截止时间';

        const isOverdue = task.deadline && new Date(task.deadline) < new Date() && !task.completed;

        const platformBadge = task.platform && task.platform !== '手动添加' ? 
            `<span class="task-platform">${task.platform}</span>` : '';
        
        const courseInfo = task.course ? 
            `<div class="task-course">📚 ${task.course}</div>` : '';
        
        const urlLink = task.url ? 
            `<a href="${task.url}" target="_blank" class="task-url">🔗 查看详情</a>` : '';

        return `
            <div class="task-item ${completedClass} ${priorityClass}">
                ${platformBadge}
                <div class="task-header">
                    <h3 class="task-title">${this.escapeHtml(task.title)}</h3>
                    <span class="task-priority priority-${task.priority}">${priorityText}</span>
                </div>
                ${task.description ? `<p class="task-description">${this.escapeHtml(task.description)}</p>` : ''}
                ${courseInfo}
                ${urlLink}
                <div class="task-meta">
                    <div class="task-deadline ${isOverdue ? 'overdue' : ''}">
                        📅 ${deadlineText}
                        ${isOverdue ? ' (已逾期)' : ''}
                    </div>
                    <div class="task-actions">
                        <button class="complete-btn" onclick="taskManager.toggleTask(${task.id})">
                            ${task.completed ? '标记未完成' : '标记完成'}
                        </button>
                        <button class="delete-btn" onclick="taskManager.deleteTask(${task.id})">
                            删除
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    async updateStatistics() {
        try {
            const response = await fetch('/api/statistics');
            const stats = await response.json();
            
            document.getElementById('totalTasks').textContent = stats.total;
            document.getElementById('completedTasks').textContent = stats.completed;
            document.getElementById('pendingTasks').textContent = stats.pending;
            document.getElementById('completionRate').textContent = `${stats.rate}%`;
        } catch (error) {
            console.error('更新统计信息失败:', error);
        }
    }

    resetForm() {
        document.getElementById('taskForm').reset();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(title, message) {
        const notification = document.getElementById('notification');
        document.getElementById('notificationTitle').textContent = title;
        document.getElementById('notificationMessage').textContent = message;
        notification.classList.add('show');

        // 自动关闭
        setTimeout(() => {
            this.closeNotification();
        }, 3000);
    }

    closeNotification() {
        const notification = document.getElementById('notification');
        notification.classList.remove('show');
    }

    startReminderCheck() {
        // 每分钟检查一次提醒
        setInterval(() => {
            this.checkReminders();
        }, 60000);

        // 页面加载时立即检查一次
        this.checkReminders();
    }

    async checkReminders() {
        try {
            const response = await fetch('/api/reminders');
            const reminders = await response.json();
            
            reminders.forEach(reminder => {
                this.showNotification(reminder.title, reminder.message);
            });
        } catch (error) {
            console.error('检查提醒失败:', error);
        }
    }
}

// 全局函数供HTML调用
function closeNotification() {
    taskManager.closeNotification();
}

function saveCredentials(platform) {
    taskManager.saveCredentials(platform);
}

// 初始化任务管理器
let taskManager;
document.addEventListener('DOMContentLoaded', () => {
    taskManager = new TaskManager();
});

// 请求通知权限
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
            console.log('通知权限已授予');
        }
    });
}

// 页面可见性变化时检查提醒
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && taskManager) {
        taskManager.checkReminders();
        taskManager.loadPlatformStatus();
    }
});
