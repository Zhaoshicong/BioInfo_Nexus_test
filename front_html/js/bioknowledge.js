// 生物知识库页面脚本
document.addEventListener('DOMContentLoaded', function() {
    const listItems = document.querySelectorAll('.knowledge-list li');

    // 初始化页面，显示欢迎信息
    initKnowledgePage();

    listItems.forEach(item => {
        item.addEventListener('click', function() {
            // 移除所有active类
            listItems.forEach(li => li.classList.remove('active'));

            // 为当前点击项添加active类
            this.classList.add('active');

            // 获取分类名称
            const category = this.getAttribute('data-category');
            const categoryName = this.querySelector('.category-name').textContent;

            // 更新右侧内容标题
            document.querySelector('.knowledge-content h2').textContent = categoryName;

            // 处理物种密码子使用分类
            if (category === 'species-codon') {
                loadSpeciesCodonData();
            } else {
                // 隐藏物种数据表格
                const speciesTable = document.getElementById('species-table-container');
                if (speciesTable) {
                    speciesTable.style.display = 'none';
                }

                // 显示普通知识内容
                const knowledgeItems = document.querySelectorAll('.knowledge-item');
                knowledgeItems.forEach(item => {
                    item.style.display = 'block';
                });

                // 示例：简单更新描述文本
                const descriptions = {
                    'molecular-biology': '分子生物学是研究生物大分子（如DNA、RNA和蛋白质）的结构、功能和相互作用的学科，它解释了生命的基本过程如何在分子水平上运作。',
                    'genetics': '遗传学是研究基因、遗传变异和遗传在生物体中的作用的科学。它探索了遗传信息如何从一代传递到下一代，以及这些信息如何影响生物体的特征和发展。',
                    'biochemistry': '生物化学是研究生物体内化学过程和物质的学科。它探索了蛋白质、碳水化合物、脂质和核酸等生物分子的结构和功能，以及它们在生命过程中的作用。',
                    'cell-biology': '细胞生物学研究细胞的结构、功能和行为。它探索了细胞如何生长、分裂、通信和死亡，以及这些过程如何影响生物体的整体功能。',
                    'microbiology': '微生物学是研究微生物（如细菌、病毒、真菌和原生生物）的科学。它探索了这些微小生物的生命过程、生态作用以及它们与其他生物的相互作用。',
                    'immunology': '免疫学研究生物体如何抵抗疾病的科学。它探索了免疫系统的组成、功能和调节，以及免疫系统如何识别和消除外来入侵者。',
                    'bioinformatics': '生物信息学是利用计算机科学、统计学和数学来分析和解释生物数据的学科。它在基因组学、蛋白质组学和系统生物学等领域发挥着重要作用。',
                    'biotechnology': '生物技术是利用生物系统、生物体或其衍生物来开发或制造产品的技术。它在医药、农业、食品加工和环境保护等领域有广泛应用。'
                };

                document.querySelector('.knowledge-content .description').textContent = descriptions[category] || '';
            }
        });
    });
});

// 初始化知识页面，显示欢迎信息
function initKnowledgePage() {
    // 隐藏物种数据表格
    const speciesTable = document.getElementById('species-table-container');
    if (speciesTable) {
        speciesTable.style.display = 'none';
    }

    // 更新右侧内容标题
    document.querySelector('.knowledge-content h2').textContent = '欢迎使用生物知识库';

    // 更新描述文本
    document.querySelector('.knowledge-content .description').textContent =
        '欢迎访问BioInfo Nexus生物知识库！这里收集了丰富的生物学知识和数据资源，包括物种密码子使用频率、分子生物学、遗传学、生物化学等多个领域的信息。请从左侧选择一个分类开始浏览。';

    // 隐藏所有知识条目
    const knowledgeItems = document.querySelectorAll('.knowledge-item');
    knowledgeItems.forEach(item => {
        item.style.display = 'none';
    });
}

