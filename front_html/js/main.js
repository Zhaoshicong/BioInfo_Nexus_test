document.addEventListener('DOMContentLoaded', function() {
    lucide.createIcons();
    
    // 特性提示框功能
    const featureList = document.querySelector('.feature-list');
    const tooltip = document.querySelector('.feature-tooltip');
    const loginForm = document.getElementById('loginForm');
    
    // 初始化检查登录状态
    checkLoginStatus();
    
    // 切换登录/注册表单
    setupAuthTabs();
    
    // 设置密码可见性切换
    setupPasswordToggles();
    
    featureList.addEventListener('mouseover', function(e) {
        const li = e.target.closest('li');
        if (li) {
            const tooltipText = li.getAttribute('data-tooltip');
            const feature = li.getAttribute('data-feature');
            if (tooltipText) {
                tooltip.textContent = tooltipText;
                tooltip.style.display = 'block';
                
                // 计算提示框位置
                const rect = li.getBoundingClientRect();
                tooltip.style.top = rect.top + window.scrollY + 'px';
                tooltip.style.left = rect.right + 20 + 'px';
                
                // 添加动画类
                setTimeout(() => tooltip.classList.add('active'), 50);
                
                // 高亮对应的输入框
                highlightLoginField(feature);
            }
        }
    });
    
    featureList.addEventListener('mouseout', function(e) {
        const li = e.target.closest('li');
        if (li) {
            tooltip.classList.remove('active');
            setTimeout(() => tooltip.style.display = 'none', 300);
        }
    });
    
    function highlightLoginField(feature) {
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        
        // 移除之前的高亮效果
        usernameInput.classList.remove('highlight-input');
        passwordInput.classList.remove('highlight-input');
        
        // 根据特性添加高亮效果
        switch(feature) {
            case 'sequence':
            case 'database':
                usernameInput.classList.add('highlight-input');
                break;
            case 'workflow':
            case 'share':
                passwordInput.classList.add('highlight-input');
                break;
        }
    }

    // 处理联系我们链接的点击事件
    const contactLink = document.querySelector('.contact-link');
    const emailTooltip = document.querySelector('.email-tooltip');
    
    if (contactLink && emailTooltip) {
        // 点击联系我们链接时
        contactLink.addEventListener('click', function(e) {
            e.preventDefault();
            emailTooltip.classList.toggle('show');
            e.stopPropagation();
        });
        
        // 点击邮箱提示框时复制邮箱地址
        emailTooltip.addEventListener('click', function(e) {
            e.stopPropagation();
            const email = this.textContent.trim();
            navigator.clipboard.writeText(email).then(() => {
                // 创建一个临时提示
                const copyHint = document.createElement('div');
                copyHint.className = 'copy-hint';
                copyHint.textContent = '已复制到剪贴板';
                this.appendChild(copyHint);
                
                // 2秒后移除提示
                setTimeout(() => {
                    copyHint.remove();
                }, 2000);
            });
        });
        
        // 点击页面其他地方时隐藏邮箱提示框
        document.addEventListener('click', function() {
            emailTooltip.classList.remove('show');
        });
    }
});

// 设置认证表单切换
function setupAuthTabs() {
    const authTabs = document.querySelectorAll('.auth-tab');
    const authContents = document.querySelectorAll('.auth-content');
    const showRegisterLink = document.getElementById('showRegister');
    const showLoginLink = document.getElementById('showLogin');
    
    // 点击标签切换
    authTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            
            // 切换标签激活状态
            authTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // 切换内容显示
            authContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabName + 'Tab') {
                    content.classList.add('active');
                }
            });
        });
    });
    
    // 点击链接切换
    if (showRegisterLink) {
        showRegisterLink.addEventListener('click', (e) => {
            e.preventDefault();
            authTabs.forEach(t => {
                t.classList.remove('active');
                if (t.getAttribute('data-tab') === 'register') {
                    t.classList.add('active');
                }
            });
            
            authContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === 'registerTab') {
                    content.classList.add('active');
                }
            });
        });
    }
    
    if (showLoginLink) {
        showLoginLink.addEventListener('click', (e) => {
            e.preventDefault();
            authTabs.forEach(t => {
                t.classList.remove('active');
                if (t.getAttribute('data-tab') === 'login') {
                    t.classList.add('active');
                }
            });
            
            authContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === 'loginTab') {
                    content.classList.add('active');
                }
            });
        });
    }
}

// 设置密码可见性切换
function setupPasswordToggles() {
    const toggleButtons = document.querySelectorAll('.password-toggle');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const iconElement = this.querySelector('.eye-icon');
            
            // 切换密码可见性
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                // 替换为眼睛关闭图标
                iconElement.removeAttribute('data-lucide');
                iconElement.setAttribute('data-lucide', 'eye-off');
            } else {
                passwordInput.type = 'password';
                // 替换为眼睛打开图标
                iconElement.removeAttribute('data-lucide');
                iconElement.setAttribute('data-lucide', 'eye');
            }
            
            // 重新渲染图标
            lucide.createIcons({
                icons: [iconElement],
                attrs: {
                    width: '18px',
                    height: '18px'
                }
            });
        });
    });
}

