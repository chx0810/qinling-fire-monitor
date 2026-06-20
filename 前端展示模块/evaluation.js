/**
 * 秦岭火灾预警系统 - 模型评估页面脚本
 * 独立模块，不影响现有 app.js
 * 功能：从 /evaluation/metrics 获取数据，绘制混淆矩阵热力图、指标柱状图、训练曲线
 */

// ==================== 全局变量 ====================
let metricsBarChart = null;      // 各类别指标柱状图实例
let accuracyChart = null;        // 准确率曲线实例
let lossChart = null;            // 损失曲线实例

// ==================== 页面加载完成后执行 ====================
document.addEventListener('DOMContentLoaded', function() {
    loadEvaluationMetrics();  // 加载评估数据
});

/**
 * 从后端获取模型评估指标数据
 * 所有 fetch 调用均有异常保护
 */
async function loadEvaluationMetrics() {
    try {
        // 发起请求获取评估指标
        const response = await fetch('/evaluation/metrics');
        
        // 检查 HTTP 响应状态
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // 检查业务逻辑是否成功
        if (!result.success) {
            showError(result.message || '获取评估数据失败');
            return;
        }
        
        const data = result.data;
        
        // 渲染各个组件
        renderSummaryCards(data);           // 渲染总体指标卡片
        renderTrainingInfo(data);           // 渲染训练信息栏
        renderConfusionMatrix(data);        // 渲染混淆矩阵
        renderMetricsBarChart(data);        // 渲染各类别指标柱状图
        renderAccuracyChart(data);          // 渲染准确率训练曲线
        renderLossChart(data);              // 渲染损失训练曲线
        renderClassificationReport(data);   // 渲染分类报告表格
        
    } catch (error) {
        // 异常捕获：显示错误信息
        console.error('加载评估指标失败:', error);
        showError('加载评估数据失败: ' + error.message);
    }
}

/**
 * 显示错误状态
 * @param {string} message - 错误消息
 */
function showError(message) {
    // 在混淆矩阵容器中显示错误
    const matrixContainer = document.getElementById('confusion-matrix-container');
    if (matrixContainer) {
        matrixContainer.innerHTML = `
            <div class="eval-error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
                <p style="font-size:0.85rem;color:var(--text-muted);margin-top:8px;">请确保已运行模型训练并生成 training_log.csv</p>
            </div>
        `;
    }
    // 在分类报告容器中显示错误
    const reportContainer = document.getElementById('classification-report-container');
    if (reportContainer) {
        reportContainer.innerHTML = `
            <div class="eval-error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
            </div>
        `;
    }
}

/**
 * 渲染总体指标卡片
 * @param {Object} data - 评估数据
 */
function renderSummaryCards(data) {
    try {
        // 准确率
        const accEl = document.getElementById('accuracy-value');
        if (accEl) {
            accEl.textContent = (data.accuracy * 100).toFixed(1) + '%';
        }
        
        // 计算平均精确率
        const precisionValues = Object.values(data.precision || {});
        const avgPrecision = precisionValues.length > 0 
            ? precisionValues.reduce((a, b) => a + b, 0) / precisionValues.length 
            : 0;
        const precEl = document.getElementById('precision-value');
        if (precEl) {
            precEl.textContent = (avgPrecision * 100).toFixed(1) + '%';
        }
        
        // 计算平均召回率
        const recallValues = Object.values(data.recall || {});
        const avgRecall = recallValues.length > 0 
            ? recallValues.reduce((a, b) => a + b, 0) / recallValues.length 
            : 0;
        const recEl = document.getElementById('recall-value');
        if (recEl) {
            recEl.textContent = (avgRecall * 100).toFixed(1) + '%';
        }
        
        // 计算平均F1分数
        const f1Values = Object.values(data.f1_score || {});
        const avgF1 = f1Values.length > 0 
            ? f1Values.reduce((a, b) => a + b, 0) / f1Values.length 
            : 0;
        const f1El = document.getElementById('f1-value');
        if (f1El) {
            f1El.textContent = (avgF1 * 100).toFixed(1) + '%';
        }
    } catch (e) {
        console.error('渲染指标卡片失败:', e);
    }
}

/**
 * 渲染训练信息栏
 * @param {Object} data - 评估数据
 */
function renderTrainingInfo(data) {
    try {
        const epochsEl = document.getElementById('total-epochs');
        if (epochsEl) epochsEl.textContent = data.total_epochs + ' 轮';
        
        const samplesEl = document.getElementById('total-samples');
        if (samplesEl) samplesEl.textContent = data.total_samples + ' 个';
        
        const classesEl = document.getElementById('total-classes');
        if (classesEl) classesEl.textContent = data.classes.length + ' 类';
    } catch (e) {
        console.error('渲染训练信息失败:', e);
    }
}

/**
 * 渲染混淆矩阵热力图（使用HTML表格）
 * @param {Object} data - 评估数据
 */
