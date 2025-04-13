document.addEventListener('DOMContentLoaded', function() {
    // 删除lucide初始化调用，已经使用FontAwesome替代
    
    // 添加全局请求拦截器，为所有请求添加认证头
    setupFetchInterceptor();
    
    // 检查登录状态
    checkLoginStatus();
    
    // 初始化各功能
    setupAuthTabs();
    setupPasswordToggles();
    setupPasswordReset();
    setupFeatureTooltips();
    setupPasswordStrengthValidator();
    
    // 检查URL参数，如果有重置密码的token，则显示重置密码模态框
    checkResetPasswordToken();
});

// 设置 fetch 请求拦截器，为所有 API 请求自动添加 Authorization 头
function setupFetchInterceptor() {
    // 保存原始的 fetch 函数
    const originalFetch = window.fetch;
    
    // 重写 fetch 函数
    window.fetch = function(url, options = {}) {
        // 获取存储的令牌 - 每次请求时都重新获取，确保使用最新的
        const token = localStorage.getItem('token');
        
        // 调试输出请求信息
        console.log(`发起请求: ${url}`, options);
        
        // 如果是 API 请求且有令牌，则添加 Authorization 头
        if (token && (url.includes('/api/') || url.startsWith('/api/'))) {
            // 创建新的 options 对象，避免修改原始对象
            const newOptions = { ...options };
            
            // 确保 headers 存在
            newOptions.headers = newOptions.headers || {};
            
            // 如果 headers 是 Headers 对象，转换为普通对象
            if (newOptions.headers instanceof Headers) {
                const headersObj = {};
                for (const [key, value] of newOptions.headers.entries()) {
                    headersObj[key] = value;
                }
                newOptions.headers = headersObj;
            }
            
            // 添加 Authorization 头
            newOptions.headers['Authorization'] = `Bearer ${token}`;
            
            console.log(`已为请求 ${url} 添加认证头`);
            console.log('完整请求选项:', newOptions);
            
            // 使用新的 options 调用原始 fetch
            return originalFetch(url, newOptions)
                .then(response => {
                    // 记录响应状态
                    console.log(`请求 ${url} 响应状态:`, response.status);
                    
                    // 检查是否是认证错误
                    if (response.status === 401) {
                        console.warn(`${url} 返回 401 未授权`);
                        
                        // 如果是刷新用户信息的请求失败，不要清除令牌
                        // 可能是服务器临时问题
                        if (!url.includes('/api/auth/me')) {
                            console.error('认证失败，清除本地令牌');
                            localStorage.removeItem('token');
                            localStorage.removeItem('user');
                            
                            // 如果不是登录页面，可以重定向到登录页
                            const isLoginPage = window.location.pathname === '/' || 
                                              window.location.pathname === '/index.html';
                            if (!isLoginPage) {
                                console.log('重定向到登录页面');
                                window.location.href = '/';
                            }
                        }
                    }
                    
                    return response;
                })
                .catch(error => {
                    console.error(`请求 ${url} 出错:`, error);
                    throw error; // 继续抛出错误，不中断错误流
                });
        }
        
        // 对于其他请求，使用原始参数
        return originalFetch(url, options);
    };
    
    console.log('Fetch 拦截器已设置，所有 API 请求将自动附加认证令牌');
}

// 设置特性提示框功能
function setupFeatureTooltips() {
    const featureList = document.querySelector('.feature-list');
    const tooltip = document.querySelector('.feature-tooltip');
    
    if (!featureList || !tooltip) return;
    
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
    
    // 处理联系我们链接的点击事件
    const contactLink = document.querySelector('.contact-link');
    const emailTooltip = document.querySelector('.email-tooltip');
    
    if (contactLink && emailTooltip) {
        // 移除点击事件，仅保留悬停显示功能
        contactLink.addEventListener('click', function(e) {
            e.preventDefault(); // 阻止默认行为，避免页面跳转
        });
        
        // 点击页面其他地方时隐藏邮箱提示框
        document.addEventListener('click', function() {
            emailTooltip.classList.remove('show');
        });
    }
}

