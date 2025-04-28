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
                <div class="analysis-phase">工具分析阶段</div>
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
            .analysis-phase {
                font-size: 12px;
                color: #666;
                margin-top: 10px;
                background-color: #f1f8ff;
                padding: 4px 8px;
                border-radius: 12px;
                display: inline-block;
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
        const sequenceInput = document.querySelector('.sequence-input-editor');
        
        if (!sequenceInput) {
            console.error("无法找到序列输入元素");
        }
        
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
        // 如果没有传入sequenceInput，则尝试获取
        if (!sequenceInput) {
            sequenceInput = document.querySelector('.sequence-input-editor');
            if (!sequenceInput) {
                console.error("无法找到序列输入元素");
                return;
            }
        }
        
        console.log("更新输入框占位符文本");
        
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
        const sequenceInput = document.querySelector('.sequence-input-editor');
        
        if (!actionAnalyzeBtn || !sequenceInput) {
            console.error("找不到分析按钮或序列输入元素");
            return;
        }
        
        console.log("正在绑定多工具分析事件到分析按钮");
        
        // 使用具名函数便于后续移除
        this.handleMultiToolAnalysis = async (event) => {
            console.log("多工具分析事件处理函数被调用");
            
            // ***** 新增检查：如果事件已经被停止，则直接返回 *****
            if (event.isImmediatePropagationStopped && event.isImmediatePropagationStopped()) {
                console.log("多工具分析处理函数：事件已被search.js停止，不执行");
                return;
            }

            // 检查是否是AI分析模式 - 修改为兼容模式
            const isAiMode = document.querySelector('.ai-analyze-btn.active') !== null;
            const aiQueryInput = document.querySelector('.ai-query-input');
            const aiQuery = isAiMode && aiQueryInput ? aiQueryInput.value.trim() : '';
            
            console.log("AI模式状态:", isAiMode ? "激活" : "未激活", "AI查询:", aiQuery ? "有" : "无");
            
            console.log("开始处理多工具分析");
            
            // 重新获取序列输入元素，确保获取到最新的值
            const sequenceInputEl = document.querySelector('.sequence-input-editor');
            if (!sequenceInputEl) {
                console.error("找不到序列输入元素");
                utils.showToast('系统错误: 找不到序列输入元素');
                return;
            }
            
            const sequence = sequenceInputEl.textContent.trim().toUpperCase();
            console.log("获取到的序列:", sequence ? sequence.substring(0, 20) + "..." : "空");
            
            if (!sequence) {
                utils.showToast('请输入序列');
                return;
            }
            
            // *** 逻辑调整：multiTool 只处理多工具情况 ***
            if (this.selectedTools.length <= 1) {
                 console.log("多工具分析处理函数：只选择了一个工具，不处理，交由 search.js 处理");
                 return;
            }
            // -------------------------------------------
            
            console.log("多工具分析处理函数：检测到多工具模式，开始执行...");

            // 如果选择了多个工具，再次验证会员状态
            //if (this.selectedTools.length > 1) { // 这个检查现在可以简化，因为上面已经保证了 > 1
                const isMultiSelectEnabled = await this.checkMembershipStatus();
                if (!isMultiSelectEnabled) {
                    utils.showToast('多工具分析仅限Plus和Premium会员使用');
                    // ... (重置选择的代码保持不变) ...
                    return;
                }
            //}
            
            // 只对第一部分序列进行类型检测，空格后的部分作为参数
            const sequenceParts = sequence.split(/\s+/);
            const mainSequence = sequenceParts[0];  // 第一部分作为主序列
            const detectedType = getSequenceType(mainSequence);
            
            console.log("序列类型检测结果:", detectedType, "仅检测空格前部分:", mainSequence);
            
            // 添加loading状态
            actionAnalyzeBtn.classList.add('loading');
            
            // 为多个工具使用专用加载动画，单个工具使用普通加载动画
            //if (this.selectedTools.length > 1) { // 现在总是 > 1
                this.showMultiToolLoading();
            //} else {
            //    utils.showLoading('正在分析...');
            //}
            
            // 存储所有工具分析结果的数组，用于AI分析
            const allToolResults = [];
            
            try {
                // 按顺序处理每个工具
                for (let i = 0; i < this.selectedTools.length; i++) {
                    const tool = this.selectedTools[i];
                    const toolName = getToolName(tool);
                    
                    try {
                        // 更新加载进度
                        //if (this.selectedTools.length > 1) { // 总是 > 1
                            this.updateMultiToolProgress(`正在分析: ${toolName}`, i);
                        //} else {
                        //    utils.updateLoadingText(`正在分析: ${toolName}...`);
                        //}
                        
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
                            const seqInput = mainSequence; // 只检查第一部分序列
                            if (seqInput.length < 5 || seqInput.length > 50) { 
                                utils.showToast('ToxinPred要求序列长度为5-50个氨基酸，跳过此工具。'); 
                                continue; 
                            }
                        }
                        
                        let result;
                        if (tool === 'analyze_codons') {
                            // 提取序列和宿主ID (允许非数字)
                            if (sequenceParts.length <= 1) {
                                utils.showToast("密码子分析需要宿主ID，跳过此工具。");
                                continue;
                            }
                            const seqPart = mainSequence; // 主序列部分
                            const hostIdPart = sequenceParts.slice(1).join(' '); // 宿主ID部分(可能包含点号等)
                            
                            console.log(`密码子分析参数: 序列=${seqPart}, 宿主ID=${hostIdPart}`);
                            result = await sequenceTools.analyzeSequence(tool, `${seqPart} ${hostIdPart}`);
                        } else if (tool === 'analyze_restriction') {
                            // 处理限制性内切酶分析，需要序列和酶名称
                            if (sequenceParts.length <= 1) {
                                utils.showToast("限制性内切酶分析需要酶名称，跳过此工具。");
                                continue;
                            }
                            const seqPart = mainSequence; // 主序列部分
                            const enzymesPart = sequenceParts.slice(1).join(' '); // 酶名称部分
                            
                            console.log(`限制性内切酶分析参数: 序列=${seqPart}, 酶名=${enzymesPart}`);
                            result = await sequenceTools.analyzeSequence(tool, `${seqPart} ${enzymesPart}`);
                        } else {
                            // 其他工具只需要序列本身
                            result = await sequenceTools.analyzeSequence(tool, sequence);
                        }
                        
                        if (result) {
                            // 保存结果用于AI分析
                            allToolResults.push({
                                tool: tool,
                                toolName: toolName,
                                result: result // 保存整个后端返回的结果对象
                            });
                            
                            // 如果不是AI模式或AI查询为空，显示结果
                            if (!isAiMode || !aiQuery) {
                                // 只显示成功的工具结果
                                if (result.success) {
                                    sequenceTools.displayResults(tool, result, detectedType);
                                } else {
                                    console.warn(`工具 ${toolName} 分析失败，结果:`, result.error);
                                    // 可以选择性地显示错误提示，或者只在控制台记录
                                    // utils.showToast(`${toolName} 分析返回失败: ${result.error || '未知原因'}`);
                                }
                            }
                        }
                        
                        // 完成一个工具的分析后更新进度
                        //if (this.selectedTools.length > 1) {
                            this.updateMultiToolProgress(`已完成: ${toolName}`, i + 1);
                        //}
                    } catch (error) {
                        console.error(`${tool}分析错误:`, error);
                        utils.showToast(`${toolName}分析失败: ${error.message || '未知错误'}`);
                        // 记录失败，但不放入 allToolResults
                    }
                }
                
                // 所有工具分析完成
                //if (this.selectedTools.length > 1) {
                    this.updateMultiToolProgress('分析完成', this.selectedTools.length);
                    await new Promise(resolve => setTimeout(resolve, 800)); // 短暂延迟让用户看到完成状态
                //}
                
                // 如果是AI分析模式且有AI查询，则将所有工具结果发送给AI
                if (isAiMode && aiQuery && allToolResults.length > 0) {
                    console.log("AI分析模式已激活，将多工具分析结果发送给AI进行分析");
                    
                    try {
                        // 过滤掉失败的工具结果再发送给AI
                        const successfulToolResults = allToolResults.filter(item => {
                             // 保持实际的过滤逻辑
                             return item.result && item.result.success === true; 
                         });
                        const successfulToolsCount = successfulToolResults.length;
                        console.log(`AI分析: 实际成功运行 ${successfulToolsCount} / ${allToolResults.length} 个工具`);

                        if (successfulToolsCount === 0) {
                           throw new Error("所有选定工具均分析失败，无法进行AI分析");
                        }
                        
                        // 更新加载动画状态为"AI分析中"
                        const loadingElement = document.getElementById('multi-tool-loading');
                        if (loadingElement) {
                            const loadingTitle = loadingElement.querySelector('.loading-title');
                            if (loadingTitle) loadingTitle.textContent = 'AI分析进行中';
                            
                            const currentTool = loadingElement.querySelector('.current-tool');
                            if (currentTool) currentTool.textContent = '正在由AI综合分析多工具结果...';
                            
                            // 进度条保持满格
                            const progressFill = loadingElement.querySelector('.progress-fill');
                            if (progressFill) progressFill.style.width = '100%';
                            
                            // 更新分析阶段标签
                            const analysisPhase = loadingElement.querySelector('.analysis-phase');
                            if (analysisPhase) {
                                analysisPhase.textContent = 'AI分析阶段';
                                analysisPhase.style.backgroundColor = '#fff0db';
                            }
                        }
                        
                        utils.updateLoadingText('正在进行AI分析...');
                        
                        // 调用AI分析API，传递所有工具结果
                        const response = await fetch('/api/ai_analyze', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                ...utils.getAuthHeader()
                            },
                            body: JSON.stringify({
                                sequence: sequence,
                                query: aiQuery,
                                // 只传递成功的结果给AI
                                toolResults: successfulToolResults.reduce((obj, item) => {
                                    obj[item.tool] = item.result;
                                    return obj;
                                }, {}),  
                                selectedTools: this.selectedTools.map(tool => ({
                                    id: tool,
                                    name: getToolName(tool)
                                })),
                                successfulToolCount: successfulToolsCount // 传递实际成功数量
                            })
                        });
                        
                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.error || `AI分析请求失败: ${response.status}`);
                        }
                        
                        const result = await response.json();
                        
                        // 处理AI分析结果
                        if (result.success) {
                            // 更新加载动画状态为"分析完成"
                            const loadingElement = document.getElementById('multi-tool-loading');
                            if (loadingElement) {
                                const loadingTitle = loadingElement.querySelector('.loading-title');
                                if (loadingTitle) loadingTitle.textContent = '分析完成';
                                
                                const currentTool = loadingElement.querySelector('.current-tool');
                                if (currentTool) currentTool.textContent = 'AI分析已完成';
                                
                                // 更新分析阶段标签
                                const analysisPhase = loadingElement.querySelector('.analysis-phase');
                                if (analysisPhase) {
                                    analysisPhase.textContent = '分析全部完成';
                                    analysisPhase.style.backgroundColor = '#e6ffe6';
                                }
                            }
                            
                            // ... (保存localStorage的代码保持不变) ...
                            
                            // 创建或获取结果容器
                            let resultsContainer = document.querySelector('.results-container');
                            if (!resultsContainer) {
                                const contentContainer = document.querySelector('.content-container');
                                if (!contentContainer) {
                                    // 如果连内容容器都找不到，这是严重的UI问题，无法继续
                                    console.error("MultiTool AI: 找不到 .content-container 元素，无法创建或显示结果！");
                                    throw new Error("UI渲染错误，无法显示结果"); // 抛出错误以便被捕获
                                }
                                resultsContainer = document.createElement('div');
                                resultsContainer.className = 'results-container';
                                contentContainer.appendChild(resultsContainer);
                                console.log("MultiTool AI: 已创建 .results-container");
                            }

                            // *** 关键检查：确保 resultsContainer 确实存在 ***
                            if (!resultsContainer) {
                                console.error("MultiTool AI: 创建或查找 .results-container 后仍然为 null！");
                                throw new Error("UI渲染错误，无法获取结果容器");
                            }
                            
                            // 确保resultsContainer可见
                            resultsContainer.style.display = 'block'; // 现在相对安全
                            
                            // 清空之前的结果
                            resultsContainer.innerHTML = ''; // 现在相对安全
                            
                            // 创建AI分析结果显示区域
                            let aiResultBox = document.createElement('div');
                            aiResultBox.className = 'ai-analysis-result result-box';
                            resultsContainer.appendChild(aiResultBox); // 现在相对安全
                            
                            // 生成带格式的AI分析报告
                            const aiReport = result.report || "AI未能生成报告";
                            
                            // 转换Markdown格式为HTML
                            const formattedReport = aiReport
                                .replace(/\n\n/g, '<br><br>')
                                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                                .replace(/```([\s\S]*?)```/g, '<pre class="code-block">$1</pre>')
                                .replace(/`(.*?)`/g, '<code>$1</code>')
                                .replace(/\n/g, '<br>');
                            
                            // --- 修正AI分析报告标题 --- 
                            aiResultBox.innerHTML = `
                                <h3>AI综合分析报告 (基于 ${successfulToolsCount} 个工具)</h3>
                                <div class="ai-report-content">
                                    ${formattedReport}
                                </div>
                                <div class="ai-report-query">
                                    <p><strong>分析需求:</strong> ${aiQuery}</p>
                                    <p><strong>原选工具:</strong> ${this.selectedTools.map(t => getToolName(t)).join(', ')}</p>
                                </div>
                                <div class="ai-tools-used" style="margin-top: 10px; font-size: 14px; color: #666;">
                                    <details>
                                        <summary style="cursor: pointer; color: #3498db;">查看成功工具的分析详情 (${successfulToolsCount}/${allToolResults.length})</summary>
                                        <div style="margin-top: 10px; padding: 10px; background-color: #f5f5f5; border-radius: 5px;">
                                            <h4 style="margin-top: 0;">成功运行的工具:</h4>
                                            <ul style="padding-left: 20px;">
                                                ${successfulToolResults.map(item => {
                                                    const resultJson = JSON.stringify(item.result, null, 2);
                                                    return `<li>
                                                        <strong>${item.toolName}</strong>: 
                                                        <pre style="margin-top: 5px; background-color: #f0f0f0; padding: 8px; border-radius: 4px; max-height: 200px; overflow: auto; font-size: 12px;">
                                                            ${resultJson}
                                                        </pre>
                                                    </li>`;
                                                }).join('')}
                                            </ul>
                                            ${allToolResults.length !== successfulToolsCount ? `<h4 style='margin-top: 15px; color: #e74c3c;'>失败的工具 (${allToolResults.length - successfulToolsCount}):</h4><ul>${allToolResults.filter(item => !item.result || item.result.success !== true).map(item => `<li><strong>${item.toolName}</strong>: ${item.result?.error || '未知错误'}</li>`).join('')}</ul>` : ''}
                                        </div>
                                    </details>
                                </div>
                            `;
                            
                            // ... (添加样式和滚动逻辑保持不变) ...
                            
                            // 确保结果可见并滚动到结果区域
                            setTimeout(() => {
                                // *** 再次检查 resultsContainer ***
                                const currentResultsContainer = document.querySelector('.results-container');
                                if (currentResultsContainer) {
                                   currentResultsContainer.scrollIntoView({ behavior: 'smooth' });
                                } else {
                                   console.error("MultiTool AI: 尝试滚动时找不到 .results-container");
                                }
                            }, 100);
                            
                            utils.showToast('AI综合分析完成');
                        } else {
                            throw new Error(result.error || "AI分析失败，未返回结果");
                        }
                    } catch (error) {
                        utils.showToast(`AI分析失败: ${error.message}`);
                        console.error('AI分析错误:', error);
                        
                        // 更新加载动画状态为"分析失败"
                        const loadingElement = document.getElementById('multi-tool-loading');
                        if (loadingElement) {
                            const loadingTitle = loadingElement.querySelector('.loading-title');
                            if (loadingTitle) loadingTitle.textContent = 'AI分析失败';
                            
                            const currentTool = loadingElement.querySelector('.current-tool');
                            if (currentTool) currentTool.textContent = '将显示常规分析结果';
                            
                            // 更新分析阶段标签
                            const analysisPhase = loadingElement.querySelector('.analysis-phase');
                            if (analysisPhase) {
                                analysisPhase.textContent = 'AI分析失败';
                                analysisPhase.style.backgroundColor = '#fff0f0';
                            }
                        }
                        
                        // 如果AI分析失败，显示普通工具结果 (只显示成功的)
                        allToolResults.filter(item => item.result && item.result.success === true).forEach(item => {
                            sequenceTools.displayResults(item.tool, item.result, detectedType);
                        });
                    }
                }
            } catch (error) {
                console.error('多工具分析过程中发生错误:', error);
                utils.showToast(`分析过程中发生错误: ${error.message || '未知错误'}`);
            } finally {
                // 无论成功或失败，都确保隐藏加载动画
                //if (this.selectedTools.length > 1) { // 现在总是 > 1
                    this.hideMultiToolLoading();
                //} else {
                //    utils.hideLoading(); // 单工具加载由 search.js 处理
                //}
                actionAnalyzeBtn.classList.remove('loading');
            }
        };

        // *** 关键：移除可能存在的旧监听器，然后添加新的 ***
        actionAnalyzeBtn.removeEventListener('click', this.handleMultiToolAnalysis);
        actionAnalyzeBtn.addEventListener('click', this.handleMultiToolAnalysis);
        console.log("多工具分析事件监听器已绑定");
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