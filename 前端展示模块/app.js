// app.js - 秦岭火灾预警系统前端逻辑（演示优化版）
class FireDetectionDashboard {
    constructor() {
        // 初始化状态
        this.useMockDetection = false;
        this.apiAvailable = false;
        this.currentMode = 'api';
        this.detectionHistory = [];
        this.isProcessing = false;
        this.currentImage = null;
        this.classNames = ['fire', 'smoke', 'fire_smoke', 'normal'];
        this.classChineseNames = {
            'fire': '🔥 明火',
            'smoke': '💨 烟雾',
            'fire_smoke': '🔥💨 火与烟',
            'normal': '✅ 正常'
        };
        this.classColors = {
            'fire': '#FF3838',
            'smoke': '#A0AEC0',
            'fire_smoke': '#FF9F1A',
            'normal': '#2ED573'
        };

        this.heatmapOverlay = null;
        this.sensorData = null;
        this.sensorUpdateInterval = null;
        this.sentAlertIds = new Set();
        
        // 后端API配置
        this.apiConfig = {
            baseUrl: 'http://localhost:8001',
            endpoints: {
                detect: '/detect',
                sensor: '/sensors',
                risk: '/assess-risk',
                health: '/health'
            },
            timeout: 10000
        };
        
        // DOM元素缓存
        this.elements = {};
        
        // 图表实例
        this.probabilityChart = null;
        this.riskTrendChart = null;
        
        this.init();
    }

    // 缓存DOM元素
    cacheElements() {
        this.elements = {
            uploadBtn: document.getElementById('upload-btn'),
            clearBtn: document.getElementById('clear-btn'),
            detectBtn: document.getElementById('detect-btn'),
            fileInput: document.getElementById('file-input'),
            modelSelector: document.getElementById('model-selector'),
            
            displayedImage: document.getElementById('displayed-image'),
            imagePlaceholder: document.getElementById('image-placeholder'),
            detectionClass: document.getElementById('detection-class'),
            confidenceBar: document.getElementById('confidence-bar'),
            confidenceValue: document.getElementById('confidence-value'),
            inferenceTime: document.getElementById('inference-time'),
            riskLevel: document.getElementById('risk-level'),
            probabilityList: document.getElementById('probability-list'),
            imageContainer: document.getElementById('image-container'),

            tfStatus: document.getElementById('tf-status'),
            serverDot: document.getElementById('server-dot'),
            serverText: document.getElementById('server-text'),
            // 【D2修复】已移除右上角弹窗DOM引用，仅保留顶部横幅通知

            debugInfo: document.getElementById('debug-info'),

            alertBanner: document.getElementById('alert-banner'),
            alertBannerText: document.getElementById('alert-banner-text'),
            alertBannerClose: document.getElementById('alert-banner-close'),
            manualAlertBtn: document.getElementById('manual-alert-btn')
        };
    }