function highlightLoginField(feature) {
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    
    if (!usernameInput || !passwordInput) return;
    
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
        case 'visual':
            passwordInput.classList.add('highlight-input');
            break;
    }
}

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
    
    // 添加发送验证码功能
    const sendVerificationCodeBtn = document.getElementById('reg-send-code');
    if (sendVerificationCodeBtn) {
        // 检查是否存在冷却时间
        const lastSendTime = localStorage.getItem('lastVerificationCodeSentTime');
        const cooldownPeriod = 60 * 1000; // 1分钟冷却
        
        if (lastSendTime) {
            const elapsedTime = Date.now() - parseInt(lastSendTime);
            if (elapsedTime < cooldownPeriod) {
                // 如果在冷却期内，设置按钮状态并开始倒计时
                const remainingSeconds = Math.ceil((cooldownPeriod - elapsedTime) / 1000);
                startCooldown(sendVerificationCodeBtn, remainingSeconds);
            }
        }
        
        sendVerificationCodeBtn.addEventListener('click', function() {
            const email = document.getElementById('reg-email').value;
            
            if (!email) {
                showAuthError('register', 'error', '请输入邮箱地址！');
                return;
            }
            
            // 检查邮箱格式
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                showAuthError('register', 'error', '请输入有效的邮箱地址！');
                return;
            }
            
            // 检查冷却期
            const lastSendTime = localStorage.getItem('lastVerificationCodeSentTime');
            const cooldownPeriod = 60 * 1000; // 1分钟冷却
            
            if (lastSendTime) {
                const elapsedTime = Date.now() - parseInt(lastSendTime);
                if (elapsedTime < cooldownPeriod) {
                    const remainingSeconds = Math.ceil((cooldownPeriod - elapsedTime) / 1000);
                    showAuthError('register', 'error', `请等待 ${remainingSeconds} 秒后再次发送验证码`);
                    
                    // 更新按钮状态，强制开始倒计时
                    startCooldown(this, remainingSeconds);
                    return;
                }
            }
            
            // 显示发送中状态
            const originalText = this.textContent;
            this.textContent = '发送中...';
            this.disabled = true;
            this.style.backgroundColor = '#cccccc';
            
            // 发送获取验证码请求
            fetch('/api/auth/send-register-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            })
            .then(response => response.json())
            .then(data => {
                // 记录发送时间
                localStorage.setItem('lastVerificationCodeSentTime', Date.now());
                
                // 直接显示成功消息，而不通过showAuthError，避免干扰倒计时
                alert(data.message || '验证码已发送，请查收邮件！');
                
                // 开始倒计时
                startCooldown(this, 60);
            })
            .catch(error => {
                console.error('Error:', error);
                this.textContent = originalText;
                this.disabled = false;
                this.style.backgroundColor = '';
                showAuthError('register', 'error', '发送验证码失败，请稍后再试！');
            });
        });
    }
    
    // 重置密码页面验证码按钮也应用相同的冷却逻辑
    const resetPasswordCodeBtn = document.getElementById('sendVerificationCode');
    if (resetPasswordCodeBtn) {
        // 检查是否存在冷却时间
        const lastSendTime = localStorage.getItem('lastResetCodeSentTime');
        const cooldownPeriod = 60 * 1000; // 1分钟冷却
        
        if (lastSendTime) {
            const elapsedTime = Date.now() - parseInt(lastSendTime);
            if (elapsedTime < cooldownPeriod) {
                // 如果在冷却期内，设置按钮状态并开始倒计时
                const remainingSeconds = Math.ceil((cooldownPeriod - elapsedTime) / 1000);
                startCooldown(resetPasswordCodeBtn, remainingSeconds);
            }
        }
    }
}