function renderConfusionMatrix(data) {
    try {
        const container = document.getElementById('confusion-matrix-container');
        if (!container) return;
        
        const classes = data.classes;
        const matrix = data.confusion_matrix;
        const classNames = {
            'fire': '火灾',
            'smoke': '烟雾',
            'fire_smoke': '火灾+烟雾',
            'normal': '正常'
        };
        
        // 计算最大值用于颜色映射
        let maxVal = 0;
        for (let i = 0; i < matrix.length; i++) {
            for (let j = 0; j < matrix[i].length; j++) {
                if (matrix[i][j] > maxVal) maxVal = matrix[i][j];
            }
        }
        
        // 构建HTML表格
        let html = '<table class="confusion-matrix">';
        
        // 表头行：空白 + 预测类别
        html += '<tr><th>真实 \\ 预测</th>';
        for (let j = 0; j < classes.length; j++) {
            html += `<th>${classNames[classes[j]] || classes[j]}</th>`;
        }
        html += '</tr>';
        
        // 数据行
        for (let i = 0; i < matrix.length; i++) {
            html += '<tr>';
            html += `<th>${classNames[classes[i]] || classes[i]}</th>`;
            for (let j = 0; j < matrix[i].length; j++) {
                const val = matrix[i][j];
                const ratio = maxVal > 0 ? val / maxVal : 0;
                
                if (i === j) {
                    // 对角线：正确分类，绿色渐变
                    const intensity = Math.floor(60 + ratio * 160);
                    const bg = `rgba(0, ${intensity}, 80, 0.85)`;
                    html += `<td class="diagonal" style="background:${bg}">${val}</td>`;
                } else {
                    // 非对角线：错误分类，红色渐变（越深越多）
                    const intensity = Math.floor(ratio * 180);
                    const bg = intensity > 0 
                        ? `rgba(${intensity}, 20, 20, 0.6)` 
                        : 'rgba(255,255,255,0.03)';
                    html += `<td class="off-diagonal" style="background:${bg}">${val}</td>`;
                }
            }
            html += '</tr>';
        }
        
        html += '</table>';
        html += '<div class="matrix-note">行表示真实类别，列表示预测类别。对角线值越高表示分类越准确。</div>';
        
        container.innerHTML = html;
    } catch (e) {
        console.error('渲染混淆矩阵失败:', e);
    }
}

/**
 * 渲染各类别 precision/recall/F1 柱状图
 * @param {Object} data - 评估数据
 */
function renderMetricsBarChart(data) {
    try {
        const canvas = document.getElementById('metrics-bar-chart');
        if (!canvas) return;
        
        const classNames = {
            'fire': '火灾',
            'smoke': '烟雾',
            'fire_smoke': '火灾+烟雾',
            'normal': '正常'
        };
        
        const labels = data.classes.map(c => classNames[c] || c);
        const precisionData = data.classes.map(c => ((data.precision[c] || 0) * 100).toFixed(1));
        const recallData = data.classes.map(c => ((data.recall[c] || 0) * 100).toFixed(1));
        const f1Data = data.classes.map(c => ((data.f1_score[c] || 0) * 100).toFixed(1));
        
        // 销毁旧图表实例（避免重复渲染）
        if (metricsBarChart) {
            metricsBarChart.destroy();
        }
        
        // 获取2D绘图上下文
        const ctx = canvas.getContext('2d');
        
        // 创建新图表
        metricsBarChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '精确率 (%)',
                        data: precisionData,
                        backgroundColor: 'rgba(255, 56, 56, 0.7)',
                        borderColor: 'rgba(255, 56, 56, 1)',
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: '召回率 (%)',
                        data: recallData,
                        backgroundColor: 'rgba(0, 212, 255, 0.7)',
                        borderColor: 'rgba(0, 212, 255, 1)',
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: 'F1 分数 (%)',
                        data: f1Data,
                        backgroundColor: 'rgba(255, 165, 2, 0.7)',
                        borderColor: 'rgba(255, 165, 2, 1)',
                        borderWidth: 1,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#a0aec0',
                            font: { size: 12 },
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#a0aec0' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            color: '#a0aec0',
                            callback: function(value) { return value + '%'; }
                        },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                }
            }
        });
    } catch (e) {
        console.error('渲染指标柱状图失败:', e);
    }
}

/**
 * 渲染训练准确率曲线
 * @param {Object} data - 评估数据
 */
