/**
 * 异步AI分析处理器
 * 提供非阻塞的AI分析体验，包括进度提示、取消功能和队列管理
 */

class AsyncAIHandler {
    constructor() {
        this.activeRequests = new Map(); // 存储活跃的请求
        this.requestQueue = []; // 请求队列
        this.maxConcurrentRequests = 3; // 最大并发请求数
        this.updateTimer = null; // 状态更新定时器
        
        // 智能轮询配置 - 可根据需要调整以减少服务器负载
        this.pollingConfig = {
            initialInterval: 3000,  // 初始轮询间隔：3秒（降低初始频率）
            maxInterval: 15000,     // 最大轮询间隔：15秒（增加最大间隔）
            backoffMultiplier: 1.8, // 退避倍数（更积极的退避）
            fastPollingDuration: 20000 // 快速轮询持续时间：20秒（缩短快速轮询期）
        };
        
        this.init();
    }

    init() {
        console.log('异步AI处理器已初始化');
        // 确保DOM加载完成后再创建状态显示
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.createStatusDisplay();
            });
        } else {
            this.createStatusDisplay();
        }
        
        // 启动实时更新计时器
        this.startUpdateTimer();
    }

    /**
     * 启动实时状态更新计时器
     */
    startUpdateTimer() {
        // 清除可能存在的旧计时器
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        // 每秒更新一次状态显示，让计时器实时更新
        this.updateTimer = setInterval(() => {
            if (this.activeRequests.size > 0) {
                // 检查是否有运行中的请求
                const hasRunningRequests = Array.from(this.activeRequests.values())
                    .some(req => req.status === 'running' || req.status === 'queued');
                
                // 如果有运行中的请求，或者刚完成的请求（需要显示完成状态），则更新显示
                if (hasRunningRequests || this.activeRequests.size > 0) {
                    this.updateStatusDisplay();
                }
            }
        }, 1000);
    }

    /**
     * 停止实时状态更新计时器
     */
    stopUpdateTimer() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }

    /**
     * 创建状态显示区域
     */
    createStatusDisplay() {
        // 检查是否已存在状态显示
        if (document.getElementById('async-ai-status')) {
            return;
        }

        const statusDiv = document.createElement('div');
        statusDiv.id = 'async-ai-status';
        statusDiv.className = 'async-ai-status';
        statusDiv.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            max-width: 300px;
            min-width: 250px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 10000;
            display: none;
            font-size: 14px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;

        statusDiv.innerHTML = `
            <div class="status-header" style="font-weight: bold; margin-bottom: 10px; color: #2563eb;">
                <i class="fas fa-brain"></i> AI分析队列
            </div>
            <div class="status-content"></div>
        `;

        document.body.appendChild(statusDiv);
    }

    /**
     * 开始异步AI分析
     */
    async startAsyncAnalysis(toolResults, userQuery, options = {}) {
        const {
            timeout = 90,
            onProgress = null,
            onComplete = null,
            onError = null,
            priority = 'normal'
        } = options;

        // 生成请求ID
        const requestId = `ai_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        // 创建请求对象
        const request = {
            id: requestId,
            toolResults,
            userQuery,
            timeout,
            onProgress,
            onComplete,
            onError,
            priority,
            startTime: Date.now(),
            status: 'queued'
        };

        // 添加到队列
        this.requestQueue.push(request);
        this.activeRequests.set(requestId, request);

        // 更新状态显示
        this.updateStatusDisplay();

        // 尝试处理队列
        this.processQueue();

        return requestId;
    }

    /**
     * 处理请求队列
     */
    async processQueue() {
        // 检查是否可以处理更多请求
        const runningCount = Array.from(this.activeRequests.values())
            .filter(req => req.status === 'running').length;

        if (runningCount >= this.maxConcurrentRequests || this.requestQueue.length === 0) {
            return;
        }

        // 按优先级排序队列
        this.requestQueue.sort((a, b) => {
            const priorityOrder = { 'high': 3, 'normal': 2, 'low': 1 };
            return priorityOrder[b.priority] - priorityOrder[a.priority];
        });

        // 取出下一个请求
        const request = this.requestQueue.shift();
        if (!request) return;

        try {
            // 更新请求状态
            request.status = 'running';
            this.updateStatusDisplay();

            // 调用进度回调
            if (request.onProgress) {
                request.onProgress('开始分析', 0);
            }

            // 从工具结果中提取序列信息
            let sequence = '';
            if (request.toolResults && typeof request.toolResults === 'object') {
                for (const toolResult of Object.values(request.toolResults)) {
                    if (toolResult && (toolResult.sequence || toolResult.original_sequence)) {
                        sequence = toolResult.sequence || toolResult.original_sequence;
                        break;
                    }
                }
            }

            // 发送异步AI分析请求
            const response = await fetch('/api/ai_analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${cookieUtils.getCookie('auth_token')}`
                },
                body: JSON.stringify({
                    sequence: sequence,
                    query: request.userQuery,
                    toolResults: request.toolResults,
                    async: true,
                    timeout: request.timeout
                })
            });

            if (!response.ok) {
                // 尝试解析错误信息
                let errorMessage = `请求失败: ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.error) {
                        errorMessage = errorData.error;
                    } else if (errorData.message) {
                        errorMessage = errorData.message;
                    }
                } catch (e) {
                    // 如果无法解析JSON，使用默认错误信息
                    console.warn('无法解析错误响应:', e);
                }
                throw new Error(errorMessage);
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'AI分析失败');
            }

            if (result.async && result.request_id) {
                // 真正的异步模式，开始轮询结果
                request.backendRequestId = result.request_id;
                this.startPolling(request);
            } else {
                // 同步模式，直接处理结果
                // 模拟一个短暂的延迟来提供更好的用户体验
                setTimeout(() => {
                    this.handleSuccess(request, result);
                }, 1000);
            }

        } catch (error) {
            this.handleError(request, error);
        }

        // 继续处理队列中的其他请求
        setTimeout(() => this.processQueue(), 100);
    }

    /**
     * 开始智能轮询结果
     */
    startPolling(request) {
        let pollCount = 0;
        let currentInterval = this.pollingConfig.initialInterval;
        const startTime = Date.now();
        
        const poll = async () => {
            try {
                pollCount++;
                const elapsedTime = Date.now() - startTime;
                
                // 检查是否超时
                if (elapsedTime > request.timeout * 1000) {
                    throw new Error('分析超时');
                }

                // 调用后端API查询真实状态
                const response = await fetch(`/api/ai_result/${request.backendRequestId}`, {
                    headers: {
                        'Authorization': `Bearer ${cookieUtils.getCookie('auth_token')}`
                    }
                });

                if (response.ok) {
                    const result = await response.json();
                    console.log(`轮询结果 (第${pollCount}次, 间隔${currentInterval}ms, 耗时${elapsedTime}ms):`, result);
                    
                    if (result.completed) {
                        // 请求已完成，停止轮询
                        if (result.status === 'completed' && result.result) {
                            this.handleSuccess(request, result.result);
                        } else if (result.status === 'error') {
                            throw new Error(result.error || '分析失败');
                        }
                        return; // 不再安排下一次轮询
                    } else {
                        // 仍在运行中，更新进度
                        const progress = Math.min(90, (elapsedTime / (request.timeout * 1000)) * 90);
                        if (request.onProgress) {
                            request.onProgress('分析进行中', progress);
                        }
                    }
                } else if (response.status === 404) {
                    // 请求不存在或已过期
                    throw new Error('请求不存在或已过期');
                } else {
                    // 其他HTTP错误，继续轮询
                    console.warn(`轮询API调用失败 (第${pollCount}次):`, response.status, response.statusText);
                }

                // 智能调整轮询间隔
                if (elapsedTime > this.pollingConfig.fastPollingDuration) {
                    // 超过快速轮询期，逐渐增加间隔
                    const newInterval = Math.min(
                        currentInterval * this.pollingConfig.backoffMultiplier,
                        this.pollingConfig.maxInterval
                    );
                    if (newInterval !== currentInterval) {
                        console.log(`轮询间隔调整: ${currentInterval}ms -> ${newInterval}ms (第${pollCount}次轮询)`);
                        currentInterval = newInterval;
                    }
                }

                // 安排下一次轮询
                request.pollingTimeout = setTimeout(poll, currentInterval);

            } catch (error) {
                this.handleError(request, error);
            }
        };

        // 开始第一次轮询
        request.pollingTimeout = setTimeout(poll, currentInterval);
    }

    /**
     * 处理成功结果
     */
    handleSuccess(request, result) {
        request.status = 'completed';
        request.result = result;
        request.endTime = Date.now(); // 记录完成时间

        if (request.onProgress) {
            request.onProgress('分析完成', 100);
        }

        if (request.onComplete) {
            request.onComplete(result);
        }

        // 延迟清理请求
        setTimeout(() => {
            this.activeRequests.delete(request.id);
            this.updateStatusDisplay();
            
            // 如果没有活跃请求了，可以考虑停止更新计时器
            if (this.activeRequests.size === 0) {
                // 延迟一点再停止，防止新请求立即到来
                setTimeout(() => {
                    if (this.activeRequests.size === 0) {
                        // 这里我们选择保持计时器运行，以便随时响应新请求
                        // this.stopUpdateTimer();
                    }
                }, 1000);
            }
        }, 3000);

        this.updateStatusDisplay();
        
        // 显示成功提示
        if (window.utils && window.utils.showToast) {
            window.utils.showToast('AI分析完成');
        }
    }

    /**
     * 处理错误
     */
    handleError(request, error) {
        request.status = 'error';
        request.error = error;
        request.endTime = Date.now(); // 记录错误发生时间

        if (request.pollingInterval) {
            clearInterval(request.pollingInterval);
        }

        if (request.onError) {
            request.onError(error);
        }

        // 延迟清理请求
        setTimeout(() => {
            this.activeRequests.delete(request.id);
            this.updateStatusDisplay();
            
            // 如果没有活跃请求了，可以考虑停止更新计时器
            if (this.activeRequests.size === 0) {
                // 延迟一点再停止，防止新请求立即到来
                setTimeout(() => {
                    if (this.activeRequests.size === 0) {
                        // 这里我们选择保持计时器运行，以便随时响应新请求
                        // this.stopUpdateTimer();
                    }
                }, 1000);
            }
        }, 5000);

        this.updateStatusDisplay();

        // 显示错误提示
        if (window.utils && window.utils.showToast) {
            window.utils.showToast(`AI分析失败: ${error.message}`);
        }
    }

    /**
     * 取消请求
     */
    async cancelRequest(requestId) {
        const request = this.activeRequests.get(requestId);
        if (!request) {
            return false;
        }

        try {
            // 如果有后端请求ID，尝试取消后端请求
            if (request.backendRequestId) {
                await fetch('/api/ai_cancel', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${cookieUtils.getCookie('auth_token')}`
                    },
                    body: JSON.stringify({
                        request_id: request.backendRequestId
                    })
                });
            }

            // 清理本地状态
            if (request.pollingTimeout) {
                clearTimeout(request.pollingTimeout);
            }

            request.status = 'cancelled';
            request.endTime = Date.now(); // 记录取消时间
            this.activeRequests.delete(requestId);

            // 从队列中移除
            const queueIndex = this.requestQueue.findIndex(req => req.id === requestId);
            if (queueIndex !== -1) {
                this.requestQueue.splice(queueIndex, 1);
            }

            this.updateStatusDisplay();
            
            if (window.utils && window.utils.showToast) {
                window.utils.showToast('AI分析已取消');
            }

            return true;

        } catch (error) {
            console.error('取消请求失败:', error);
            return false;
        }
    }

    /**
     * 更新状态显示
     */
    updateStatusDisplay() {
        let statusDiv = document.getElementById('async-ai-status');
        if (!statusDiv) {
            // 如果状态显示区域不存在，先创建它
            this.createStatusDisplay();
            statusDiv = document.getElementById('async-ai-status');
            if (!statusDiv) return; // 如果仍然创建失败，则返回
        }

        const content = statusDiv.querySelector('.status-content');
        const activeList = Array.from(this.activeRequests.values());

        if (activeList.length === 0) {
            statusDiv.style.display = 'none';
            // 如果没有活跃请求，可以暂停更新计时器以节省资源
            // 但我们仍然保持计时器运行，因为新请求可能随时到来
            return;
        }

        statusDiv.style.display = 'block';

        content.innerHTML = activeList.map(request => {
            const statusIcon = {
                'queued': '<i class="fas fa-clock" style="color: #fbbf24;"></i>',
                'running': '<i class="fas fa-spinner fa-spin" style="color: #3b82f6;"></i>',
                'completed': '<i class="fas fa-check" style="color: #10b981;"></i>',
                'error': '<i class="fas fa-times" style="color: #ef4444;"></i>',
                'cancelled': '<i class="fas fa-ban" style="color: #6b7280;"></i>'
            }[request.status] || '';

            const statusText = {
                'queued': '排队中',
                'running': '分析中',
                'completed': '已完成',
                'error': '出错',
                'cancelled': '已取消'
            }[request.status] || '';

            // 对于已完成的请求，显示固定的完成时间；对于运行中的请求，显示实时时间
            let elapsed;
            if (request.status === 'completed' || request.status === 'error' || request.status === 'cancelled') {
                // 如果请求已完成，使用完成时间或当前时间作为结束时间
                const endTime = request.endTime || Date.now();
                elapsed = Math.round((endTime - request.startTime) / 1000);
            } else {
                // 对于运行中的请求，显示实时经过时间
                elapsed = Math.round((Date.now() - request.startTime) / 1000);
            }

            return `
                <div class="request-item" style="margin-bottom: 8px; padding: 8px; background: #f9fafb; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            ${statusIcon}
                            <span style="font-size: 12px;">${statusText}</span>
                        </div>
                        <div style="display: flex; gap: 4px;">
                            <span style="font-size: 11px; color: #6b7280;">${elapsed}s</span>
                            ${request.status === 'running' || request.status === 'queued' ? 
                                `<button onclick="window.asyncAI.cancelRequest('${request.id}')" 
                                        style="font-size: 10px; padding: 2px 6px; border: none; background: #ef4444; color: white; border-radius: 3px; cursor: pointer;">取消</button>` : 
                                ''}
                        </div>
                    </div>
                    <div style="font-size: 11px; color: #6b7280; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${request.userQuery}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * 获取AI服务状态
     */
    async getServiceStatus() {
        try {
            const response = await fetch('/api/ai_status', {
                headers: {
                    'Authorization': `Bearer ${cookieUtils.getCookie('auth_token')}`
                }
            });

            if (response.ok) {
                const result = await response.json();
                return result.status;
            }
        } catch (error) {
            console.error('获取AI服务状态失败:', error);
        }
        return null;
    }

    /**
     * 检查是否可用
     */
    async isAvailable() {
        try {
            const response = await fetch('/api/ai_status', {
                headers: {
                    'Authorization': `Bearer ${cookieUtils.getCookie('auth_token')}`
                }
            });

            if (response.ok) {
                const result = await response.json();
                console.log('AI状态检查响应:', result);
                // 后端返回格式是 { success: true, status: {...} }
                // 这里简化检查：如果能成功获取状态且success为true，就认为可用
                return result.success === true;
            } else {
                console.error('AI状态检查失败:', response.status, response.statusText);
                return false;
            }
        } catch (error) {
            console.error('检查AI服务状态失败:', error);
            return false;
        }
    }

    /**
     * 配置轮询参数以优化服务器负载
     */
    configurePolling(config = {}) {
        this.pollingConfig = {
            ...this.pollingConfig,
            ...config
        };
        console.log('轮询配置已更新:', this.pollingConfig);
    }

    /**
     * 获取当前轮询配置
     */
    getPollingConfig() {
        return { ...this.pollingConfig };
    }

    /**
     * 设置低负载模式（更长的轮询间隔）
     */
    setLowLoadMode() {
        this.configurePolling({
            initialInterval: 5000,  // 5秒
            maxInterval: 30000,     // 30秒
            backoffMultiplier: 2.0,
            fastPollingDuration: 15000 // 15秒
        });
        console.log('已切换到低负载模式');
    }

    /**
     * 设置标准模式
     */
    setStandardMode() {
        this.configurePolling({
            initialInterval: 3000,  // 3秒
            maxInterval: 15000,     // 15秒
            backoffMultiplier: 1.8,
            fastPollingDuration: 20000 // 20秒
        });
        console.log('已切换到标准模式');
    }

    /**
     * 设置高频模式（用于测试或紧急情况）
     */
    setHighFrequencyMode() {
        this.configurePolling({
            initialInterval: 1000,  // 1秒
            maxInterval: 5000,      // 5秒
            backoffMultiplier: 1.3,
            fastPollingDuration: 30000 // 30秒
        });
        console.log('已切换到高频模式');
    }

    /**
     * 测试状态显示功能
     */
    testStatusDisplay() {
        console.log('开始测试状态显示功能...');
        
        // 创建一个模拟请求
        const mockRequest = {
            id: 'test_' + Date.now(),
            toolResults: { test: { success: true, result: 'test' } },
            userQuery: '这是一个测试AI分析请求',
            timeout: 60,
            onProgress: null,
            onComplete: null,
            onError: null,
            priority: 'normal',
            startTime: Date.now(),
            status: 'running'
        };

        // 添加到活跃请求中
        this.activeRequests.set(mockRequest.id, mockRequest);
        
        // 更新状态显示
        this.updateStatusDisplay();
        
        console.log('状态显示已创建，右上角应该显示一个测试请求');
        
        // 5秒后模拟完成
        setTimeout(() => {
            mockRequest.status = 'completed';
            this.updateStatusDisplay();
            
            // 再3秒后清理
            setTimeout(() => {
                this.activeRequests.delete(mockRequest.id);
                this.updateStatusDisplay();
                console.log('测试完成，状态显示已清理');
            }, 3000);
        }, 5000);
    }
}

// 创建全局实例
window.asyncAI = new AsyncAIHandler();

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    if (window.asyncAI) {
        window.asyncAI.stopUpdateTimer();
    }
});

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AsyncAIHandler;
} 