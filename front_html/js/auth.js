// 认证相关工具函数
const authUtils = {
    // 保存令牌到本地存储
    saveToken(token, username, isAdmin) {
        localStorage.setItem('token', token);
        localStorage.setItem('username', username);
        localStorage.setItem('isAdmin', isAdmin);
        localStorage.setItem('loginTime', new Date().toISOString());
    },
    
    // 从本地存储获取令牌
    getToken() {
        return localStorage.getItem('token');
    },
    
    // 获取用户名
    getUsername() {
        return localStorage.getItem('username');
    },
    
    // 检查是否是管理员
    isAdmin() {
        return localStorage.getItem('isAdmin') === 'true';
    },
    
    // 检查用户是否已登录
    isLoggedIn() {
        return !!this.getToken();
    },
    
    // 清除令牌（注销）
    clearToken() {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('isAdmin');
        localStorage.removeItem('loginTime');
    },
    
    // 获取认证头
    getAuthHeader() {
        const token = this.getToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },
    
    // 检查令牌是否过期（默认24小时）
    isTokenExpired() {
        const loginTime = localStorage.getItem('loginTime');
        if (!loginTime) return true;
        
        const loginDate = new Date(loginTime);
        const now = new Date();
        const hoursDiff = (now - loginDate) / (1000 * 60 * 60);
        
        return hoursDiff > 24;
    }
};

// 认证API
const authAPI = {
    // 登录
    async login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || '登录失败');
            }
            
            // 保存令牌
            authUtils.saveToken(data.token, data.username, data.is_admin);
            
            return data;
        } catch (error) {
            console.error('登录错误:', error);
            throw error;
        }
    },
    
    // 注册
    async register(userData) {
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || '注册失败');
            }
            
            return data;
        } catch (error) {
            console.error('注册错误:', error);
            throw error;
        }
    },
    
    // 注销
    async logout() {
        try {
            // 如果用户已登录，调用注销API
            if (authUtils.isLoggedIn()) {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        ...authUtils.getAuthHeader(),
                        'Content-Type': 'application/json'
                    }
                });
            }
            
            // 清除本地令牌
            authUtils.clearToken();
        } catch (error) {
            console.error('注销错误:', error);
            // 即使API调用失败，也清除本地令牌
            authUtils.clearToken();
        }
    },
    
    // 获取当前用户信息
    async getCurrentUser() {
        try {
            if (!authUtils.isLoggedIn()) {
                return null;
            }
            
            const response = await fetch('/api/auth/me', {
                headers: authUtils.getAuthHeader()
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    // 令牌无效或过期，清除本地令牌
                    authUtils.clearToken();
                    return null;
                }
                throw new Error('获取用户信息失败');
            }
            
            return await response.json();
        } catch (error) {
            console.error('获取用户信息错误:', error);
            return null;
        }
    },
    
    // 更新用户信息
    async updateUserInfo(userData) {
        try {
            const response = await fetch('/api/auth/me', {
                method: 'PUT',
                headers: {
                    ...authUtils.getAuthHeader(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || '更新用户信息失败');
            }
            
            return data;
        } catch (error) {
            console.error('更新用户信息错误:', error);
            throw error;
        }
    },
    
    // 上传头像
    async uploadAvatar(file) {
        try {
            const formData = new FormData();
            formData.append('avatar', file);
            
            const response = await fetch('/api/auth/me/avatar', {
                method: 'POST',
                headers: authUtils.getAuthHeader(),
                body: formData
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || '上传头像失败');
            }
            
            return data;
        } catch (error) {
            console.error('上传头像错误:', error);
            throw error;
        }
    }
};

// 页面加载时检查登录状态
document.addEventListener('DOMContentLoaded', async function() {
    // 检查是否已登录
    if (authUtils.isLoggedIn()) {
        // 检查令牌是否过期
        if (authUtils.isTokenExpired()) {
            console.log('令牌已过期，请重新登录');
            authUtils.clearToken();
            updateUIForLoggedOut();
        } else {
            // 获取用户信息
            const user = await authAPI.getCurrentUser();
            if (user) {
                updateUIForLoggedIn(user);
            } else {
                updateUIForLoggedOut();
            }
        }
    } else {
        updateUIForLoggedOut();
    }
    
    // 绑定登录表单提交事件
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const result = await authAPI.login(username, password);
                console.log('登录成功:', result);
                
                // 更新UI
                const user = await authAPI.getCurrentUser();
                updateUIForLoggedIn(user);
                
                // 跳转到搜索页面
                window.location.href = '/search.html';
            } catch (error) {
                alert('登录失败: ' + error.message);
            }
        });
    }
    
    // 绑定注册表单提交事件
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            
            const userData = {
                username: document.getElementById('reg-username').value,
                email: document.getElementById('reg-email').value,
                password: document.getElementById('reg-password').value,
                full_name: document.getElementById('reg-fullname').value,
                organization: document.getElementById('reg-organization').value,
                position: document.getElementById('reg-position').value
            };
            
            try {
                const result = await authAPI.register(userData);
                console.log('注册成功:', result);
                alert('注册成功，请登录！');
                
                // 切换到登录表单
                document.querySelector('.login-tab').click();
                
                // 清空注册表单
                registerForm.reset();
            } catch (error) {
                alert('注册失败: ' + error.message);
            }
        });
    }
    
    // 绑定注销按钮点击事件
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function() {
            try {
                await authAPI.logout();
                updateUIForLoggedOut();
                
                // 如果在用户个人资料页面，跳转到首页
                if (window.location.pathname.includes('/profile.html')) {
                    window.location.href = '/';
                } else {
                    // 刷新当前页面
                    window.location.reload();
                }
            } catch (error) {
                console.error('注销失败:', error);
            }
        });
    }
});

