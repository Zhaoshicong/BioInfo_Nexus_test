// user-ui.js - 用户界面相关共享函数
// 提供用户信息、会员状态显示等共用功能

/**
 * 获取并显示会员状态
 * @param {Object} userMenu - 包含会员状态展示区域的用户菜单DOM元素
 * @param {Object} user - 用户信息对象
 * @returns {Promise<Object>} - 会员信息对象
 */
export async function updateMembershipStatus(userMenu, user) {
    const membershipInfo = await getMembershipInfo(user);
    const membershipStatus = userMenu.querySelector('.membership-badge');
    if (!membershipStatus) return membershipInfo;
    
    if (!membershipInfo) {
        membershipStatus.textContent = '普通会员';
        membershipStatus.className = 'membership-badge free';
    } else {
        let level = membershipInfo.membership_level || membershipInfo.level || 'free';
        level = level.toLowerCase();
        
        // 根据会员级别设置显示内容和样式
        if (level === 'plus') {
            membershipStatus.textContent = 'Plus会员';
            membershipStatus.className = 'membership-badge plus';
        } else if (level === 'premium') {
            membershipStatus.textContent = 'Premium会员';
            membershipStatus.className = 'membership-badge premium';
        } else {
            membershipStatus.textContent = '普通会员';
            membershipStatus.className = 'membership-badge free';
        }
        
        // 如果有过期日期，添加到显示
        if (membershipInfo.expiry_date) {
            const expiryDate = new Date(membershipInfo.expiry_date);
            const today = new Date();
            if (expiryDate > today) {
                const daysLeft = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
                const expiryInfo = document.createElement('div');
                expiryInfo.className = 'membership-expiry';
                expiryInfo.textContent = `有效期: 还剩${daysLeft}天`;
                userMenu.querySelector('.membership-status').appendChild(expiryInfo);
            }
        }
    }
    
    // 获取并显示AI使用情况（异步执行，不阻塞主流程）
    setTimeout(async () => {
        try {
            const aiUsageInfo = await getAIUsageInfo();
            if (aiUsageInfo) {
                displayAIUsageInMenu(userMenu, aiUsageInfo);
            }
        } catch (error) {
            console.warn('获取AI使用情况失败:', error);
        }
    }, 100);
    
    return membershipInfo;
}

/**
 * 获取会员状态信息
 * @param {Object} user - 用户信息对象
 * @returns {Promise<Object>} - 会员信息对象
 */
export async function getMembershipInfo(user) {
    try {
        // 如果已有会员信息则直接使用
        if (user.membership_level) {
            return {
                level: user.membership_level,
                is_active: user.membership_active || true
            };
        }
        
        // 否则通过API获取会员信息
        let token;
        if (typeof cookieUtils !== 'undefined') {
            token = cookieUtils.getCookie('auth_token');
        } else {
            token = getCookie('auth_token');
        }
        if (!token) return null;
        
        const response = await fetch('/api/membership/status', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            console.log('获取会员状态失败:', response.status);
            return null;
        }
        
        const data = await response.json();
        console.log('会员状态:', data);
        return data;
    } catch (error) {
        console.error('获取会员状态出错:', error);
        return null;
    }
}

/**
 * 创建用户下拉菜单
 * @param {Element} navLinks - 导航链接容器
 * @param {Object} user - 用户信息对象
 * @param {Function} logoutHandler - 注销处理函数
 * @returns {Element} - 创建的用户菜单元素
 */
export function createUserMenu(navLinks, user, logoutHandler) {
    if (!navLinks || !user) return null;
    
    // 如果已存在用户菜单，则不重复创建
    if (navLinks.querySelector('.user-menu')) {
        return navLinks.querySelector('.user-menu');
    }
    
    const userMenu = document.createElement('div');
    userMenu.className = 'user-menu';
    
    // 创建下拉菜单的HTML
    userMenu.innerHTML = `
        <span class="username">${user.username}</span>
        <div class="dropdown-menu">
            <div class="dropdown-header">
                <div class="user-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="user-info">
                    <div class="user-name">${user.username}</div>
                    <div class="user-email">${user.email || ''}</div>
                </div>
            </div>
            <div class="membership-info">
                <div class="membership-status">
                    <span class="membership-badge">加载中...</span>
                </div>
            </div>
            <!--<div class="dropdown-divider"></div> 
            <a href="/profile.html"><i class="fas fa-user-circle"></i> 个人资料</a> -->
            <div class="dropdown-divider"></div>
            ${(user.is_admin === true || user.is_admin === 1 || user.role === 'admin') ? '<a href="/admin.html"><i class="fas fa-cog"></i> 管理控制台</a>' : ''}
            <a href="#" id="logoutBtn"><i class="fas fa-sign-out-alt"></i> 注销</a>
        </div>
    `;
    
    navLinks.appendChild(userMenu);
    
    // 绑定注销按钮事件
    const logoutBtn = userMenu.querySelector('#logoutBtn');
    if (logoutBtn && logoutHandler) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logoutHandler();
        });
    }
    
    return userMenu;
}

