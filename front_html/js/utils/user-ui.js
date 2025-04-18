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
        return null;
    }
    
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
        const token = localStorage.getItem('token');
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
            <div class="dropdown-divider"></div>
            <a href="/profile.html"><i class="fas fa-user-circle"></i> 个人资料</a>
            ${user.is_admin || user.role === 'admin' ? '<a href="/admin.html"><i class="fas fa-cog"></i> 管理控制台</a>' : ''}
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
        .membership-badge.plus {
            background-color: #e6f7ff;
            color: #1890ff;
            border: 1px solid #91d5ff;
        }
        .membership-badge.premium {
            background-color: #fff7e6;
            color: #fa8c16;
            border: 1px solid #ffd591;
        }
        .membership-expiry {
            font-size: 11px;
            color: #888;
            margin-top: 4px;
        }
    `;
    document.head.appendChild(styleEl);
} 