function renderAccuracyChart(data) {
    try {
        const canvas = document.getElementById('accuracy-chart');
        if (!canvas || !data.training_history || data.training_history.length === 0) return;
        
        const history = data.training_history;
        const epochLabels = history.map(h => 'E' + h.epoch);
        const trainAcc = history.map(h => (h.accuracy * 100).toFixed(2));
        const valAcc = history.map(h => (h.val_accuracy * 100).toFixed(2));
        
        // 销毁旧图表实例
        if (accuracyChart) {
            accuracyChart.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        accuracyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: epochLabels,
                datasets: [
                    {
                        label: '训练准确率',
                        data: trainAcc,
                        borderColor: 'rgba(255, 56, 56, 0.9)',
                        backgroundColor: 'rgba(255, 56, 56, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        borderWidth: 2
                    },
                    {
                        label: '验证准确率',
                        data: valAcc,
                        borderColor: 'rgba(0, 212, 255, 0.9)',
                        backgroundColor: 'rgba(0, 212, 255, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#a0aec0',
                            font: { size: 12 },
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#a0aec0',
                            maxTicksLimit: 10
                        },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        beginAtZero: false,
                        min: 40,
                        max: 100,
                        ticks: {
                            color: '#a0aec0',
                            callback: function(value) { return value + '%'; }
                        },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                }
            }
        });
    } catch (e) {
        console.error('渲染准确率曲线失败:', e);
    }
}

/**
 * 渲染训练损失曲线
 * @param {Object} data - 评估数据
 */
function renderLossChart(data) {
    try {
        const canvas = document.getElementById('loss-chart');
        if (!canvas || !data.training_history || data.training_history.length === 0) return;
        
        const history = data.training_history;
        const epochLabels = history.map(h => 'E' + h.epoch);
        const trainLoss = history.map(h => h.loss.toFixed(4));
        const valLoss = history.map(h => h.val_loss.toFixed(4));
        
        // 销毁旧图表实例
        if (lossChart) {
            lossChart.destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        lossChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: epochLabels,
                datasets: [
                    {
                        label: '训练损失',
                        data: trainLoss,
                        borderColor: 'rgba(255, 165, 2, 0.9)',
                        backgroundColor: 'rgba(255, 165, 2, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        borderWidth: 2
                    },
                    {
                        label: '验证损失',
                        data: valLoss,
                        borderColor: 'rgba(123, 237, 159, 0.9)',
                        backgroundColor: 'rgba(123, 237, 159, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#a0aec0',
                            font: { size: 12 },
                            padding: 15
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#a0aec0',
                            maxTicksLimit: 10
                        },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#a0aec0' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                }
            }
        });
    } catch (e) {
        console.error('渲染损失曲线失败:', e);
    }
}

/**
 * 渲染分类报告表格
 * @param {Object} data - 评估数据
 */
function renderClassificationReport(data) {
    try {
        const container = document.getElementById('classification-report-container');
        if (!container) return;
        
        const classNames = {
            'fire': '火灾 (fire)',
            'smoke': '烟雾 (smoke)',
            'fire_smoke': '火灾+烟雾 (fire_smoke)',
            'normal': '正常 (normal)'
        };
        
        const report = data.classification_report;
        if (!report) {
            container.innerHTML = '<p style="color:var(--text-muted);text-align:center;">无分类报告数据</p>';
            return;
        }
        
        let html = '<table class="report-table">';
        
        // 表头
        html += '<tr>';
        html += '<th>类别</th>';
        html += '<th>精确率 (Precision)</th>';
        html += '<th>召回率 (Recall)</th>';
        html += '<th>F1 分数</th>';
        html += '<th>样本数 (Support)</th>';
        html += '</tr>';
        
        // 数据行
        let totalSupport = 0;
        let totalPrecision = 0;
        let totalRecall = 0;
        let totalF1 = 0;
        let classCount = 0;
        
        for (const cls of data.classes) {
            const metrics = report[cls];
            if (!metrics) continue;
            
            const p = (metrics.precision * 100).toFixed(2);
            const r = (metrics.recall * 100).toFixed(2);
            const f = (metrics['f1-score'] * 100).toFixed(2);
            const s = metrics.support;
            
            totalSupport += s;
            totalPrecision += metrics.precision;
            totalRecall += metrics.recall;
            totalF1 += metrics['f1-score'];
            classCount++;
            
            html += '<tr>';
            html += `<td>${classNames[cls] || cls}</td>`;
            html += `<td>${p}%</td>`;
            html += `<td>${r}%</td>`;
            html += `<td>${f}%</td>`;
            html += `<td>${s}</td>`;
            html += '</tr>';
        }
        
        // 加权平均行
        if (classCount > 0) {
            html += '<tr class="highlight-row">';
            html += '<td style="color:var(--primary-red);">加权平均</td>';
            html += `<td><strong>${(totalPrecision / classCount * 100).toFixed(2)}%</strong></td>`;
            html += `<td><strong>${(totalRecall / classCount * 100).toFixed(2)}%</strong></td>`;
            html += `<td><strong>${(totalF1 / classCount * 100).toFixed(2)}%</strong></td>`;
            html += `<td><strong>${totalSupport}</strong></td>`;
            html += '</tr>';
        }
        
        html += '</table>';
        
        container.innerHTML = html;
    } catch (e) {
        console.error('渲染分类报告失败:', e);
    }
}
