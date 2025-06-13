// 应用配置文件
window.APP_CONFIG = {
    // 生产环境设置为 false，开发环境设置为 true
    DEBUG_MODE: false,
    
    // 版本信息
    VERSION: '1.0.0',
    
    // API配置
    API_TIMEOUT: 30000,
    
    // 其他配置...
};

// 重写console方法，在生产环境中禁用调试输出
if (!window.APP_CONFIG.DEBUG_MODE) {
    // 保留错误和警告，但禁用普通日志
    console.log = function() {};
    // console.error 和 console.warn 保留，用于生产环境错误监控
}

// 提供一个安全的日志函数
window.safeLog = function(...args) {
    if (window.APP_CONFIG.DEBUG_MODE) {
        console.log(...args);
    }
};

window.safeWarn = function(...args) {
    if (window.APP_CONFIG.DEBUG_MODE) {
        console.warn(...args);
    }
}; 