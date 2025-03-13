// 全局变量
let currentUserId = null;
let token = localStorage.getItem('token');
const API_BASE = '/admin';
let currentUserInfo = null; // 存储当前登录用户信息

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否已登录
    if (!token) {
        window.location.href = 'admin-login.html';
        return;
    }
    
    // 获取当前用户信息
    getCurrentUserInfo();
    
    // 初始化
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    loadDashboardData();
    
    // 标签页切换
    initTabs();
    
    // 监听事件
    document.getElementById('logout-btn').addEventListener('click', logout);
    document.getElementById('user-search').addEventListener('input', filterUsers);
    document.getElementById('log-level').addEventListener('change', filterLogs);
    document.getElementById('settings-form').addEventListener('submit', saveSettings);
    
    // 模态框事件
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    document.getElementById('cancel-delete').addEventListener('click', closeModal);
    document.getElementById('confirm-delete').addEventListener('click', deleteUser);
});

// 获取当前用户信息
function getCurrentUserInfo() {
    // 解析JWT令牌获取用户ID (不验证签名)
    try {
        const tokenParts = token.split('.');
        if (tokenParts.length === 3) {
            const payload = JSON.parse(atob(tokenParts[1]));
            currentUserInfo = {
                id: payload.user_id || payload.id || null,
                publicId: payload.public_id || null,
                username: payload.username || null,
                isAdmin: payload.is_admin || payload.admin || false
            };
            console.log('当前登录用户:', currentUserInfo);
        }
    } catch (e) {
        console.error('解析令牌出错:', e);
    }
}

// 更新当前时间
function updateCurrentTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleString('zh-CN');
}

// 加载控制面板数据
function loadDashboardData() {
    showLoading();
    
    // 获取统计数据
    fetch(`${API_BASE}/api/stats`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取统计数据失败');
        }
        return response.json();
    })
    .then(data => {
        document.getElementById('total-users').textContent = data.user_count || '0';
        document.getElementById('admin-count').textContent = data.admin_count || '0';
        document.getElementById('active-today').textContent = data.active_today || '0';
        document.getElementById('reg-today').textContent = data.today_users || '0';
    })
    .catch(error => {
        showMessage('获取统计数据失败: ' + error.message, 'danger');
    });
    
    // 获取用户列表
    fetch(`${API_BASE}/api/users`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取用户列表失败');
        }
        return response.json();
    })
    .then(users => {
        // 所有用户
        renderUsersList(users);
        hideLoading();
    })
    .catch(error => {
        showMessage('获取用户列表失败: ' + error.message, 'danger');
        hideLoading();
    });
    
    // 获取系统日志
    loadSystemLogs();
}

