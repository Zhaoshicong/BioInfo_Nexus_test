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

    // 每2.5分钟刷新一次图表数据
    setInterval(refreshChartData, 150000);
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

    // 创建渐变背景
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(54, 162, 235, 0.4)');
    gradient.addColorStop(1, 'rgba(54, 162, 235, 0.01)');

    userGrowthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: '用户数量',
                    data: [],
                    backgroundColor: gradient,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2,
                    tension: 0.5,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(54, 162, 235, 1)',
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
                    text: '用户总数趋势',
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
                    display: false // 隐藏图例
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
                    displayColors: true,
                    callbacks: {
                        title: function(tooltipItems) {
                            return tooltipItems[0].label;
                        },
                        label: function(context) {
                            return '用户数量: ' + context.raw;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    min: 0,
                    title: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        padding: 8,
                        autoSkip: true,
                        maxTicksLimit: 8,
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'
                    }
                },
                x: {
                    title: {
                        display: false // 隐藏X轴标题
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
            elements: {
                line: {
                    tension: 0.5 // 曲线平滑度
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
        console.log('获取的系统资源使用数据:', data);
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
        // 使用总用户数量数据
        userGrowthChart.data.datasets[0].data = data.total_users || [];

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
        let activeUsers = [];

        // 根据时间范围选择器生成对应的数据
        let dataPointCount = 12; // 默认数据点数量

        switch(timeRangeSelector) {
            case 'month':
                labels = Array.from({length: 30}, (_, i) => `${i+1}日`);
                dataPointCount = 30;
                break;
            case 'year':
            default:
                // 年度数据 - 12个月
                labels = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
                dataPointCount = 12;
                break;
        }

        // 使用平滑曲线生成器生成更美观的数据
        if (window.smoothCurveGenerator) {
            // 根据不同的时间范围设置不同的数据范围
            let minValue, maxValue;

            switch(timeRangeSelector) {
                case 'week':
                    minValue = 30;
                    maxValue = 80;
                    break;
                case 'month':
                    minValue = 20;
                    maxValue = 100;
                    break;
                case 'quarter':
                    minValue = 40;
                    maxValue = 120;
                    break;
                case 'year':
                default:
                    minValue = 30;
                    maxValue = 150;
                    break;
            }

            activeUsers = window.smoothCurveGenerator.generateSmoothCurveData(dataPointCount, minValue, maxValue);
        } else {
            // 如果平滑曲线生成器不可用，则使用普通随机数据
            activeUsers = generateRandomData(dataPointCount, 30, 150);
        }

        // 更新图表数据
        userGrowthChart.data.labels = labels;
        userGrowthChart.data.datasets[0].data = activeUsers;

        // 更新图表
        userGrowthChart.update();
    });


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