// 验证登录表单
function validateLogin(event) {
    event.preventDefault();
    const email = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    // 显示加载状态
    const loginBtn = document.querySelector('.login-btn');
    loginBtn.innerHTML = '登录中...';
    loginBtn.disabled = true;
    
    // 发送登录请求
    fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: email,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            // 登录成功
            loginBtn.style.background = 'linear-gradient(45deg, #27ae60, #2ecc71)';
            loginBtn.innerHTML = '登录成功 <span style="margin-left: 5px">✓</span>';
            
            // 保存token和用户信息
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify({
                username: email,
                public_id: data.public_id
            }));
            
            // 跳转到主页
            setTimeout(() => {
                document.querySelector('.content-wrapper').style.opacity = '0';
                setTimeout(() => {
                    window.location.href = 'search.html';
                }, 500);
            }, 800);
        } else if (data.needs_verification) {
            // 账户未激活，需要验证邮箱
            showVerificationPrompt(data.email);
            loginBtn.innerHTML = '登录';
            loginBtn.disabled = false;
        } else {
            // 登录失败
            showAuthError(loginBtn, '登录', data.message || '邮箱或密码错误！');
        }
    })
    .catch(error => {
        console.error('登录错误:', error);
        showAuthError(loginBtn, '登录', '登录请求失败，请稍后再试！');
    });
    
    return false;
}

// 验证注册表单
function validateRegister(event) {
    event.preventDefault();
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const confirmPassword = document.getElementById('reg-confirm-password').value;
    
    // 验证密码匹配
    if (password !== confirmPassword) {
        alert('两次输入的密码不一致！');
        return false;
    }
    
    // 显示加载状态
    const registerBtn = document.querySelector('.register-btn');
    registerBtn.innerHTML = '注册中...';
    registerBtn.disabled = true;
    
    // 发送注册请求
    fetch('/api/auth/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: email,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message.includes('注册成功')) {
            // 注册成功
            registerBtn.style.background = 'linear-gradient(45deg, #27ae60, #2ecc71)';
            registerBtn.innerHTML = '注册成功 <span style="margin-left: 5px">✓</span>';
            
            // 显示成功消息并切换到登录表单
            setTimeout(() => {
                alert('注册成功！请查收验证邮件以激活您的账户。');
                // 切换到登录表单
                document.querySelector('.auth-tab[data-tab="login"]').click();
                // 重置注册表单
                document.getElementById('registerForm').reset();
                registerBtn.innerHTML = '注册';
                registerBtn.disabled = false;
                registerBtn.style.background = '';
            }, 1000);
        } else {
            // 注册失败
            showAuthError(registerBtn, '注册', data.message || '注册失败，请稍后再试！');
        }
    })
    .catch(error => {
        console.error('注册错误:', error);
        showAuthError(registerBtn, '注册', '注册请求失败，请稍后再试！');
    });
    
    return false;
}

// 显示认证错误
function showAuthError(button, type, message) {
    button.style.background = 'linear-gradient(45deg, #e74c3c, #c0392b)';
    button.innerHTML = `${type}失败`;
    
    // 显示错误消息
    alert(message);
    
    // 重置按钮状态
    setTimeout(() => {
        button.style.background = '';
        button.innerHTML = type === '登录' ? '登录' : '注册';
        button.disabled = false;
    }, 1500);
    
    // 添加抖动效果
    const container = document.querySelector('.login-container');
    container.style.animation = 'shake 0.5s ease-in-out';
    setTimeout(() => {
        container.style.animation = '';
    }, 500);
}

// 检查登录状态
function checkLoginStatus() {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    
    if (token && user) {
        try {
            // 验证token是否过期
            const tokenData = JSON.parse(atob(token.split('.')[1]));
            const expirationTime = tokenData.exp * 1000; // 转换为毫秒
            
            if (Date.now() < expirationTime) {
                // token有效，直接跳转到主页
                window.location.href = 'search.html';
                return;
            }
        } catch (e) {
            console.error('Token验证错误:', e);
        }
        
        // token无效或过期，清除本地存储
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }
}

// 显示邮箱验证提示
function showVerificationPrompt(email) {
    // 创建模态框
    const modal = document.createElement('div');
    modal.className = 'verification-modal';
    modal.innerHTML = `
        <div class="verification-content">
            <h3>账户未激活</h3>
            <p>您的账户尚未激活，请查收邮箱中的验证邮件。</p>
            <p>如果您没有收到验证邮件，可以点击下方按钮重新发送。</p>
            <div class="verification-email">${email}</div>
            <button id="resendVerification" class="resend-btn">重新发送验证邮件</button>
            <button id="closeVerification" class="close-btn">关闭</button>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 添加事件监听
    document.getElementById('resendVerification').addEventListener('click', () => {
        resendVerificationEmail(email);
    });
    
    document.getElementById('closeVerification').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
}

// 重新发送验证邮件
function resendVerificationEmail(email) {
    const resendBtn = document.getElementById('resendVerification');
    resendBtn.innerHTML = '发送中...';
    resendBtn.disabled = true;
    
    fetch('/api/auth/resend-verification', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: email
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message.includes('已重新发送')) {
            resendBtn.innerHTML = '发送成功 ✓';
            setTimeout(() => {
                resendBtn.innerHTML = '重新发送验证邮件';
                resendBtn.disabled = false;
            }, 3000);
            alert('验证邮件已重新发送，请查收！');
        } else {
            resendBtn.innerHTML = '发送失败';
            setTimeout(() => {
                resendBtn.innerHTML = '重新发送验证邮件';
                resendBtn.disabled = false;
            }, 3000);
            alert(data.message || '发送失败，请稍后再试！');
        }
    })
    .catch(error => {
        console.error('重发验证邮件错误:', error);
        resendBtn.innerHTML = '发送失败';
        setTimeout(() => {
            resendBtn.innerHTML = '重新发送验证邮件';
            resendBtn.disabled = false;
        }, 3000);
        alert('发送请求失败，请稍后再试！');
    });
}