// 渲染用户列表
function renderUsersList(users) {
    console.log('渲染用户列表:', users);
    const tbody = document.getElementById('users-list');
    tbody.innerHTML = '';
    
    if (users.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="6" style="text-align: center;">暂无数据</td>';
        tbody.appendChild(tr);
        return;
    }
    
    // 不再过滤admin账户
    const filteredUsers = users;
    
    // 为用户添加序号
    filteredUsers.forEach((user, index) => {
        // 确保用户ID存在
        const userId = user.id;
        if (!userId) {
            console.warn('警告: 用户数据中没有ID', user);
            return; // 跳过没有ID的用户
        }
        
        // 确定用户角色
        let roleDisplay;
        let role = '';
        
        // 处理角色信息：可能是布尔值、数字或字符串
        if (user.role === 'admin' || user.role === 1 || user.role === true || user.is_admin === 1 || user.is_admin === true) {
            roleDisplay = '<span class="role-badge role-admin">管理员</span>';
            role = 'admin';
        } else {
            roleDisplay = '<span class="role-badge role-user">普通用户</span>';
            role = 'user';
        }
        
        const tr = document.createElement('tr');
        const safeUsername = (user.username || '').replace(/'/g, '&#39;'); // 转义单引号
        
        // 检查是否是当前用户，不允许取消自己的管理员权限
        const isSelf = currentUserInfo && userId == currentUserInfo.id;
        
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td>${user.username || ''}</td>
            <td>${user.email || ''}</td>
            <td>${roleDisplay}</td>
            <td>${formatDate(user.registered_on || user.created_at)}</td>
            <td>
                ${role === 'admin' 
                    ? (isSelf 
                        ? `<button class="btn btn-warning btn-sm" disabled title="不能修改自己的权限">
                            <i class="fas fa-user-minus"></i> 移除管理员
                          </button>`
                        : `<button class="btn btn-warning btn-sm" onclick="setUserRole(${userId}, 'user')">
                            <i class="fas fa-user-minus"></i> 移除管理员
                          </button>`
                      )
                    : `<button class="btn btn-success btn-sm" onclick="setUserRole(${userId}, 'admin')">
                        <i class="fas fa-user-shield"></i> 设为管理员
                      </button>`
                }
                ${isSelf
                    ? `<button class="btn btn-danger btn-sm" disabled title="不能删除自己的账户">
                        <i class="fas fa-trash"></i> 删除
                      </button>`
                    : `<button class="btn btn-danger btn-sm" onclick="showDeleteModal(${userId}, '${safeUsername}')">
                        <i class="fas fa-trash"></i> 删除
                      </button>`
                }
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 加载系统日志
function loadSystemLogs() {
    fetch(`${API_BASE}/api/logs`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取系统日志失败');
        }
        return response.json();
    })
    .then(logs => {
        renderLogs(logs);
    })
    .catch(error => {
        showMessage('获取系统日志失败: ' + error.message, 'danger');
    });
}

// 渲染日志
function renderLogs(logs) {
    const container = document.getElementById('logs-container');
    container.innerHTML = '';
    
    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="log-entry">暂无日志数据</div>';
        return;
    }
    
    logs.forEach(log => {
        const div = document.createElement('div');
        div.className = 'log-entry';
        
        if (log.toLowerCase().includes('error')) {
            div.classList.add('log-error');
        } else if (log.toLowerCase().includes('warn')) {
            div.classList.add('log-warning');
        } else {
            div.classList.add('log-info');
        }
        
        div.textContent = log;
        container.appendChild(div);
    });
}

// 筛选日志
function filterLogs() {
    const level = document.getElementById('log-level').value;
    const logEntries = document.querySelectorAll('.log-entry');
    
    logEntries.forEach(entry => {
        if (level === 'all') {
            entry.style.display = '';
        } else if (level === 'error' && entry.classList.contains('log-error')) {
            entry.style.display = '';
        } else if (level === 'warning' && entry.classList.contains('log-warning')) {
            entry.style.display = '';
        } else if (level === 'info' && entry.classList.contains('log-info')) {
            entry.style.display = '';
        } else {
            entry.style.display = 'none';
        }
    });
}

// 筛选用户
function filterUsers() {
    const filter = document.getElementById('user-search').value.toLowerCase();
    const rows = document.querySelectorAll('#users-list tr');
    
    rows.forEach(row => {
        const username = row.cells[1]?.textContent.toLowerCase() || '';
        const email = row.cells[2]?.textContent.toLowerCase() || '';
        
        if (username.includes(filter) || email.includes(filter)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// 设置用户角色
function setUserRole(userId, role) {
    if (!userId) return;
    
    showLoading();
    
    const url = role === 'admin' 
        ? `${API_BASE}/api/users/${userId}/set_admin` 
        : `${API_BASE}/api/users/${userId}/remove_admin`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        // 先获取响应内容，即使状态码表示错误
        return response.json().then(data => {
            if (!response.ok) {
                // 如果服务器返回了错误信息，使用该信息
                if (data && data.error) {
                    throw new Error(data.error);
                } else {
                    throw new Error('设置用户角色失败 (状态码: ' + response.status + ')');
                }
            }
            return data;
        });
    })
    .then(data => {
        showMessage(data.message || '设置成功', 'success');
        // 刷新用户列表
        loadDashboardData();
    })
    .catch(error => {
        console.error('设置用户角色错误:', error);
        showMessage(error.message || '设置用户角色失败', 'danger');
        // 即使报错也刷新用户列表，因为可能已经成功修改了
        loadDashboardData();
        hideLoading();
    });
}

// 显示删除确认框
function showDeleteModal(userId, username) {
    console.log('显示删除确认框, userId:', userId, 'username:', username);
    if (!userId || userId === 'null' || userId === 'undefined') {
        showMessage('错误：无法删除用户，用户ID不存在', 'danger');
        return;
    }
    
    // 确保userId是数字
    userId = parseInt(userId);
    if (isNaN(userId)) {
        showMessage('错误：无效的用户ID', 'danger');
        return;
    }
    
    currentUserId = userId;
    document.getElementById('delete-username').textContent = username || '未知用户';
    document.getElementById('delete-modal').style.display = 'flex';
}

// 关闭模态框
function closeModal() {
    document.getElementById('delete-modal').style.display = 'none';
    currentUserId = null;
}

// 删除用户
function deleteUser() {
    console.log('尝试删除用户, currentUserId:', currentUserId);
    if (!currentUserId || currentUserId === 'null' || currentUserId === 'undefined') {
        showMessage('错误：无法删除用户，用户ID不存在', 'danger');
        return;
    }
    
    // 确保userId是数字
    const userId = parseInt(currentUserId);
    if (isNaN(userId)) {
        showMessage('错误：无效的用户ID', 'danger');
        return;
    }
    
    showLoading();
    closeModal();
    
    const url = `${API_BASE}/api/users/${userId}/delete`;
    console.log('发送删除请求到:', url);
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('删除请求响应状态:', response.status);
        // 先获取响应内容，即使状态码表示错误
        return response.json().then(data => {
            if (!response.ok) {
                // 如果服务器返回了错误信息，使用该信息
                if (data && data.error) {
                    throw new Error(data.error);
                } else {
                    throw new Error('删除用户失败 (状态码: ' + response.status + ')');
                }
            }
            return data;
        });
    })
    .then(data => {
        console.log('删除成功, 响应数据:', data);
        showMessage(data.message || '删除成功', 'success');
        // 刷新用户列表
        loadDashboardData();
    })
    .catch(error => {
        console.error('删除用户出错:', error, '用户ID:', currentUserId);
        showMessage(error.message || '删除用户失败', 'danger');
        // 即使报错也刷新用户列表，因为可能已经成功删除
        loadDashboardData();
        hideLoading();
    });
}

// 保存系统设置
function saveSettings(event) {
    event.preventDefault();
    showLoading();
    
    const formData = new FormData();
    formData.append('siteName', document.getElementById('site-name').value);
    formData.append('siteDescription', document.getElementById('site-description').value);
    formData.append('adminEmail', document.getElementById('admin-email').value);
    formData.append('smtpServer', document.getElementById('smtp-server').value);
    formData.append('smtpPort', document.getElementById('smtp-port').value);
    
    fetch(`${API_BASE}/api/settings/update`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('保存设置失败');
        }
        return response.json();
    })
    .then(data => {
        showMessage(data.message || '设置已保存', 'success');
        hideLoading();
    })
    .catch(error => {
        showMessage('保存设置失败: ' + error.message, 'danger');
        hideLoading();
    });
}

