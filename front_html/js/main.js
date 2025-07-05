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
    setupAgreementLinks();
    setupPricingButtons();
    
    // 检查URL参数，如果有重置密码的token，则显示重置密码模态框
    checkResetPasswordToken();
    
    // 初始化cookie同意横幅
    cookieConsentManager.init();
    
    // 设置页面上下文
    setContextText();
});

// 设置 fetch 请求拦截器，为所有 API 请求自动添加 Authorization 头
function setupFetchInterceptor() {
    // 保存原始的 fetch 函数
    const originalFetch = window.fetch;
    
    // 重写 fetch 函数
    window.fetch = function(url, options = {}) {
        // 获取存储的令牌 - 每次请求时都重新获取，确保使用最新的
        const token = cookieUtils.getCookie('auth_token');
        
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
                            console.error('认证失败，清除cookie令牌');
                            cookieUtils.deleteCookie('auth_token');
                            cookieUtils.deleteCookie('username');
                            cookieUtils.deleteCookie('isAdmin');
                            cookieUtils.deleteCookie('loginTime');
                            
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
            
            // 保存token和用户信息到cookies
            authUtils.saveToken(data.token, data.username, data.is_admin);
            console.log('令牌已保存到cookies:', cookieUtils.getCookie('auth_token'));
            
            // 确保role字段存在
            const role = data.role || (data.is_admin ? 'admin' : 'user');
            console.log('用户角色:', role);
            
            // 保存额外的用户信息到cookies（如果需要）
            if (data.email) {
                cookieUtils.setCookie('user_email', data.email, 7, false);
            }
            if (data.public_id) {
                cookieUtils.setCookie('user_public_id', data.public_id, 7, false);
            }
            if (data.user_id) {
                cookieUtils.setCookie('user_id', data.user_id, 7, false);
            }
            
            console.log('用户信息已保存到cookies');
            
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
    
    // 验证用户协议同意
    const agreementCheckbox = document.getElementById('agreement-checkbox');
    if (!agreementCheckbox.checked) {
        showAuthError('register', 'error', '请先阅读并同意用户协议、隐私政策和产品服务协议');
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
    const token = cookieUtils.getCookie('auth_token');
    
    if (token) {
        console.log('找到令牌:', token);
        
        // 验证令牌格式
        const parts = token.split('.');
        if (parts.length !== 3) {
            console.error('令牌格式无效:', token);
            cookieUtils.deleteCookie('auth_token');
            cookieUtils.deleteCookie('username');
            cookieUtils.deleteCookie('isAdmin');
            cookieUtils.deleteCookie('loginTime');
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
        
        // token无效或过期，清除cookies
        cookieUtils.deleteCookie('auth_token');
        cookieUtils.deleteCookie('username');
        cookieUtils.deleteCookie('isAdmin');
        cookieUtils.deleteCookie('loginTime');
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

// 登录/注册模态框交互逻辑 (Moved from index.html)
document.addEventListener('DOMContentLoaded', function() {
    const loginBtn = document.getElementById('loginBtn');
    const getStartedBtn = document.getElementById('getStartedBtn');
    const aiAssistantBtn = document.getElementById('aiAssistantBtn');
    const loginModal = document.getElementById('loginModal');
    const closeModal = document.querySelector('.close-modal');
    const authTabs = document.querySelectorAll('.auth-tab');
    
    // 点击登录按钮打开模态框
    if (loginBtn) {
        loginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (loginModal) loginModal.classList.add('show');
        });
    }
    
    // 点击开始使用按钮打开模态框
    if (getStartedBtn) {
        getStartedBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (loginModal) loginModal.classList.add('show');
        });
    }
    
    // 点击体验AI助手按钮打开模态框并切换到注册页面
    if (aiAssistantBtn) {
        aiAssistantBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (loginModal) {
                loginModal.classList.add('show');
                
                // 切换到注册标签
                const registerTab = document.querySelector('[data-tab="register"]');
                const loginTab = document.querySelector('[data-tab="login"]');
                const registerContent = document.getElementById('registerTab');
                const loginContent = document.getElementById('loginTab');
                
                if (registerTab && loginTab && registerContent && loginContent) {
                    // 移除所有活动状态
                    authTabs.forEach(tab => tab.classList.remove('active'));
                    document.querySelectorAll('.auth-content').forEach(content => {
                        content.classList.remove('active');
                    });
                    
                    // 激活注册标签和内容
                    registerTab.classList.add('active');
                    registerContent.classList.add('active');
                }
            }
        });
    }
    
    // 点击关闭按钮关闭模态框
    if (closeModal) {
        closeModal.addEventListener('click', function() {
            if (loginModal) loginModal.classList.remove('show');
        });
    }
    
    // 点击模态框外部关闭模态框
    if (loginModal) {
        loginModal.addEventListener('click', function(e) {
            if (e.target === loginModal) {
                loginModal.classList.remove('show');
            }
        });
    }
    
    // 切换登录/注册标签
    if (authTabs.length > 0) {
        authTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const tabId = this.getAttribute('data-tab');
                
                // 移除所有标签的活动状态
                authTabs.forEach(tab => tab.classList.remove('active'));
                
                // 隐藏所有内容区域
                document.querySelectorAll('.auth-content').forEach(content => {
                    content.classList.remove('active');
                });
                
                // 激活当前标签
                this.classList.add('active');
                
                // 显示对应的内容区域
                const targetTabContent = document.getElementById(tabId + 'Tab');
                if (targetTabContent) targetTabContent.classList.add('active');
            });
        });
    }
});

