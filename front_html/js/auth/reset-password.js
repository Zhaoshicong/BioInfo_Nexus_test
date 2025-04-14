document.addEventListener('DOMContentLoaded', function() {
    // 设置密码可见性切换
    setupPasswordToggles();
    
    // 设置发送验证码功能
    setupVerificationCode();
    
    // 设置密码强度验证
    setupPasswordStrengthValidator();
    
    // 处理表单提交
    setupResetForm();
});

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

// 设置发送验证码功能
function setupVerificationCode() {
    const sendCodeBtn = document.getElementById('sendVerificationCode');
    if (sendCodeBtn) {
        // 检查是否存在冷却时间
        const lastSendTime = localStorage.getItem('lastResetCodeSentTime');
        const cooldownPeriod = 60 * 1000; // 1分钟冷却
        
        if (lastSendTime) {
            const elapsedTime = Date.now() - parseInt(lastSendTime);
            if (elapsedTime < cooldownPeriod) {
                // 如果在冷却期内，设置按钮状态并开始倒计时
                const remainingSeconds = Math.ceil((cooldownPeriod - elapsedTime) / 1000);
                startCooldown(sendCodeBtn, remainingSeconds);
            }
        }
        
        sendCodeBtn.addEventListener('click', function() {
            const email = document.getElementById('resetEmail').value;
            if (!email) {
                showMessage('请输入邮箱地址！', 'error');
                return;
            }
            
            // 检查邮箱格式
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                showMessage('请输入有效的邮箱地址！', 'error');
                return;
            }
            
            // 检查冷却期
            const lastSendTime = localStorage.getItem('lastResetCodeSentTime');
            const cooldownPeriod = 60 * 1000; // 1分钟冷却
            
            if (lastSendTime) {
                const elapsedTime = Date.now() - parseInt(lastSendTime);
                if (elapsedTime < cooldownPeriod) {
                    const remainingSeconds = Math.ceil((cooldownPeriod - elapsedTime) / 1000);
                    showMessage(`请等待 ${remainingSeconds} 秒后再次发送验证码`, 'error');
                    // 强制更新按钮状态
                    startCooldown(this, remainingSeconds);
                    return;
                }
            }
            
            // 显示发送中状态
            const originalText = this.textContent;
            this.textContent = '发送中...';
            this.disabled = true;
            this.style.backgroundColor = '#cccccc';
            this.style.cursor = 'not-allowed';
            
            // 发送获取验证码请求
            console.log('正在发送重置密码验证码请求，邮箱:', email);
            fetch('/api/auth/forgot-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            })
            .then(response => {
                console.log('验证码请求响应状态:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('验证码请求响应数据:', data);
                
                // 记录发送时间
                localStorage.setItem('lastResetCodeSentTime', Date.now());
                
                // 显示结果消息
                showMessage(data.message || '验证码已发送，请查收邮件！', 'success');
                
                // 开始倒计时
                startCooldown(this, 60);
            })
            .catch(error => {
                console.error('验证码请求错误:', error);
                this.textContent = originalText;
                this.disabled = false;
                this.style.backgroundColor = '';
                this.style.cursor = '';
                showMessage('发送验证码失败，请稍后再试！', 'error');
            });
        });
    }
}

// 设置密码强度验证
function setupPasswordStrengthValidator() {
    const passwordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmNewPassword');
    const popup = document.getElementById('password-strength-popup');
    
    if (!popup || !passwordInput) {
        console.error('找不到密码强度浮窗或密码输入框');
        return;
    }
    
    console.log('初始化密码强度验证浮窗');
    
    // 调整浮窗位置
    function updatePopupPosition() {
        if (passwordInput && popup) {
            const rect = passwordInput.getBoundingClientRect();
            popup.style.top = (rect.bottom + 5) + 'px';
            popup.style.left = rect.left + 'px';
        }
    }
    
    // 初始调整位置
    updatePopupPosition();
    
    // 窗口大小改变时重新调整位置
    window.addEventListener('resize', updatePopupPosition);
    
    // 输入框聚焦时显示浮窗
    passwordInput.addEventListener('focus', function() {
        updatePopupPosition();
        popup.classList.add('show-popup');
        console.log('输入框聚焦，显示浮窗');
    });
    
    // 输入框输入时更新密码强度
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        
        // 检查长度
        const lengthCheck = document.getElementById('length-check');
        const hasLength = password.length >= 8 ;
        updateCheckIcon(lengthCheck, hasLength);
        
        // 检查是否同时包含字母和数字
        const letterNumberCheck = document.getElementById('letter-check');
        const hasLetterAndNumber = /[a-zA-Z]/.test(password) && /[0-9]/.test(password);
        updateCheckIcon(letterNumberCheck, hasLetterAndNumber);
        
        // 如果输入框有值，显示浮窗；否则隐藏
        if (password.length > 0) {
            popup.classList.add('show-popup');
            updatePopupPosition();
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
            !popup.contains(e.target)) {
            popup.classList.remove('show-popup');
        }
    });
}

// 处理表单提交
function setupResetForm() {
    const resetForm = document.getElementById('resetPasswordForm');
    if (!resetForm) {
        console.error('找不到重置密码表单');
        return;
    }
    
    resetForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const email = document.getElementById('resetEmail').value;
        const verificationCode = document.getElementById('verificationCode').value;
        const password = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmNewPassword').value;
        
        // 验证邮箱
        if (!email) {
            showMessage('请输入邮箱地址！', 'error');
            return;
        }
        
        // 验证验证码
        if (!verificationCode) {
            showMessage('请输入验证码！', 'error');
            return;
        }
        
        // 验证密码
        if (!password) {
            showMessage('请输入新密码！', 'error');
            return;
        }
        
        if (password !== confirmPassword) {
            showMessage('两次输入的密码不一致！', 'error');
            return;
        }
        
        // 验证密码强度 - 添加这部分以确保表单验证仍然工作
        const hasLength = password.length >= 6 && password.length <= 20;
        const hasLetter = /[a-zA-Z]/.test(password);
        const hasNumber = /[0-9]/.test(password);
        
        if (!hasLength || !hasLetter || !hasNumber) {
            showMessage('密码不符合强度要求，请确保密码6-20位，包含字母和数字！', 'error');
            return false;
        }
        
        // 显示加载状态
        const submitBtn = resetForm.querySelector('.reset-btn');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = '重置中...';
        submitBtn.disabled = true;
        
        // 发送重置密码请求
        fetch('/api/auth/reset-password-with-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                email,
                verification_code: verificationCode,
                password 
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
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
            
            if (isSuccess) {
                showMessage(data.message || '密码重置成功！您现在可以使用新密码登录。', 'success');
                
                // 清空表单
                resetForm.reset();
                
                // 3秒后重定向到登录页面
                setTimeout(() => {
                    window.location.href = '/';
                }, 3000);
            } else {
                showMessage(data.message || '重置密码失败，请稍后再试。', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
            showMessage('重置密码时出错，请稍后再试。', 'error');
        });
    });
}

// 倒计时函数
function startCooldown(button, seconds) {
    // 保存原始文本
    const originalText = button.textContent || '发送验证码';
    
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

// 显示消息
function showMessage(message, type) {
    const messageElement = document.getElementById('resetMessage');
    messageElement.textContent = message;
    messageElement.className = `message ${type}`;
}