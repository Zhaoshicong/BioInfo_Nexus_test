// 全局变量
let currentUserId = null;
let token = null; // 延迟获取token
const API_BASE = '/admin';
let currentUserInfo = null; // 存储当前登录用户信息

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log("管理面板页面加载中...");
    
    // 延迟获取token，确保cookieUtils已加载
    setTimeout(() => {
        token = cookieUtils.getCookie('auth_token');
    console.log("检查令牌:", token ? "已找到" : "未找到");
    
    // 检查是否已登录
    if (!token) {
        console.log("未找到令牌，重定向到登录页...");
        window.location.href = 'admin-login.html';
        return;
    }
    
        // 验证管理员权限
        checkAdminPermission();
    }, 100);
});

// 验证管理员权限
async function checkAdminPermission() {
    try {
        // 首先通过API验证token有效性和管理员权限
        const response = await fetch('/api/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            console.log("Token验证失败，重定向到登录页...");
            window.location.href = 'admin-login.html';
            return;
        }
        
        const userData = await response.json();
        console.log("API返回的用户数据:", userData);
            
        // 检查是否是管理员
        if (!userData.is_admin && userData.role !== 'admin') {
                console.log("非管理员用户，重定向到登录页...");
                window.location.href = 'admin-login.html';
                return;
            }
            
            // 设置当前用户信息
        currentUserInfo = {
            id: userData.id,
            username: userData.username,
            email: userData.email,
            is_admin: userData.is_admin,
            role: userData.role || 'admin'
        };
        
        console.log("管理员权限验证成功:", currentUserInfo);
        
        // 初始化管理后台
        initAdminPanel();
        
    } catch (e) {
        console.error("验证管理员权限出错:", e);
        window.location.href = 'admin-login.html';
    }
}

// 初始化管理后台
function initAdminPanel() {
    console.log("开始初始化管理后台...");
    
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
}

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
        // 添加调试日志
        console.log('API返回的统计数据:', data);
        
        // 检查数据内容
        console.log('用户总数:', data.user_count, typeof data.user_count);
        console.log('管理员数量:', data.admin_count, typeof data.admin_count);
        
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
        // 添加调试日志
        console.log('API返回的用户列表:', users);
        
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

    // 监听日志类型切换
    document.getElementById('log-type').addEventListener('change', loadSystemLogs);
}

// 渲染用户列表
function renderUsersList(users) {
    console.log('渲染用户列表:', users);
    
    // 清空用户列表
    const adminUsersList = document.getElementById('admin-users-list');
    const normalUsersList = document.getElementById('normal-users-list');
    
    adminUsersList.innerHTML = '';
    normalUsersList.innerHTML = '';
    
    if (users.length === 0) {
        const noDataRow = '<tr><td colspan="6" style="text-align: center;">暂无数据</td></tr>';
        adminUsersList.innerHTML = noDataRow;
        normalUsersList.innerHTML = noDataRow;
        return;
    }
    
    // 分类用户
    const adminUsers = [];
    const normalUsers = [];
    
    users.forEach(user => {
        // 确定用户角色
        if (user.role === 'admin' || user.role === 1 || user.role === true || user.is_admin === 1 || user.is_admin === true) {
            adminUsers.push({...user, role: 'admin'});
        } else {
            normalUsers.push({...user, role: 'user'});
        }
    });
    
    // 渲染管理员列表
    if (adminUsers.length > 0) {
        renderUserTable(adminUsers, adminUsersList);
    } else {
        adminUsersList.innerHTML = '<tr><td colspan="6" style="text-align: center;">暂无管理员</td></tr>';
    }
    
    // 渲染普通用户列表
    if (normalUsers.length > 0) {
        renderUserTable(normalUsers, normalUsersList);
    } else {
        normalUsersList.innerHTML = '<tr><td colspan="6" style="text-align: center;">暂无普通用户</td></tr>';
    }
}

