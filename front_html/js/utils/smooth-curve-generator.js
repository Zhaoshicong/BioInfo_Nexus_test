/**
 * 平滑曲线数据生成器
 * 用于生成类似图片中的波动曲线数据
 */

// 生成平滑曲线数据
function generateSmoothCurveData(count, min, max) {
    // 基础点 - 用于生成平滑曲线的关键点
    const basePoints = [];
    const segmentCount = Math.floor(count / 5) + 1; // 将总长度分为几段
    
    // 生成几个关键点
    for (let i = 0; i <= segmentCount; i++) {
        basePoints.push({
            x: i * (count / segmentCount),
            y: Math.floor(Math.random() * (max - min)) + min
        });
    }
    
    // 使用关键点插值生成平滑曲线
    const result = [];
    for (let i = 0; i < count; i++) {
        // 找到当前点所在的区间
        let leftIndex = 0;
        while (leftIndex < basePoints.length - 1 && basePoints[leftIndex + 1].x <= i) {
            leftIndex++;
        }
        
        let rightIndex = leftIndex + 1;
        if (rightIndex >= basePoints.length) {
            rightIndex = basePoints.length - 1;
            result.push(basePoints[leftIndex].y);
            continue;
        }
        
        // 计算插值
        const leftPoint = basePoints[leftIndex];
        const rightPoint = basePoints[rightIndex];
        
        // 线性插值
        const ratio = (i - leftPoint.x) / (rightPoint.x - leftPoint.x);
        const value = leftPoint.y + ratio * (rightPoint.y - leftPoint.y);
        
        // 添加一些小波动使曲线更自然
        const noise = (Math.random() - 0.5) * 5;
        result.push(Math.floor(value + noise));
    }
    
    return result;
}

// 导出函数供其他模块使用
window.smoothCurveGenerator = {
    generateSmoothCurveData: generateSmoothCurveData
};