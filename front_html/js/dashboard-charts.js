// 数据可视化脚本 - 使用Chart.js

// 全局变量
let resourceUsageChart = null;
let userGrowthChart = null;
let timeRangeSelector = 'year'; // 默认显示年度数据

// 初始化图表
document.addEventListener('DOMContentLoaded', function() {
    // 如果在控制面板页面，初始化图表
    if (document.getElementById('resource-usage-chart') && 
        document.getElementById('user-growth-chart')) {
        initCharts();
    }
});

// 初始化所有图表
function initCharts() {
    initResourceUsageChart();
    initUserGrowthChart();
    
    // 设置时间范围选择器事件
    setupTimeRangeSelector();
    
    // 每5分钟刷新一次图表数据
    setInterval(refreshChartData, 300000);
}

// 设置时间范围选择器事件
function setupTimeRangeSelector() {
    // 检查是否存在时间范围选择器
    const timeRangeSelect = document.getElementById('time-range-select');
    if (timeRangeSelect) {
        timeRangeSelect.addEventListener('change', function() {
            timeRangeSelector = this.value;
            updateUserGrowthChart();
        });
    }
}

// 初始化系统资源使用图表
function initResourceUsageChart() {
    const ctx = document.getElementById('resource-usage-chart').getContext('2d');
    
    resourceUsageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['CPU', '内存', '磁盘', '网络'],
            datasets: [{
                label: '使用率 (%)',
                data: [45, 60, 35, 25],
                backgroundColor: [
                    'rgba(74, 107, 175, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)'
                ],
                borderColor: [
                    'rgba(74, 107, 175, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '系统资源使用情况',
                    font: {
                        size: 20,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 20
                    }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    padding: 12,
                    cornerRadius: 6,
                    displayColors: true
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: '使用率 (%)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        padding: {top: 0, bottom: 10}
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        padding: 8
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'
                    }
                },
                x: {
                    ticks: {
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        padding: 8
                    },
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
}

// 初始化用户增长图表
function initUserGrowthChart() {
    const ctx = document.getElementById('user-growth-chart').getContext('2d');
    
    userGrowthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: '新增用户',
                    data: [],
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(75, 192, 192, 1)',
                    pointHoverBorderWidth: 3,
                    fill: true
                },
                {
                    label: '累计用户',
                    data: [],
                    backgroundColor: 'rgba(153, 102, 255, 0.2)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    pointBackgroundColor: 'rgba(153, 102, 255, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(153, 102, 255, 1)',
                    pointHoverBorderWidth: 3,
                    fill: true
                },
                {
                    label: '活跃用户',
                    data: [],
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(54, 162, 235, 1)',
                    pointHoverBorderWidth: 3,
                    fill: true
                },
                {
                    label: '流失用户',
                    data: [],
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    pointBackgroundColor: 'rgba(255, 99, 132, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(255, 99, 132, 1)',
                    pointHoverBorderWidth: 3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '用户增长趋势',
                    font: {
                        size: 20,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 20
                    }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            size: 13,
                            weight: 'bold'
                        },
                        padding: 15,
                        usePointStyle: true,
                        pointStyleWidth: 10
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    padding: 12,
                    cornerRadius: 6,
                    displayColors: true
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '用户数',
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        padding: {top: 0, bottom: 10}
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        padding: 8,
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '时间',
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        padding: {top: 10, bottom: 0}
                    },
                    ticks: {
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        padding: 8
                    },
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
    
    // 初始化后立即更新图表数据
    updateUserGrowthChart();
}

// 刷新图表数据
function refreshChartData() {
    // 从API获取系统资源使用数据
    const token = localStorage.getItem('token');
    if (!token) {
        console.error('未找到认证令牌');
        return;
    }
    
    // 获取系统资源使用数据
    fetch('/api/dashboard/resource-usage', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取系统资源使用数据失败');
        }
        return response.json();
    })
    .then(data => {
        // 更新系统资源使用图表
        resourceUsageChart.data.datasets[0].data = [
            data.cpu || 0,     // CPU
            data.memory || 0,   // 内存
            data.disk || 0,     // 磁盘
            data.network || 0   // 网络
        ];
        resourceUsageChart.update();
    })
    .catch(error => {
        console.error('获取系统资源使用数据出错:', error);
        // 出错时使用模拟数据
        resourceUsageChart.data.datasets[0].data = [
            Math.floor(Math.random() * 60) + 20, // CPU
            Math.floor(Math.random() * 40) + 40, // 内存
            Math.floor(Math.random() * 30) + 30, // 磁盘
            Math.floor(Math.random() * 40) + 10  // 网络
        ];
        resourceUsageChart.update();
    });
    
    // 更新用户增长图表
    updateUserGrowthChart();
}