// 加载物种密码子使用数据
function loadSpeciesCodonData() {
    // 隐藏普通知识内容
    const knowledgeItems = document.querySelectorAll('.knowledge-item');
    knowledgeItems.forEach(item => {
        item.style.display = 'none';
    });

    // 更新描述文本
    document.querySelector('.knowledge-content .description').textContent =
        '物种密码子使用频率数据库包含了各种生物物种的密码子使用偏好信息。这些数据对于基因表达优化、进化分析和比较基因组学研究具有重要价值。';

    // 检查是否已经存在表格容器
    let tableContainer = document.getElementById('species-table-container');

    if (!tableContainer) {
        // 创建表格容器
        tableContainer = document.createElement('div');
        tableContainer.id = 'species-table-container';
        tableContainer.className = 'species-table-container';

        // 创建搜索框
        const searchContainer = document.createElement('div');
        searchContainer.className = 'species-search-container';

        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.id = 'species-search';
        searchInput.placeholder = '搜索物种（ID或名称）...';
        searchInput.className = 'species-search-input';

        searchContainer.appendChild(searchInput);
        tableContainer.appendChild(searchContainer);

        // 创建表格
        const table = document.createElement('table');
        table.className = 'species-table';

        // 创建表头
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');

        const headers = ['物种ID', '英文名称', '操作'];
        headers.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        table.appendChild(thead);

        // 创建表格主体
        const tbody = document.createElement('tbody');
        tbody.id = 'species-table-body';
        table.appendChild(tbody);

        // 创建分页控件
        const pagination = document.createElement('div');
        pagination.className = 'species-pagination';
        pagination.innerHTML = `
            <button id="prev-page" disabled>上一页</button>
            <span id="page-info">第 <span id="current-page">1</span> 页，共 <span id="total-pages">0</span> 页</span>
            <button id="next-page">下一页</button>
        `;

        // 添加到容器
        tableContainer.appendChild(table);
        tableContainer.appendChild(pagination);

        // 添加到页面
        document.querySelector('.knowledge-content').appendChild(tableContainer);

        // 添加事件监听器
        document.getElementById('species-search').addEventListener('input', function() {
            loadSpeciesData(1);
        });

        document.getElementById('prev-page').addEventListener('click', function() {
            const currentPage = parseInt(document.getElementById('current-page').textContent);
            if (currentPage > 1) {
                loadSpeciesData(currentPage - 1);
            }
        });

        document.getElementById('next-page').addEventListener('click', function() {
            const currentPage = parseInt(document.getElementById('current-page').textContent);
            const totalPages = parseInt(document.getElementById('total-pages').textContent);
            if (currentPage < totalPages) {
                loadSpeciesData(currentPage + 1);
            }
        });
    } else {
        // 显示已存在的表格容器
        tableContainer.style.display = 'block';
    }

    // 加载第一页数据
    loadSpeciesData(1);
}

