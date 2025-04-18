// 多工具分析功能
// 此模块处理Plus和Premium会员的多选工具功能

// 导入需要的函数和对象
import { getSequenceType, getToolName, utils, sequenceTools, checkResults, reloadParticles } from './search.js';

const multiTool = {
    // 存储选中的工具列表
    selectedTools: [],
    // 存储会员状态
    isMembershipActive: false,
    // 存储分析进度
    processingTools: 0,
    totalTools: 0,
    
    // 初始化多工具功能
    async init() {
        console.log("初始化多工具模块...");
        // 重要：确保会员状态检查完成后再初始化UI
        try {
            this.isMembershipActive = await this.checkMembershipStatus();
            console.log("会员状态检查结果:", this.isMembershipActive ? "可以多选" : "只能单选");
            
            // 如果用户是会员，显示会员特权提示
            if (this.isMembershipActive) {
                utils.showToast("Plus/Premium会员可同时选择多个工具进行分析");
            } else {
                // 为免费用户添加提示信息
                const toolGrid = document.querySelector('.tool-grid');
                if (toolGrid) {
                    const membershipTip = document.createElement('div');
                    membershipTip.className = 'membership-tip';
                    membershipTip.innerHTML = '<i class="fas fa-info-circle"></i> 免费用户只能单选一个工具，<a href="/membership">升级会员</a>解锁多选功能';
                    membershipTip.style.textAlign = 'center';
                    membershipTip.style.margin = '10px 0';
                    membershipTip.style.padding = '8px';
                    membershipTip.style.backgroundColor = '#f8f9fa';
                    membershipTip.style.borderRadius = '4px';
                    membershipTip.style.color = '#666';
                    toolGrid.parentNode.insertBefore(membershipTip, toolGrid);
                }
            }
            
            this.updateToolCards();
            
            // 更新操作栏
            this.updateSelectedToolsDisplay();
            
            // 绑定分析按钮事件
            this.bindAnalyzeButton();
            
            // 创建多工具专用加载动画
            this.createMultiToolLoadingElement();
        } catch (error) {
            console.error("初始化多工具模块失败:", error);
            // 失败时默认为非会员状态，确保安全
            this.isMembershipActive = false;
            this.updateToolCards();
        }
    },
    
    // 创建多工具专用加载动画元素
    createMultiToolLoadingElement() {
        // 检查是否已存在，避免重复创建
        if (document.getElementById('multi-tool-loading')) return;
        
        const loadingElement = document.createElement('div');
        loadingElement.id = 'multi-tool-loading';
        loadingElement.className = 'multi-tool-loading';
        loadingElement.innerHTML = `
            <div class="loading-backdrop"></div>
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <div class="loading-title">多工具分析进行中</div>
                <div class="loading-progress">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div class="progress-text">
                        <span class="current-tool">准备中...</span>
                        <span class="progress-count">0/0</span>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(loadingElement);
        
        // 添加加载动画样式
        const style = document.createElement('style');
        style.textContent = `
            .multi-tool-loading {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 10000;
            }
            .multi-tool-loading.active {
                display: block;
            }
            .loading-backdrop {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(5px);
            }
            .loading-container {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 30px rgba(0, 0, 0, 0.3);
                width: 400px;
                max-width: 90%;
                text-align: center;
            }
            .loading-spinner {
                display: inline-block;
                width: 50px;
                height: 50px;
                border: 5px solid rgba(0, 123, 255, 0.2);
                border-radius: 50%;
                border-top-color: #007bff;
                animation: spin 1s linear infinite;
                margin-bottom: 20px;
            }
            .loading-title {
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 15px;
                color: #333;
            }
            .progress-bar {
                height: 10px;
                background-color: #e9ecef;
                border-radius: 5px;
                margin-bottom: 10px;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background-color: #007bff;
                border-radius: 5px;
                width: 0%;
                transition: width 0.3s ease;
            }
            .progress-text {
                display: flex;
                justify-content: space-between;
                color: #666;
                font-size: 14px;
            }
            .current-tool {
                text-align: left;
                font-weight: bold;
            }
            .progress-count {
                text-align: right;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    },
    
    // 显示多工具加载动画
    showMultiToolLoading() {
        const loadingElement = document.getElementById('multi-tool-loading');
        if (!loadingElement) return;
        
        this.processingTools = 0;
        this.totalTools = this.selectedTools.length;
        
        // 更新进度信息
        const progressCount = loadingElement.querySelector('.progress-count');
        const progressFill = loadingElement.querySelector('.progress-fill');
        const currentTool = loadingElement.querySelector('.current-tool');
        
        if (progressCount) progressCount.textContent = `0/${this.totalTools}`;
        if (progressFill) progressFill.style.width = '0%';
        if (currentTool) currentTool.textContent = '准备中...';
        
        // 显示加载动画
        loadingElement.classList.add('active');
    },
    
    // 更新多工具加载进度
    updateMultiToolProgress(toolName, completed) {
        const loadingElement = document.getElementById('multi-tool-loading');
        if (!loadingElement) return;
        
        this.processingTools = completed;
        
        // 更新进度信息
        const progressCount = loadingElement.querySelector('.progress-count');
        const progressFill = loadingElement.querySelector('.progress-fill');
        const currentTool = loadingElement.querySelector('.current-tool');
        
        if (progressCount) progressCount.textContent = `${this.processingTools}/${this.totalTools}`;
        if (progressFill) progressFill.style.width = `${(this.processingTools / this.totalTools) * 100}%`;
        if (currentTool) currentTool.textContent = toolName || '处理中...';
    },
    
    // 隐藏多工具加载动画
    hideMultiToolLoading() {
        const loadingElement = document.getElementById('multi-tool-loading');
        if (!loadingElement) return;
        
        // 隐藏加载动画
        loadingElement.classList.remove('active');
    },
    
    // 检查用户会员状态
    async checkMembershipStatus() {
        try {
            console.log("开始检查会员状态...");
            const token = localStorage.getItem('token');
            if (!token) {
                console.log("未找到令牌，返回非会员状态");
                return false;
            }
            
            console.log("正在向服务器请求会员状态...");
            const response = await fetch('/api/membership/status', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                console.log(`服务器响应错误: ${response.status}, 返回非会员状态`);
                return false;
            }
            
            const data = await response.json();
            console.log("会员状态API返回:", data);
            
            // 获取会员级别，确保转换为小写进行比较
            const membershipLevel = data.membership_level ? data.membership_level.toLowerCase() : 'free';
            
            // 检查是否为活跃会员
            const isActive = data.is_active !== undefined ? data.is_active : false;
            
            // 只有Plus和Premium会员可以多选
            const isEligible = (membershipLevel === 'plus' || membershipLevel === 'premium') && isActive;
            
            console.log(`会员级别: ${membershipLevel}, 是否活跃: ${isActive}, 是否有多选资格: ${isEligible}`);
            return isEligible;
            
        } catch (error) {
            console.error('检查会员状态出错:', error);
            return false;
        }
    },
    
    // 更新工具卡片的点击事件处理
    updateToolCards() {
        const toolCards = document.querySelectorAll('.tool-card');
        const sequenceInput = document.querySelector('.sequence-input');
        
        console.log(`正在设置工具卡片，多选模式: ${this.isMembershipActive}`);
        
        toolCards.forEach(card => {
            // 移除现有的点击事件（如果有）
            const oldCard = card.cloneNode(true);
            card.parentNode.replaceChild(oldCard, card);
            
            // 添加新的点击事件处理
            oldCard.addEventListener('click', () => {
                const tool = oldCard.dataset.tool;
                
                if (this.isMembershipActive) {
                    // 会员用户可以多选
                    if (oldCard.classList.contains('active')) {
                        // 如果已经选中，则取消选择
                        oldCard.classList.remove('active');
                        this.selectedTools = this.selectedTools.filter(t => t !== tool);
                        console.log(`取消选中工具: ${tool}, 当前已选: ${this.selectedTools.join(', ') || '无'}`);
                    } else {
                        // 选中该工具
                        oldCard.classList.add('active');
                        this.selectedTools.push(tool);
                        console.log(`选中工具: ${tool}, 当前已选: ${this.selectedTools.join(', ')}`);
                    }
                } else {
                    // 非会员用户只能单选
                    // 先清除所有选中状态
                    document.querySelectorAll('.tool-card').forEach(c => {
                        c.classList.remove('active');
                    });
                    
                    // 清空选中工具列表
                    this.selectedTools = [];
                    
                    // 设置当前工具为激活状态
                    oldCard.classList.add('active');
                    this.selectedTools = [tool];
                    console.log(`单选模式选中工具: ${tool}`);
                }
                
                // 更新操作栏显示的工具名称
                this.updateSelectedToolsDisplay();
                
                // 更新输入框提示
                this.updateInputPlaceholder(sequenceInput);
            });
        });
    },
    
    // 更新选中工具的显示
    updateSelectedToolsDisplay() {
        const toolSelection = document.querySelector('.action-bar .tool-selection span');
        if (!toolSelection) return;
        
        if (this.selectedTools.length === 0) {
            toolSelection.textContent = '请选择工具';
        } else if (this.selectedTools.length === 1) {
            const toolCard = document.querySelector(`.tool-card[data-tool="${this.selectedTools[0]}"]`);
            if (toolCard) {
                const toolName = toolCard.querySelector('h4').textContent;
                toolSelection.textContent = toolName;
            } else {
                toolSelection.textContent = '已选择1个工具';
            }
        } else {
            toolSelection.textContent = `已选择 ${this.selectedTools.length} 个工具`;
        }
    },
    
    // 更新输入框提示文字
    updateInputPlaceholder(sequenceInput) {
        if (!sequenceInput) return;
        
        if (this.selectedTools.length === 1) {
            const singleTool = this.selectedTools[0];
            if (singleTool === 'analyze_restriction') {
                sequenceInput.setAttribute('placeholder', '请输入: [DNA序列] [酶名1] [酶名2]... 例如: ATGCGAATTC EcoRI BamHI');
            } else if (singleTool === 'find_cutting_enzymes') {
                sequenceInput.setAttribute('placeholder', '请输入DNA序列，将查找所有可切割该序列的限制酶');
            } else if (singleTool === 'analyze_nucleic_acid') {
                sequenceInput.setAttribute('placeholder', '请输入DNA或RNA序列，用于分析GC含量等物理化学特性');
            } else if (singleTool === 'analyze_codons') {
                sequenceInput.setAttribute('placeholder', '请输入DNA序列和宿主物种ID（如：ATGC 9606）[ID请前往生物知识库查询]');
            } else if (singleTool === 'transform') {
                sequenceInput.setAttribute('placeholder', '请输入FASTA形式');
            } else {
                sequenceInput.setAttribute('placeholder', '请输入序列...');
            }
        } else if (this.selectedTools.length > 1) {
            sequenceInput.setAttribute('placeholder', '请输入序列...（多工具分析模式）');
        } else {
            sequenceInput.setAttribute('placeholder', '请输入序列...');
        }
    },
    
    // 绑定分析按钮事件
    bindAnalyzeButton() {
        const actionAnalyzeBtn = document.querySelector('.action-bar .analyze-btn');
        const sequenceInput = document.querySelector('.sequence-input');
        
        if (!actionAnalyzeBtn || !sequenceInput) return;
        
        // 移除现有的点击事件（如果有）
        const oldBtn = actionAnalyzeBtn.cloneNode(true);
        actionAnalyzeBtn.parentNode.replaceChild(oldBtn, actionAnalyzeBtn);
        
        // 添加新的点击事件处理
        oldBtn.addEventListener('click', async () => {
            const sequence = sequenceInput.value.trim().toUpperCase();
            
            if (!sequence) {
                utils.showToast('请输入序列');
                return;
            }
            
            if (this.selectedTools.length === 0) {
                utils.showToast('请选择至少一个分析工具');
                return;
            }
            
            // 如果选择了多个工具，再次验证会员状态
            if (this.selectedTools.length > 1) {
                const isMultiSelectEnabled = await this.checkMembershipStatus();
                if (!isMultiSelectEnabled) {
                    utils.showToast('多工具分析仅限Plus和Premium会员使用');
                    // 重置为只选择第一个工具
                    const firstTool = this.selectedTools[0];
                    this.selectedTools = [firstTool];
                    
                    // 更新UI
                    document.querySelectorAll('.tool-card').forEach(card => {
                        card.classList.remove('active');
                        if (card.dataset.tool === firstTool) {
                            card.classList.add('active');
                        }
                    });
                    
                    this.updateSelectedToolsDisplay();
                    return;
                }
            }
            
            const detectedType = getSequenceType(sequence);
            
            // 添加loading状态
            oldBtn.classList.add('loading');
            
            // 为多个工具使用专用加载动画，单个工具使用普通加载动画
            if (this.selectedTools.length > 1) {
                this.showMultiToolLoading();
            } else {
                utils.showLoading('正在分析...');
            }
            
            try {
                // 按顺序处理每个工具
                for (let i = 0; i < this.selectedTools.length; i++) {
                    const tool = this.selectedTools[i];
                    const toolName = getToolName(tool);
                    
                    try {
                        // 更新加载进度
                        if (this.selectedTools.length > 1) {
                            this.updateMultiToolProgress(`正在分析: ${toolName}`, i);
                        } else {
                            utils.updateLoadingText(`正在分析: ${toolName}...`);
                        }
                        
                        // 前端验证特定工具的序列类型
                        if (tool === 'analyze_nucleic_acid') {
                            if (detectedType === 'protein') { 
                                utils.showToast('核酸特性分析工具无法处理蛋白质序列，跳过此工具。'); 
                                continue; 
                            } else if (detectedType === 'unknown') { 
                                utils.showToast('序列包含无法识别的字符，跳过核酸分析工具。'); 
                                continue; 
                            }
                        }
                        if (tool === 'find_cutting_enzymes' && detectedType !== 'dna') { 
                            utils.showToast('限制酶分析工具仅支持DNA序列，跳过此工具。'); 
                            continue; 
                        }
                        if (tool === 'sequence_annotation' && detectedType !== 'protein') { 
                            utils.showToast('DNA或RNA序列无法进行序列注释，跳过此工具。'); 
                            continue; 
                        }
                        if (tool === 'translate' && detectedType === 'protein') { 
                            utils.showToast('蛋白质序列无法进行翻译，跳过此工具。'); 
                            continue; 
                        }
                        if (tool === 'toxinpred') {
                            const seqInput = sequence.split(/\s+/)[0];
                            if (seqInput.length < 5 || seqInput.length > 50) { 
                                utils.showToast('ToxinPred要求序列长度为5-50个氨基酸，跳过此工具。'); 
                                continue; 
                            }
                        }
                        
                        let result;
                        if (tool === 'analyze_codons') {
                            // 提取序列和宿主ID (允许非数字)
                            const inputParts = sequence.trim().split(/\s+/);
                            if (inputParts.length <= 1) {
                                utils.showToast("密码子分析需要宿主ID，跳过此工具。");
                                continue;
                            }
                            const seqPart = inputParts[0];
                            const hostIdPart = inputParts.slice(1).join(' ');
                            
                            result = await sequenceTools.analyzeSequence(tool, `${seqPart} ${hostIdPart}`);
                        } else {
                            result = await sequenceTools.analyzeSequence(tool, sequence);
                        }
                        
                        if (result) {
                            sequenceTools.displayResults(tool, result, detectedType);
                        }
                        
                        // 完成一个工具的分析后更新进度
                        if (this.selectedTools.length > 1) {
                            this.updateMultiToolProgress(`已完成: ${toolName}`, i + 1);
                        }
                    } catch (error) {
                        console.error(`${tool}分析错误:`, error);
                        utils.showToast(`${toolName}分析失败: ${error.message || '未知错误'}`);
                    }
                }
                
                // 所有工具分析完成
                if (this.selectedTools.length > 1) {
                    this.updateMultiToolProgress('分析完成', this.selectedTools.length);
                    await new Promise(resolve => setTimeout(resolve, 800)); // 短暂延迟让用户看到完成状态
                }
            } catch (error) {
                console.error('多工具分析过程中发生错误:', error);
                utils.showToast(`分析过程中发生错误: ${error.message || '未知错误'}`);
            } finally {
                // 无论成功或失败，都确保隐藏加载动画
                if (this.selectedTools.length > 1) {
                    this.hideMultiToolLoading();
                } else {
                    utils.hideLoading();
                }
                
                // 移除按钮加载状态
                oldBtn.classList.remove('loading');
                
                // 检查结果并重载粒子效果
                try {
                    checkResults();
                    
                    // 延迟重载粒子效果，以确保DOM更新完成
                    setTimeout(() => {
                        try {
                            reloadParticles();
                            console.log('粒子效果已重载');
                        } catch (e) {
                            console.error('重载粒子效果失败:', e);
                        }
                    }, 500);
                } catch (e) {
                    console.error('检查结果失败:', e);
                }
                
                console.log('分析完成，界面已更新');
            }
        });
    }
};

// 添加CSS样式
const addToolCardStyles = () => {
    const styleEl = document.createElement('style');
    styleEl.textContent = `
        .tool-card {
            transition: all 0.3s ease;
        }
        .membership-tip {
            animation: fadeIn 0.5s;
        }
        .membership-tip a {
            color: #007bff;
            text-decoration: none;
            font-weight: bold;
        }
        .membership-tip a:hover {
            text-decoration: underline;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    `;
    document.head.appendChild(styleEl);
};

// 页面加载后添加样式
document.addEventListener('DOMContentLoaded', addToolCardStyles);

// 导出模块
export default multiTool; 