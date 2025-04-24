// 工具函数
const utils = {
    showToast(message) {
        // 控制台打印消息（用于调试）
        console.log("显示Toast消息:", message);
        
        // 使用固定的toast元素
        const toast = document.getElementById('fixed-toast');
        const toastContent = toast.querySelector('.toast-content');
        
        // 设置消息内容
        toastContent.textContent = message;
        
        // 显示toast
        toast.classList.add('show');
        
        // 3秒后隐藏
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    },

    showLoading(message) {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">${message}</div>
        `;
        document.body.appendChild(overlay);
        setTimeout(() => overlay.classList.add('show'), 100);
    },
    
    updateLoadingText(message) {
        const loadingText = document.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = message;
        }
    },

    hideLoading() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => overlay.remove(), 300);
        }
    },
    
    // 获取认证头
    getAuthHeader() {
        const token = localStorage.getItem('token');
        console.log('utils.getAuthHeader: token =', token);
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },
    
    // 检查是否已登录
    isLoggedIn() {
        const token = localStorage.getItem('token');
        const userStr = localStorage.getItem('user');
        const isLogged = Boolean(token && userStr);
        console.log('utils.isLoggedIn:', isLogged);
        return isLogged;
    }
};

// 序列分析工具
const sequenceTools = {
    async analyzeSequence(tool, sequence, retryCount = 0) {
        try {
            // 检查用户是否已登录
            if (!utils.isLoggedIn()) {
                utils.hideLoading();
                alert('请先登录后再使用序列分析功能');
                window.location.href = 'index.html';
                return;
            }
            
            // 对于SignalP分析，显示特殊提示并强制等待
            if (tool === 'signalp') {
                utils.showToast("SignalP分析需要较长时间(5-10秒)，请耐心等待...");
                
                // 强制等待1秒，模拟服务器处理时间
                if (retryCount === 0) {
                    utils.updateLoadingText("正在提交序列...");
                    await new Promise(resolve => setTimeout(resolve, 500));
                    utils.updateLoadingText("服务器正在处理序列，请等待(约10秒)...");
                    await new Promise(resolve => setTimeout(resolve, 500));
                    utils.updateLoadingText("正在获取分析结果...");
                }
            }

            // 处理限制性内切酶分析
            if (tool === 'analyze_restriction') {
                // 检查输入中是否包含空格，用于分割序列和酶名
                const inputParts = sequence.trim().split(/\s+/);
                
                // 如果只有序列没有酶名
                if (inputParts.length <= 1) {
                    utils.hideLoading();
                    utils.showToast("请在序列后用空格分隔输入限制酶名称，例如：ATGC EcoRI BamHI");
                    return null;
                }
                
                // 提取序列和酶名
                const seqPart = inputParts[0];
                const enzymesPart = inputParts.slice(1).join(' ');
                
                // 发送请求，包含提取的序列和酶名称
                const response = await fetch(`/api/${tool}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...utils.getAuthHeader()
                    },
                    body: JSON.stringify({ 
                        sequence: seqPart,
                        enzymes: enzymesPart
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `请求失败: ${response.status}`);
                }
                
                return await response.json();
            }

            // 处理密码子使用分析
            if (tool === 'analyze_codons') {
                // 检查输入中是否包含空格，用于分割序列和宿主ID
                const inputParts = sequence.trim().split(/\s+/);
                
                // 如果只有序列没有宿主ID
                if (inputParts.length <= 1) {
                    utils.hideLoading();
                    utils.showToast("请在序列后用空格分隔输入宿主ID，例如：ATGC 9606");
                    return null;
                }
                
                // 提取序列和宿主ID 
                const seqPart = inputParts[0];
                const hostIdPart = inputParts.slice(1).join(' ');
                
                // 发送请求，包含提取的序列和宿主ID
                const response = await fetch(`/api/${tool}`, {
                    method: 'POST', 
                    headers: {
                        'Content-Type': 'application/json',
                        ...utils.getAuthHeader()
                    },
                    body: JSON.stringify({ 
                        sequence: seqPart,
                        host_id: hostIdPart
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `请求失败: ${response.status}`);
                }
                
                return await response.json();
            }
            
            // 处理FASTA格式转换
            if (tool === 'transform') {
                // 识别是否是FASTA格式
                const isFasta = sequence.trim().startsWith('>');
                
                if (!isFasta) {
                    utils.hideLoading();
                    utils.showToast("输入不是FASTA格式，请确保序列以'>'开头");
                    return null;
                }
                
                // 是否返回所有序列（检查序列中是否包含多个'>'行）
                const hasManySequences = (sequence.match(/^>/gm) || []).length > 1;
                
                // 发送FASTA转换请求
                const response = await fetch('/api/transform', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...utils.getAuthHeader()
                    },
                    body: JSON.stringify({
                        sequence: sequence,
                        return_all: hasManySequences, // 根据序列数量决定是否返回所有序列
                        format_output: true
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `请求失败: ${response.status}`);
                }
                
                return await response.json();
            }
            
            // 其他工具的常规处理
            const response = await fetch(`/api/${tool}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...utils.getAuthHeader()  // 添加认证头
                },
                body: JSON.stringify({ sequence })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `请求失败: ${response.status}`);
            }
            
            const result = await response.json();
            
            // 检查结果是否包含必要的信息
            if (tool === 'signalp' && result.success && (!result.result_text || result.result_text === "无详细预测文本")) {
                // 如果没有结果文本，尝试重试
                if (retryCount < 2) {
                    utils.showToast(`未获取到详细预测文本，正在重试 (${retryCount + 1}/3)...`);
                    await new Promise(resolve => setTimeout(resolve, 10000));
                    return this.analyzeSequence(tool, sequence, retryCount + 1);
                }
            }
            
            return result;
        } catch (error) {
            // 添加重试逻辑
            if (retryCount < 2) {
                const waitTime = tool === 'signalp' ? 5000 : 2000; // SignalP等待时间缩短为5秒
                utils.showToast(`请求失败，${waitTime/1000}秒后重试 (${retryCount + 1}/3)...`);
                // 等待后重试
                await new Promise(resolve => setTimeout(resolve, waitTime));
                return this.analyzeSequence(tool, sequence, retryCount + 1);
            }
            throw new Error(`请求失败: ${error.message}`);
        }
    },

    displayResults(tool, result, detectedType) {
        // 创建结果容器（如果不存在）
        let resultsContainer = document.querySelector('.results-container');
        if (!resultsContainer) {
            resultsContainer = document.createElement('div');
            resultsContainer.className = 'results-container';
            document.querySelector('.content-container').appendChild(resultsContainer);
        }
        
        // 创建或清空特定工具的结果区域
        let toolResult = document.querySelector(`.${tool}-result`);
        if (!toolResult) {
            toolResult = document.createElement('div');
            toolResult.className = `${tool}-result result-box`;
            toolResult.innerHTML = `
                <h3>${getToolName(tool)}</h3>
                <div class="result-content"></div>
                <img class="result-image" style="display: none;">
            `;
            resultsContainer.appendChild(toolResult);
        }
        
        const resultBox = toolResult.querySelector('.result-content');
        
        switch(tool) {
            case 'transform':
                //将FASTA形式转换成纯序列
                if (result.sequences && Object.keys(result.sequences).length > 0) {
                    // 多序列情况
                    const sequenceEntries = Object.entries(result.sequences).map(([id, seq]) => `
                        <div class="sequence-entry">
                            <h5><i class="fas fa-file-alt"></i> 序列ID: ${id}</h5>
                            <div class="sequence-text">${seq}</div>
                            <button class="copy-btn" data-sequence="${seq.replace(/\n/g, '')}">
                                <i class="fas fa-copy"></i> 复制序列
                            </button>
                        </div>
                    `).join('');
                    
                    resultBox.innerHTML = `
                        <h4>转换结果 (共${result.count}个序列):</h4>
                        <div class="sequences-container">
                            ${sequenceEntries}
                        </div>
                    `;
                    
                    // 添加复制功能
                    setTimeout(() => {
                        document.querySelectorAll('.copy-btn').forEach(btn => {
                            btn.addEventListener('click', function() {
                                const sequence = this.getAttribute('data-sequence');
                                navigator.clipboard.writeText(sequence).then(() => {
                                    utils.showToast('序列已复制到剪贴板');
                                });
                            });
                        });
                    }, 100);
                } else {
                    // 单序列情况
                    resultBox.innerHTML = `
                        <h4>转换结果:</h4>
                        <div class="sequence-text">${result.sequence}</div>
                        <p>序列长度: ${result.length} 个字符</p>
                        <button class="copy-btn" data-sequence="${result.sequence.replace(/\n/g, '')}">
                            <i class="fas fa-copy"></i> 复制序列
                        </button>
                    `;
                    
                    // 添加复制功能
                    setTimeout(() => {
                        document.querySelector('.copy-btn').addEventListener('click', function() {
                            const sequence = this.getAttribute('data-sequence');
                            navigator.clipboard.writeText(sequence).then(() => {
                                utils.showToast('序列已复制到剪贴板');
                            });
                        });
                    }, 100);
                }
                break;
                
            case 'protparam':
                // 将氨基酸组成转换为紧凑表格形式
                let aaTable = '<table class="aa-composition"><tr>';
                let count = 0;
                for (const [aa, percent] of Object.entries(result.amino_acid_composition)) {
                    aaTable += `<td>${aa}: ${percent}</td>`;
                    count++;
                    if (count % 4 === 0) {
                        aaTable += '</tr><tr>';
                    }
                }
                aaTable += '</tr></table>';
                
                resultBox.innerHTML = `
                    <h4>序列:</h4>
                    <div class="sequence-text">${result.sequence}</div>
                    <p>序列类型: ${result.sequence_type}</p>
                    <p>分子量: ${result.molecular_weight} Da</p>
                    <p>氨基酸组成:</p>
                    ${aaTable}
                `;
                break;
                
            case 'sequence_annotation':
                // 基本信息
                resultBox.innerHTML = `
                    <h4>序列:</h4>
                    <div class="sequence-text">${result.sequence}</div>
                    <h4>基本信息:</h4>
                    <p>分子量: ${result.molecular_weight} Da</p>
                    <p>理论等电点: ${result.isoelectric_point}</p>
                `;
                
                // 稳定性和疏水性
                resultBox.innerHTML += `
                    <h4>稳定性与疏水性:</h4>
                    <p>不稳定指数: ${result.instability_index} (${result.stability})</p>
                    <p>芳香族氨基酸比例: ${result.aromaticity}</p>
                    <p>疏水性平均值 (GRAVY): ${result.gravy} (${result.hydrophobicity})</p>
                `;
                
                // 二级结构预测
                resultBox.innerHTML += `
                    <h4>二级结构预测:</h4>
                    <div class="secondary-structure">
                        <div class="structure-item">
                            <span>α-螺旋 (Helix):</span>
                            <div class="progress-bar">
                                <div class="progress" style="width: ${result.secondary_structure.helix}%;"></div>
                            </div>
                            <span>${result.secondary_structure.helix}%</span>
                        </div>
                        <div class="structure-item">
                            <span>β-折叠 (Sheet):</span>
                            <div class="progress-bar">
                                <div class="progress" style="width: ${result.secondary_structure.sheet}%;"></div>
                            </div>
                            <span>${result.secondary_structure.sheet}%</span>
                        </div>
                        <div class="structure-item">
                            <span>转角 (Turn):</span>
                            <div class="progress-bar">
                                <div class="progress" style="width: ${result.secondary_structure.turn}%;"></div>
                            </div>
                            <span>${result.secondary_structure.turn}%</span>
                        </div>
                    </div>
                `;
                
                // 功能域预测
                if (result.domains && result.domains.length > 0) {
                    resultBox.innerHTML += `
                        <h4>预测的功能域:</h4>
                        <div class="domains-container">
                            ${result.domains.map(domain => `
                                <div class="domain-item">
                                    <p>名称: ${domain.name}</p>
                                    <p>位置: ${domain.start}-${domain.end}</p>
                                    <p>序列: ${domain.sequence}</p>
                                </div>
                            `).join('')}
                        </div>
                    `;
                } else {
                    resultBox.innerHTML += `
                        <h4>预测的功能域:</h4>
                        <p>未检测到明显的功能域</p>
                    `;
                }
                
                // 信号肽预测
                resultBox.innerHTML += `
                    <h4>信号肽预测:</h4>
                    <p>预测结果: ${result.signal_peptide.predicted ? '可能含有信号肽' : '可能不含信号肽'}</p>
                    <p>概率: ${result.signal_peptide.probability}</p>
                    ${result.signal_peptide.cleavage_site ? `<p>可能的切割位点: ${result.signal_peptide.cleavage_site}</p>` : ''}
                `;
                
                // 跨膜区域预测
                if (result.transmembrane_regions && result.transmembrane_regions.length > 0) {
                    resultBox.innerHTML += `
                        <h4>预测的跨膜区域:</h4>
                        <div class="tm-regions-container">
                            ${result.transmembrane_regions.map(region => `
                                <div class="tm-region-item">
                                    <p>位置: ${region.start}-${region.end}</p>
                                    <p>平均疏水性: ${region.avg_hydrophobicity}</p>
                                    <p>序列: ${region.sequence}</p>
                                </div>
                            `).join('')}
                        </div>
                    `;
                } else {
                    resultBox.innerHTML += `
                        <h4>预测的跨膜区域:</h4>
                        <p>未检测到明显的跨膜区域</p>
                    `;
                }
                break;
                
            case 'translate':
                // 基本翻译结果
                resultBox.innerHTML = `
                    <h4>序列:</h4>
                    <div class="sequence-text">${result.original_sequence}</div>
                    <div class="translation-result">
                        <p><strong>翻译后蛋白质序列:</strong></p>
                        <div class="sequence-text">${result.translated_sequence}</div>
                    </div>
                `;
                
                // 翻译信息
                resultBox.innerHTML += `
                    <div class="translation-info">
                        <p>使用的遗传密码表: ${result.translation_table_name} (ID: ${result.translation_table})</p>
                    </div>
                `;
                
                // 添加控制选项
                if (result.available_tables) {
                    const tableOptions = Object.entries(result.available_tables)
                        .map(([id, name]) => `<option value="${id}" ${id == result.translation_table ? 'selected' : ''}>${id}: ${name}</option>`)
                        .join('');
                    
                    resultBox.innerHTML += `
                        <div class="translation-controls">
                            <h4>翻译设置:</h4>
                            <div class="control-group">
                                <label for="table-select">遗传密码表:</label>
                                <select id="table-select" class="table-select">
                                    ${tableOptions}
                                </select>
                            </div>
                            <div class="control-group">
                                <label>
                                    <input type="checkbox" id="to-stop-checkbox" class="to-stop-checkbox">
                                    在第一个终止密码子处停止翻译
                                </label>
                            </div>
                            <div class="control-group">
                                <label>
                                    <input type="checkbox" id="cds-checkbox" class="cds-checkbox">
                                    作为完整编码序列处理(检查起始/终止密码子)
                                </label>
                            </div>
                            <div class="sequence-type">
                                <span>序列类型:</span>
                                <label>
                                    <input type="radio" name="seq-type" value="dna" checked>
                                    DNA
                                </label>
                                <label>
                                    <input type="radio" name="seq-type" value="rna">
                                    RNA
                                </label>
                            </div>
                            <button class="retranslate-btn">重新翻译</button>
                        </div>
                    `;
                    
                    // 添加重新翻译的事件处理
                    setTimeout(() => {
                        const retranslateBtn = document.querySelector('.retranslate-btn');
                        if (retranslateBtn) {
                            retranslateBtn.addEventListener('click', () => {
                                const tableId = parseInt(document.querySelector('.table-select').value);
                                const toStop = document.querySelector('.to-stop-checkbox').checked;
                                const cds = document.querySelector('.cds-checkbox').checked;
                                const seqType = document.querySelector('input[name="seq-type"]:checked').value;
                                
                                // 显示加载状态
                                utils.showLoading('正在重新翻译...');
                                
                                // 发送翻译请求
                                fetch('/api/translate', {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json',
                                        ...utils.getAuthHeader()
                                    },
                                    body: JSON.stringify({
                                        sequence: result.original_sequence,
                                        seq_type: seqType,
                                        table_id: tableId,
                                        to_stop: toStop,
                                        cds: cds
                                    })
                                })
                                .then(response => {
                                    if (!response.ok) {
                                        throw new Error('翻译请求失败');
                                    }
                                    return response.json();
                                })
                                .then(newResult => {
                                    utils.hideLoading();
                                    // 更新翻译结果
                                    document.querySelector('.sequence-display').textContent = newResult.translated_sequence;
                                    document.querySelector('.translation-info').innerHTML = `
                                        <p>使用的遗传密码表: ${newResult.translation_table_name} (ID: ${newResult.translation_table})</p>
                                    `;
                                    utils.showToast('翻译成功!');
                                })
                                .catch(error => {
                                    utils.hideLoading();
                                    utils.showToast(`错误: ${error.message}`);
                                });
                            });
                        }
                    }, 100);
                }
                break;
        
                case 'analyze_codons':
                    // 确保我们有分析结果
                    const analysis = result.analysis || {};
                    const rscuValues = analysis.rscu_values || {};
                    const rareCodons = analysis.rare_codons_found || [];
                    const caiValue = analysis.cai_value || "未计算";
                    
                    // 显示密码子分析结果
                    resultBox.innerHTML = `
                        <h4>序列:</h4>
                        <div class="sequence-text">${result.sequence || result.input_sequence_preview || "未提供序列"}</div>
                        <h4>宿主物种:</h4>
                        <p>宿主ID: ${result.host_id || "未知"}</p>
                        <h4>密码子适应性指数 (CAI):</h4>
                        <p>${typeof caiValue === 'number' ? caiValue.toFixed(2) : caiValue}</p>
                        <p class="small-note">CAI值越接近1.0，表示密码子使用与宿主偏好越一致</p>
                        
                        <h4>稀有密码子:</h4>
                        ${rareCodons && rareCodons.length > 0 ? `
                        <div class="codon-table">
                            <div class="codon-header">
                                <div>密码子</div>
                                <div>位置</div>
                                <div>宿主频率</div>
                            </div>
                            <div class="table-body">
                            ${rareCodons.map(codon => `
                                <div class="codon-row">
                                    <div>${codon.codon}</div>
                                    <div>${codon.position_1_based || '-'}</div>
                                    <div>${typeof codon.host_frequency === 'number' ? codon.host_frequency.toFixed(3) : codon.host_frequency || '-'}</div>
                                </div>
                            `).join('')}
                            </div>
                        </div>
                        ` : '<p>未发现稀有密码子</p>'}
                        
                        <h4>RSCU值:</h4>
                        ${Object.keys(rscuValues).length > 0 ? `
                        <div class="rscu-table">
                            <div class="codon-header">
                                <div>密码子</div>
                                <div>RSCU</div>
                            </div>
                            <div class="table-body">
                            ${Object.entries(rscuValues).map(([codon, rscu]) => `
                                <div class="codon-row">
                                    <div>${codon}</div>
                                    <div>${typeof rscu === 'number' ? rscu.toFixed(2) : rscu}</div>
                                </div>
                            `).join('')}
                            </div>
                        </div>
                        <p class="small-note">RSCU (相对同义密码子使用) 反映每个密码子的使用偏好。值=1表示无偏好，>1表示偏好，<1表示不偏好</p>
                        ` : '<p>未计算RSCU值</p>'}
                    `;
                    break;
                
            case 'find_cutting_enzymes':
                resultBox.innerHTML = `
                    <h4>序列:</h4>
                    <div class="sequence-text">${result.sequence}</div>
                    <h4>序列长度: ${result.sequence_length} bp</h4>
                    <h4>找到 ${result.cutting_enzymes.length} 种可以切割此序列的酶:</h4>
                    <div class="enzyme-scroll-box">`;
                
                if (result.cutting_enzymes.length > 0) {
                    // 添加标题行
                    resultBox.querySelector('.enzyme-scroll-box').innerHTML += `
                        <div class="enzyme-header">
                            <span class="enzyme-name-col">酶名</span>
                            <span class="arrow-col">→</span>
                            <span class="count-col">切割次数</span>
                            <span class="pos-col">切割位置 (0-based, 最多显示10个)</span>
                        </div>
                    `;
                    
                    // 使用紧凑的文本格式展示结果
                    result.cutting_enzymes.forEach(enzymeData => {
                        const positions = enzymeData.cut_positions.slice(0, 10).join(', '); // 只显示前10个位点
                        const morePositions = enzymeData.cut_positions.length > 10 ? '...' : '';
                        resultBox.querySelector('.enzyme-scroll-box').innerHTML += `
                            <div class="enzyme-line">
                                <span class="enzyme-name-col"><span class="enzyme-name">${enzymeData.name}</span></span>
                                <span class="arrow-col">→</span>
                                <span class="count-col">${enzymeData.site_count}</span>
                                <span class="pos-col">[${positions}${morePositions}]</span>
                            </div>
                        `;
                    });
                    
                    resultBox.innerHTML += `
                        <p class="small-tip">点击酶名可复制用于限制性内切酶分析</p>
                    `;
                    
                    // 添加点击复制功能
                    setTimeout(() => {
                        const enzymeNames = document.querySelectorAll('.enzyme-name');
                        enzymeNames.forEach(name => {
                            name.addEventListener('click', function() {
                                // 创建一个临时输入框
                                const tempInput = document.createElement('input');
                                tempInput.value = this.textContent;
                                document.body.appendChild(tempInput);
                                tempInput.select();
                                document.execCommand('copy');
                                document.body.removeChild(tempInput);
                                
                                // 显示复制成功提示
                                utils.showToast(`已复制: ${this.textContent}`);
                            });
                        });
                    }, 100);
                } else {
                    resultBox.querySelector('.enzyme-scroll-box').innerHTML += '<p>没有找到任何可以切割该序列的标准限制酶。</p>';
                }
                break;
                
            case 'analyze_restriction':
                // 显示限制性内切酶分析结果
                resultBox.innerHTML = `
                    <h4>序列:</h4>
                    <div class="sequence-text">${result.sequence}</div>
                    <h4>序列长度:</h4>
                    <p>${result.sequence_length} bp</p>
                    <h4>使用的有效酶:</h4>
                    <p>${result.enzymes_used.join(', ') || '无'}</p>
                `;
                
                // 显示模糊匹配结果
                if (result.fuzzy_matched && Object.keys(result.fuzzy_matched).length > 0) {
                    let fuzzyMatchHtml = '<h4>模糊匹配结果:</h4><div class="fuzzy-match">';
                    for (const [query, match] of Object.entries(result.fuzzy_matched)) {
                        fuzzyMatchHtml += `<p>'${query}' <span class="match-arrow">→</span> '${match}'</p>`;
                    }
                    fuzzyMatchHtml += '</div>';
                    resultBox.innerHTML += fuzzyMatchHtml;
                }
                
                if (result.invalid_enzymes_skipped && result.invalid_enzymes_skipped.length > 0) {
                    resultBox.innerHTML += `
                        <div class="warning-message">
                            <p>跳过的无效酶: ${result.invalid_enzymes_skipped.join(', ')}</p>
                        </div>
                    `;
                }
                
                // 各酶切割详情
                resultBox.innerHTML += '<h4>各酶切割详情 (0-based):</h4>';
                if (Object.keys(result.analysis).length > 0) {
                    let enzymeDetails = '<div class="enzyme-details">';
                    for (const enzyme in result.analysis) {
                        const data = result.analysis[enzyme];
                        const positions = data.cut_positions.length > 0 ? data.cut_positions.join(', ') : '无';
                        enzymeDetails += `
                            <div class="enzyme-detail-item">
                                <strong>${enzyme}</strong>: 
                                切割次数: ${data.site_count}, 
                                位置: [${positions}]
                            </div>
                        `;
                    }
                    enzymeDetails += '</div>';
                    resultBox.innerHTML += enzymeDetails;
                } else {
                    resultBox.innerHTML += '<p>未找到指定酶的切割位点。</p>';
                }
                
                // 酶切片段总结
                const summary = result.summary;
                resultBox.innerHTML += `
                    <h4>酶切片段总结 (0-based):</h4>
                    <p>总切割位点数: ${summary.total_cuts}</p>
                `;
                
                if (summary.cut_sites_all.length > 0) {
                    resultBox.innerHTML += `<p>所有切割位点: [${summary.cut_sites_all.join(', ')}]</p>`;
                }
                
                resultBox.innerHTML += `<p>片段数量: ${summary.fragment_count}</p>`;
                
                if (summary.fragments.length > 0) {
                    // 使用滚动窗口样式显示片段列表
                    let fragmentsBox = `
                        <div class="enzyme-scroll-box">
                            <div class="enzyme-header">
                                <span class="enzyme-name-col">片段编号</span>
                                <span class="arrow-col">→</span>
                                <span class="count-col">位置</span>
                                <span class="pos-col">长度</span>
                            </div>
                    `;
                    
                    // 显示所有片段
                    summary.fragments.forEach((frag, index) => {
                        fragmentsBox += `
                            <div class="enzyme-line">
                                <span class="enzyme-name-col">片段 ${index + 1}</span>
                                <span class="arrow-col">→</span>
                                <span class="count-col">${frag.start}-${frag.end}</span>
                                <span class="pos-col">${frag.length} bp</span>
                            </div>
                        `;
                    });
                    
                    fragmentsBox += `</div>`;
                    resultBox.innerHTML += fragmentsBox;
                }
                break;

                case 'analyze_nucleic_acid':
                    // 显示核酸物理化学性质分析结果
                    resultBox.innerHTML = `
                        <h4>序列:</h4>
                        <div class="sequence-text">${result.sequence}</div>
                        <p>序列类型: ${result.is_rna ? "RNA" : "DNA"}</p>
                        
                        <h4>GC含量:</h4>
                        <p>${result.overall_gc}%</p>
                        
                        <h4>熔解温度 (Tm) 估算:</h4>
                        <div class="property-section">
                            <p>基于GC含量 (简单方法): ${result.tm_gc_simple}°C</p>
                            <p>最近邻模型 (标准条件*): ${result.tm_nn_standard}°C</p>
                            <p class="small-note">*标准条件近似为: 50mM Na+, 0mM K+, 0mM Mg++</p>
                        </div>
                        
                        <h4>浮力密度估算:</h4>
                        <div class="property-section">
                            <p>在CsCl梯度中 (Schildkraut公式): ${result.estimated_density_cscl} g/cm³</p>
                            <p class="small-note">这个估算主要适用于双链DNA，基于GC含量和Schildkraut公式。</p>
                        </div>
                    `;
                    break;
                
            case 'signalp':
                if (result.success) {
                    // 添加预测文本结果
                    let resultText = result.result_text || "无详细预测文本";
                    
                    // 检查结果文本是否有效
                    const hasValidText = resultText !== "无详细预测文本" && 
                                        (resultText.includes("SP=") || 
                                         resultText.includes("pos") || 
                                         resultText.includes("aa"));
                    
                    if (hasValidText) {
                        // 格式化预测文本，保留原始格式
                        resultBox.innerHTML = `
                            <h4>序列:</h4>
                            <div class="sequence-text">${result.sequence}</div>
                            <p>序列长度: ${result.sequence.length} 个氨基酸</p>
                            <p class="success-message">预测完成</p>
                            <pre class="prediction-text">${resultText}</pre>
                        `;
                        
                        // 处理图像
                        if (result.image) {
                            console.log("原始图像URL:", result.image);
                            
                            // 确保URL是有效的
                            let imageUrl = result.image;
                            
                            // 如果URL不是以http或/开头，添加/
                            if (!imageUrl.startsWith('http') && !imageUrl.startsWith('/')) {
                                imageUrl = '/' + imageUrl;
                            }
                            
                            console.log("处理后的图像URL:", imageUrl);
                            
                            // 创建新的图像元素，替换原有的
                            const oldImg = toolResult.querySelector('.result-image');
                            const newImg = document.createElement('img');
                            newImg.className = 'result-image';
                            newImg.style.maxWidth = '100%';
                            newImg.style.marginTop = '10px';
                            newImg.style.display = 'none'; // 初始隐藏
                            
                            // 设置图像加载事件
                            newImg.onload = () => {
                                console.log("图像加载成功");
                                newImg.style.display = 'block';
                                utils.showToast("图像加载成功！");
                                
                                // 图像加载成功后，调用API删除临时文件
                                setTimeout(() => {
                                    fetch('/api/delete_temp_file', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json',
                                        },
                                        body: JSON.stringify({ file_path: imageUrl })
                                    })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.success) {
                                            console.log("临时文件已删除:", imageUrl);
                                        } else {
                                            console.warn("删除临时文件失败:", data.error);
                                        }
                                    })
                                    .catch(error => {
                                        console.error("调用删除API时出错:", error);
                                    });
                                }, 1000); // 延迟1秒执行，确保图像完全加载
                            };
                            
                            newImg.onerror = (e) => {
                                console.error("图像加载失败:", e);
                                utils.showToast("图像加载失败，请重试");
                                newImg.style.display = 'none';
                                resultBox.innerHTML += `
                                    <p class="error-message">图像加载失败，但预测结果已显示</p>
                                    <p class="error-message">图像URL: ${imageUrl}</p>
                                `;
                            };
                            
                            // 设置图像源 - 添加时间戳防止缓存
                            const timestamp = new Date().getTime();
                            newImg.src = `${imageUrl}?t=${timestamp}`;
                            
                            // 替换原有图像元素
                            if (oldImg && oldImg.parentNode) {
                                oldImg.parentNode.replaceChild(newImg, oldImg);
                            } else {
                                toolResult.appendChild(newImg);
                            }
                            
                            // 尝试使用fetch直接检查图像是否可访问
                            fetch(imageUrl)
                                .then(response => {
                                    if (!response.ok) {
                                        throw new Error(`HTTP error! status: ${response.status}`);
                                    }
                                    console.log("Fetch检查图像成功:", response.status);
                                    return response.blob();
                                })
                                .then(blob => {
                                    console.log("图像blob类型:", blob.type);
                                    if (blob.type.startsWith('image/')) {
                                        console.log("有效的图像类型");
                                    } else {
                                        console.warn("无效的图像类型:", blob.type);
                                    }
                                })
                                .catch(e => {
                                    console.error("Fetch检查图像失败:", e);
                                });
                        } else {
                            resultBox.innerHTML += `<p class="warning-message">无法获取预测图像，但预测结果已显示</p>`;
                        }
                        
                        // 调整结果框的宽度
                        toolResult.style.width = '100%';
                        toolResult.style.maxWidth = '800px';
                    } else {
                        resultBox.innerHTML = `
                            <p class="error-message">预测失败: 未获取到有效的预测结果</p>
                            <p>可能原因:</p>
                            <ul>
                                <li>服务器响应时间过长</li>
                                <li>序列格式不正确</li>
                                <li>外部API暂时不可用</li>
                            </ul>
                            <p>建议: 稍后重试或使用较短的序列</p>
                        `;
                    }
                } else {
                    resultBox.innerHTML = `
                        <p class="error-message">预测失败: ${result.error || '未知错误'}</p>
                        <p>可能原因:</p>
                        <ul>
                            <li>服务器响应时间过长</li>
                            <li>序列格式不正确</li>
                            <li>外部API暂时不可用</li>
                        </ul>
                        <p>建议: 稍后重试或使用较短的序列</p>
                        <p>您也可以尝试直接运行SignalP.py脚本</p>
                    `;
                }
                break;
                
            case 'vaxijen':
                resultBox.innerHTML = `
                    <h4>序列:</h4>
                    <div class="sequence-text">${result.sequence}</div>
                    <p>预测结果: ${result.result}</p>
                    <p>Vaxijen打分: ${result.score}</p>
                `;
                break;

            case 'toxinpred':
                resultBox.innerHTML = `
                    <h4>序列:</h4>
                    <div class="sequence-text">${result.sequence}</div>
                    <p>SVM得分: ${result.svm_score}</p>
                    <p>预测结果: <span class="${result.is_toxin ? 'error' : 'success'}">${result.result}</span></p>
                `;
                if (result.toxicity_features) {
                    resultBox.innerHTML += `
                        <div class="toxin-features">
                            <h4>详细特征分析:</h4>
                            <p>Hydrophobicity: ${result.toxicity_features.Hydrophobicity}</p>
                            <p>Hydropathicity: ${result.toxicity_features.Hydropathicity}</p>
                            <p>Hydrophilicity: ${result.toxicity_features.Hydrophilicity}</p>
                            <p>Charge: ${result.toxicity_features.Charge}</p>
                            <p>Mol wt: ${result.toxicity_features['Mol wt']}</p>
                        </div>
                    `;
                }
                break;
                
            case 'physchemparam':
                // 基本信息
                resultBox.innerHTML = `
                    <h4>序列:</h4>
                    <div class="sequence-text">${result.sequence}</div>
                    <h4>基本信息:</h4>
                    <p>分子量: ${result.molecular_weight.toFixed(2)} Da</p>
                    <p>理论等电点: ${result.theoretical_pi.toFixed(2)}</p>
                `;
                
                // 氨基酸组成
                if (result.amino_acid_composition) {
                    resultBox.innerHTML += `
                        <h4>氨基酸组成:</h4>
                        <div class="aa-composition">
                            ${Object.entries(result.amino_acid_composition).map(([aa, data]) => 
                                `<div>${aa}: ${data.count} (${data.percent}%)</div>`).join('')}
                        </div>
                    `;
                }
                
                // 电荷残基
                resultBox.innerHTML += `
                    <p>带负电荷残基数量 (Asp + Glu): ${result.negative_residues}</p>
                    <p>带正电荷残基数量 (Arg + Lys): ${result.positive_residues}</p>
                `;

                // 消光系数
                if (result.extinction_coefficients) {
                    resultBox.innerHTML += `
                        <h4>消光系数:</h4>
                    `;
                    if (result.extinction_coefficients.cystines) {
                        resultBox.innerHTML += `
                            <p>Cystine状态: ${result.extinction_coefficients.cystines.coefficient} M⁻¹cm⁻¹ 
                            (Abs 0.1% = ${result.extinction_coefficients.cystines.abs_01})</p>
                        `;
                    }
                    if (result.extinction_coefficients.reduced) {
                        resultBox.innerHTML += `                            <p>还原状态: ${result.extinction_coefficients.reduced.coefficient} M⁻¹cm⁻¹ 
                            (Abs 0.1% = ${result.extinction_coefficients.reduced.abs_01})</p>
                        `;
                    }
                }

                // 半衰期
                if (result.half_life) {
                    resultBox.innerHTML += `
                        <h4>估计半衰期:</h4>
                    `;
                    if (result.half_life.n_terminal) {
                        resultBox.innerHTML += `<p>N末端氨基酸: ${result.half_life.n_terminal}</p>`;
                    }
                    if (result.half_life.mammalian) {
                        resultBox.innerHTML += `<p>哺乳动物网织红细胞 (体外): ${result.half_life.mammalian}</p>`;
                    }
                    if (result.half_life.yeast) {
                        resultBox.innerHTML += `<p>酵母 (体内): ${result.half_life.yeast}</p>`;
                    }
                    if (result.half_life.ecoli) {
                        resultBox.innerHTML += `<p>大肠杆菌 (体内): ${result.half_life.ecoli}</p>`;
                    }
                }

                resultBox.innerHTML += `<br>`;
                
                // 稳定性和特性
                if (result.instability_index) {
                    resultBox.innerHTML += `
                        <p>不稳定指数: ${result.instability_index.toFixed(2)}</p>
                        <p>蛋白质分类为: ${result.stability_classification || '未知'}</p>
                        <p>脂肪族指数: ${result.aliphatic_index.toFixed(2)}</p>
                        <p>疏水性平均值 (GRAVY): ${result.gravy.toFixed(3)}</p>
                        <p class="small-note">GRAVY 指数 (Grand Average of Hydropathicity) 的含义：
GRAVY 指数是蛋白质疏水性的量化指标，通过计算蛋白质序列中所有氨基酸疏水性值的平均值得出。每个氨基酸都有一个预先定义的疏水性值（通常基于 Kyte-Doolittle 疏水性尺度）。
关于正负值的说明:GRAVY 值为负数，表示该蛋白质整体上是亲水性的 (hydrophilic)。 这意味着该蛋白的氨基酸组成中,亲水性氨基酸(例如;精氨酸、赖氨酸、谷氨酸、天冬氨酸等0的比例相对较高。反之,为正数,则呈现疏水性(hydrophobic)特征。
关于数值大小的说明: 数值的绝对值越接近于 0,表示该蛋白的疏水性或亲水性不强,可能兼具一定的亲水性和疏水性。相反,绝对值越大,则表示该蛋白的疏水性或亲水性越强。</p>
                    `;
                }            
                break;
                
            default:{
                resultBox.innerHTML = `<p>未知工具类型: ${tool}</p>`;
                break;
            }
        }
        // 显示结果容器
        resultsContainer.style.display = 'block';
    }
};

// 获取工具名称
function getToolName(tool) {
    switch(tool) {
        case 'transform':
            return 'FASTA格式转换 (BioPython)';
        case 'protparam':
            return '分子量计算 (BioPython)';
        case 'sequence_annotation':
            return '序列注释分析 (BioPython)';
        case 'translate':
            return '序列翻译 (BioPython)';
        case 'analyze_codons':
            return '密码子使用分析 (BioPython))';
        case 'find_cutting_enzymes':
            return '酶谱分析 (BioPython)';
        case 'analyze_restriction':
            return '限制性内切酶分析 (BioPython)';
        case 'analyze_nucleic_acid':
            return 'GC含量计算等性质 (BioPython)';
        case 'signalp':
            return '信号肽预测 (SignalP)';
        case 'vaxijen':
            return '抗原性预测 (VaxiJen)';
        case 'toxinpred':
            return '毒性预测 (ToxinPred)';
        case 'physchemparam':
            return '物理化学参数分析 (ProtParam)';
        default:
            return tool;
    }
}

// 统一的序列类型检测函数
function getSequenceType(seq) {
    if (!seq) return 'unknown';
    
    // 只取第一个空格前的部分作为序列
    const firstPart = seq.split(/\s+/)[0];
    if (!firstPart) return 'unknown';
    
    const seqUpper = firstPart.toUpperCase(); // 转大写
    if (!seqUpper) return 'unknown';
    
    console.log("序列类型检测只检查空格前的内容:", seqUpper);

    // 检查是否只包含 DNA 碱基
    if (/^[ATGC]+$/.test(seqUpper)) {
        return 'dna';
    }
    // 检查是否只包含 RNA 碱基
    if (/^[AUGC]+$/.test(seqUpper)) {
        return 'rna';
    }
    // 检查是否包含蛋白质特有字符，并且不是纯 DNA/RNA
    if (/[EFHIKLMNPQRSVWY]/i.test(seqUpper)) {
        // 进一步检查是否混有非氨基酸字符 (除了允许的ATGCU)
        if (/[^ACDEFGHIKLMNPQRSTVWYUTGC]/i.test(seqUpper)) {
            return 'unknown'; // 包含非法字符
        }
        return 'protein';
    }
    // 如果只包含ATGCU，但不是纯DNA或纯RNA（例如混用T和U），则认为是未知
    if (/^[ATGCU]+$/.test(seqUpper)) {
         return 'unknown'; // 可能是混合或需要后端判断
    }
    // 包含其他无法识别的字符
    return 'unknown';
}

// 默认粒子配置
const defaultParticleConfig = {
    particles: {
        number: {
            value: 80,
            density: {
                enable: true,
                value_area: 800
            }
        },
        color: {
            value: '#3498db'
        },
        shape: {
            type: 'circle'
        },
        opacity: {
            value: 0.5,
            random: false,
            anim: {
                enable: false
            }
        },
        size: {
            value: 3,
            random: true,
            anim: {
                enable: false
            }
        },
        line_linked: {
            enable: true,
            distance: 150,
            color: '#3498db',
            opacity: 0.4,
            width: 1
        },
        move: {
            enable: true,
            speed: 2,
            direction: 'none',
            random: false,
            straight: false,
            out_mode: 'out',
            bounce: false,
            attract: {
                enable: true,
                rotateX: 600,
                rotateY: 1200
            }
        }
    },
    interactivity: {
        detect_on: 'canvas',
        events: {
            onhover: {
                enable: true,
                mode: 'grab'
            },
            onclick: {
                enable: true,
                mode: 'push'
            },
            resize: true
        },
        modes: {
            grab: {
                distance: 140,
                line_linked: {
                    opacity: 1
                }
            },
            push: {
                particles_nb: 4
            }
        }
    },
    retina_detect: true
};

// 重新初始化粒子系统
function reloadParticles() {
    // 首先检查是否存在粒子系统
    if (window.pJSDom && window.pJSDom.length > 0) {
        // 删除现有的粒子系统
        window.pJSDom = [];
        const canvas = document.querySelector('#particles-js canvas');
        if (canvas) {
            canvas.remove();
        }
        
        // 重新初始化粒子系统
        setTimeout(() => {
            particlesJS('particles-js', window.particleConfig || defaultParticleConfig);
        }, 100);
    }
}

// 在页面加载时初始化
document.addEventListener('DOMContentLoaded', async function() {
    // 检查登录状态
    const token = localStorage.getItem('token');
    if (!token) {
        // 未登录，跳转到首页
        window.location.href = 'index.html';
        alert('请先登录后再使用序列分析功能');
        return;
    }
    
    // 导入共享UI模块
    let userUI;
    try {
        userUI = await import('../utils/user-ui.js');
        // 添加会员状态样式
        userUI.addMembershipStyles();
    } catch(error) {
        console.error('无法加载用户UI共享模块:', error);
    }
    
    // 检查登录状态并更新UI
    await checkLoginStatus(userUI);
    
    // 初始化页面
    initPage();
    
    try {
        // 导入多工具模块
        console.log("正在导入多工具模块...");
        const multiToolModule = await import('./multiTool.js');
        const multiTool = multiToolModule.default;
        
        // 初始化多工具功能(处理会员多选功能)
        console.log("初始化多工具功能...");
        await multiTool.init();
        
        // 添加全局标记，表示多工具模块已加载
        window.multiToolLoaded = true;
        console.log("多工具模块已成功加载和初始化");
    } catch (error) {
        console.error('无法加载多工具模块:', error);
        // 如果多工具模块加载失败，回退到默认的单选功能
        window.multiToolLoaded = false;
        console.log("多工具模块加载失败，回退到单工具模式");
        initPage();
    }
    
    // 设置工具搜索和分类功能
    setupToolsFiltering();
    
    // 保存粒子配置以便重新初始化
    if (window.pJSDom && window.pJSDom[0] && window.pJSDom[0].pJS) {
        window.particleConfig = window.pJSDom[0].pJS.particles.json;
    }
    
    // 添加window resize事件，解决粒子背景拉伸问题
    window.addEventListener('resize', function() {
        // 延迟执行以避免频繁触发
        if (this.resizeTimeout) clearTimeout(this.resizeTimeout);
        this.resizeTimeout = setTimeout(function() {
            // 重新加载粒子系统
            reloadParticles();
        }, 200);
    });
});

// 初始化页面
function initPage() {
    // 获取页面元素
    const sequenceInput = document.querySelector('.sequence-input-editor');
    const toolCards = document.querySelectorAll('.tool-card');
    const aiAnalyzeBtn = document.querySelector('.ai-analyze-btn');
    
    // 获取操作栏元素
    const actionBar = document.querySelector('.action-bar');
    if (!actionBar) { 
        console.error("Action bar element not found!");
        return; 
    }
    const toolSelection = actionBar.querySelector('.tool-selection span');
    const actionAnalyzeBtn = actionBar.querySelector('.analyze-btn');
    
    // 设置粒子背景
    setupParticles();
    
    // 设置文本输入和计数器
    setupSequenceInput(sequenceInput);
    
    // 设置AI分析按钮点击事件
    if (aiAnalyzeBtn) {
        aiAnalyzeBtn.addEventListener('click', function() {
            this.classList.toggle('active');
            const aiQueryContainer = document.querySelector('.ai-query-container');
            if (aiQueryContainer) {
                // 显示/隐藏AI查询容器
                const isActive = this.classList.contains('active');
                aiQueryContainer.style.display = isActive ? 'block' : 'none';
                
                // 如果显示查询容器，则将序列输入框的内容复制到查询输入框
                if (isActive) {
                    const aiQueryInput = aiQueryContainer.querySelector('.ai-query-input');
                    if (aiQueryInput && sequenceInput.textContent) {
                        aiQueryInput.value = `请分析以下序列：\n${sequenceInput.textContent.trim()}`;
                        
                        // 聚焦到输入框并将光标放到文本末尾
                        setTimeout(() => {
                            aiQueryInput.focus();
                            aiQueryInput.setSelectionRange(aiQueryInput.value.length, aiQueryInput.value.length);
                        }, 100);
                    }
                }
            }
        });
    }
    
    // 设置工具过滤功能
    setupToolsFiltering();
    
    // 工具卡片点击事件更新
    toolCards.forEach(card => {
        card.addEventListener('click', function() {
            toolCards.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            
            // 更新操作栏显示的工具名称
            const toolName = this.querySelector('h4').textContent;
            toolSelection.textContent = toolName;
            
            // 检查是否选择了特殊工具，更新输入框 placeholder
            const tool = this.dataset.tool;
            if (tool === 'analyze_restriction') {
                // 显示限制性内切酶分析的输入格式提示
                sequenceInput.setAttribute('placeholder', '请输入: [DNA序列] [酶名1] [酶名2]... 例如: ATGCGAATTC EcoRI BamHI');
            } else if (tool === 'find_cutting_enzymes') {
                // 显示查找切割酶的输入格式提示
                sequenceInput.setAttribute('placeholder', '请输入DNA序列，将查找所有可切割该序列的限制酶');
            } else if (tool === 'analyze_nucleic_acid') {
                // 显示核酸物理化学性质分析的提示
                sequenceInput.setAttribute('placeholder', '请输入DNA或RNA序列，用于分析GC含量等物理化学特性');
            } else if (tool === 'analyze_codons') {
                sequenceInput.placeholder = '请输入DNA序列和宿主物种ID（如：ATGC 9606）[ID请前往生物知识库查询]';
            } else if (tool === 'transform') {
                sequenceInput.placeholder = '请输入FASTA形式'
            } else {
                sequenceInput.placeholder = '请输入序列...';
            }
        });
    });
    
    // 设置操作栏的分析按钮点击事件
    if (actionAnalyzeBtn) { 
        actionAnalyzeBtn.addEventListener('click', async function(event) {
            console.log("分析按钮被点击，检查AI模式状态和多工具模块状态");
            
            const sequence = sequenceInput.textContent.trim().toUpperCase();
            
            if (!sequence) {
                utils.showToast('请输入序列');
                return;
            }
            
            const activeCard = document.querySelector('.tool-card.active');
            if (!activeCard) {
                utils.showToast('请选择分析工具');
                return;
            }
            
            const tool = activeCard.dataset.tool;
            const detectedType = getSequenceType(sequence);
            
            // 检查是否处于AI分析模式
            const isAiMode = document.querySelector('.ai-analyze-btn.active') !== null;
            const aiQueryInput = document.querySelector('.ai-query-input');
            const aiQuery = isAiMode && aiQueryInput ? aiQueryInput.value.trim() : '';
            
            console.log("AI模式状态:", isAiMode ? "激活" : "未激活");
            console.log("多工具模块状态:", window.multiToolLoaded ? "已加载" : "未加载");
            
            // 如果是AI分析模式且有查询内容，则调用AI分析API
            if (isAiMode && aiQuery) {
                console.log("执行AI分析流程");
                // 标记为在AI模式，防止多工具模块触发
                this.dataset.aiMode = 'true';
                
                // 注意：不要在这个判断中阻止事件传播，否则会影响多工具功能
                
                this.classList.add('loading'); 
                utils.showLoading('正在进行AI分析...');
                
                try {
                    // 调用AI分析API
                    const response = await fetch('/api/ai_analyze', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...utils.getAuthHeader()
                        },
                        body: JSON.stringify({
                            sequence: sequence,
                            query: aiQuery,
                            tool: tool // 可选，传递当前选中的工具
                        })
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `AI分析请求失败: ${response.status}`);
                    }
                    
                    const result = await response.json();
                    
                    // 处理AI分析结果
                    if (result.success) {
                        // 创建或获取结果容器
                        let resultsContainer = document.querySelector('.results-container');
                        if (!resultsContainer) {
                            resultsContainer = document.createElement('div');
                            resultsContainer.className = 'results-container';
                            document.querySelector('.content-container').appendChild(resultsContainer);
                        }
                        
                        // 创建AI分析结果显示区域
                        let aiResultBox = document.querySelector('.ai-analysis-result');
                        if (!aiResultBox) {
                            aiResultBox = document.createElement('div');
                            aiResultBox.className = 'ai-analysis-result result-box';
                            resultsContainer.appendChild(aiResultBox);
                        }
                        
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
                        
                        // 设置AI分析结果内容
                        aiResultBox.innerHTML = `
                            <h3>AI分析报告</h3>
                            <div class="ai-report-content">
                                ${formattedReport}
                            </div>
                            <div class="ai-report-query">
                                <p><strong>分析需求:</strong> ${aiQuery}</p>
                            </div>
                        `;
                        
                        // 添加结果展示样式
                        const styleElement = document.createElement('style');
                        styleElement.textContent = `
                            .ai-report-content {
                                padding: 15px;
                                background-color: #f9f9fd;
                                border-radius: 10px;
                                font-size: 15px;
                                line-height: 1.6;
                                margin-bottom: 15px;
                            }
                            .ai-report-content pre.code-block {
                                background-color: #f0f0f0;
                                padding: 12px;
                                border-radius: 5px;
                                overflow-x: auto;
                                font-family: Consolas, Monaco, monospace;
                                margin: 10px 0;
                            }
                            .ai-report-content code {
                                background-color: #f0f0f0;
                                padding: 2px 5px;
                                border-radius: 3px;
                                font-family: Consolas, Monaco, monospace;
                            }
                            .ai-report-query {
                                border-top: 1px solid #eee;
                                padding-top: 10px;
                                color: #666;
                                font-size: 14px;
                            }
                        `;
                        document.head.appendChild(styleElement);
                        
                        // 更新检查结果状态
                        checkResults();
                        
                        // 重载粒子系统
                        setTimeout(reloadParticles, 300);
                        
                        // 隐藏AI查询容器
                        const aiAnalyzeBtn = document.querySelector('.ai-analyze-btn');
                        if (aiAnalyzeBtn) {
                            aiAnalyzeBtn.classList.remove('active');
                        }
                        const aiQueryContainer = document.querySelector('.ai-query-container');
                        if (aiQueryContainer) {
                            aiQueryContainer.style.display = 'none';
                        }
                        
                        utils.showToast('AI分析完成');
                    } else {
                        throw new Error(result.error || "AI分析失败，未返回结果");
                    }
                } catch (error) {
                    utils.showToast(`分析失败: ${error.message}`);
                    console.error('AI分析错误:', error);
                } finally {
                    utils.hideLoading();
                    this.classList.remove('loading');
                    // 重置模式标记
                    this.removeAttribute('data-ai-mode');
                }
            } else {
                // 非AI模式，此时可以由multiTool模块处理
                console.log("非AI模式，多工具模块状态:", window.multiToolLoaded ? "已加载" : "未加载");
                
                // 如果多工具模块已加载，让事件继续传播给多工具模块处理
                if (window.multiToolLoaded) {
                    console.log("多工具模块已加载，交由多工具模块处理");
                    return; // 不阻止事件传播，让multiTool模块处理
                }
                
                // 多工具模块未加载，使用默认的单工具处理逻辑
                console.log("多工具模块未加载，使用默认单工具处理");
                
                // Frontend Validation 
                if (tool === 'analyze_nucleic_acid') {
                    if (detectedType === 'protein') { utils.showToast('核酸特性分析工具无法处理蛋白质序列，请输入DNA或RNA。'); return; } 
                    else if (detectedType === 'unknown') { utils.showToast('序列包含无法识别的字符，无法进行核酸分析。'); return; }
                }
                if (tool === 'find_cutting_enzymes' && detectedType !== 'dna') { utils.showToast('限制酶分析工具仅支持DNA序列'); return; }
                if (tool === 'sequence_annotation' && detectedType !== 'protein') { utils.showToast('DNA或RNA序列无法进行序列注释，请输入蛋白质。'); return; }
                if (tool === 'translate' && detectedType === 'protein') { utils.showToast('蛋白质序列无法进行翻译，请输入DNA或RNA。'); return; }
                if (tool === 'toxinpred') {
                    const seqInput = sequence.split(/\s+/)[0];
                    if (seqInput.length < 5) { utils.showToast('ToxinPred要求序列长度至少为5个氨基酸'); return; }
                    if (seqInput.length > 50) { utils.showToast('ToxinPred工具限制序列长度最多50个氨基酸，请缩短序列'); return; }
                }
            
                this.classList.add('loading'); 
            
                try {
                    utils.showLoading('正在分析...');
                    
                    // --- Modify analyzeSequence call for analyze_codons ---
                    let result;
                    if (tool === 'analyze_codons') {
                        // 提取序列和宿主ID (允许非数字)
                        const inputParts = sequence.trim().split(/\s+/);
                        if (inputParts.length <= 1) {
                            utils.hideLoading();
                            this.classList.remove('loading');
                            utils.showToast("请在序列后用空格分隔输入宿主ID (例如：ATGC 9606 或 ATGC 3645.chloroplast)");
                            return;
                        }
                        const seqPart = inputParts[0];
                        const hostIdPart = inputParts.slice(1).join(' '); // 获取序列后的所有部分作为ID
                        
                        // 直接将提取的 hostIdPart (可能是 3645.chloroplast) 传给后端
                        result = await sequenceTools.analyzeSequence(tool, `${seqPart} ${hostIdPart}`); // 保持原始格式发送
                    } else {
                        // 其他工具的常规处理
                        result = await sequenceTools.analyzeSequence(tool, sequence);
                    }
                    // --- End modification ---
                    
                    utils.hideLoading();
                    
                    if (result) {
                        sequenceTools.displayResults(tool, result, detectedType);
                        checkResults(); 
                        // 重载粒子系统
                        setTimeout(reloadParticles, 300); 
                    }
                } catch (error) {
                    utils.hideLoading();
                    utils.showToast(error.message || '分析失败');
                    console.error('分析错误:', error);
                } finally {
                    this.classList.remove('loading');
                }
            }
        });
    }
    
    // 智能隐藏操作栏的逻辑
    let lastScrollPosition = window.scrollY;
    let isScrollingDown = false;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.scrollY;
        isScrollingDown = currentScroll > lastScrollPosition + 10; 
        const isScrollingUp = currentScroll < lastScrollPosition - 10; 

        if (isScrollingDown || isScrollingUp) {
            lastScrollPosition = currentScroll <= 0 ? 0 : currentScroll; 
        }
        
        const isNearBottom = (window.innerHeight + currentScroll) >= document.body.offsetHeight - 100;
        const isNearTop = currentScroll < 100;
        
        if (isScrollingDown && !isNearBottom && !isNearTop) {
            actionBar.classList.add('hide');
        } else if (isScrollingUp || isNearBottom || isNearTop) { 
            actionBar.classList.remove('hide');
        }
    });

    // 鼠标靠近底部时显示
    window.addEventListener('mousemove', function(e) {
        if (window.innerHeight - e.clientY < 100) {
            actionBar.classList.remove('hide');
        }
    });
    
    // 初始化检查
    checkResults(); 
    
}

// 检查是否有结果
function checkResults() {
    const resultsContainer = document.querySelector('.results-container');
    if (resultsContainer && resultsContainer.children.length > 0) { 
        document.body.classList.add('has-results');
    } else {
        document.body.classList.remove('has-results');
    }
}

// 设置粒子背景系统
function setupParticles() {
    if (window.particlesJS) {
        particlesJS("particles-js", defaultParticleConfig); // Use default config
    }
}

// 设置文本输入和计数器
function setupSequenceInput(sequenceInput) {
    const charCounter = document.querySelector('.char-counter');
    
    // 更新字符计数并将输入转换为大写
    sequenceInput.addEventListener('input', function() {
        // 将输入内容转换为大写
        const originalValue = this.textContent;
        const cursorPosition = window.getSelection().getRangeAt(0).startOffset;
        
        // 转换为大写
        if (originalValue !== originalValue.toUpperCase()) {
            this.textContent = originalValue.toUpperCase();
            
            // 恢复光标位置
            const range = document.createRange();
            const sel = window.getSelection();
            
            try {
                range.setStart(this.childNodes[0] || this, Math.min(cursorPosition, this.textContent.length));
                range.collapse(true);
                sel.removeAllRanges();
                sel.addRange(range);
            } catch (e) {
                console.log('光标位置恢复失败', e);
            }
        }
        
        // 更新字符计数
        const sequence = this.textContent.trim();
        const count = sequence.length;
        // 只更新计数部分，保留提示信息
        charCounter.innerHTML = `<span style="font-size: 14px; font-weight: 500;">${count} 个氨基酸</span> <span style="margin-left: 10px; font-size: 12px; color: #666;">* 序列将自动转换为大写字母</span>`;
    });
}

// 检查用户登录状态
async function checkLoginStatus(userUI) {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            console.log('search.js: 未找到令牌，用户未登录');
            return;
        }
        
        console.log('search.js: 令牌验证中，令牌存在');
        // 验证令牌并获取用户信息
        const response = await fetch('/api/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                console.error('search.js: 令牌验证失败(401)，清除本地存储');
                // 令牌无效，清除本地存储
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                console.log('search.js: 令牌已清除，准备跳转到登录页面');
                window.location.href = 'index.html';
            }
            return;
        }
        
        console.log('search.js: 令牌验证成功，获取用户数据');
        const user = await response.json();
        console.log('search.js: 用户数据:', user);
        
        // 更新UI显示已登录状态
        updateUIForLoggedIn(user, userUI);
    } catch (error) {
        console.error('search.js: 检查登录状态出错:', error);
    }
}

// 更新UI显示已登录状态
function updateUIForLoggedIn(user, userUI) {
    console.log('search.js: 更新UI为已登录状态');
    console.log('search.js: 传入的用户数据:', JSON.stringify(user));
    
    // 如果没有直接从API获取用户，尝试从localStorage获取
    if (!user) {
        try {
            const userStr = localStorage.getItem('user');
            if (userStr) {
                user = JSON.parse(userStr);
                console.log('search.js: 从localStorage获取用户信息:', user);
            } else {
                console.error('search.js: localStorage中没有用户信息');
                return;
            }
        } catch (e) {
            console.error('search.js: 解析localStorage中的用户信息失败:', e);
            return;
        }
    }
    
    // 确保用户对象有基本字段
    if (!user || !user.username) {
        console.error('search.js: 无法获取有效的用户信息');
        return;
    }
    
    // 更新导航栏
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        console.log('search.js: 更新导航栏显示用户信息');
        
        // 移除登录/注册链接
        const loginLink = navLinks.querySelector('.login-link');
        if (loginLink) loginLink.remove();
        
        // 使用共享函数创建用户菜单
        if (userUI) {
            const userMenu = userUI.createUserMenu(navLinks, user, function() {
                // 注销函数
                logoutUser();
            });
            
            // 更新会员状态
            userUI.updateMembershipStatus(userMenu, user);
        }
    }
}

// 注销用户
async function logoutUser() {
    console.log('准备注销用户');
    const token = localStorage.getItem('token');
    if (!token) {
        console.log('未找到令牌，无需注销');
        return;
    }
    
    try {
        // 调用注销API
        console.log('发送注销请求');
        await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        console.log('注销请求已发送');
    } catch (error) {
        console.error('注销出错:', error);
    } finally {
        // 清除本地存储
        console.log('清除本地存储的用户凭据');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        
        // 跳转到首页
        console.log('准备跳转到首页');
        window.location.href = 'index.html';
    }
}

// 处理联系我们链接的点击事件
const contactLink = document.querySelector('.contact-link');
const emailTooltip = document.querySelector('.email-tooltip');

if (contactLink && emailTooltip) {
    // 点击联系我们链接时
    contactLink.addEventListener('click', function(e) {
        e.preventDefault();
        emailTooltip.classList.toggle('show');
        e.stopPropagation();
    });
    
    // 点击邮箱提示框时阻止事件冒泡
    emailTooltip.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    
    // 点击页面其他地方时隐藏邮箱提示框
    document.addEventListener('click', function() {
        emailTooltip.classList.remove('show');
    });
}

// 搜索工具功能
function setupToolsFiltering() {
    const searchInput = document.querySelector('.tool-search-input');
    const categoryItems = document.querySelectorAll('.category-item');
    const toolCards = document.querySelectorAll('.tool-card');
    
    // 搜索功能
    searchInput.addEventListener('input', function() {
        // 确保任何加载指示器都被隐藏
        utils.hideLoading();
        filterTools();
    });
    
    // 分类功能
    categoryItems.forEach(item => {
        item.addEventListener('click', function() {
            // 移除其他分类的active状态
            categoryItems.forEach(cat => cat.classList.remove('active'));
            // 为当前分类添加active状态
            this.classList.add('active');
            // 确保任何加载指示器都被隐藏
            utils.hideLoading();
            filterTools();
        });
    });
    
    // 过滤工具
    function filterTools() {
        const searchTerm = searchInput.value.toLowerCase();
        const activeCategory = document.querySelector('.category-item.active').dataset.category;
        let visibleCardCount = 0;
        
        // 首先移除现有的"无结果"提示(如果有)
        const existingNoResult = document.querySelector('.no-result-message');
        if (existingNoResult) {
            existingNoResult.remove();
        }
        
        toolCards.forEach(card => {
            // 获取工具名称和描述
            const toolName = card.querySelector('h4').innerText.toLowerCase();
            const toolDesc = card.querySelector('p').innerText.toLowerCase();
            const categories = card.dataset.category ? card.dataset.category.split(' ') : [];
            
            // 检查搜索词是否匹配
            const matchesSearch = searchTerm === '' || 
                                 toolName.includes(searchTerm) || 
                                 toolDesc.includes(searchTerm);
            
            // 检查分类是否匹配
            const matchesCategory = activeCategory === 'all' || 
                                   categories.includes(activeCategory);
            
            // 显示或隐藏工具卡片
            if (matchesSearch && matchesCategory) {
                card.style.display = 'flex';
                visibleCardCount++;
            } else {
                card.style.display = 'none';
            }
        });
        
        // 检查是否有可见的卡片，如果没有，显示提示信息
        if (visibleCardCount === 0) {
            const toolCardsContainer = document.querySelector('.tool-cards');
            const noResultMessage = document.createElement('div');
            noResultMessage.className = 'no-result-message';
            noResultMessage.textContent = '暂时还没有这个工具';
            toolCardsContainer.appendChild(noResultMessage);
        }
        
        // 确保在过滤完成后隐藏任何加载指示器
        setTimeout(() => utils.hideLoading(), 100);
    }
}

// 导出需要给其他模块使用的函数和对象
export { 
    utils, 
    sequenceTools, 
    getToolName, 
    getSequenceType, 
    checkResults, 
    reloadParticles 
};