// 初始化标签页
function initTabs() {
    const tabs = document.querySelectorAll('.sidebar-menu a');
    const panes = document.querySelectorAll('.tab-pane');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            // 移除所有active类
            tabs.forEach(t => t.classList.remove('active'));
            panes.forEach(p => p.classList.remove('active'));
            
            // 添加active类到当前tab
            this.classList.add('active');
            
            // 显示对应的内容区
            const target = this.getAttribute('data-tab');
            document.getElementById(target).classList.add('active');
        });
    });
}

// 退出登录
function logout() {
    localStorage.removeItem('token');
    window.location.href = 'admin-login.html';
}

// 显示加载动画
function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

// 隐藏加载动画
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// 显示消息
function showMessage(message, type) {
    // 移除旧消息
    const oldAlerts = document.querySelectorAll('.alert');
    oldAlerts.forEach(alert => alert.remove());
    
    // 创建新消息
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        ${message}
        <span class="alert-close" onclick="this.parentElement.remove()">&times;</span>
    `;
    
    // 添加到DOM
    const container = document.querySelector('.admin-container');
    container.insertBefore(alert, container.firstChild);
    
    // 5秒后自动消失
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// 日期格式化
function formatDate(dateStr) {
    if (!dateStr) return '未知';
    
    const date = new Date(dateStr);
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
        return dateStr;
    }
    
    return date.toLocaleString('zh-CN');
} 