// 倒计时函数
function startCooldown(button, seconds) {
    // 保存原始文本
    const originalText = button.innerText || button.textContent;
    
    // 确保按钮被禁用，并添加视觉样式
    button.disabled = true;
    button.style.backgroundColor = '#cccccc';
    button.style.cursor = 'not-allowed';
    button.style.opacity = '0.7';
    
    // 设置初始倒计时文本
    button.textContent = `重新发送(${seconds}s)`;
    
    // 清除可能存在的旧计时器
    if (button._cooldownTimer) {
        clearInterval(button._cooldownTimer);
    }
    
    // 创建新的计时器
    button._cooldownTimer = setInterval(() => {
        // 获取当前的数字
        const currentSeconds = parseInt(button.textContent.match(/\d+/)[0]);
        const newCount = currentSeconds - 1;
        
        if (newCount <= 0) {
            // 倒计时结束，恢复按钮状态
            clearInterval(button._cooldownTimer);
            button.textContent = originalText;
            button.disabled = false;
            button.style.backgroundColor = '';
            button.style.cursor = '';
            button.style.opacity = '';
        } else {
            // 更新倒计时显示
            button.textContent = `重新发送(${newCount}s)`;
        }
    }, 1000);
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
                // 使用FontAwesome切换图标（从闭眼变成睁眼）
                iconElement.classList.remove('fa-eye-slash');
                iconElement.classList.add('fa-eye');
            } else {
                passwordInput.type = 'password';
                // 使用FontAwesome切换图标（从睁眼变成闭眼）
                iconElement.classList.remove('fa-eye');
                iconElement.classList.add('fa-eye-slash');
            }
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
        console.log('登录响应数据:', data);
        console.log('登录响应数据类型:', typeof data);
        console.log('登录响应数据结构:', JSON.stringify(data, null, 2));
        
        if (data.token) {
            // 登录成功
            console.log('登录成功，获取到令牌:', data.token);
            
            loginBtn.style.background = 'linear-gradient(45deg, #27ae60, #2ecc71)';
            loginBtn.innerHTML = '登录成功 <span style="margin-left: 5px">✓</span>';
            
            // 保存token和用户信息
            localStorage.setItem('token', data.token);
            console.log('令牌已保存到localStorage:', localStorage.getItem('token'));
            
            // 确保role字段存在
            const role = data.role || (data.is_admin ? 'admin' : 'user');
            console.log('用户角色:', role);
            
            localStorage.setItem('user', JSON.stringify({
                username: data.username,  // 使用响应中的用户名
                public_id: data.public_id,
                user_id: data.user_id,
                email: data.email,
                role: role   // 确保包含role字段
            }));
            
            console.log('用户信息已保存到 localStorage:', JSON.parse(localStorage.getItem('user')));
            
            // 跳转到主页
            setTimeout(() => {
                document.querySelector('.content-wrapper').style.opacity = '0';
                setTimeout(() => {
                    console.log('正在跳转到 search.html');
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
            console.error('登录失败:', data.message || '未知错误');
            showAuthError(loginBtn, '登录', data.message || '邮箱或密码错误！');
        }
    })
    .catch(error => {
        console.error('登录错误:', error);
        showAuthError(loginBtn, '登录', '登录请求失败，请稍后再试！');
    });
    
    return false;
}

// 设置密码强度验证浮窗
function setupPasswordStrengthValidator() {
    const passwordInput = document.getElementById('reg-password');
    const confirmPasswordInput = document.getElementById('reg-confirm-password');
    const popup = document.getElementById('password-strength-popup');
    
    if (!popup || !passwordInput) {
        return;
    }
    
    // 输入框聚焦时显示浮窗
    passwordInput.addEventListener('focus', function() {
        popup.classList.add('show-popup');
    });
    
    // 输入框输入时更新密码强度
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        
        // 检查长度
        const lengthCheck = document.getElementById('length-check');
        const hasLength = password.length >= 8;
        updateCheckIcon(lengthCheck, hasLength);
        
        // 检查是否同时包含字母和数字
        const letterNumberCheck = document.getElementById('letter-check');
        const hasLetterAndNumber = /[a-zA-Z]/.test(password) && /[0-9]/.test(password);
        updateCheckIcon(letterNumberCheck, hasLetterAndNumber);
        
        // 如果输入框有值，显示浮窗；否则隐藏
        if (password.length > 0) {
            popup.classList.add('show-popup');
        } else {
            popup.classList.remove('show-popup');
        }
    });
    
    // 更新检查图标
    function updateCheckIcon(element, isValid) {
        if (!element) return;
        
        const icon = element.querySelector('i');
        if (!icon) return;
        
        if (isValid) {
            icon.className = 'fas fa-check-circle';
            element.classList.add('valid');
            element.classList.remove('invalid');
        } else {
            icon.className = 'fas fa-times-circle';
            element.classList.add('invalid');
            element.classList.remove('valid');
        }
    }
    
    // 点击页面其他区域时隐藏浮窗
    document.addEventListener('click', function(e) {
        if (e.target !== passwordInput && 
            e.target !== confirmPasswordInput && 
            !popup.contains(e.target) &&
            !e.target.closest('.password-toggle')) {
            popup.classList.remove('show-popup');
        }
    });
    
    // 处理切换标签时的浮窗隐藏
    const authTabs = document.querySelectorAll('.auth-tab');
    authTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            popup.classList.remove('show-popup');
        });
    });
}