// 渲染用户表格
function renderUserTable(users, tableBody) {
    // 为用户添加序号
    users.forEach((user, index) => {
        // 确保用户ID存在
        const userId = user.id;
        if (!userId) {
            console.warn('警告: 用户数据中没有ID', user);
            return; // 跳过没有ID的用户
        }
        
        // 确定用户角色
        let roleDisplay;
        let role = user.role || '';
        
        // 处理角色信息：可能是布尔值、数字或字符串
        if (role === 'admin' || role === 1 || role === true || user.is_admin === 1 || user.is_admin === true) {
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
        tableBody.appendChild(tr);
    });
}

// 加载系统日志
function loadSystemLogs() {
    const logType = document.getElementById('log-type').value;
    fetch(`${API_BASE}/logs?type=${logType}`, {
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
    const adminUserRows = document.querySelectorAll('#admin-users-list tr');
    const normalUserRows = document.querySelectorAll('#normal-users-list tr');
    
    // 筛选管理员列表
    filterUserRows(adminUserRows, filter);
    
    // 筛选普通用户列表
    filterUserRows(normalUserRows, filter);
}

// 筛选用户行
function filterUserRows(rows, filter) {
    rows.forEach(row => {
        // 检查是否是数据行（有单元格）
        if (row.cells && row.cells.length > 1) {
            const username = row.cells[1]?.textContent.toLowerCase() || '';
            const email = row.cells[2]?.textContent.toLowerCase() || '';
            
            if (username.includes(filter) || email.includes(filter)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
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
    
    const url = `${API_BASE}/api/users/${userId}`;
    console.log('发送删除请求到:', url);
    
    fetch(url, {
        method: 'DELETE',
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
    const tabs = document.querySelectorAll('.sidebar-menu > li > a, .submenu > li > a');
    const panes = document.querySelectorAll('.tab-pane');
    const subPanes = document.querySelectorAll('.subtab-pane');
    const menuToggles = document.querySelectorAll('.menu-toggle');
    
    // 为菜单切换按钮添加事件监听
    menuToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            
            const target = this.getAttribute('data-tab');
            const parentLi = this.closest('li');
            
            // 切换菜单的展开/折叠状态
            if (parentLi.classList.contains('active')) {
                // 如果已经是active状态，则只切换折叠状态，不切换内容
                parentLi.classList.remove('active');
                e.stopPropagation(); // 阻止事件冒泡，防止触发标签切换
            } else {
                // 如果不是active状态，则展开子菜单并切换到该标签
                document.querySelectorAll('.sidebar-menu > li').forEach(li => {
                    li.classList.remove('active');
                });
                parentLi.classList.add('active');
                
                // 切换到对应的标签内容
                panes.forEach(p => p.classList.remove('active'));
                document.getElementById(target).classList.add('active');
                
                // 默认显示第一个子标签
                const firstSubTab = parentLi.querySelector('.submenu li:first-child a');
                if (firstSubTab) {
                    const firstSubTabTarget = firstSubTab.getAttribute('data-tab');
                    document.querySelectorAll('.submenu a').forEach(t => t.classList.remove('active'));
                    firstSubTab.classList.add('active');
                    
                    subPanes.forEach(p => p.classList.remove('active'));
                    document.getElementById(firstSubTabTarget).classList.add('active');
                }
            }
        });
    });
    
    // 为子标签添加事件监听
    document.querySelectorAll('.submenu > li > a').forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            const target = this.getAttribute('data-tab');
            const parentTab = this.getAttribute('data-parent');
            
            // 移除所有子标签的active类
            document.querySelectorAll('.submenu a').forEach(t => t.classList.remove('active'));
            subPanes.forEach(p => p.classList.remove('active'));
            
            // 添加active类到当前子标签
            this.classList.add('active');
            
            // 确保父标签也是active
            const parentTabEl = document.querySelector(`a[data-tab="${parentTab}"]`);
            if (parentTabEl && !parentTabEl.closest('li').classList.contains('active')) {
                document.querySelectorAll('.sidebar-menu > li').forEach(li => {
                    li.classList.remove('active');
                });
                parentTabEl.closest('li').classList.add('active');
                
                // 显示父标签内容
                panes.forEach(p => p.classList.remove('active'));
                document.getElementById(parentTab).classList.add('active');
            }
            
            // 显示对应的子标签内容
            document.getElementById(target).classList.add('active');
        });
    });
    
    // 为非折叠菜单的主标签添加事件监听
    document.querySelectorAll('.sidebar-menu > li > a:not(.menu-toggle)').forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            const target = this.getAttribute('data-tab');
            
            // 移除所有标签的active类
            document.querySelectorAll('.sidebar-menu a').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.sidebar-menu > li').forEach(li => {
                li.classList.remove('active');
            });
            panes.forEach(p => p.classList.remove('active'));
            subPanes.forEach(p => p.classList.remove('active'));
            
            // 添加active类到当前标签
            this.classList.add('active');
            
            // 显示对应的内容区
            document.getElementById(target).classList.add('active');
        });
    });
}

// 退出登录
function logout() {
            cookieUtils.deleteCookie('auth_token');
        cookieUtils.deleteCookie('username');
        cookieUtils.deleteCookie('isAdmin');
        cookieUtils.deleteCookie('loginTime');
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