    // 初始化事件监听
    initEventListeners() {
        this.elements.uploadBtn.addEventListener('click', () => this.elements.fileInput.click());
        this.elements.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        this.elements.clearBtn.addEventListener('click', () => this.clearImage());
        this.elements.detectBtn.addEventListener('click', () => this.detectFire());
        
        if (this.elements.alertBannerClose) {
            this.elements.alertBannerClose.addEventListener('click', () => this.hideAlertBanner());
        }

        // 【D2修复】已移除右上角弹窗事件绑定
        
        if (this.elements.manualAlertBtn) {
            this.elements.manualAlertBtn.addEventListener('click', () => this.triggerManualAlert());
        }
        
        const alertHistoryBtn = document.getElementById('alert-history-btn');
        if (alertHistoryBtn) {
            alertHistoryBtn.addEventListener('click', () => this.loadAlertHistory());
        }
        
        // 图表范围选择
        const chartRange = document.getElementById('chart-range');
        if (chartRange) {
            chartRange.addEventListener('change', () => this.updateRiskTrendChart());
        }
        
        // 拖放支持
        const imageContainer = document.getElementById('image-container');
        imageContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            imageContainer.style.borderColor = 'var(--primary-red)';
        });
        
        imageContainer.addEventListener('dragleave', () => {
            imageContainer.style.borderColor = 'var(--border-color)';
        });
        
        imageContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            imageContainer.style.borderColor = 'var(--border-color)';
            if (e.dataTransfer.files.length) {
                this.handleFileUpload({ target: { files: e.dataTransfer.files } });
            }
        });
    }

    // 主初始化
    async init() {
        console.log('🔥 秦岭火灾预警系统启动...');
        
        this.cacheElements();
        this.initEventListeners();
        this.updateCurrentTime();
        setInterval(() => this.updateCurrentTime(), 1000);
        
        await this.checkBackendConnection();
        await this.loadDetectionHistory();
        this.startSensorUpdates();
        this.fetchSystemStatus();
        setInterval(() => this.fetchSystemStatus(), 30000);
        this.updateUIStatus();
        
        console.log('✅ 系统初始化完成');
    }

    // 更新API连接状态
    updateApiStatus(isConnected, message) {
        const dot = document.getElementById('server-dot');
        const text = document.getElementById('server-text');
        
        if (dot && text) {
            dot.className = isConnected ? 'status-dot connected' : 'status-dot disconnected';
            text.textContent = message;
        }
    }

    // 检查后端连接
    async checkBackendConnection() {
        try {
            const response = await fetch(`${this.apiConfig.baseUrl}${this.apiConfig.endpoints.health}`, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            
            if (response.ok) {
                this.apiAvailable = true;
                this.updateApiStatus(true, '后端已连接');
                return true;
            } else {
                this.updateApiStatus(false, `连接失败: ${response.status}`);
                return false;
            }
        } catch (error) {
            this.updateApiStatus(false, `连接错误`);
            return false;
        }
    }

    // 处理文件上传
    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.type.match('image.*')) {
            this.showAlert('请选择图片文件 (JPG, PNG等)', 'error');
            return;
        }
        
        this.showLoading('正在加载图片...');
        
        try {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    this.currentImage = img;
                    this.elements.displayedImage.src = e.target.result;
                    this.elements.displayedImage.classList.remove('hidden');
                    this.elements.imagePlaceholder.classList.add('hidden');
                    this.elements.detectBtn.disabled = false;
                    this.hideLoading();
                    
                    const autoDetect = document.getElementById('auto-detect');
                    if (autoDetect && autoDetect.checked) {
                        setTimeout(() => this.detectFire(), 500);
                    }
                };
                
                img.onerror = () => {
                    this.hideLoading();
                    this.showAlert('图片加载失败，请重试', 'error');
                };
                
                img.src = e.target.result;
            };
            
            reader.onerror = () => {
                this.hideLoading();
                this.showAlert('文件读取失败，请重试', 'error');
            };
            
            reader.readAsDataURL(file);
        } catch (error) {
            this.hideLoading();
            this.showAlert('处理文件时出错: ' + error.message, 'error');
        }
    }

    // 清空图片
    clearImage() {
        try {
            this.currentImage = null;
            
            if (this.elements.fileInput) {
                const newFileInput = document.createElement('input');
                newFileInput.type = 'file';
                newFileInput.id = 'file-input';
                newFileInput.accept = 'image/*';
                newFileInput.hidden = true;
                
                const oldFileInput = this.elements.fileInput;
                oldFileInput.parentNode.replaceChild(newFileInput, oldFileInput);
                this.elements.fileInput = newFileInput;
                this.elements.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
            }
            
            if (this.elements.displayedImage) {
                this.elements.displayedImage.src = '';
                this.elements.displayedImage.classList.add('hidden');
            }
            
            if (this.elements.imagePlaceholder) {
                this.elements.imagePlaceholder.classList.remove('hidden');
            }
            
            if (this.elements.detectBtn) {
                this.elements.detectBtn.disabled = true;
            }
            
            this.removeHeatmap();
            this.resetResults();
            
            if (this.probabilityChart) {
                this.probabilityChart.destroy();
                this.probabilityChart = null;
            }
        } catch (error) {
            this.showAlert('清空失败: ' + error.message, 'error');
        }
    }

    // 重置结果
    resetResults() {
        this.elements.detectionClass.textContent = '--';
        this.elements.confidenceBar.style.width = '0%';
        this.elements.confidenceValue.textContent = '0%';
        this.elements.inferenceTime.textContent = '-- ms';
        this.elements.riskLevel.textContent = '--';
        this.elements.riskLevel.className = 'risk-badge risk-low';
        this.elements.probabilityList.innerHTML = '';
        
        const probabilityCanvas = document.getElementById('probability-chart');
        if (probabilityCanvas) {
            const ctx = probabilityCanvas.getContext('2d');
            ctx.clearRect(0, 0, probabilityCanvas.width, probabilityCanvas.height);
        }
        
        const trendCanvas = document.getElementById('risk-trend-chart');
        if (trendCanvas) {
            const ctx = trendCanvas.getContext('2d');
            ctx.clearRect(0, 0, trendCanvas.width, trendCanvas.height);
        }
    }

    // 执行火灾检测
    async detectFire() {
        if (!this.currentImage) {
            this.showAlert('请先上传图片', 'warning');
            return;
        }
        
        if (this.isProcessing) return;
        
        this.isProcessing = true;
        this.setDetectionState(true);
        const startTime = performance.now();
        
        try {
            let result;
            
            if (this.apiAvailable && this.currentMode === 'api') {
                result = await this.detectWithAPI();
            } else {
                throw new Error('后端API不可用，请检查连接');
            }
            
            const inferenceTime = performance.now() - startTime;
            
            if (result) {
                result.inferenceTime = inferenceTime;
                this.detectionHistory.push({
                    timestamp: new Date().toISOString(),
                    result: result,
                    inferenceTime: inferenceTime
                });

                this.saveDetectionHistory();
                this.updateDetectionCount();
                this.displayDetectionResult(result);
                
                if (result.probabilities && Object.keys(result.probabilities).length > 0) {
                    this.updateProbabilityChart(result);
                }

                this.updateRiskTrendChart();
            } else {
                throw new Error('检测结果为空');
            }
            
        } catch (error) {
            this.showAlert(`检测失败: ${error.message}`, 'error');
            this.displayErrorResult();
        } finally {
            this.isProcessing = false;
            this.setDetectionState(false);
        }
    }

    // 使用后端API检测
    async detectWithAPI() {
        if (!this.apiAvailable) {
            throw new Error('后端API不可用');
        }
        
        const startTime = performance.now();
        
        try {
            const blob = await this.imageToBlob(this.currentImage);
            const formData = new FormData();
            formData.append('file', blob, 'detection.jpg');
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.apiConfig.timeout);
            
            const response = await fetch(`${this.apiConfig.baseUrl}${this.apiConfig.endpoints.detect}`, {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`API错误: ${response.status}`);
            }
            
            const data = await response.json();
            const inferenceTime = performance.now() - startTime;
            const resultData = data.data || data;
            
            return {
                class: resultData.prediction || resultData.class || 'unknown',
                classChinese: this.classChineseNames[resultData.prediction || resultData.class] || resultData.prediction || resultData.class,
                confidence: resultData.confidence || 0,
                inferenceTime: inferenceTime,
                probabilities: resultData.probabilities || resultData.all_probabilities || {},
                riskAssessment: resultData.riskAssessment || resultData.risk_assessment || {},
                heatmap: resultData.heatmap || null,
                detectionMode: 'api'
            };
            
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('后端API请求超时');
            }
            throw new Error(`后端检测失败: ${error.message}`);
        }
    }

    // 基于检测结果进行风险评估
    assessRisk(className, confidence) {
        let riskScore, riskLevel, description;
        
        if (className === 'fire') {
            riskScore = 80 + (confidence * 0.2);
            riskLevel = confidence > 70 ? 'critical' : 'high';
            description = '检测到明火';
        } else if (className === 'fire_smoke') {
            riskScore = 60 + (confidence * 0.3);
            riskLevel = 'high';
            description = '检测到火与烟';
        } else if (className === 'smoke') {
            riskScore = 40 + (confidence * 0.3);
            riskLevel = 'medium';
            description = '检测到烟雾';
        } else {
            riskScore = 10 + (confidence * 0.1);
            riskLevel = 'low';
            description = '情况正常';
        }
        
        riskScore = Math.max(0, Math.min(100, riskScore));
        
        return {
            score: Math.round(riskScore),
            level: riskLevel,
            description: description,
            recommendation: this.getRiskRecommendation(riskLevel)
        };
    }

    getRiskRecommendation(riskLevel) {
        const recommendations = {
            critical: '立即启动应急预案，通知消防部门，组织人员撤离',
            high: '立即派人前往现场确认，准备启动应急预案',
            medium: '加强监控，派人前往检查，准备应急物资',
            low: '保持正常监控，定期巡检'
        };
        return recommendations[riskLevel] || '保持监控';
    }

    // 显示检测结果 - AI仪式感增强
    displayDetectionResult(result) {
        if (!result) {
            this.displayErrorResult();
            return;
        }
        
        try {
            // 检测类别（带渐显动画）
            this.elements.detectionClass.textContent = result.classChinese || result.class || '未知';
            this.elements.detectionClass.classList.remove('result-animate-in');
            void this.elements.detectionClass.offsetWidth;
            this.elements.detectionClass.classList.add('result-animate-in');
            
            // 置信度
            const rawConfidence = typeof result.confidence === 'number' ? result.confidence : 0;
            const displayConfidence = Math.min(99.9, rawConfidence * 99);
            this.elements.confidenceBar.style.width = `${displayConfidence}%`;
            this.elements.confidenceValue.textContent = `${displayConfidence.toFixed(1)}%`;
            
            // 高风险时置信度条变色
            const riskLevel = result.riskAssessment?.level || 'low';
            if (riskLevel === 'critical' || riskLevel === 'high') {
                this.elements.confidenceBar.classList.add('meter-critical');
            } else {
                this.elements.confidenceBar.classList.remove('meter-critical');
            }
            
            // 推理时间
            const inferenceTime = typeof result.inferenceTime === 'number' ? result.inferenceTime : 0;
            this.elements.inferenceTime.textContent = `${inferenceTime.toFixed(1)} ms`;
            
            // 更新平均速度
            const avgSpeedEl = document.getElementById('avg-speed');
            if (avgSpeedEl && this.detectionHistory.length > 0) {
                const avgTime = this.detectionHistory.reduce((sum, item) =>
                    sum + item.inferenceTime, 0) / this.detectionHistory.length;
                avgSpeedEl.textContent = `${avgTime.toFixed(1)} ms`;
            }
            
            // 风险等级（带动画 + 卡片边框联动）
            const riskText = this.getRiskLevelText(riskLevel);
            this.elements.riskLevel.textContent = riskText;
            this.elements.riskLevel.className = `risk-badge risk-${riskLevel} result-animate-in`;
            
            // 结果卡片风险边框联动
            const resultCard = this.elements.riskLevel.closest('.modern-card');
            if (resultCard) {
                resultCard.classList.remove('risk-alert-active', 'risk-high-active', 'result-animate-in');
                void resultCard.offsetWidth;
                resultCard.classList.add('result-animate-in');
                if (riskLevel === 'critical') {
                    resultCard.classList.add('risk-alert-active');
                } else if (riskLevel === 'high') {
                    resultCard.classList.add('risk-alert-active', 'risk-high-active');
                }
            }
            
            // 概率列表
            if (result.probabilities && Object.keys(result.probabilities).length > 0) {
                this.updateProbabilityList(result.probabilities);
            } else {
                this.elements.probabilityList.innerHTML = '';
            }
            
            // 热力图
            if (result.heatmap) {
                this.showHeatmap(result.heatmap);
            } else {
                this.removeHeatmap();
            }

            this.recordDetectionHistory(result);
            this.checkAndTriggerAlert(result);
            this.updateRiskTrendChart();
            
        } catch (error) {
            this.displayErrorResult(error);
        }
    }

    // 更新概率列表
    updateProbabilityList(probabilities) {
        this.elements.probabilityList.innerHTML = '';
        
        Object.entries(probabilities).forEach(([className, prob]) => {
            const percentage = (prob * 100).toFixed(1);
            const color = this.classColors[className];
            
            const probItem = document.createElement('div');
            probItem.className = 'prob-item';
            probItem.innerHTML = `
                <span class="prob-label">${this.classChineseNames[className]}</span>
                <div class="prob-bar">
                    <div class="prob-fill" style="width: ${percentage}%; background: ${color};"></div>
                </div>
                <span class="prob-value">${percentage}%</span>
            `;
            
            this.elements.probabilityList.appendChild(probItem);
        });
    }

    // 更新概率图表（环形图）
    updateProbabilityChart(result) {
        const ctx = document.getElementById('probability-chart').getContext('2d');
        
        if (this.probabilityChart) {
            this.probabilityChart.destroy();
        }
        
        const labels = Object.keys(result.probabilities).map(name => this.classChineseNames[name]);
        const data = Object.values(result.probabilities).map(prob => prob * 100);
        const backgroundColors = Object.keys(result.probabilities).map(name => this.classColors[name]);
        
        this.probabilityChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors,
                    borderWidth: 2,
                    borderColor: 'var(--bg-card)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                color: '#FFFFFF',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#FFFFFF',
                            padding: 12,
                            font: { size: 11 },
                            generateLabels: function(chart) {
                                const data = chart.data;
                                if (data.labels.length && data.datasets.length) {
                                    return data.labels.map(function(label, i) {
                                        return {
                                            text: label,
                                            fillStyle: data.datasets[0].backgroundColor[i],
                                            hidden: false,
                                            index: i
                                        };
                                    });
                                }
                                return [];
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => `${context.label}: ${context.parsed.toFixed(1)}%`
                        },
                        titleColor: '#FFFFFF',
                        bodyColor: '#FFFFFF',
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        borderColor: '#FFFFFF',
                        borderWidth: 1
                    }
                }
            }
        });
    }

    // 【D2修复2】生成明显波动的历史趋势初始数据（0~100范围，肉眼可见高低起伏）
    generateRealisticInitialData(count) {
        const baseValues = [
            12, 78, 35, 92, 48, 67, 15, 88, 42, 73,
            22, 85, 31, 64, 19, 91, 55, 38, 76, 27,
            83, 14, 69, 45, 96, 21, 58, 74, 33, 87,
            41, 62, 11, 93, 29, 77, 46, 84, 18, 65,
            52, 89, 24, 71, 36, 95, 16, 53, 82, 43
        ];
        const result = [];
        for (let i = 0; i < count; i++) {
            result.push(baseValues[i % baseValues.length]);
        }
        return result;
    }

    // 更新风险趋势图表
    updateRiskTrendChart() {
        const chartRange = document.getElementById('chart-range');
        const range = chartRange ? parseInt(chartRange.value) : 20;
        
        const ctx = document.getElementById('risk-trend-chart').getContext('2d');
        
        if (this.riskTrendChart) {
            this.riskTrendChart.destroy();
        }
        
        let labels, riskScores;

        if (this.detectionHistory.length < 2) {
            // 【修复2】无检测数据时展示真实感历史模拟趋势
            const count = range;
            labels = Array.from({length: count}, (_, i) => `T-${count - i}`);
            riskScores = this.generateRealisticInitialData(count);
        } else {
            const recentHistory = this.detectionHistory.slice(-range);
            labels = recentHistory.map((item, i) => `检测${i+1}`);
            riskScores = recentHistory.map(item => {
                const score = item.result.riskAssessment?.score || 50;
                return Math.min(100, Math.max(0, score));
            });
        }

        const lineColor = '#FF6B35';
        const fillColor = 'rgba(255, 107, 53, 0.15)';
        
        this.riskTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '风险分数',
                    data: riskScores,
                    borderColor: lineColor,
                    backgroundColor: fillColor,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: lineColor,
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                color: '#FFFFFF',
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.08)' },
                        ticks: {
                            color: '#FFFFFF',
                            callback: function(value) { return value + '分'; }
                        }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.08)' },
                        ticks: {
                            color: '#FFFFFF',
                            maxTicksLimit: 10
                        }
                    }
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#FFFFFF',
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) { return `风险分数: ${context.parsed.y}分`; }
                        },
                        titleColor: '#FFFFFF',
                        bodyColor: '#FFFFFF',
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        borderColor: lineColor,
                        borderWidth: 2
                    }
                }
            }
        });
    }

    // 更新检测次数
    updateDetectionCount() {
        const countElement = document.getElementById('detection-count');
        if (countElement) {
            countElement.textContent = this.detectionHistory.length;
        }
    }

    // 记录检测历史
    recordDetectionHistory(result) {
        this.updateUIStatus();
    }

    getRiskLevelText(level) {
        const texts = {
            'critical': '🔥 紧急',
            'high': '⚠️ 高危',
            'medium': '🔶 中危',
            'low': '✅ 低危'
        };
        return texts[level] || level;
    }

    getRiskColor(level) {
        const colors = {
            'critical': 'var(--critical-color)',
            'high': 'var(--high-color)',
            'medium': 'var(--medium-color)',
            'low': 'var(--low-color)'
        };
        return colors[level] || 'var(--text-secondary)';
    }

    // 设置检测状态 - AI仪式感增强
    setDetectionState(isDetecting) {
        if (this.elements.detectBtn) {
            this.elements.detectBtn.disabled = isDetecting;
            this.elements.detectBtn.innerHTML = isDetecting
                ? '<i class="fas fa-spinner fa-spin"></i> 检测中...'
                : '<i class="fas fa-bolt"></i> 立即检测';
        }
        
        if (this.elements.uploadBtn) {
            this.elements.uploadBtn.disabled = isDetecting;
        }

        // AI分析中覆盖层
        const imageContainer = this.elements.imageContainer || document.getElementById('image-container');
        if (imageContainer) {
            const existingOverlay = imageContainer.querySelector('.ai-analyzing-overlay');
            if (isDetecting) {
                if (!existingOverlay) {
                    const overlay = document.createElement('div');
                    overlay.className = 'ai-analyzing-overlay';
                    overlay.innerHTML = `
                        <div class="ai-scan-ring"></div>
                        <div class="ai-scan-line"></div>
                        <div class="ai-status-text">AI 深度分析中</div>
                        <div class="ai-status-sub">NEURAL NETWORK PROCESSING...</div>
                    `;
                    imageContainer.appendChild(overlay);
                }
            } else {
                if (existingOverlay) {
                    existingOverlay.style.animation = 'overlay-fade-in 0.2s ease reverse';
                    setTimeout(() => existingOverlay.remove(), 200);
                }
            }
        }
    }

    // 【D2修复】showAlert改为使用toast通知，不再使用右上角弹窗
    showAlert(message, type = 'info') {
        this.showToast(message, type);
    }

    // 【D2修复】hideAlert保留空方法防报错
    hideAlert() {
        // 右上角弹窗已彻底删除
    }

    showLoading(message = '处理中...') {
        let overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-spinner"></div>
                <div id="loading-message">${message}</div>
            `;
            document.body.appendChild(overlay);
        }
        
        document.getElementById('loading-message').textContent = message;
        overlay.style.display = 'flex';
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    // 更新时间
    updateCurrentTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('zh-CN');
        const dateString = now.toLocaleDateString('zh-CN');
        
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = `${dateString} ${timeString}`;
        }
        
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = now.toLocaleTimeString('zh-CN');
        }
    }

    // 更新UI状态
    updateUIStatus() {
        if (this.detectionHistory.length > 0) {
            const avgTime = this.detectionHistory.reduce((sum, item) =>
                sum + item.result.inferenceTime, 0) / this.detectionHistory.length;
            
            const speedElement = document.getElementById('avg-speed');
            if (speedElement) {
                speedElement.textContent = `${avgTime.toFixed(1)} ms`;
            }
        }
    }

    displayErrorResult(error) {
        this.elements.detectionClass.textContent = '检测失败';
        this.elements.confidenceBar.style.width = '0%';
        this.elements.confidenceValue.textContent = '0%';
        this.elements.inferenceTime.textContent = '-- ms';
        this.elements.riskLevel.textContent = '未知';
        this.elements.riskLevel.className = 'risk-badge risk-low';
    }

    async imageToBlob(image) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            canvas.width = image.width;
            canvas.height = image.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(image, 0, 0);
            canvas.toBlob(resolve, 'image/jpeg', 0.9);
        });
    }

    // 启动传感器更新
    startSensorUpdates() {
        this.updateSensorData();
        this.sensorUpdateInterval = setInterval(() => this.updateSensorData(), 10000);
    }

    // 获取传感器数据
    async updateSensorData() {
        if (!this.apiAvailable) return;
        
        try {
            const response = await fetch(`${this.apiConfig.baseUrl}${this.apiConfig.endpoints.sensor}`);
            if (response.ok) {
                const json = await response.json();
                const data = json.data || json;
                this.sensorData = data;
                this.displaySensorData(data);
            }
        } catch (error) {
            this.displaySensorData({
                temperature: '--',
                humidity: '--',
                wind_speed: '--',
                air_quality: '--'
            });
        }
    }

    // 显示传感器数据（紧凑版，顶部栏）
    displaySensorData(data) {
        const sensorArea = document.getElementById('sensor-status-area');
        if (!sensorArea) return;
        
        sensorArea.innerHTML = `
            <span class="sensor-chip"><i class="fas fa-temperature-high"></i> ${data.temperature || '--'}°C</span>
            <span class="sensor-chip"><i class="fas fa-tint"></i> ${data.humidity || '--'}%</span>
            <span class="sensor-chip"><i class="fas fa-wind"></i> ${data.wind_speed || '--'}m/s</span>
            <span class="sensor-chip"><i class="fas fa-smog"></i> ${data.air_quality || '--'}AQI</span>
        `;
    }

    // 加载检测历史
    async loadDetectionHistory() {
        try {
            if (!this.apiAvailable) {
                const stored = localStorage.getItem('fireDetectionHistory');
                if (stored) {
                    this.detectionHistory = JSON.parse(stored);
                }
                return;
            }

            const response = await fetch(`${this.apiConfig.baseUrl}/history?limit=50`);
            if (response.ok) {
                const json = await response.json();
                const history = json.data || [];
                this.detectionHistory = history.map(item => ({
                    timestamp: item.timestamp,
                    result: {
                        class: item.prediction,
                        classChinese: this.classChineseNames[item.prediction] || item.prediction,
                        confidence: item.confidence,
                        inferenceTime: 0,
                        probabilities: item.probabilities || {},
                        riskAssessment: {
                            score: item.risk_score,
                            level: item.risk_level,
                            description: '',
                            recommendation: ''
                        },
                        heatmap: item.heatmap || null,
                        detectionMode: 'api'
                    },
                    inferenceTime: 0
                }));
                this.updateDetectionCount();
                this.updateUIStatus();
                this.updateRiskTrendChart();
            }
        } catch (error) {
            const stored = localStorage.getItem('fireDetectionHistory');
            if (stored) {
                this.detectionHistory = JSON.parse(stored);
            }
        }
    }

    saveDetectionHistory() {
        try {
            const recentHistory = this.detectionHistory.slice(-50);
            localStorage.setItem('fireDetectionHistory', JSON.stringify(recentHistory));
        } catch (error) {
            console.warn('保存历史记录失败:', error);
        }
    }

    // 显示热力图
    showHeatmap(heatmapBase64) {
        if (!heatmapBase64) return;

        this.removeHeatmap();

        const imageContainer = this.elements.imageContainer || document.getElementById('image-container');
        if (!imageContainer) return;

        imageContainer.style.position = 'relative';
        imageContainer.style.overflow = 'hidden';

        // 【D2修复3】热力图改为蓝色高对比方案 - 与火焰颜色形成强烈反差
        const overlay = document.createElement('img');
        overlay.id = 'heatmap-overlay';
        overlay.src = 'data:image/png;base64,' + heatmapBase64;
        overlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: contain;
            pointer-events: none;
            opacity: 0.78;
            z-index: 10;
            mix-blend-mode: screen;
            filter: contrast(1.6) saturate(0.3) brightness(1.2) hue-rotate(200deg);
        `;

        overlay.onerror = () => overlay.remove();

        imageContainer.appendChild(overlay);
        this.heatmapOverlay = overlay;

        let toggleBtn = document.getElementById('heatmap-toggle-btn');
        if (!toggleBtn) {
            toggleBtn = document.createElement('button');
            toggleBtn.id = 'heatmap-toggle-btn';
            toggleBtn.className = 'heatmap-toggle-btn';
            toggleBtn.innerHTML = '<i class="fas fa-fire-alt"></i> 热力图';
            toggleBtn.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 20;
                background: rgba(0, 150, 255, 0.85);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                cursor: pointer;
                font-size: 12px;
            `;
            toggleBtn.onclick = () => {
                if (this.heatmapOverlay) {
                    const isVisible = this.heatmapOverlay.style.opacity !== '0';
                    this.heatmapOverlay.style.opacity = isVisible ? '0' : '0.78';
                    toggleBtn.style.background = isVisible ? 'rgba(128, 128, 128, 0.8)' : 'rgba(0, 150, 255, 0.85)';
                }
            };
            imageContainer.appendChild(toggleBtn);
        }
    }

    removeHeatmap() {
        const existing = document.getElementById('heatmap-overlay');
        if (existing) existing.remove();
        const toggleBtn = document.getElementById('heatmap-toggle-btn');
        if (toggleBtn) toggleBtn.remove();
        this.heatmapOverlay = null;
    }

    // ==================== 告警模块 ====================

    checkAndTriggerAlert(result) {
        if (!result || !result.riskAssessment) return;

        const riskLevel = result.riskAssessment.level;
        const riskScore = result.riskAssessment.score || 0;
        const imageId = result.detectionMode + '_' + (result.class || 'unknown') + '_' + Math.round(riskScore) + '_' + (this.detectionHistory.length);

        if (riskLevel === 'critical' || riskScore >= 50) {
            if (this.elements.manualAlertBtn) {
                this.elements.manualAlertBtn.style.display = 'inline-flex';
            }

            if (this.sentAlertIds.has(imageId)) return;
            
            this.sentAlertIds.add(imageId);
            if (this.sentAlertIds.size > 100) {
                const firstKey = this.sentAlertIds.values().next().value;
                this.sentAlertIds.delete(firstKey);
            }

            const now = new Date();
            const alertData = {
                risk_level: riskLevel,
                risk_score: riskScore,
                detection_type: result.classChinese || result.class || '未知',
                location: this.sensorData?.location || '秦岭北麓-监测点1',
                detected_at: now.getFullYear() + '-' +
                    String(now.getMonth() + 1).padStart(2, '0') + '-' +
                    String(now.getDate()).padStart(2, '0') + ' ' +
                    String(now.getHours()).padStart(2, '0') + ':' +
                    String(now.getMinutes()).padStart(2, '0') + ':' +
                    String(now.getSeconds()).padStart(2, '0'),
                image_id: imageId
            };

            this.sendAlert(alertData);
        } else {
            if (this.elements.manualAlertBtn) {
                this.elements.manualAlertBtn.style.display = 'none';
            }
            this.hideAlertBanner();
        }
    }

    async sendAlert(alertData) {
        try {
            const response = await fetch(`${this.apiConfig.baseUrl}/send-alert`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(alertData)
            });

            if (response.ok) {
                const data = await response.json();
                const alertId = data.data?.alert_id || '未知';
                const riskText = this.getRiskLevelText(alertData.risk_level);
                const score = alertData.risk_score || 0;
                this.showAlertBanner(
                    `🔥紧急告警！已向消防部门发送通知（模拟） 风险等级：${riskText} 风险分数：${score} 告警编号：${alertId}`
                );
                this.showAlert(`告警已发送！编号: ${alertId}`, 'error');
            } else {
                this.showAlertBanner(`🚨 紧急告警！风险等级: ${this.getRiskLevelText(alertData.risk_level)}`);
            }
        } catch (error) {
            this.showAlertBanner(`🚨 紧急告警！风险等级: ${this.getRiskLevelText(alertData.risk_level)}`);
        }
    }

    showAlertBanner(message) {
        if (!this.elements.alertBanner) return;
        if (this.elements.alertBannerText) {
            this.elements.alertBannerText.textContent = message;
        }
        this.elements.alertBanner.style.display = 'block';
    }

    hideAlertBanner() {
        if (this.elements.alertBanner) {
            this.elements.alertBanner.style.display = 'none';
        }
    }

    async triggerManualAlert() {
        const latestResult = this.detectionHistory.length > 0
            ? this.detectionHistory[this.detectionHistory.length - 1].result
            : null;

        const now = new Date();
        const formattedTime = now.getFullYear() + '-' +
            String(now.getMonth() + 1).padStart(2, '0') + '-' +
            String(now.getDate()).padStart(2, '0') + ' ' +
            String(now.getHours()).padStart(2, '0') + ':' +
            String(now.getMinutes()).padStart(2, '0') + ':' +
            String(now.getSeconds()).padStart(2, '0');

        const alertData = {
            risk_level: latestResult?.riskAssessment?.level || 'high',
            risk_score: latestResult?.riskAssessment?.score || 90,
            detection_type: latestResult?.classChinese || latestResult?.class || '未知',
            location: this.sensorData?.location || '秦岭北麓-监测点1',
            detected_at: formattedTime,
            image_id: 'manual_' + now.getTime()
        };

        await this.sendAlert(alertData);
    }

    // 加载告警历史
    async loadAlertHistory() {
        try {
            const response = await fetch(`${this.apiConfig.baseUrl}/alert-history`);
            if (response.ok) {
                const json = await response.json();
                const history = json.data || [];
                this.showAlertHistoryPanel(history);
                return history;
            } else {
                this.showAlert('告警历史获取失败', 'warning');
            }
        } catch (error) {
            this.showAlert('无法连接后端获取告警历史', 'warning');
        }
        return [];
    }

    // 告警状态配置
    getAlertStatusConfig(status) {
        const configs = {
            'pending': { label: '待处理', color: '#FF4757', bgColor: 'rgba(255, 71, 87, 0.15)', borderColor: 'rgba(255, 71, 87, 0.5)', icon: 'fa-exclamation-circle' },
            'acknowledged': { label: '已确认', color: '#FFD700', bgColor: 'rgba(255, 215, 0, 0.12)', borderColor: 'rgba(255, 215, 0, 0.5)', icon: 'fa-user-check' },
            'resolved': { label: '已解决', color: '#2ED573', bgColor: 'rgba(46, 213, 115, 0.12)', borderColor: 'rgba(46, 213, 115, 0.5)', icon: 'fa-check-circle' }
        };
        return configs[status] || configs['pending'];
    }

    // 显示告警历史面板
    showAlertHistoryPanel(history) {
        this._currentAlertHistory = history;

        let panel = document.getElementById('alert-history-panel');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'alert-history-panel';
            panel.className = 'alert-history-panel';
            document.body.appendChild(panel);
        }

        const pendingCount = history.filter(a => a.status === 'pending').length;
        const ackedCount = history.filter(a => a.status === 'acknowledged').length;
        const resolvedCount = history.filter(a => a.status === 'resolved').length;

        let listHtml = '';
        if (history.length === 0) {
            listHtml = '<div class="alert-history-empty"><i class="fas fa-inbox" style="font-size:2rem;margin-bottom:12px;display:block;opacity:0.4;"></i>暂无告警记录</div>';
        } else {
            const reversed = [...history].reverse();
            listHtml = reversed.map(item => {
                const riskText = this.getRiskLevelText(item.risk_level);
                const status = item.status || 'pending';
                const statusCfg = this.getAlertStatusConfig(status);
                const dbId = item.id;

                let actionHtml = '';
                if (status === 'pending') {
                    actionHtml = `<button class="alert-action-btn alert-action-ack" data-alert-id="${dbId}" onclick="window.dashboard.acknowledgeAlert(${dbId})"><i class="fas fa-hand-paper"></i> 确认</button>`;
                } else if (status === 'acknowledged') {
                    actionHtml = `<button class="alert-action-btn alert-action-acked-disabled" disabled><i class="fas fa-user-check"></i> 已确认</button><button class="alert-action-btn alert-action-resolve" data-alert-id="${dbId}" onclick="window.dashboard.resolveAlert(${dbId})"><i class="fas fa-check-double"></i> 解决</button>`;
                } else if (status === 'resolved') {
                    actionHtml = `<button class="alert-action-btn alert-action-resolved-disabled" disabled><i class="fas fa-check-circle"></i> 已解决</button>`;
                }

                let timeDetailsHtml = `<div class="alert-history-time"><i class="fas fa-paper-plane"></i> 发送: ${item.sent_at || '--'}</div>`;
                if (status === 'acknowledged' || status === 'resolved') {
                    timeDetailsHtml += `<div class="alert-history-time"><i class="fas fa-user"></i> 确认人: ${item.acknowledged_by || '--'} | 确认时间: ${item.acknowledged_time || '--'}</div>`;
                }
                if (status === 'resolved') {
                    timeDetailsHtml += `<div class="alert-history-time"><i class="fas fa-flag-checkered"></i> 解决时间: ${item.resolved_time || '--'}</div>`;
                }

                return `
                    <div class="alert-history-item alert-item-${status}" style="border-left-color: ${statusCfg.color};">
                        <div class="alert-history-header">
                            <span class="alert-history-id">${item.alert_id || '--'}</span>
                            <div class="alert-history-badges">
                                <span class="alert-history-risk risk-${item.risk_level || 'low'}">${riskText}</span>
                                <span class="alert-status-badge" style="background:${statusCfg.bgColor};color:${statusCfg.color};border:1px solid ${statusCfg.borderColor};">
                                    <i class="fas ${statusCfg.icon}"></i> ${statusCfg.label}
                                </span>
                            </div>
                        </div>
                        <div class="alert-history-detail">
                            <span><i class="fas fa-tachometer-alt"></i> 分数: ${item.risk_score || '--'}</span>
                            <span><i class="fas fa-tag"></i> 类型: ${item.detection_type || '--'}</span>
                            <span><i class="fas fa-map-marker-alt"></i> 位置: ${item.location || '--'}</span>
                        </div>
                        ${timeDetailsHtml}
                        <div class="alert-history-actions">${actionHtml}</div>
                    </div>
                `;
            }).join('');
        }

        panel.innerHTML = `
            <div class="alert-history-content">
                <div class="alert-history-title">
                    <h3><i class="fas fa-history"></i> 告警生命周期管理</h3>
                    <button id="close-alert-history" class="close-history-btn">&times;</button>
                </div>
                <div class="alert-history-stats">
                    <span class="stat-item stat-pending"><i class="fas fa-exclamation-circle"></i> 待处理: ${pendingCount}</span>
                    <span class="stat-item stat-acked"><i class="fas fa-user-check"></i> 已确认: ${ackedCount}</span>
                    <span class="stat-item stat-resolved"><i class="fas fa-check-circle"></i> 已解决: ${resolvedCount}</span>
                    <span class="stat-item stat-total"><i class="fas fa-list"></i> 总计: ${history.length}</span>
                </div>
                <div class="alert-history-list">${listHtml}</div>
            </div>
        `;

        document.getElementById('close-alert-history').addEventListener('click', () => {
            panel.style.display = 'none';
        });

        panel.addEventListener('click', (e) => {
            if (e.target === panel) panel.style.display = 'none';
        });

        panel.style.display = 'flex';
    }

    async acknowledgeAlert(alertId) {
        if (!alertId) { this.showToast('告警ID无效', 'error'); return; }

        const btn = document.querySelector(`.alert-action-ack[data-alert-id="${alertId}"]`);
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...'; }

        try {
            const response = await fetch(`${this.apiConfig.baseUrl}/alert/acknowledge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ alert_id: alertId, acknowledged_by: 'admin' })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.showToast('✅ 告警已确认', 'success');
                    await this.refreshAlertHistory();
                } else {
                    this.showToast(data.message || '确认失败', 'warning');
                    await this.refreshAlertHistory();
                }
            } else {
                this.showToast('服务器响应异常: ' + response.status, 'error');
            }
        } catch (error) {
            this.showToast('网络异常: ' + error.message, 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-hand-paper"></i> 确认'; }
        }
    }

    async resolveAlert(alertId) {
        if (!alertId) { this.showToast('告警ID无效', 'error'); return; }

        const btn = document.querySelector(`.alert-action-resolve[data-alert-id="${alertId}"]`);
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...'; }

        try {
            const response = await fetch(`${this.apiConfig.baseUrl}/alert/resolve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ alert_id: alertId })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.showToast('✅ 告警已解决', 'success');
                    await this.refreshAlertHistory();
                } else {
                    this.showToast(data.message || '解决失败', 'warning');
                    await this.refreshAlertHistory();
                }
            } else {
                this.showToast('服务器响应异常: ' + response.status, 'error');
            }
        } catch (error) {
            this.showToast('网络异常: ' + error.message, 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-check-double"></i> 解决'; }
        }
    }

    async refreshAlertHistory() {
        try {
            const response = await fetch(`${this.apiConfig.baseUrl}/alert-history`);
            if (response.ok) {
                const json = await response.json();
                const history = json.data || [];
                this.showAlertHistoryPanel(history);
            }
        } catch (error) {
            console.warn('刷新告警历史异常:', error);
        }
    }

    showToast(message, type = 'info') {
        const existing = document.getElementById('alert-toast');
        if (existing) existing.remove();

        const typeStyles = {
            'success': { bg: 'rgba(46, 213, 115, 0.95)', icon: 'fa-check-circle' },
            'error': { bg: 'rgba(255, 71, 87, 0.95)', icon: 'fa-exclamation-circle' },
            'warning': { bg: 'rgba(255, 215, 0, 0.95)', icon: 'fa-exclamation-triangle', textColor: '#1a1a2e' },
            'info': { bg: 'rgba(30, 144, 255, 0.95)', icon: 'fa-info-circle' }
        };
        const style = typeStyles[type] || typeStyles.info;

        const toast = document.createElement('div');
        toast.id = 'alert-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 99999;
            background: ${style.bg};
            color: ${style.textColor || '#FFFFFF'};
            padding: 14px 24px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.95rem;
            box-shadow: 0 8px 30px rgba(0,0,0,0.4);
            display: flex;
            align-items: center;
            gap: 10px;
            animation: toast-slide-in 0.3s ease;
            max-width: 400px;
        `;
        toast.innerHTML = `<i class="fas ${style.icon}"></i> ${message}`;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toast-slide-out 0.3s ease forwards';
            setTimeout(() => { if (toast.parentNode) toast.remove(); }, 300);
        }, 3000);
    }

    // 系统状态获取
    async fetchSystemStatus() {
        try {
            const response = await fetch(`${this.apiConfig.baseUrl}/system-status`);
            if (!response.ok) return;

            const json = await response.json();
            if (json.success && json.data) {
                // 更新模型大小（如果有）
                const modelSizeEl = document.getElementById('model-size');
                if (modelSizeEl && json.data.model_size) {
                    modelSizeEl.textContent = json.data.model_size;
                }
            }
        } catch (error) {
            console.warn('系统状态获取异常:', error);
        }
    }
}

// 启动应用
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new FireDetectionDashboard();
});