// 验证注册表单
function validateRegister(event) {
    event.preventDefault();
    
    // 获取表单数据
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const confirmPassword = document.getElementById('reg-confirm-password').value;
    const verificationCode = document.getElementById('reg-verification-code').value;
    
    // 验证邮箱
    if (!email) {
        showAuthError('register', 'error', '请输入邮箱地址');
        return false;
    }
    
    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showAuthError('register', 'error', '请输入有效的邮箱地址');
        return false;
    }
    
    // 验证密码
    if (!password) {
        showAuthError('register', 'error', '请输入密码');
        return false;
    }
    
    // 验证密码长度和复杂度
    const hasLength = password.length >= 8;
    const hasLetterAndNumber = /[a-zA-Z]/.test(password) && /[0-9]/.test(password);
    
    // 如果密码不符合要求
    if (!hasLength || !hasLetterAndNumber) {
        showAuthError('register', 'error', '密码不符合要求，请确保密码至少8位，同时包含字母和数字');
        
        // 强制显示密码强度浮窗并聚焦密码输入框
        const popup = document.getElementById('password-strength-popup');
        const passwordInput = document.getElementById('reg-password');
        
        if (popup && passwordInput) {
            popup.classList.add('show-popup');
            passwordInput.focus();
        }
        
        return false;
    }
    
    // 验证密码确认
    if (password !== confirmPassword) {
        showAuthError('register', 'error', '两次输入的密码不一致');
        return false;
    }
    
    // 验证验证码
    if (!verificationCode) {
        showAuthError('register', 'error', '请输入验证码');
        return false;
    }
    
    // 显示注册中状态
    const registerBtn = document.querySelector('.register-btn');
    const originalText = registerBtn.textContent;
    registerBtn.textContent = '注册中...';
    registerBtn.disabled = true;
    
    // 发送注册请求
    fetch('/api/auth/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            email, 
            password,
            verification_code: verificationCode
        })
    })
    .then(response => {
        // 保存响应状态
        const isSuccess = response.ok;
        return response.json().then(data => {
            return { data, isSuccess };
        });
    })
    .then(({ data, isSuccess }) => {
        // 恢复按钮状态
        registerBtn.textContent = originalText;
        registerBtn.disabled = false;
        
        if (isSuccess) {
            // 显示成功消息
            showSuccessModal('注册成功', data.message || '账号注册成功！请登录您的账号。', () => {
                // 切换到登录标签
                const loginTab = document.querySelector('.auth-tab[data-tab="login"]');
                if (loginTab) {
                    loginTab.click();
                }
                // 重置注册表单
                document.getElementById('registerForm').reset();
            });
        } else {
            // 显示错误信息
            showAuthError('register', 'error', data.message || '注册失败，请稍后再试。');
            
            // 如果是邮箱已注册但未验证，显示验证提示
            if (data.code && data.code === 'email_unverified') {
                showVerificationPrompt(email);
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        registerBtn.textContent = originalText;
        registerBtn.disabled = false;
        showAuthError('register', 'error', '注册请求失败，请检查网络连接或稍后再试。');
    });
    
    return false;
}

// 显示认证错误
function showAuthError(button, type, message, shouldResetButton = true) {
    // 如果是字符串，查找对应的按钮
    if (typeof button === 'string') {
        if (button === 'register') {
            button = document.querySelector('.register-btn');
        } else if (button === 'login') {
            button = document.querySelector('.login-btn');
        }
    }
    
    // 显示错误消息
    alert(message);
    
    // 如果需要重置按钮状态
    if (shouldResetButton) {
        button.style.background = 'linear-gradient(45deg, #e74c3c, #c0392b)';
        button.innerHTML = `${type}失败`;
        
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
}

// 检查登录状态
function checkLoginStatus() {
    console.log('正在检查登录状态...');
    const token = localStorage.getItem('token');
    
    if (token) {
        console.log('找到令牌:', token);
        
        // 验证令牌格式
        const parts = token.split('.');
        if (parts.length !== 3) {
            console.error('令牌格式无效:', token);
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            return;
        }
        
        try {
            // 验证token是否过期
            const tokenData = JSON.parse(atob(token.split('.')[1]));
            console.log('令牌数据:', tokenData);
            
            const expirationTime = tokenData.exp * 1000; // 转换为毫秒
            console.log('过期时间:', new Date(expirationTime).toLocaleString());
            console.log('当前时间:', new Date().toLocaleString());
            
            // 检查当前页面是否是登录页
            const isLoginPage = window.location.pathname === '/' || 
                               window.location.pathname === '/index.html' ||
                               window.location.pathname === '/BioInfo_Nexus_test/' ||
                               window.location.pathname === '/BioInfo_Nexus_test/index.html';
            
            console.log('当前是否为登录页:', isLoginPage);
            
            if (Date.now() < expirationTime) {
                // token有效
                console.log('令牌有效，检查是否需要跳转');
                
                if (isLoginPage) {
                    console.log('当前在登录页面，跳转到主页');
                    window.location.href = 'search.html';
                } else {
                    console.log('当前不在登录页面，不需要跳转');
                }
                return;
            } else {
                console.error('令牌已过期:', new Date(expirationTime).toLocaleString());
            }
        } catch (e) {
            console.error('令牌验证错误:', e);
        }
        
        // token无效或过期，清除本地存储
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    } else {
        console.log('未找到令牌');
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

// 设置忘记密码和重置密码功能
function setupPasswordReset() {
    // 获取元素
    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    
    // 忘记密码链接在HTML中已设置为直接跳转到reset-password.html，不需要阻止默认行为
    // 如果有其他相关模态框逻辑，可在此处进行处理
    
    // 检查URL参数处理逻辑保留不变
    checkResetPasswordToken();
}

// 检查URL参数，如果有重置密码的token，则显示重置密码模态框
function checkResetPasswordToken() {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (token) {
        // 验证token是否有效
        fetch(`/api/auth/verify-reset-token/${token}`)
            .then(response => response.json())
            .then(data => {
                if (data.valid) {
                    // token有效，显示重置密码模态框
                    document.getElementById('resetToken').value = token;
                    document.getElementById('resetPasswordModal').style.display = 'block';
                } else {
                    // token无效，显示错误消息
                    showToast('重置链接无效或已过期，请重新申请。', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('验证重置链接时出错，请稍后再试。', 'error');
            });
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 检查是否已存在toast元素
    let toast = document.querySelector('.toast');
    
    // 如果不存在，创建一个
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    
    // 设置消息和类型
    toast.textContent = message;
    toast.className = `toast ${type}`;
    
    // 显示toast
    toast.style.display = 'block';
    
    // 3秒后隐藏
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// 显示成功弹窗
function showSuccessModal(title, message, callback) {
    // 创建模态框
    const modal = document.createElement('div');
    modal.className = 'success-modal';
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    modal.style.display = 'flex';
    modal.style.justifyContent = 'center';
    modal.style.alignItems = 'center';
    modal.style.zIndex = '1000';
    
    // 创建模态框内容
    const modalContent = document.createElement('div');
    modalContent.style.backgroundColor = '#fff';
    modalContent.style.borderRadius = '8px';
    modalContent.style.padding = '30px';
    modalContent.style.width = '400px';
    modalContent.style.maxWidth = '90%';
    modalContent.style.textAlign = 'center';
    modalContent.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.2)';
    
    // 添加成功图标
    const icon = document.createElement('div');
    icon.innerHTML = '<i class="fas fa-check-circle" style="font-size: 60px; color: #27ae60; margin-bottom: 20px;"></i>';
    
    // 添加标题
    const titleElement = document.createElement('h3');
    titleElement.textContent = title;
    titleElement.style.fontSize = '24px';
    titleElement.style.margin = '10px 0';
    
    // 添加消息
    const messageElement = document.createElement('p');
    messageElement.textContent = message;
    messageElement.style.fontSize = '16px';
    messageElement.style.margin = '15px 0';
    messageElement.style.color = '#555';
    
    // 添加确认按钮
    const button = document.createElement('button');
    button.textContent = '确定';
    button.style.backgroundColor = '#27ae60';
    button.style.color = '#fff';
    button.style.border = 'none';
    button.style.borderRadius = '4px';
    button.style.padding = '10px 20px';
    button.style.fontSize = '16px';
    button.style.cursor = 'pointer';
    button.style.marginTop = '20px';
    button.style.transition = 'background-color 0.3s';
    
    button.addEventListener('mouseover', function() {
        this.style.backgroundColor = '#2ecc71';
    });
    
    button.addEventListener('mouseout', function() {
        this.style.backgroundColor = '#27ae60';
    });
    
    button.addEventListener('click', function() {
        document.body.removeChild(modal);
        if (typeof callback === 'function') {
            callback();
        }
    });
    
    // 组装模态框
    modalContent.appendChild(icon);
    modalContent.appendChild(titleElement);
    modalContent.appendChild(messageElement);
    modalContent.appendChild(button);
    modal.appendChild(modalContent);
    
    // 添加到页面
    document.body.appendChild(modal);
    
    // 添加动画效果
    modalContent.style.transform = 'scale(0.7)';
    modalContent.style.opacity = '0';
    modalContent.style.transition = 'all 0.3s ease-out';
    
    setTimeout(function() {
        modalContent.style.transform = 'scale(1)';
        modalContent.style.opacity = '1';
    }, 10);
}

