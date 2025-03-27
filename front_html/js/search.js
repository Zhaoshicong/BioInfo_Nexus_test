// 工具函数
const utils = {
    showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 100);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
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
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },
    
    // 检查是否已登录
    isLoggedIn() {
        return !!localStorage.getItem('token');
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

    displayResults(tool, result) {
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
                    <p>序列: ${result.sequence}</p>
                    <p>分子量: ${result.molecular_weight} Da</p>
                    <p>氨基酸组成:</p>
                    ${aaTable}
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
                            <p class="success-message">预测完成</p>
                            <p>序列: ${result.sequence}</p>
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
                    <p>序列: ${result.sequence}</p>
                    <p>预测结果: ${result.result}</p>
                    <p>Vaxijen打分: ${result.score}</p>
                `;
                break;

            case 'toxinpred':
                resultBox.innerHTML = `
                    <p>序列: ${result.sequence}</p>
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
                    <h4>基本信息:</h4>
                    <p>序列: ${result.sequence}</p>
                    <p>分子量: ${result.molecular_weight.toFixed(2)} Da</p>
                    <p>理论等电点: ${result.theoretical_pi.toFixed(2)}</p>
                `;
                
                // 氨基酸组成
                if (result.amino_acid_composition) {
                    resultBox.innerHTML += `
                        <h4>氨基酸组成:</h4>
                        <div class="aa-composition" style="max-height: 200px; overflow-y: auto; margin: 10px 0; padding: 10px; border: 1px solid #eee;">
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
                        resultBox.innerHTML += `
                            <p>还原状态: ${result.extinction_coefficients.reduced.coefficient} M⁻¹cm⁻¹ 
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
                        <p>GRAVY 指数 (Grand Average of Hydropathicity) 的含义：
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
        case 'protparam':
            return '分子量计算 (BioPython)';
        case 'signalp':
            return '信号肽预测 (SignalP)';
        case 'vaxijen':
            return '抗原性预测 (VaxiJen)';
        case 'toxinpred':
            return '毒性预测 (ToxinPred)';
        case 'physchemparam':
            return '物理化学参数分析';
        default:
            return tool;
    }
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

// 页面加载时执行
document.addEventListener('DOMContentLoaded', async function() {
    // 检查登录状态
    const token = localStorage.getItem('token');
    if (!token) {
        // 未登录，跳转到首页
        window.location.href = 'index.html';
        alert('请先登录后再使用序列分析功能');
        return;
    }
    
    // 检查登录状态并更新UI
    await checkLoginStatus();
    
    // 初始化页面
    initPage();
    
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
    // 获取DOM元素
    const sequenceInput = document.querySelector('.sequence-input');
    const charCounter = document.querySelector('.char-counter');
    const toolCards = document.querySelectorAll('.tool-card');
    const analyzeBtn = document.querySelector('.analyze-btn');
    
    // 更新字符计数并将输入转换为大写
    sequenceInput.addEventListener('input', function() {
        // 将输入内容转换为大写
        const originalValue = this.value;
        const cursorPosition = this.selectionStart;
        
        // 转换为大写
        this.value = originalValue.toUpperCase();
        
        // 恢复光标位置
        this.setSelectionRange(cursorPosition, cursorPosition);
        
        // 更新字符计数
        const sequence = this.value.trim();
        const count = sequence.length;
        // 只更新计数部分，保留提示信息
        charCounter.innerHTML = `${count} 个氨基酸 <span style="margin-left: 10px; font-size: 12px; color: #666;">* 序列将自动转换为大写字母</span>`;
    });
    
    // 工具卡片点击事件
    toolCards.forEach(card => {
        card.addEventListener('click', function() {
            toolCards.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // 分析按钮点击事件
    analyzeBtn.addEventListener('click', async function() {
        // 获取序列并确保转换为大写
        const sequence = sequenceInput.value.trim().toUpperCase();
        
        if (!sequence) {
            utils.showToast('请输入氨基酸序列');
            return;
        }
        
        const activeCard = document.querySelector('.tool-card.active');
        if (!activeCard) {
            utils.showToast('请选择分析工具');
            return;
        }
        
        const tool = activeCard.dataset.tool;
        
        try {
            utils.showLoading('正在分析中...');
            const result = await sequenceTools.analyzeSequence(tool, sequence);
            utils.hideLoading();
            sequenceTools.displayResults(tool, result);
            
            // 添加结果后重新初始化粒子系统
            setTimeout(function() {
                reloadParticles();
            }, 300);
        } catch (error) {
            utils.hideLoading();
            utils.showToast(`分析失败: ${error.message}`);
        }
    });
}

// 检查用户登录状态
async function checkLoginStatus() {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    try {
        // 获取用户信息
        const response = await fetch('/api/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                // 令牌无效，清除本地存储
                localStorage.removeItem('token');
                localStorage.removeItem('username');
                localStorage.removeItem('isAdmin');
                localStorage.removeItem('loginTime');
                window.location.href = 'index.html';
            }
            return;
        }
        
        const user = await response.json();
        
        // 更新UI显示已登录状态
        updateUIForLoggedIn(user);
    } catch (error) {
        console.error('检查登录状态出错:', error);
    }
}

// 更新UI显示已登录状态
function updateUIForLoggedIn(user) {
    // 更新导航栏
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        // 添加用户菜单
        if (!navLinks.querySelector('.user-menu')) {
            const userMenu = document.createElement('div');
            userMenu.className = 'user-menu';
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
                    <div class="dropdown-divider"></div>
                    ${user.is_admin ? '<a href="admin.html"><i class="fas fa-cog"></i> 管理控制台</a>' : ''}
                    <a href="#" id="logoutBtn"><i class="fas fa-sign-out-alt"></i> 注销</a>
                </div>
            `;
            navLinks.appendChild(userMenu);
            
            // 绑定注销按钮事件
            userMenu.querySelector('#logoutBtn').addEventListener('click', async function(e) {
                e.preventDefault();
                await logoutUser();
            });
        }
    }
}

// 注销用户
async function logoutUser() {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    try {
        // 调用注销API
        await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        console.error('注销出错:', error);
    } finally {
        // 清除本地存储
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('isAdmin');
        localStorage.removeItem('loginTime');
        
        // 跳转到首页
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