// 滚动到指定区域的函数
function scrollToSection(selector) {
    const section = document.querySelector(selector);
    if (section) {
        window.scrollTo({
            top: section.offsetTop,
            behavior: 'smooth'
        });
    }
}

// 设置协议链接功能
function setupAgreementLinks() {
    const agreementLinks = document.querySelectorAll('.agreement-link');
    
    agreementLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const agreementType = this.getAttribute('data-agreement');
            showAgreementModal(agreementType);
        });
    });
}

// 显示协议模态框
function showAgreementModal(type) {
    let title, content;
    
    switch(type) {
        case 'user':
            title = '用户协议';
            content = getUserAgreement();
            break;
        case 'privacy':
            title = '隐私政策';
            content = getPrivacyPolicy();
            break;
        case 'service':
            title = '产品服务协议';
            content = getServiceAgreement();
            break;
        default:
            return;
    }
    
    // 创建模态框
    const modal = document.createElement('div');
    modal.className = 'modal agreement-modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content agreement-content">
            <span class="close-modal agreement-close">&times;</span>
            <h2>${title}</h2>
            <div class="agreement-text">
                ${content}
            </div>
            <div class="agreement-actions">
                <button class="btn-primary agreement-confirm">我已阅读</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 添加关闭事件
    const closeBtn = modal.querySelector('.agreement-close');
    const confirmBtn = modal.querySelector('.agreement-confirm');
    
    closeBtn.addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    confirmBtn.addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    // 点击模态框外部关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

// 用户协议内容
function getUserAgreement() {
    return `
        <h3>1. 服务条款的接受</h3>
        <p>欢迎使用BioInfo Nexus平台。在使用我们的服务之前，请仔细阅读以下服务条款。通过注册、访问或使用我们的服务，您表示同意受这些条款的约束。</p>
        
        <h3>2. 服务描述</h3>
        <p>BioInfo Nexus是一个专业的生物信息学集成平台，提供以下服务：</p>
        <ul>
            <li>序列分析工具（包括但不限于序列比对、结构预测、功能注释等）</li>
            <li>生物数据库查询服务</li>
            <li>基于AI的生物学知识问答</li>
            <li>其他相关的生物信息学分析工具</li>
        </ul>
        
        <h3>3. 用户责任</h3>
        <p>作为用户，您同意：</p>
        <ul>
            <li>提供准确、完整的注册信息</li>
            <li>保护您的账户安全，不与他人共享登录凭据</li>
            <li>仅将服务用于合法的科研和学术目的</li>
            <li>不上传恶意软件、病毒或其他有害内容</li>
            <li>尊重知识产权，不侵犯他人权利</li>
            <li>遵守相关法律法规和学术伦理规范</li>
        </ul>
        
        <h3>4. 禁止行为</h3>
        <p>严禁以下行为：</p>
        <ul>
            <li>利用服务进行任何非法活动</li>
            <li>试图破坏、干扰或未经授权访问系统</li>
            <li>恶意使用服务资源，影响其他用户正常使用</li>
            <li>传播虚假、误导性或有害信息</li>
            <li>商业化使用免费服务</li>
        </ul>
        
        <h3>5. 知识产权</h3>
        <p>本平台的所有内容，包括但不限于软件、界面设计、文档、数据等，均受知识产权法保护。未经许可，不得复制、修改、分发或商业化使用。</p>
        
        <h3>6. 免责声明</h3>
        <p>本服务按"现状"提供，我们不对服务的可用性、准确性或完整性作任何明示或暗示的保证。用户使用服务的风险由其自行承担。</p>
        
        <h3>7. 服务变更与终止</h3>
        <p>我们保留随时修改、暂停或终止服务的权利。对于服务的变更，我们将尽力提前通知用户。</p>
        
        <h3>8. 争议解决</h3>
        <p>因使用本服务产生的争议，应通过友好协商解决。协商不成的，提交有管辖权的人民法院解决。</p>
        
        <h3>9. 条款修订</h3>
        <p>我们可能会不时更新这些条款。修订后的条款将在平台上公布，继续使用服务即表示接受修订后的条款。</p>
        
        <p><strong>生效日期：2025年1月1日</strong></p>
    `;
}

// 隐私政策内容
function getPrivacyPolicy() {
    return `
        <h3>1. 信息收集</h3>
        <p>我们收集以下类型的信息：</p>
        <ul>
            <li><strong>账户信息：</strong>邮箱地址、密码（加密存储）</li>
            <li><strong>使用数据：</strong>分析历史、查询记录、偏好设置</li>
            <li><strong>技术信息：</strong>IP地址、浏览器类型、操作系统、访问时间</li>
            <li><strong>分析数据：</strong>您上传的序列数据和分析结果</li>
        </ul>
        
        <h3>2. 信息使用</h3>
        <p>我们使用收集的信息用于：</p>
        <ul>
            <li>提供和改进我们的服务</li>
            <li>个性化用户体验</li>
            <li>技术支持和故障排除</li>
            <li>安全监控和防欺诈</li>
            <li>发送重要通知和更新</li>
            <li>数据统计和分析（匿名化处理）</li>
        </ul>
        
        <h3>3. 信息共享</h3>
        <p>我们不会出售、出租或交易您的个人信息。仅在以下情况下可能共享信息：</p>
        <ul>
            <li>获得您的明确同意</li>
            <li>法律要求或执法部门要求</li>
            <li>保护我们的权利和安全</li>
            <li>与可信的第三方服务提供商（已签署保密协议）</li>
        </ul>
        
        <h3>4. 数据安全</h3>
        <p>我们采取以下措施保护您的数据：</p>
        <ul>
            <li>SSL加密传输</li>
            <li>密码加密存储</li>
            <li>定期安全审计</li>
            <li>访问控制和权限管理</li>
            <li>数据备份和恢复机制</li>
        </ul>
        
        <h3>5. 数据保存</h3>
        <p>我们保存您的数据期限：</p>
        <ul>
            <li>账户信息：账户存续期间</li>
            <li>分析数据：用户可自主删除，我们最多保存2年</li>
            <li>日志数据：最多保存1年</li>
            <li>匿名统计数据：可长期保存</li>
        </ul>
        
        <h3>6. 您的权利</h3>
        <p>您有权：</p>
        <ul>
            <li>查看和更新您的个人信息</li>
            <li>删除您的账户和相关数据</li>
            <li>导出您的数据</li>
            <li>限制某些数据处理</li>
            <li>撤回同意（在适用情况下）</li>
        </ul>
        
        <h3>7. Cookie和跟踪技术</h3>
        <p>我们使用Cookie和类似技术来：</p>
        <ul>
            <li>记住您的登录状态</li>
            <li>保存您的偏好设置</li>
            <li>分析网站使用情况</li>
            <li>提供个性化内容</li>
        </ul>
        
        <h3>8. 第三方服务</h3>
        <p>我们可能集成第三方服务（如AI模型），这些服务有自己的隐私政策。我们建议您也阅读相关的第三方隐私政策。</p>
        
        <h3>9. 未成年人保护</h3>
        <p>我们的服务主要面向成年用户。如果您未满18岁，请在监护人同意下使用我们的服务。</p>
        
        <h3>10. 政策更新</h3>
        <p>我们可能会更新此隐私政策。重大变更会通过邮件或网站公告通知用户。</p>
        
        <h3>11. 联系我们</h3>
        <p>如有隐私相关问题，请联系：bioinfo.nexus@example.com</p>
        
        <p><strong>生效日期：2025年1月1日</strong></p>
    `;
}

// 产品服务协议内容
function getServiceAgreement() {
    return `
        <h3>1. 服务级别</h3>
        <p>我们提供以下服务级别：</p>
        <ul>
            <li><strong>免费服务：</strong>基础分析工具，有使用频率限制</li>
            <li><strong>会员服务：</strong>高级功能，更高的使用限额，优先支持</li>
            <li><strong>API服务：</strong>程序化访问接口，适用于批量处理</li>
        </ul>
        
        <h3>2. 服务可用性</h3>
        <p>我们努力保证服务的可用性，但不保证服务100%可用。可能因以下原因暂时中断：</p>
        <ul>
            <li>定期维护和更新</li>
            <li>技术故障</li>
            <li>网络问题</li>
            <li>不可抗力因素</li>
        </ul>
        
        <h3>3. 使用限制</h3>
        <p>为确保服务质量，我们对使用进行以下限制：</p>
        <ul>
            <li><strong>免费用户：</strong>每日最多50次分析请求</li>
            <li><strong>序列大小：</strong>单次分析最大50MB</li>
            <li><strong>并发请求：</strong>同时最多5个分析任务</li>
            <li><strong>存储限制：</strong>历史数据最多保存100个项目</li>
        </ul>
        
        <h3>4. 数据处理</h3>
        <p>关于您提交的数据：</p>
        <ul>
            <li>我们仅为提供服务而处理您的数据</li>
            <li>分析过程中的临时数据会在24小时内自动删除</li>
            <li>您可以随时删除保存的结果</li>
            <li>我们不会将您的序列数据用于其他目的</li>
        </ul>
        
        <h3>5. 质量保证</h3>
        <p>我们努力提供准确的分析结果，但：</p>
        <ul>
            <li>结果仅供科研参考，不构成医疗建议</li>
            <li>用户应验证重要结果</li>
            <li>我们不对基于结果的决策承担责任</li>
            <li>算法和数据库会定期更新，结果可能有变化</li>
        </ul>
        
        <h3>6. 付费服务</h3>
        <p>对于付费服务：</p>
        <ul>
            <li>费用按月或年收取</li>
            <li>支持常见的支付方式</li>
            <li>可随时取消订阅</li>
            <li>退款政策：30天内可申请全额退款</li>
        </ul>
        
        <h3>7. 技术支持</h3>
        <p>我们提供：</p>
        <ul>
            <li>在线文档和教程</li>
            <li>邮件技术支持</li>
            <li>会员用户享有优先支持</li>
            <li>工作日24小时内响应</li>
        </ul>
        
        <h3>8. 服务变更</h3>
        <p>我们可能会：</p>
        <ul>
            <li>增加新功能和工具</li>
            <li>调整使用限制</li>
            <li>修改价格（提前30天通知）</li>
            <li>停止某些功能（提前90天通知）</li>
        </ul>
        
        <h3>9. 责任限制</h3>
        <p>在法律允许的最大范围内：</p>
        <ul>
            <li>我们的责任仅限于提供服务</li>
            <li>不对间接损失承担责任</li>
            <li>赔偿上限为您支付的服务费用</li>
            <li>不保证服务满足您的特定需求</li>
        </ul>
        
        <h3>10. 合规要求</h3>
        <p>用户使用服务时应：</p>
        <ul>
            <li>遵守所在地区的法律法规</li>
            <li>获得必要的数据使用许可</li>
            <li>尊重他人的知识产权</li>
            <li>不用于危害公共安全的目的</li>
        </ul>
        
        <p><strong>生效日期：2025年1月1日</strong></p>
    `;
}

// 设置页面上下文文本
function setContextText() {
    const contextElement = document.getElementById('context-text');
    if (contextElement) {
        contextElement.textContent = '进入生物信息学数据分析和AI辅助研究平台，探索前沿科学工具。';
    }
}

// 设置会员卡片按钮事件
function setupPricingButtons() {
    const pricingButtons = document.querySelectorAll('.pricing-btn.primary');
    
    pricingButtons.forEach(button => {
        button.addEventListener('click', function() {
            const card = this.closest('.pricing-card');
            const planName = card.querySelector('h3').textContent;
            
            // 检查用户是否已登录
            const token = cookieUtils.getCookie('auth_token');
            
            if (!token) {
                // 未登录，显示登录模态窗口
                const modal = document.getElementById('loginModal');
                if (modal) {
                    modal.style.display = 'block';
                    modal.classList.add('show');
                }
                showToast('请先登录以升级会员', 'info');
                return;
            }
            
            // 已登录，显示升级提示
            showToast(`正在处理 ${planName} 升级...`, 'info');
            
            // 这里可以添加实际的升级逻辑
            setTimeout(() => {
                showToast('升级功能正在开发中，敬请期待！', 'info');
            }, 1000);
        });
    });
}



