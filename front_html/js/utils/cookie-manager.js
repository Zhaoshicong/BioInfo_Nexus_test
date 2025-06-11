// Cookie工具函数
const cookieUtils = {
    // 设置cookie
    setCookie(name, value, days = 7, secure = true, httpOnly = false) {
        let expires = '';
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = '; expires=' + date.toUTCString();
        }
        
        let cookieString = `${name}=${encodeURIComponent(value)}${expires}; path=/`;
        
        // 如果是HTTPS环境，设置secure标志
        if (secure && window.location.protocol === 'https:') {
            cookieString += '; secure';
        }
        
        // 设置SameSite
        cookieString += '; samesite=lax';
        
        document.cookie = cookieString;
    },
    
    // 获取cookie
    getCookie(name) {
        const nameEQ = name + '=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) {
                return decodeURIComponent(c.substring(nameEQ.length, c.length));
            }
        }
        return null;
    },
    
    // 删除cookie
    deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    },
    
    // 检查cookie是否存在
    hasCookie(name) {
        return this.getCookie(name) !== null;
    }
};

// Cookie 同意横幅管理
const cookieConsentManager = {
    init() {
        // 检查是否已经同意cookies
        if (!cookieUtils.getCookie('cookie_consent')) {
            this.showBanner();
        }
        
        // 绑定事件
        this.bindEvents();
    },
    
    showBanner() {
        const banner = document.getElementById('cookieConsentBanner');
        if (banner) {
            setTimeout(() => {
                banner.classList.add('show');
            }, 1000); // 页面加载1秒后显示
        }
    },
    
    hideBanner() {
        const banner = document.getElementById('cookieConsentBanner');
        if (banner) {
            banner.classList.remove('show');
        }
    },
    
    acceptCookies() {
        // 设置同意cookie，1年过期
        cookieUtils.setCookie('cookie_consent', 'accepted', 365, false);
        this.hideBanner();
        
        // 可以在这里启用其他分析或跟踪脚本
        console.log('用户已同意使用cookies');
    },
    
    manageCookies() {
        // 这里可以打开更详细的cookie设置页面
        alert('Cookie管理功能正在开发中，如有疑问请联系客服。');
    },
    
    bindEvents() {
        const acceptBtn = document.getElementById('acceptCookies');
        const manageBtn = document.getElementById('manageCookies');
        
        if (acceptBtn) {
            acceptBtn.addEventListener('click', () => {
                this.acceptCookies();
            });
        }
        
        if (manageBtn) {
            manageBtn.addEventListener('click', () => {
                this.manageCookies();
            });
        }
    }
}; 