// 更新UI显示已登录状态
function updateUIForLoggedIn(user) {
    // 更新导航栏
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        // 移除登录/注册链接
        const loginLink = navLinks.querySelector('.login-link');
        if (loginLink) loginLink.remove();
        
        // 添加用户菜单
        if (!navLinks.querySelector('.user-menu')) {
            const userMenu = document.createElement('div');
            userMenu.className = 'user-menu';
            userMenu.innerHTML = `
                <span class="username">${user.username}</span>
                <div class="dropdown-menu">
                    <a href="/profile.html">个人资料</a>
                    ${user.is_admin ? '<a href="/admin.html">管理控制台</a>' : ''}
                    <a href="#" id="logoutBtn">注销</a>
                </div>
            `;
            navLinks.appendChild(userMenu);
            
            // 绑定注销按钮事件
            userMenu.querySelector('#logoutBtn').addEventListener('click', async function() {
                try {
                    await authAPI.logout();
                    updateUIForLoggedOut();
                    window.location.reload();
                } catch (error) {
                    console.error('注销失败:', error);
                }
            });
        }
    }
    
    // 隐藏登录表单（如果在首页）
    const loginContainer = document.querySelector('.login-container');
    if (loginContainer) {
        loginContainer.style.display = 'none';
        
        // 显示欢迎信息
        const welcomeContainer = document.createElement('div');
        welcomeContainer.className = 'welcome-container';
        welcomeContainer.innerHTML = `
            <h2>欢迎回来，${user.username}！</h2>
            <p>您已成功登录。</p>
            <a href="/search.html" class="search-link">开始分析</a>
        `;
        
        loginContainer.parentNode.appendChild(welcomeContainer);
    }
}

// 更新UI显示未登录状态
function updateUIForLoggedOut() {
    // 更新导航栏
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        // 移除用户菜单
        const userMenu = navLinks.querySelector('.user-menu');
        if (userMenu) userMenu.remove();
        
        // 添加登录/注册链接
        if (!navLinks.querySelector('.login-link')) {
            const loginLink = document.createElement('a');
            loginLink.href = '/login.html';
            loginLink.className = 'login-link';
            loginLink.textContent = '登录/注册';
            navLinks.appendChild(loginLink);
        }
    }
    
    // 显示登录表单（如果在首页）
    const loginContainer = document.querySelector('.login-container');
    if (loginContainer) {
        loginContainer.style.display = 'block';
        
        // 移除欢迎信息
        const welcomeContainer = document.querySelector('.welcome-container');
        if (welcomeContainer) welcomeContainer.remove();
    }
} 