// 生成随机数据
function generateRandomData(count, min, max) {
    const data = [];
    for (let i = 0; i < count; i++) {
        data.push(Math.floor(Math.random() * (max - min + 1)) + min);
    }
    return data;
}

// 更新用户增长图表数据
function updateUserGrowthChart() {
    const token = localStorage.getItem('token');
    if (!token) {
        console.error('未找到认证令牌');
        return;
    }
    
    // 显示加载状态
    const userGrowthChartElement = document.getElementById('user-growth-chart');
    if (userGrowthChartElement) {
        userGrowthChartElement.style.opacity = '0.6';
    }
    
    // 从API获取用户增长数据
    fetch(`/api/dashboard/user-growth?range=${timeRangeSelector}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取用户增长数据失败');
        }
        return response.json();
    })
    .then(data => {
        // 更新图表数据
        userGrowthChart.data.labels = data.labels || [];
        userGrowthChart.data.datasets[0].data = data.new_users || [];
        userGrowthChart.data.datasets[1].data = data.total_users || [];
        userGrowthChart.data.datasets[2].data = data.active_users || [];
        userGrowthChart.data.datasets[3].data = data.churn_users || [];
        
        // 恢复正常显示
        if (userGrowthChartElement) {
            userGrowthChartElement.style.opacity = '1';
        }
        
        // 更新图表
        userGrowthChart.update();
    })
    .catch(error => {
        console.error('获取用户增长数据出错:', error);
        
        // 出错时使用模拟数据
        let labels = [];
        let newUsers = [];
        let totalUsers = [];
        let activeUsers = [];
        let churnUsers = [];
        
        // 根据时间范围选择器生成对应的数据
        switch(timeRangeSelector) {
            case 'week':
                labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
                newUsers = [5, 7, 8, 12, 15, 20, 10];
                activeUsers = [30, 35, 40, 45, 50, 60, 45];
                churnUsers = [2, 3, 1, 2, 3, 4, 5];
                break;
            case 'month':
                labels = Array.from({length: 30}, (_, i) => `${i+1}日`);
                newUsers = generateRandomData(30, 1, 10);
                activeUsers = generateRandomData(30, 20, 60);
                churnUsers = generateRandomData(30, 0, 5);
                break;
            case 'quarter':
                // 季度数据 - 最近3个月的数据
                labels = [];
                const currentMonth = new Date().getMonth();
                for (let i = 0; i < 3; i++) {
                    // 获取最近3个月的月份名称
                    const monthIndex = (currentMonth - 2 + i) >= 0 ? 
                                      (currentMonth - 2 + i) : 
                                      (currentMonth - 2 + i + 12);
                    const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
                    labels.push(monthNames[monthIndex]);
                }
                // 为季度生成不同的随机数据
                newUsers = generateRandomData(3, 15, 45);
                activeUsers = generateRandomData(3, 50, 120);
                churnUsers = generateRandomData(3, 5, 15);
                break;
            case 'year':
            default:
                // 年度数据 - 12个月
                labels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
                // 为年度生成不同的随机数据
                newUsers = generateRandomData(12, 10, 50);
                activeUsers = generateRandomData(12, 40, 130);
                churnUsers = generateRandomData(12, 3, 18);
                break;
        }
        
        // 计算累计用户数
        totalUsers = newUsers.reduce((acc, curr, idx) => {
            if (idx === 0) return [curr];
            return [...acc, acc[idx-1] + curr - churnUsers[idx]];
        }, []);
        
        // 更新图表数据
        userGrowthChart.data.labels = labels;
        userGrowthChart.data.datasets[0].data = newUsers;
        userGrowthChart.data.datasets[1].data = totalUsers;
        userGrowthChart.data.datasets[2].data = activeUsers;
        userGrowthChart.data.datasets[3].data = churnUsers;
        
        // 更新图表
        userGrowthChart.update();
    });
    
    // 更新图表标题
    let titleText = '用户增长趋势';
    switch(timeRangeSelector) {
        case 'month':
            titleText = '本月用户增长趋势';
            break;
        case 'year':
            titleText = '年度用户增长趋势';
            break;
    }
    
    userGrowthChart.options.plugins.title.text = titleText;
    userGrowthChart.update();
}

// 导出函数供其他模块使用
window.dashboardCharts = {
    refreshChartData: refreshChartData,
    updateUserGrowthChart: updateUserGrowthChart,
    setTimeRange: function(range) {
        if(['week', 'month', 'quarter', 'year'].includes(range)) {
            timeRangeSelector = range;
            updateUserGrowthChart();
        }
    }
};