// 加载物种数据
function loadSpeciesData(page) {
    const itemsPerPage = 20;
    const searchTerm = document.getElementById('species-search').value.toLowerCase();

    // 使用fetch API获取CSV数据
    fetch('../Bio_tools/data/codon_tables/species_map.csv')
        .then(response => response.text())
        .then(data => {
            // 解析CSV数据
            const lines = data.split('\n');
            const headers = lines[0].split(',');

            // 过滤数据
            let filteredData = [];
            for (let i = 1; i < lines.length; i++) {
                if (lines[i].trim() === '') continue;

                const values = lines[i].split(',');
                const speciesId = values[0];
                const englishName = values[1] || '';
                const chineseName = values[2] || '';

                // 搜索过滤
                if (searchTerm && !speciesId.toLowerCase().includes(searchTerm) &&
                    !englishName.toLowerCase().includes(searchTerm)) {
                    continue;
                }

                filteredData.push({
                    id: speciesId,
                    englishName: englishName
                });
            }

            // 计算分页
            const totalPages = Math.ceil(filteredData.length / itemsPerPage);
            document.getElementById('total-pages').textContent = totalPages;
            document.getElementById('current-page').textContent = page;

            // 更新分页按钮状态
            document.getElementById('prev-page').disabled = page <= 1;
            document.getElementById('next-page').disabled = page >= totalPages;

            // 计算当前页的数据
            const startIndex = (page - 1) * itemsPerPage;
            const endIndex = Math.min(startIndex + itemsPerPage, filteredData.length);
            const currentPageData = filteredData.slice(startIndex, endIndex);

            // 更新表格
            const tableBody = document.getElementById('species-table-body');
            tableBody.innerHTML = '';

            currentPageData.forEach(species => {
                const row = document.createElement('tr');

                // 物种ID
                const idCell = document.createElement('td');
                idCell.textContent = species.id;
                row.appendChild(idCell);

                // 英文名称
                const englishNameCell = document.createElement('td');
                englishNameCell.textContent = species.englishName;
                row.appendChild(englishNameCell);

                // 操作按钮
                const actionCell = document.createElement('td');
                const viewButton = document.createElement('button');
                viewButton.className = 'view-codon-btn';
                viewButton.textContent = '查看密码子使用';
                viewButton.dataset.speciesId = species.id;
                viewButton.addEventListener('click', function() {
                    viewCodonUsage(species.id, species.englishName);
                });

                actionCell.appendChild(viewButton);
                row.appendChild(actionCell);

                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('加载物种数据失败:', error);
            document.getElementById('species-table-body').innerHTML =
                '<tr><td colspan="3">加载数据失败，请稍后再试</td></tr>';
        });
}

// 查看密码子使用频率
function viewCodonUsage(speciesId, speciesName) {
    // 创建模态框
    let modal = document.getElementById('codon-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'codon-modal';
        modal.className = 'codon-modal';
        document.body.appendChild(modal);
    }

    // 设置模态框内容
    modal.innerHTML = `
        <div class="codon-modal-content">
            <div class="codon-modal-header">
                <h3>${speciesName} (ID: ${speciesId}) 密码子使用频率</h3>
                <span class="close-modal">&times;</span>
            </div>
            <div class="codon-modal-body">
                <div id="codon-loading">加载中...</div>
                <div id="codon-table-container" style="display:none;">
                    <table class="codon-table">
                        <thead>
                            <tr>
                                <th>密码子</th>
                                <th>使用频率</th>
                            </tr>
                        </thead>
                        <tbody id="codon-table-body"></tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    // 显示模态框
    modal.style.display = 'block';

    // 关闭模态框事件
    modal.querySelector('.close-modal').addEventListener('click', function() {
        modal.style.display = 'none';
    });

    // 点击模态框外部关闭
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    // 加载密码子使用数据
    fetch(`../Bio_tools/data/codon_tables/${speciesId}.json`)
        .then(response => {
            if (!response.ok) {
                throw new Error('物种密码子数据不存在');
            }
            return response.json();
        })
        .then(data => {
            // 隐藏加载提示
            document.getElementById('codon-loading').style.display = 'none';
            document.getElementById('codon-table-container').style.display = 'block';

            // 更新表格
            const tableBody = document.getElementById('codon-table-body');
            tableBody.innerHTML = '';

            // 将数据转换为数组并排序
            const codonData = Object.entries(data).sort((a, b) => a[0].localeCompare(b[0]));

            codonData.forEach(([codon, frequency]) => {
                const row = document.createElement('tr');

                // 密码子
                const codonCell = document.createElement('td');
                codonCell.textContent = codon;
                row.appendChild(codonCell);

                // 使用频率
                const frequencyCell = document.createElement('td');
                frequencyCell.textContent = frequency.toFixed(4);
                row.appendChild(frequencyCell);

                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('加载密码子数据失败:', error);
            document.getElementById('codon-loading').innerHTML =
                '无法加载该物种的密码子使用数据，可能该物种数据不存在。';
        });
}