/**
 * 添加会员状态样式
 */
export function addMembershipStyles() {
    if (document.getElementById('membership-styles')) return;
    
    const styleEl = document.createElement('style');
    styleEl.id = 'membership-styles';
    styleEl.textContent = `
        .membership-info {
            padding: 10px 16px;
            border-bottom: 1px solid #f0f0f0;
        }
        .membership-status {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .membership-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            text-align: center;
        }
        .membership-badge.free {
            background-color: #e9ecef;
            color: #495057;
        }
        .membership-expiry {
            font-size: 11px;
            color: #888;
            margin-top: 4px;
        }
    `;
    document.head.appendChild(styleEl);
} 

/**
 * 获取AI使用情况
 * @returns {Promise<Object>} - AI使用情况对象
 */
async function getAIUsageInfo() {
    try {
        // 获取token，优先使用全局cookieUtils，如果不存在则使用简单的cookie获取方法
        let token;
        if (typeof cookieUtils !== 'undefined') {
            token = cookieUtils.getCookie('auth_token');
        } else {
            token = getCookie('auth_token');
        }
        
        const response = await fetch('/api/membership/ai-usage', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        if (data.message) {
            throw new Error(data.message);
        }
        
        return data;
    } catch (error) {
        console.error('获取AI使用情况失败:', error);
        return null;
    }
}

/**
 * 在用户菜单中显示AI使用情况
 * @param {Element} userMenu - 用户菜单元素
 * @param {Object} aiUsage - AI使用情况数据
 */
function displayAIUsageInMenu(userMenu, aiUsage) {
    const membershipInfo = userMenu.querySelector('.membership-info');
    if (!membershipInfo) return;
    
    // 移除现有的AI使用信息
    const existingAIInfo = membershipInfo.querySelector('.ai-usage-info');
    if (existingAIInfo) {
        existingAIInfo.remove();
    }
    
    // 创建AI使用信息元素
    const aiUsageDiv = document.createElement('div');
    aiUsageDiv.className = 'ai-usage-info';
    
    let usageText = '';
    let usageClass = 'ai-usage-normal';
    
    if (aiUsage.unlimited || aiUsage.monthly_limit === -1) {
        usageText = `AI分析: 无限制使用`;
        usageClass = 'ai-usage-unlimited';
    } else {
        const percentage = aiUsage.usage_percentage || 0;
        usageText = `AI分析: ${aiUsage.current_usage}/${aiUsage.monthly_limit}`;
        
        if (percentage >= 90) {
            usageClass = 'ai-usage-danger';
        } else if (percentage >= 70) {
            usageClass = 'ai-usage-warning';
        }
    }
    
    aiUsageDiv.innerHTML = `
        <div class="ai-usage-status ${usageClass}">
            <i class="fas fa-brain"></i>
            <span class="usage-text">${usageText}</span>
        </div>
        ${!aiUsage.unlimited && aiUsage.monthly_limit > 0 ? `
            <div class="ai-usage-bar">
                <div class="ai-usage-progress" style="width: ${Math.min(aiUsage.usage_percentage || 0, 100)}%"></div>
            </div>
        ` : ''}
    `;
    
    membershipInfo.appendChild(aiUsageDiv);
}

/**
 * 简单的获取Cookie函数（备用）
 * @param {string} name - Cookie名称
 * @returns {string|null} - Cookie值
 */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// 自动加载用户状态
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM加载完成，初始化用户UI');
    
    // 初始化cookie同意横幅
    if (typeof cookieConsentManager !== 'undefined') {
        cookieConsentManager.init();
    }
}); 