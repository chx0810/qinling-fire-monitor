/**
 * ====================================================================
 * 秦岭森林火情智能监测指挥中心 - 大屏交互逻辑
 * 第六阶段C增强：Leaflet地图 + 实时告警推送 + 视觉增强 + 演示模式
 * 原则：不重构、不改API、不改数据库、所有新增前端实现
 * ====================================================================
 */

// ==================== 全局轮询定时器ID ====================
/** 系统状态刷新定时器（每30秒） */
var timerSystemStatus = null;
/** 告警历史刷新定时器（每15秒） */
var timerAlertHistory = null;
/** 统计数据刷新定时器（每30秒） */
var timerDashboardStats = null;
/** 风险趋势图刷新定时器（每60秒） */
var timerRiskTrend = null;

/** Chart.js实例引用（用于销毁旧实例，防止内存泄漏） */
var riskTrendChartInstance = null;

// ==================== 第六阶段C：新增全局变量 ====================

/** Leaflet地图实例 */
var leafletMap = null;
/** 地图上的所有标记图层组 */
var markerLayerGroup = null;
/** 模拟火情监测点数据（前端生成） */
var simulatedFirePoints = [];
/** 当前告警计数器（今日告警数，前端维护） */
var currentAlertCount = 0;
/** 实时告警定时器（每5秒轮询真实告警） */
var timerRealtimeAlert = null;
/** 上次已知的最新告警ID（用于检测新告警） */
var lastKnownAlertId = null;
/** 演示模式开关 */
var demoModeActive = false;
/** 演示模式定时器（告警+地图） */
var timerDemoMode = null;
/** 演示模式风险趋势快速刷新定时器 */
var timerDemoTrend = null;
/** 风险趋势图当前小时索引 */
var currentTrendHourIndex = -1;
/** 缓存系统状态数据（供统计卡片使用） */
var cachedSystemStatus = {
    model_loaded: false,
    sensors_active: false,
    database_connected: false,
    today_alert_count: 0
};

// ==================== 第五阶段-D1：工程级初始风险值优化 ====================
/**
 * 风险趋势图初始数据（24点，大幅波动，视觉冲击感强）
 * 用于API未返回数据或返回平坦数据时的兜底展示
 * 最大值≤100，最小值≥20，呈明显起伏状态
 */
var INITIAL_RISK_TREND_DATA = [
    20, 100, 35, 90, 40, 75, 30, 95, 45, 85, 25, 80,
    50, 70, 30, 100, 20, 90, 40, 80, 30, 95, 25, 85
];
var INITIAL_RISK_TREND_HOURS = [
    '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
    '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
    '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
    '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'
];
var INITIAL_RISK_TREND_ALERTS = [
    0, 3, 1, 2, 1, 2, 0, 3, 1, 2, 0, 2,
    1, 2, 0, 3, 0, 2, 1, 2, 0, 3, 0, 2
];

// ==================== 秦岭区域模拟监测点数据 ====================

/**
 * 秦岭区域模拟火情监测点（15个点位）
 * 包含：名称、风险等级、风险分数、经纬度
 * 经纬度范围：经度106°~111°，纬度33°~34.5°（秦岭山脉区域）
 */
var QINLING_FIRE_POINTS = [
    { name: '太白山北坡监测点', level: 'critical', score: 92.5, lat: 33.97, lng: 107.76 },
    { name: '华山南峰预警站', level: 'high', score: 78.3, lat: 34.48, lng: 110.10 },
    { name: '佛坪保护区东区', level: 'medium', score: 55.2, lat: 33.52, lng: 107.99 },
    { name: '周至老县城林区', level: 'high', score: 81.7, lat: 33.86, lng: 107.83 },
    { name: '凤县紫柏山站点', level: 'low', score: 28.4, lat: 33.96, lng: 106.53 },
    { name: '商洛天竺山监测', level: 'critical', score: 88.9, lat: 33.52, lng: 110.01 },
    { name: '蓝田王顺山林区', level: 'medium', score: 62.1, lat: 33.99, lng: 109.38 },
    { name: '宁陕平河梁站', level: 'low', score: 19.7, lat: 33.55, lng: 108.38 },
    { name: '洋县华阳古镇站', level: 'high', score: 74.6, lat: 33.61, lng: 107.54 },
    { name: '镇安木王林区', level: 'medium', score: 58.3, lat: 33.44, lng: 109.12 },
    { name: '柞水牛背梁站', level: 'critical', score: 95.1, lat: 33.77, lng: 108.94 },
    { name: '勉县定军山监测', level: 'low', score: 22.8, lat: 33.16, lng: 106.64 },
    { name: '石泉云雾山林区', level: 'medium', score: 47.5, lat: 33.09, lng: 108.22 },
    { name: '山阳天竺山东区', level: 'high', score: 71.9, lat: 33.53, lng: 109.89 },
    { name: '留坝紫柏山北区', level: 'medium', score: 53.8, lat: 33.72, lng: 106.93 }
];

/** 用于生成模拟告警的地点名称池 */
var ALERT_LOCATIONS = [
    '太白山北坡', '华山南峰', '佛坪东区', '周至老县城', '凤县紫柏山',
    '商洛天竺山', '蓝田王顺山', '宁陕平河梁', '洋县华阳', '镇安木王',
    '柞水牛背梁', '勉县定军山', '石泉云雾山', '山阳天竺山', '留坝紫柏山',
    '长安翠华山', '户县朱雀公园', '临潼骊山', '渭南少华山', '安康南宫山'
];

/** 用于生成模拟告警的描述模板池 */
var ALERT_DESCRIPTIONS = [
    '传感器检测到温度异常升高',
    '烟雾浓度超过阈值',
    '红外热成像发现异常热源',
    'AI模型识别疑似火情',
    '可见光检测到明火特征',
    '多传感器融合预警',
    '风速增大，火险等级提升',
    '巡护无人机发现可疑烟点'
];

// ==================== 第三阶段-C2：真实告警→地图联动 ====================

/** 真实告警产生的Marker列表（用于生命周期管理） */
var realAlertMarkers = [];
/** 地图上保留的最大真实告警Marker数量 */
var MAX_REAL_ALERT_MARKERS = 15;
/** 已处理的真实告警ID集合（防止重复添加） */
var processedAlertIds = {};

/**
 * 区域名称→经纬度映射表
 * 基于秦岭山脉实际地理坐标
 * 用于将告警的location字段映射到地图坐标
 */
var LOCATION_COORDS = {
    '太白山北坡': { lat: 33.97, lng: 107.76 },
    '华山南峰':   { lat: 34.48, lng: 110.10 },
    '佛坪东区':   { lat: 33.52, lng: 107.99 },
    '周至老县城': { lat: 33.86, lng: 107.83 },
    '凤县紫柏山': { lat: 33.96, lng: 106.53 },
    '商洛天竺山': { lat: 33.52, lng: 110.01 },
    '蓝田王顺山': { lat: 33.99, lng: 109.38 },
    '宁陕平河梁': { lat: 33.55, lng: 108.38 },
    '洋县华阳':   { lat: 33.61, lng: 107.54 },
    '镇安木王':   { lat: 33.44, lng: 109.12 },
    '柞水牛背梁': { lat: 33.77, lng: 108.94 },
    '勉县定军山': { lat: 33.16, lng: 106.64 },
    '石泉云雾山': { lat: 33.09, lng: 108.22 },
    '山阳天竺山': { lat: 33.53, lng: 109.89 },
    '留坝紫柏山': { lat: 33.72, lng: 106.93 },
    '长安翠华山': { lat: 33.95, lng: 109.01 },
    '户县朱雀公园': { lat: 33.84, lng: 108.62 },
    '临潼骊山':   { lat: 34.36, lng: 109.28 },
    '渭南少华山': { lat: 34.42, lng: 109.82 },
    '安康南宫山': { lat: 32.38, lng: 108.90 },
    '秦岭山区':   { lat: 33.80, lng: 108.50 },
    '秦岭北麓':   { lat: 34.10, lng: 108.90 },
    '秦岭南麓':   { lat: 33.50, lng: 108.50 },
    '太白山区':   { lat: 33.97, lng: 107.76 },
    '山阳区域':   { lat: 33.53, lng: 109.89 },
    '佛坪保护区': { lat: 33.52, lng: 107.99 }
};

// ==================== 初始化函数 ====================

/**
 * 页面加载完成后初始化所有模块
 * 按顺序：时钟 → 系统状态 → 告警历史 → 统计数据 → 风险趋势图 → 监控点 → 系统信息 → Leaflet地图 → 实时告警推送
 */
document.addEventListener('DOMContentLoaded', function () {
    console.log('🖥️ 指挥大屏初始化开始（第三阶段-A仪式感增强版）...');

    // ==================== 第三阶段-A：指挥中心启动仪式感 ====================
    // 启动遮罩 + 进度条 → 进度完成后渐隐遮罩 → UI逐步点亮 → 全部在~1秒内完成
    var bootOverlay = document.getElementById('boot-overlay');
    var progressBar = document.getElementById('boot-progress-bar');
    var container = document.getElementById('large-screen-container');

    // 步骤1：进度条快速填充（400ms）
    if (progressBar) {
        progressBar.style.width = '100%';
        progressBar.style.transition = 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
    }

    // 步骤2：进度完成后渐隐遮罩（400ms后开始，持续400ms）
    setTimeout(function () {
        if (bootOverlay) {
            bootOverlay.classList.add('fade-out');
        }
    }, 420);

    // 步骤3：遮罩渐隐后激活UI入场动画 + 初始化数据模块
    setTimeout(function () {
        // 移除遮罩DOM
        if (bootOverlay && bootOverlay.parentNode) {
            bootOverlay.parentNode.removeChild(bootOverlay);
        }

        // 激活大屏容器（触发CSS入场动画序列：header→左右→中间→底部）
        if (container) {
            container.classList.add('boot-active');
        }

        // 初始化数据模块（与入场动画并行）
        try {
            // 1. 启动实时时钟（每秒刷新）
            initClock();

            // 2. 渲染监控点状态（静态数据）
            renderCameraList();

            // 3. 获取系统状态数据（首次加载 + 每30秒刷新）
            fetchSystemStatus();
            timerSystemStatus = setInterval(fetchSystemStatus, 30000);

            // 4. 获取告警历史数据（首次加载 + 每15秒刷新）
            fetchAlertHistory();
            timerAlertHistory = setInterval(fetchAlertHistory, 15000);

            // 5. 获取统计数据（首次加载 + 每30秒刷新）
            fetchDashboardStats();
            timerDashboardStats = setInterval(fetchDashboardStats, 30000);

            // 6. 【第五阶段-D1】立即渲染初始波动数据，再异步获取真实数据覆盖
            renderInitialRiskTrendChart();
            fetchRiskTrend();
            timerRiskTrend = setInterval(fetchRiskTrend, 60000);

            // 7. 初始化Leaflet真实地图
            initLeafletMap();

            // 8. 启动实时告警推送模拟（每10秒）
            startRealtimeAlertSimulation();

            console.log('✅ 指挥大屏初始化完成（第三阶段-A仪式感增强版），轮询已启动');
        } catch (err) {
            console.error('❌ 指挥大屏初始化异常:', err);
        }
    }, 850);
});

// ==================== 实时时钟模块 ====================

/**
 * 初始化顶部实时时钟
 * 每秒刷新一次当前时间显示
 */
function initClock() {
    /** 更新时钟显示 */
    function updateClock() {
        try {
            var now = new Date();
            var year = now.getFullYear();
            var month = String(now.getMonth() + 1).padStart(2, '0');
            var day = String(now.getDate()).padStart(2, '0');
            var hours = String(now.getHours()).padStart(2, '0');
            var minutes = String(now.getMinutes()).padStart(2, '0');
            var seconds = String(now.getSeconds()).padStart(2, '0');
            var timeStr = year + '-' + month + '-' + day + ' ' + hours + ':' + minutes + ':' + seconds;

            var el = document.getElementById('header-time');
            if (el) {
                el.textContent = timeStr;
            }
        } catch (err) {
            console.error('时钟更新异常:', err);
        }
    }

    // 立即执行一次，然后每秒刷新
    updateClock();
    setInterval(updateClock, 1000);
}

// ==================== 任务1：系统状态数据接口 ====================

/**
 * 从 /system-status 接口获取真实系统状态数据
 * 更新顶部栏：今日告警数、系统状态
 * 更新底部：系统启动时间
 * 更新系统信息面板：AI模型状态、数据库状态、运行时长等
 * 每30秒自动调用一次
 */
async function fetchSystemStatus() {
    try {
        var resp = await fetch('/system-status');
        var json = await resp.json();

        if (!json.success || !json.data) {
            console.warn('⚠️ 系统状态接口返回失败:', json.message);
            return;
        }

        var data = json.data;

        // 更新缓存系统状态数据（供统计卡片使用）
        cachedSystemStatus.model_loaded = data.model_loaded;
        cachedSystemStatus.sensors_active = data.sensors_active;
        cachedSystemStatus.database_connected = data.database_connected;
        cachedSystemStatus.today_alert_count = data.today_alert_count || 0;

        // 更新顶部栏 - 今日告警数（同步到前端计数器）
        var alertCountEl = document.getElementById('header-alert-count');
        if (alertCountEl) {
            var serverCount = data.today_alert_count || 0;
            // 取服务端计数与前端计数的较大值，避免覆盖前端实时新增
            if (serverCount > currentAlertCount) {
                currentAlertCount = serverCount;
            }
            alertCountEl.textContent = currentAlertCount;
        }

        // 更新底部 - 系统启动时间
        var startTimeEl = document.getElementById('system-start-time');
        if (startTimeEl && data.uptime) {
            startTimeEl.textContent = data.uptime;
        }

        // 更新系统信息面板
        var sysInfoList = document.getElementById('system-info-list');
        if (sysInfoList) {
            var modelStatusText = data.model_status || '未知';
            var modelStatusClass = data.model_loaded ? 'status-good' : 'status-bad';
            var dbStatusText = data.database_status || '未知';
            var dbStatusClass = data.database_connected ? 'status-good' : 'status-bad';

            var systemInfoData = [
                { label: 'AI模型状态', value: modelStatusText, statusClass: modelStatusClass },
                { label: '数据库状态', value: dbStatusText, statusClass: dbStatusClass },
                { label: '传感器状态', value: data.sensors_active ? '运行中' : '离线', statusClass: data.sensors_active ? 'status-good' : 'status-bad' },
                { label: 'API版本', value: data.api_version || 'v1.0.0', statusClass: '' },
                { label: '系统运行时长', value: data.uptime || '未知', statusClass: 'status-good' },
                { label: '今日检测数', value: String(data.today_detection_count || 0), statusClass: '' }
            ];

            var html = '';
            for (var i = 0; i < systemInfoData.length; i++) {
                var info = systemInfoData[i];
                var cls = info.statusClass ? ' ' + info.statusClass : '';
                html += '<div class="system-info-row">' +
                    '<span class="info-label">' + info.label + '</span>' +
                    '<span class="info-value' + cls + '">' + info.value + '</span>' +
                '</div>';
            }
            sysInfoList.innerHTML = html;
        }

        console.log('✅ 系统状态数据已更新');
    } catch (err) {
        console.error('❌ 获取系统状态失败:', err);
    }
}

// ==================== 任务2：告警历史数据接口 ====================

/**
 * 从 /alert-history 接口获取真实告警数据
 * 更新左侧"实时告警流"面板
 * 按时间倒序排列，最多显示20条
 * 每15秒自动调用一次
 */
async function fetchAlertHistory() {
    try {
        var resp = await fetch('/alert-history?limit=50');
        var json = await resp.json();

        if (!json.success || !json.data) {
            console.warn('⚠️ 告警历史接口返回失败:', json.message);
            renderAlertFallback('数据获取失败');
            return;
        }

        var alerts = json.data;

        // 如果无数据显示"暂无告警记录"
        if (!alerts || alerts.length === 0) {
            renderAlertFallback('暂无告警记录');
            return;
        }

        // 按时间倒序排列
        alerts.sort(function (a, b) {
            var timeA = a.detected_at || a.sent_at || '';
            var timeB = b.detected_at || b.sent_at || '';
            return timeB.localeCompare(timeA);
        });

        // 最多显示20条
        var displayAlerts = alerts.slice(0, 20);

        // 构建告警HTML
        var wrapper = document.getElementById('alert-scroll-wrapper');
        if (!wrapper) return;

        var html = '';
        for (var i = 0; i < displayAlerts.length; i++) {
            html += buildRealAlertItemHTML(displayAlerts[i]);
        }

        wrapper.innerHTML = html;

        console.log('✅ 告警历史数据已更新，共' + displayAlerts.length + '条');
    } catch (err) {
        console.error('❌ 获取告警历史失败:', err);
        renderAlertFallback('数据获取失败');
    }
}

/**
 * 当告警数据获取失败或为空时，显示占位信息
 * @param {string} message - 提示文字
 */
function renderAlertFallback(message) {
    var wrapper = document.getElementById('alert-scroll-wrapper');
    if (!wrapper) return;
    wrapper.innerHTML = '<div style="text-align:center;padding:30px;color:#4a7a9b;font-size:14px;">' +
        '<div style="font-size:28px;margin-bottom:10px;">📭</div>' +
        '<div>' + message + '</div>' +
    '</div>';
}

/**
 * 构建单条真实告警项的HTML字符串
 * @param {Object} alert - 告警数据对象
 * @returns {string} HTML字符串
 */
function buildRealAlertItemHTML(alert) {
    var level = alert.risk_level || 'low';
    var levelText = getLevelText(level);
    var score = alert.risk_score || 0;
    var detectedAt = alert.detected_at || alert.sent_at || '--';
    var timeShort = detectedAt.length > 10 ? detectedAt.substring(11) : detectedAt;
    var status = alert.status || 'pending';
    var statusText = getStatusText(status);
    var alertId = alert.alert_id || ('#' + (alert.id || ''));
    var location = alert.location || '未知位置';

    return '<div class="alert-stream-item level-' + level + '">' +
        '<div class="alert-item-header">' +
            '<span class="alert-level-tag tag-' + level + '">' + levelText + '</span>' +
            '<span class="alert-item-time">' + timeShort + '</span>' +
        '</div>' +
        '<div class="alert-item-location">📍 ' + location + '</div>' +
        '<div class="alert-item-score">⚠️ 风险: <span class="score-value">' + score.toFixed(1) + '</span> · ' + statusText + '</div>' +
        '<div style="font-size:10px;color:#4a7a9b;margin-top:2px;">' + alertId + '</div>' +
    '</div>';
}

/**
 * 构建模拟实时告警项HTML（带新告警动画效果）
 * @param {Object} alert - 模拟告警对象
 * @returns {string} HTML字符串
 */
function buildSimulatedAlertItemHTML(alert) {
    var level = alert.level || 'low';
    var levelText = getLevelText(level);
    var score = alert.score || 0;
    var timeStr = alert.time || '--';
    var location = alert.location || '未知位置';
    var alertId = alert.id || '';

    return '<div class="alert-stream-item alert-new-item alert-highlight level-' + level + '">' +
        '<div class="alert-item-header">' +
            '<span class="alert-level-tag tag-' + level + '">' + levelText + '</span>' +
            '<span class="alert-item-time">' + timeStr + '</span>' +
        '</div>' +
        '<div class="alert-item-location">📍 ' + location + '</div>' +
        '<div class="alert-item-score">⚠️ 风险: <span class="score-value">' + score.toFixed(1) + '</span> · 待处理</div>' +
        '<div style="font-size:10px;color:#4a7a9b;margin-top:2px;">' + alertId + '</div>' +
    '</div>';
}

/**
 * 获取风险等级中文文本
 * @param {string} level - 风险等级英文标识
 * @returns {string} 中文文本
 */
function getLevelText(level) {
    var map = {
        'critical': '紧急',
        'high': '高危',
        'medium': '中等',
        'low': '低危'
    };
    return map[level] || level;
}

/**
 * 获取告警状态中文文本
 * @param {string} status - 告警状态英文标识
 * @returns {string} 中文文本
 */
function getStatusText(status) {
    var map = {
        'pending': '待处理',
        'acknowledged': '已确认',
        'resolved': '已解决',
        'sent': '已发送'
    };
    return map[status] || status;
}

// ==================== 任务3：统计数据接口 ====================

/**
 * 从 /dashboard-stats 接口获取核心统计数据
 * 每30秒自动调用一次
 */
async function fetchDashboardStats() {
    try {
        var resp = await fetch('/dashboard-stats');
        var json = await resp.json();

        if (!json.success || !json.data) {
            console.warn('⚠️ 统计数据接口返回失败:', json.message);
            // 接口失败时填充占位符，保证布局美观
            renderStatsCardsPlaceholder();
            return;
        }

        var data = json.data;

        // 风险等级文字映射
        var riskLevelMap = {
            critical: '极高',
            high: '高危',
            medium: '中等',
            low: '低'
        };
        var avgRisk = data.average_risk_score || 0;
        var riskLabel, riskColor;
        if (avgRisk >= 80) { riskLabel = 'critical'; riskColor = 'card-red'; }
        else if (avgRisk >= 60) { riskLabel = 'high'; riskColor = 'card-orange'; }
        else if (avgRisk >= 40) { riskLabel = 'medium'; riskColor = 'card-yellow'; }
        else { riskLabel = 'low'; riskColor = 'card-green'; }

        // AI巡检覆盖率（基于传感器在线状态推算）
        var aiCoverage = cachedSystemStatus.sensors_active ? '96.8' : '0.0';

        // 构建统计卡片数据数组（四项新指标）
        var statsData = [
            {
                icon: 'fas fa-shield-alt',
                label: '当前风险等级',
                value: riskLevelMap[riskLabel] || '低',
                colorClass: riskColor
            },
            {
                icon: 'fas fa-bell',
                label: '活跃告警数',
                value: String(cachedSystemStatus.today_alert_count || data.today_detections || 0),
                colorClass: 'card-red'
            },
            {
                icon: 'fas fa-robot',
                label: 'AI巡检覆盖率',
                value: aiCoverage + '%',
                colorClass: 'card-green'
            },
            {
                icon: 'fas fa-signal',
                label: '系统在线状态',
                value: cachedSystemStatus.database_connected && cachedSystemStatus.model_loaded ? '正常运行' : '异常',
                colorClass: cachedSystemStatus.database_connected && cachedSystemStatus.model_loaded ? 'card-green' : 'card-red'
            }
        ];

        // 渲染统计卡片（带动画效果）
        renderStatsCardsAnimated(statsData);

        console.log('✅ 统计数据已更新');
    } catch (err) {
        console.error('❌ 获取统计数据失败:', err);
        // 网络异常时也填充占位符
        renderStatsCardsPlaceholder();
    }
}

/**
 * 渲染统计卡片占位符（API不可用时保证布局美观）
 */
function renderStatsCardsPlaceholder() {
    var statsData = [
        { icon: 'fas fa-shield-alt', label: '当前风险等级', value: '--', colorClass: '' },
        { icon: 'fas fa-bell', label: '活跃告警数', value: '--', colorClass: '' },
        { icon: 'fas fa-robot', label: 'AI巡检覆盖率', value: '--', colorClass: '' },
        { icon: 'fas fa-signal', label: '系统在线状态', value: '--', colorClass: '' }
    ];
    renderStatsCardsAnimated(statsData);
}

/**
 * 渲染右侧核心统计指标卡片（带数字变化动画）
 * @param {Array} statsData - 统计数据数组
 */
function renderStatsCardsAnimated(statsData) {
    var grid = document.getElementById('stats-card-grid');
    if (!grid) return;

    var html = '';
    for (var i = 0; i < statsData.length; i++) {
        var stat = statsData[i];
        var colorClass = stat.colorClass ? ' ' + stat.colorClass : '';
        html += '<div class="stat-card' + colorClass + '">' +
            '<div class="stat-card-icon"><i class="' + stat.icon + '"></i></div>' +
            '<div class="stat-card-info">' +
                '<span class="stat-card-label">' + stat.label + '</span>' +
                '<span class="stat-card-value stat-value-animated">' + stat.value + '</span>' +
            '</div>' +
        '</div>';
    }

    grid.innerHTML = html;

    // 触发动画
    var animatedEls = grid.querySelectorAll('.stat-value-animated');
    for (var j = 0; j < animatedEls.length; j++) {
        animateStatValue(animatedEls[j]);
    }
}

/**
 * 对统计数字元素执行轻微弹跳动画
 * @param {HTMLElement} el - 要动画的元素
 */
function animateStatValue(el) {
    el.style.transition = 'transform 0.3s ease-out, opacity 0.3s ease-out';
    el.style.transform = 'scale(0.8)';
    el.style.opacity = '0.5';

    setTimeout(function () {
        el.style.transform = 'scale(1.05)';
        el.style.opacity = '1';
        setTimeout(function () {
            el.style.transform = 'scale(1)';
        }, 150);
    }, 100);
}

/**
 * 格式化数字（添加千分位逗号）
 * @param {number} num - 要格式化的数字
 * @returns {string} 格式化后的字符串
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// ==================== 任务4：风险趋势图动态化 ====================

/**
 * 从 /risk-trend 接口获取近24小时风险趋势数据
 * 每60秒自动调用一次
 */
async function fetchRiskTrend() {
    try {
        var resp = await fetch('/risk-trend');
        var json = await resp.json();

        if (!json.success || !json.data) {
            console.warn('⚠️ 风险趋势接口返回失败，使用工程级初始数据兜底');
            // API失败时保持当前图表（已由初始数据渲染）
            return;
        }

        var data = json.data;
        var hours = data.hours || [];
        var riskScores = data.risk_scores || [];
        var alertCounts = data.alert_counts || [];

        // 【第五阶段-D1】检测API返回数据是否过于平坦（全为0或无变化），若是则使用初始波动数据
        var isFlat = riskScores.length === 0 || riskScores.every(function(v) { return v === riskScores[0]; });
        if (isFlat) {
            console.log('📊 API返回平坦数据，保持工程级初始波动数据');
            return;
        }

        // 记录当前小时索引（用于高亮显示）
        var now = new Date();
        var currentHour = String(now.getHours()).padStart(2, '0') + ':00';
        currentTrendHourIndex = hours.indexOf(currentHour);

        // 使用真实数据渲染图表
        renderRiskTrendChart(hours, riskScores, alertCounts);

        console.log('✅ 风险趋势图已更新（API真实数据）');
    } catch (err) {
        console.error('❌ 获取风险趋势数据失败，保持工程级初始数据:', err.message);
    }
}

/**
 * 【第五阶段-D1】使用工程级初始波动数据立即渲染风险趋势图
 * 在API数据返回前确保图表不为空白，曲线呈明显起伏状态
 */
function renderInitialRiskTrendChart() {
    // 设置当前小时索引
    var now = new Date();
    var currentHour = String(now.getHours()).padStart(2, '0') + ':00';
    currentTrendHourIndex = INITIAL_RISK_TREND_HOURS.indexOf(currentHour);

    // 使用初始数据渲染图表
    renderRiskTrendChart(
        INITIAL_RISK_TREND_HOURS.slice(),
        INITIAL_RISK_TREND_DATA.slice(),
        INITIAL_RISK_TREND_ALERTS.slice()
    );

    console.log('✅ 风险趋势图已使用工程级初始波动数据渲染（24点大幅波动）');
}

/**
 * 渲染或更新底部风险趋势折线图（增强版：平滑动画 + 科技风tooltip）
 * @param {Array} hours - 时间标签数组
 * @param {Array} riskScores - 风险分数数组
 * @param {Array} alertCounts - 告警数量数组
 */
function renderRiskTrendChart(hours, riskScores, alertCounts) {
    var canvas = document.getElementById('risk-trend-chart');
    if (!canvas) {
        console.warn('⚠️ 找不到图表Canvas元素');
        return;
    }

    // 销毁旧的Chart实例，防止内存泄漏
    if (riskTrendChartInstance) {
        riskTrendChartInstance.destroy();
        riskTrendChartInstance = null;
    }

    var ctx = canvas.getContext('2d');

    // 构建高亮背景色数组（当前小时高亮）
    var highlightBars = [];
    for (var i = 0; i < hours.length; i++) {
        highlightBars.push(i === currentTrendHourIndex ? 'rgba(0, 212, 255, 0.15)' : 'transparent');
    }

    riskTrendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours,
            datasets: [
                {
                    label: '风险分数',
                    data: riskScores,
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: hours.map(function(_, idx) { return idx === currentTrendHourIndex ? 6 : 3; }),
                    pointBackgroundColor: hours.map(function(_, idx) { return idx === currentTrendHourIndex ? '#ffffff' : '#00d4ff'; }),
                    pointBorderColor: hours.map(function(_, idx) { return idx === currentTrendHourIndex ? '#00d4ff' : '#00d4ff'; }),
                    pointBorderWidth: hours.map(function(_, idx) { return idx === currentTrendHourIndex ? 3 : 1; }),
                    pointHoverRadius: 6,
                    yAxisID: 'y',
                },
                {
                    label: '告警数量',
                    data: alertCounts,
                    borderColor: '#FF4757',
                    backgroundColor: 'rgba(255, 71, 87, 0.05)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: hours.map(function(_, idx) { return idx === currentTrendHourIndex ? 6 : 3; }),
                    pointBackgroundColor: hours.map(function(_, idx) { return idx === currentTrendHourIndex ? '#ffffff' : '#FF4757'; }),
                    pointBorderColor: hours.map(function(_, idx) { return idx === currentTrendHourIndex ? '#FF4757' : '#FF4757'; }),
                    pointBorderWidth: hours.map(function(_, idx) { return idx === currentTrendHourIndex ? 3 : 1; }),
                    pointHoverRadius: 6,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1200,
                easing: 'easeInOutQuart'
            },
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: '#7eb8d8',
                        font: { size: 11 },
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'circle',
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(6, 30, 65, 0.95)',
                    titleColor: '#00d4ff',
                    bodyColor: '#e8f4ff',
                    borderColor: 'rgba(0, 212, 255, 0.5)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    titleFont: { size: 13, weight: 'bold' },
                    bodyFont: { size: 12 },
                    displayColors: true,
                    callbacks: {
                        title: function(tooltipItems) {
                            return '🕐 ' + tooltipItems[0].label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: function(context) {
                            return context.tick && context.tick.label === hours[currentTrendHourIndex]
                                ? 'rgba(0, 212, 255, 0.3)'
                                : 'rgba(0, 212, 255, 0.08)';
                        },
                        drawBorder: false,
                    },
                    ticks: {
                        color: function(context) {
                            return context.index === currentTrendHourIndex ? '#00d4ff' : '#4a7a9b';
                        },
                        font: { size: 10, weight: function(context) { return context.index === currentTrendHourIndex ? 'bold' : 'normal'; } },
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '风险分数',
                        color: '#00d4ff',
                        font: { size: 11 },
                    },
                    grid: {
                        color: 'rgba(0, 212, 255, 0.06)',
                        drawBorder: false,
                    },
                    ticks: {
                        color: '#4a7a9b',
                        font: { size: 10 },
                    },
                    min: 0,
                    max: 100,
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '告警数量',
                        color: '#FF4757',
                        font: { size: 11 },
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        color: '#4a7a9b',
                        font: { size: 10 },
                    },
                    min: 0,
                },
            },
            layout: {
                padding: {
                    left: 5,
                    right: 5,
                    top: 5,
                    bottom: 5,
                }
            }
        }
    });
}

// ==================== 监控点渲染模块 ====================

/**
 * 渲染左侧监控点状态列表
 */
function renderCameraList() {
    var cameras = [
        { name: '太白山监测点', status: 'online' },
        { name: '佛坪保护区', status: 'online' },
        { name: '华山监测站', status: 'online' },
        { name: '周至保护区', status: 'online' },
        { name: '凤县林区', status: 'offline' },
        { name: '商洛监测站', status: 'online' },
        { name: '蓝田林区', status: 'online' },
        { name: '宁陕保护区', status: 'online' },
    ];

    var list = document.getElementById('camera-list');
    if (!list) return;

    var html = '';
    for (var i = 0; i < cameras.length; i++) {
        var cam = cameras[i];
        var statusText = cam.status === 'online' ? '在线' : '离线';
        html += '<div class="camera-item">' +
            '<span class="camera-dot ' + (cam.status === 'offline' ? 'offline' : '') + '"></span>' +
            '<span class="camera-name">' + cam.name + '</span>' +
            '<span class="camera-status ' + cam.status + '">' + statusText + '</span>' +
        '</div>';
    }

    list.innerHTML = html;
}

// ====================================================================
// 第六阶段C新增功能模块
// ====================================================================

// ==================== 模块A：Leaflet真实地图接入 ====================

/**
 * 初始化Leaflet地图
 * 使用深色地图瓦片，默认中心为秦岭区域（陕西附近），缩放级别7
 * 在地图上渲染模拟火情监测点标记
 */
function initLeafletMap() {
    try {
        var mapContainer = document.getElementById('leaflet-map');
        if (!mapContainer) {
            console.warn('⚠️ 找不到Leaflet地图容器元素');
            return;
        }

        // 检查Leaflet库是否已加载
        if (typeof L === 'undefined') {
            console.warn('⚠️ Leaflet库未加载，地图功能不可用');
            return;
        }

        // 强制确保容器尺寸正确（避免白块）
        mapContainer.style.width = '100%';
        mapContainer.style.height = '100%';

        // 创建Leaflet地图实例，扩大初始视野范围确保tiles全部加载
        // 使用fitBounds覆盖整个秦岭区域，比单独center+zoom能触发更多tile加载
        var qinlingBounds = L.latLngBounds(
            L.latLng(32.0, 105.5),   // 西南角（秦岭南麓+安康）
            L.latLng(35.0, 111.5)    // 东北角（秦岭北麓+华山）
        );

        leafletMap = L.map('leaflet-map', {
            center: [33.8, 108.5],        // 秦岭中心坐标
            zoom: 6,                       // 初始用较低缩放级别，视野更大
            zoomControl: true,             // 显示缩放控件
            attributionControl: true,      // 显示归属信息
            minZoom: 4,
            maxZoom: 15,
            maxBounds: L.latLngBounds(L.latLng(30, 103), L.latLng(37, 114)),  // 限制拖拽范围
            maxBoundsViscosity: 0.8
        });

        // 使用深色地图瓦片（CartoDB Dark Matter）
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(leafletMap);

        // 强制重绘地图，消除因容器尺寸计算不准确导致的白块
        // 延迟执行以确保容器完全渲染后再计算尺寸
        setTimeout(function () {
            if (leafletMap) {
                leafletMap.invalidateSize();
                // 使用fitBounds将视野适配到秦岭区域，确保周围tiles也被加载
                leafletMap.fitBounds(qinlingBounds, { padding: [20, 20] });
            }
        }, 300);

        // 二次重绘：确保所有tiles加载完毕后再次校准
        setTimeout(function () {
            if (leafletMap) {
                leafletMap.invalidateSize();
            }
        }, 1000);

        // 创建标记图层组（便于后续批量管理）
        markerLayerGroup = L.layerGroup().addTo(leafletMap);

        // 渲染初始火情监测点
        renderFireMarkers(QINLING_FIRE_POINTS);

        console.log('✅ Leaflet地图初始化完成，已渲染' + QINLING_FIRE_POINTS.length + '个监测点');
    } catch (err) {
        console.error('❌ Leaflet地图初始化失败:', err);
    }
}

/**
 * 在地图上渲染火情监测点标记
 * 根据风险等级使用不同颜色，高风险点增加闪烁动画
 * @param {Array} points - 火情点位数组
 */
function renderFireMarkers(points) {
    if (!leafletMap || !markerLayerGroup) return;

    try {
        // 清除旧标记
        markerLayerGroup.clearLayers();

        // 风险等级对应颜色映射
        var colorMap = {
            'critical': '#FF4757',    // 红色
            'high': '#FFA502',        // 橙色
            'medium': '#FFD700',      // 黄色
            'low': '#1E90FF'          // 蓝色
        };

        // 标记大小映射
        var sizeMap = {
            'critical': 14,
            'high': 12,
            'medium': 10,
            'low': 9
        };

        for (var i = 0; i < points.length; i++) {
            var point = points[i];
            var color = colorMap[point.level] || '#1E90FF';
            var size = sizeMap[point.level] || 9;

            // 构建CSS类名（高风险点增加闪烁动画）
            var markerClass = 'fire-marker';
            if (point.level === 'critical') {
                markerClass += ' blink-critical';
            } else if (point.level === 'high') {
                markerClass += ' blink-high';
            }

            // 创建自定义DivIcon标记
            var icon = L.divIcon({
                className: '',
                html: '<div class="' + markerClass + '" style="width:' + size + 'px;height:' + size + 'px;background:' + color + ';"></div>',
                iconSize: [size, size],
                iconAnchor: [size / 2, size / 2]
            });

            // 创建标记并添加到图层组
            var marker = L.marker([point.lat, point.lng], { icon: icon });

            // 构建弹出窗口内容（中文信息）
            var now = new Date();
            var timeStr = now.getFullYear() + '-' +
                String(now.getMonth() + 1).padStart(2, '0') + '-' +
                String(now.getDate()).padStart(2, '0') + ' ' +
                String(now.getHours()).padStart(2, '0') + ':' +
                String(now.getMinutes()).padStart(2, '0') + ':' +
                String(now.getSeconds()).padStart(2, '0');

            var popupContent = '<div class="popup-title">🔥 ' + point.name + '</div>' +
                '<div class="popup-info-row">' +
                    '<span class="popup-label">风险等级</span>' +
                    '<span class="popup-value level-' + point.level + '">' + getLevelText(point.level) + '</span>' +
                '</div>' +
                '<div class="popup-info-row">' +
                    '<span class="popup-label">风险分数</span>' +
                    '<span class="popup-value">' + point.score.toFixed(1) + '</span>' +
                '</div>' +
                '<div class="popup-info-row">' +
                    '<span class="popup-label">监测时间</span>' +
                    '<span class="popup-value">' + timeStr + '</span>' +
                '</div>' +
                '<div class="popup-info-row">' +
                    '<span class="popup-label">坐标</span>' +
                    '<span class="popup-value">' + point.lat.toFixed(2) + ', ' + point.lng.toFixed(2) + '</span>' +
                '</div>';

            marker.bindPopup(popupContent, {
                maxWidth: 280,
                className: 'fire-popup'
            });

            // 保存点位数据引用到marker（便于演示模式使用）
            marker.pointData = point;
            markerLayerGroup.addLayer(marker);
        }
    } catch (err) {
        console.error('❌ 渲染火情标记失败:', err);
    }
}

/**
 * 向地图添加单个新的火情标记点（演示模式用）
 * @param {Object} point - 火情点位对象 { name, level, score, lat, lng }
 */
function addFireMarker(point) {
    if (!leafletMap || !markerLayerGroup) return;

    try {
        var colorMap = {
            'critical': '#FF4757',
            'high': '#FFA502',
            'medium': '#FFD700',
            'low': '#1E90FF'
        };

        var color = colorMap[point.level] || '#FF4757';
        var markerClass = 'fire-marker';
        if (point.level === 'critical') {
            markerClass += ' blink-critical';
        } else if (point.level === 'high') {
            markerClass += ' blink-high';
        }

        var icon = L.divIcon({
            className: '',
            html: '<div class="' + markerClass + '" style="width:14px;height:14px;background:' + color + ';"></div>',
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });

        var marker = L.marker([point.lat, point.lng], { icon: icon });

        var now = new Date();
        var timeStr = now.getFullYear() + '-' +
            String(now.getMonth() + 1).padStart(2, '0') + '-' +
            String(now.getDate()).padStart(2, '0') + ' ' +
            String(now.getHours()).padStart(2, '0') + ':' +
            String(now.getMinutes()).padStart(2, '0') + ':' +
            String(now.getSeconds()).padStart(2, '0');

        var popupContent = '<div class="popup-title">🔥 ' + point.name + '</div>' +
            '<div class="popup-info-row">' +
                '<span class="popup-label">风险等级</span>' +
                '<span class="popup-value level-' + point.level + '">' + getLevelText(point.level) + '</span>' +
            '</div>' +
            '<div class="popup-info-row">' +
                '<span class="popup-label">风险分数</span>' +
                '<span class="popup-value">' + point.score.toFixed(1) + '</span>' +
            '</div>' +
            '<div class="popup-info-row">' +
                '<span class="popup-label">监测时间</span>' +
                '<span class="popup-value">' + timeStr + '</span>' +
            '</div>' +
            '<div class="popup-info-row">' +
                '<span class="popup-label">坐标</span>' +
                '<span class="popup-value">' + point.lat.toFixed(2) + ', ' + point.lng.toFixed(2) + '</span>' +
            '</div>';

        marker.bindPopup(popupContent, { maxWidth: 280 });
        markerLayerGroup.addLayer(marker);
    } catch (err) {
        console.error('❌ 添加火情标记失败:', err);
    }
}

// ==================== 模块B：实时告警推送增强 ====================

/**
 * 启动真实告警轮询
 * 每5秒从 /alert-history 接口轮询最新告警
 * 发现新告警时：插入告警流顶部 + 高亮闪烁动画 + 计数器+1
 * 替代原来的随机模拟数据生成
 */
function startRealtimeAlertSimulation() {
    // 初始化今日告警计数（从页面读取当前值）
    var countEl = document.getElementById('header-alert-count');
    if (countEl) {
        currentAlertCount = parseInt(countEl.textContent) || 0;
    }

    // 每5秒轮询真实告警数据
    timerRealtimeAlert = setInterval(function () {
        // 演示模式下由演示模式定时器控制，跳过普通轮询
        if (demoModeActive) return;
        pollRealtimeAlerts();
    }, 5000);

    console.log('✅ 真实告警轮询已启动（每5秒从SQLite读取）');
}

/**
 * 轮询 /alert-history 接口，检测新告警并插入告警流
 * 通过比较 lastKnownAlertId 判断是否有新告警
 */
async function pollRealtimeAlerts() {
    try {
        var resp = await fetch('/alert-history?limit=20');
        var json = await resp.json();

        if (!json.success || !json.data || json.data.length === 0) return;

        var alerts = json.data;

        // 按时间倒序排列（最新的在前）
        alerts.sort(function (a, b) {
            var timeA = a.detected_at || a.sent_at || '';
            var timeB = b.detected_at || b.sent_at || '';
            return timeB.localeCompare(timeA);
        });

        // 获取当前最新告警ID
        var latestAlert = alerts[0];
        var latestId = latestAlert.alert_id || latestAlert.id || '';

        // 首次运行：记录当前最新ID，不触发动画
        if (lastKnownAlertId === null) {
            lastKnownAlertId = latestId;
            return;
        }

        // 检测是否有新告警
        if (latestId !== lastKnownAlertId) {
            // 找出所有新告警（ID比 lastKnownAlertId 新的）
            var newAlerts = [];
            for (var i = 0; i < alerts.length; i++) {
                var aId = alerts[i].alert_id || alerts[i].id || '';
                if (aId === lastKnownAlertId) break;
                newAlerts.push(alerts[i]);
            }

            // 逐条插入新告警（最新先入，带动画高亮）
            for (var j = 0; j < newAlerts.length; j++) {
                insertRealAlertToStream(newAlerts[j]);
                incrementAlertCount();

                // 向趋势图添加数据点
                var alertLevel = newAlerts[j].risk_level || 'medium';
                var rawAlertScore = newAlerts[j].risk_score;
                var alertScore = (rawAlertScore > 0) ? rawAlertScore : INITIAL_RISK_TREND_DATA[new Date().getHours()];
                addDataPointToTrendChart(alertLevel, alertScore);

                // 【第三阶段-C2核心】真实告警→地图风险点联动
                addRealAlertToMap(newAlerts[j]);
            }

            // 更新最新告警ID
            lastKnownAlertId = latestId;

            console.log('📢 检测到' + newAlerts.length + '条新真实告警');
        }
    } catch (err) {
        // 静默失败，不影响页面
        console.warn('⚠️ 轮询真实告警失败:', err.message);
    }
}

/**
 * 将真实告警插入告警流顶部（带新告警高亮动画）
 * @param {Object} alert - 真实告警数据（来自 /alert-history API）
 */
function insertRealAlertToStream(alert) {
    var wrapper = document.getElementById('alert-scroll-wrapper');
    if (!wrapper) return;

    try {
        var level = alert.risk_level || 'low';
        var levelText = getLevelText(level);
        var score = alert.risk_score || 0;
        var detectedAt = alert.detected_at || alert.sent_at || '--';
        var timeShort = detectedAt.length > 10 ? detectedAt.substring(11, 19) : detectedAt;
        var location = alert.location || '未知位置';
        var alertId = alert.alert_id || ('#' + (alert.id || ''));
        var category = alert.detection_category || alert.category || '';
        var categoryText = getCategoryText(category);

        var html = '<div class="alert-stream-item alert-new-item alert-highlight level-' + level + '">' +
            '<div class="alert-item-header">' +
                '<span class="alert-level-tag tag-' + level + '">' + levelText + '</span>' +
                '<span class="alert-item-time">' + timeShort + '</span>' +
            '</div>' +
            '<div class="alert-item-location">📍 ' + location + '</div>' +
            (categoryText ? '<div class="alert-item-category" style="font-size:11px;color:#7eb8d8;margin-top:2px;">🔍 ' + categoryText + '</div>' : '') +
            '<div class="alert-item-score">⚠️ 风险: <span class="score-value">' + score.toFixed(1) + '</span> · 待处理</div>' +
            '<div style="font-size:10px;color:#4a7a9b;margin-top:2px;">' + alertId + '</div>' +
        '</div>';

        var tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        var newElement = tempDiv.firstChild;

        if (wrapper.firstChild) {
            wrapper.insertBefore(newElement, wrapper.firstChild);
        } else {
            wrapper.appendChild(newElement);
        }

        // 超过20条自动删除最旧数据
        var allItems = wrapper.querySelectorAll('.alert-stream-item');
        if (allItems.length > 20) {
            for (var i = 20; i < allItems.length; i++) {
                allItems[i].remove();
            }
        }

        // 2秒后移除高亮动画类（避免持续动画影响性能）
        setTimeout(function () {
            if (newElement && newElement.classList) {
                newElement.classList.remove('alert-new-item', 'alert-highlight');
            }
        }, 2500);
    } catch (err) {
        console.error('❌ 插入真实告警失败:', err);
    }
}

/**
 * 获取检测类别中文文本
 * @param {string} category - 检测类别英文标识
 * @returns {string} 中文文本
 */
function getCategoryText(category) {
    var map = {
        'fire': '火灾',
        'fire_smoke': '烟与火',
        'smoke': '烟雾',
        'normal': '正常'
    };
    return map[category] || category || '';
}

/**
 * 将新告警插入告警流顶部（带动画效果）
 * 超过20条自动删除最旧数据
 * @param {Object} alertData - 告警数据对象
 */
function insertAlertToStream(alertData) {
    var wrapper = document.getElementById('alert-scroll-wrapper');
    if (!wrapper) return;

    try {
        // 生成告警HTML（带进入动画和高亮闪烁）
        var html = buildSimulatedAlertItemHTML(alertData);

        // 插入到顶部
        var tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        var newElement = tempDiv.firstChild;

        if (wrapper.firstChild) {
            wrapper.insertBefore(newElement, wrapper.firstChild);
        } else {
            wrapper.appendChild(newElement);
        }

        // 超过20条自动删除最旧数据
        var allItems = wrapper.querySelectorAll('.alert-stream-item');
        if (allItems.length > 20) {
            for (var i = 20; i < allItems.length; i++) {
                allItems[i].remove();
            }
        }

        // 1.5秒后移除高亮动画类（避免持续动画影响性能）
        setTimeout(function () {
            if (newElement && newElement.classList) {
                newElement.classList.remove('alert-new-item', 'alert-highlight');
            }
        }, 2000);
    } catch (err) {
        console.error('❌ 插入告警失败:', err);
    }
}

/**
 * 今日告警数 +1 并更新页面显示
 */
function incrementAlertCount() {
    currentAlertCount++;
    var alertCountEl = document.getElementById('header-alert-count');
    if (alertCountEl) {
        alertCountEl.textContent = currentAlertCount;
        // 轻微闪烁效果
        alertCountEl.style.transition = 'color 0.3s, text-shadow 0.3s';
        alertCountEl.style.color = '#FF4757';
        alertCountEl.style.textShadow = '0 0 10px rgba(255, 71, 87, 0.5)';
        setTimeout(function () {
            alertCountEl.style.color = '';
            alertCountEl.style.textShadow = '';
        }, 800);
    }
}

/**
 * 向风险趋势图添加新数据点（模拟实时数据流入）
 * @param {string} level - 告警等级
 * @param {number} score - 风险分数
 */
function addDataPointToTrendChart(level, score) {
    if (!riskTrendChartInstance) return;

    try {
        var chart = riskTrendChartInstance;
        var now = new Date();
        var timeLabel = String(now.getHours()).padStart(2, '0') + ':' +
            String(now.getMinutes()).padStart(2, '0');

        // 添加新时间标签
        chart.data.labels.push(timeLabel);

        // 添加新的风险分数数据点
        chart.data.datasets[0].data.push(score);

        // 添加新的告警数量数据点（+1）
        var lastAlertCount = chart.data.datasets[1].data.length > 0
            ? chart.data.datasets[1].data[chart.data.datasets[1].data.length - 1]
            : 0;
        chart.data.datasets[1].data.push(lastAlertCount + 1);

        // 保持最多24个数据点
        if (chart.data.labels.length > 24) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
            chart.data.datasets[1].data.shift();
        }

        // 更新图表（带动画）
        chart.update('none');
    } catch (err) {
        console.error('❌ 趋势图添加数据点失败:', err);
    }
}

// ==================== 模块C：比赛演示模式 ====================

/**
 * 切换演示模式
 * 开启：自动每5秒生成高风险告警、地图新增红色闪烁点、告警数量快速增长、趋势图动态上涨
 * 关闭：恢复普通模式
 */
function toggleDemoMode() {
    try {
        var btn = document.getElementById('demo-mode-btn');
        var container = document.querySelector('.large-screen-container');

        if (!demoModeActive) {
            // ===== 开启演示模式 =====
            demoModeActive = true;

            // 按钮状态更新
            if (btn) {
                btn.classList.add('active');
                btn.querySelector('span').textContent = '关闭演示';
                btn.querySelector('i').className = 'fas fa-stop-circle';
            }

            // 整体容器添加演示模式类（触发高风险视觉效果）
            if (container) {
                container.classList.add('demo-active');
            }

            // 启动演示模式定时器：每1秒生成高风险告警（高频刷屏）
            timerDemoMode = setInterval(function () {
                if (!demoModeActive) return;

                // 每次生成2~3条告警（快速刷屏效果）
                var alertCount = 2 + Math.floor(Math.random() * 2);
                for (var di = 0; di < alertCount; di++) {
                    generateAndInsertAlert('demo');
                }

                // 地图每次新增1~2个红色闪烁点（高频出现）
                addDemoFirePoint();
                if (Math.random() < 0.5) {
                    addDemoFirePoint();
                }

                // 更新统计卡片（模拟活跃告警数快速增长）
                updateDemoStatsCards();
            }, 1000);

            // 风险趋势图快速波动定时器（每800ms刷新一次，产生剧烈波动效果）
            timerDemoTrend = setInterval(function () {
                if (!demoModeActive) return;
                demoRapidTrendUpdate();
            }, 800);

            // 立即执行一次（开屏即冲击）
            for (var initI = 0; initI < 3; initI++) {
                generateAndInsertAlert('demo');
            }
            addDemoFirePoint();
            addDemoFirePoint();
            demoRapidTrendUpdate();

            console.log('🚀 演示模式已开启');
        } else {
            // ===== 关闭演示模式 =====
            demoModeActive = false;

            // 按钮状态恢复
            if (btn) {
                btn.classList.remove('active');
                btn.querySelector('span').textContent = '演示模式';
                btn.querySelector('i').className = 'fas fa-rocket';
            }

            // 移除演示模式视觉效果
            if (container) {
                container.classList.remove('demo-active');
            }

            // 停止演示模式定时器
            if (timerDemoMode) {
                clearInterval(timerDemoMode);
                timerDemoMode = null;
            }
            if (timerDemoTrend) {
                clearInterval(timerDemoTrend);
                timerDemoTrend = null;
            }

            console.log('⏹️ 演示模式已关闭');
        }
    } catch (err) {
        console.error('❌ 切换演示模式失败:', err);
    }
}

/**
 * 【第三阶段-C2核心函数】将真实告警添加到地图上
 * 
 * 流程：读取告警location → 查找坐标映射 → 创建Marker → 添加风险圈动画 → 管理生命周期
 * 
 * @param {Object} alert - 真实告警数据（来自 /alert-history API）
 *        alert.location   - 区域名称（如"太白山北坡"）
 *        alert.risk_level - 风险等级（critical/high/medium/low）
 *        alert.risk_score - 风险分数（0-100）
 *        alert.alert_id   - 告警唯一ID
 *        alert.detection_category - 检测类别
 */
function addRealAlertToMap(alert) {
    if (!leafletMap) return;

    try {
        var alertId = alert.alert_id || alert.id || '';
        // 防止同一告警重复添加
        if (alertId && processedAlertIds[alertId]) return;
        if (alertId) processedAlertIds[alertId] = true;

        var location = alert.location || '秦岭山区';
        var level = alert.risk_level || 'medium';
        var rawMapScore = alert.risk_score;
        var score = (rawMapScore > 0) ? rawMapScore : INITIAL_RISK_TREND_DATA[new Date().getHours()];

        // 1. 查找区域坐标（精确匹配 → 模糊匹配 → 随机偏移）
        var coords = LOCATION_COORDS[location];
        if (!coords) {
            // 模糊匹配：遍历映射表查找包含关键词的区域
            var keys = Object.keys(LOCATION_COORDS);
            for (var k = 0; k < keys.length; k++) {
                if (location.indexOf(keys[k]) !== -1 || keys[k].indexOf(location) !== -1) {
                    coords = LOCATION_COORDS[keys[k]];
                    break;
                }
            }
        }
        if (!coords) {
            // 兜底：秦岭中心 + 小幅随机偏移（避免重叠）
            coords = {
                lat: 33.8 + (Math.random() - 0.5) * 0.6,
                lng: 108.5 + (Math.random() - 0.5) * 2.0
            };
        }

        // 2. 风险等级对应颜色
        var colorMap = {
            'critical': '#FF4757',
            'high':     '#FFA502',
            'medium':   '#FFD700',
            'low':      '#1E90FF'
        };
        var color = colorMap[level] || '#FFD700';

        // 3. 风险圈半径（根据等级）
        var radiusMap = {
            'critical': 18000,
            'high':     14000,
            'medium':   10000,
            'low':      7000
        };
        var radius = radiusMap[level] || 10000;

        // 4. 创建风险圈（半透明填充 + 边框）
        var riskCircle = L.circle([coords.lat, coords.lng], {
            radius: radius,
            color: color,
            fillColor: color,
            fillOpacity: 0.15,
            weight: 2,
            opacity: 0.6,
            className: 'risk-circle-anim'
        }).addTo(leafletMap);

        // 5. 创建扩散波纹圈（从中心向外扩散，然后消失）
        var rippleCircle = L.circle([coords.lat, coords.lng], {
            radius: 500,
            color: color,
            fillColor: 'transparent',
            weight: 3,
            opacity: 0.9,
            className: 'ripple-circle'
        }).addTo(leafletMap);

        // 6. 创建Marker（高风险带呼吸光）
        var markerSize = level === 'critical' ? 16 : (level === 'high' ? 14 : 11);
        var markerClass = 'fire-marker real-alert-marker';
        if (level === 'critical') {
            markerClass += ' blink-critical real-alert-glow-critical';
        } else if (level === 'high') {
            markerClass += ' blink-high real-alert-glow-high';
        }

        var icon = L.divIcon({
            className: '',
            html: '<div class="' + markerClass + '" style="width:' + markerSize + 'px;height:' + markerSize + 'px;background:' + color + ';"></div>',
            iconSize: [markerSize, markerSize],
            iconAnchor: [markerSize / 2, markerSize / 2]
        });

        var marker = L.marker([coords.lat, coords.lng], { icon: icon });

        // 7. 弹出窗口（真实告警信息）
        var detectedAt = alert.detected_at || alert.sent_at || '';
        var category = alert.detection_category || alert.category || '';
        var categoryText = getCategoryText(category);

        var popupHtml = '<div class="popup-title">🔥 ' + location + '</div>' +
            '<div style="font-size:11px;color:#FF4757;font-weight:bold;margin-bottom:6px;">⚠️ 真实告警</div>' +
            '<div class="popup-info-row">' +
                '<span class="popup-label">风险等级</span>' +
                '<span class="popup-value level-' + level + '">' + getLevelText(level) + '</span>' +
            '</div>' +
            '<div class="popup-info-row">' +
                '<span class="popup-label">风险分数</span>' +
                '<span class="popup-value">' + score.toFixed(1) + '</span>' +
            '</div>' +
            (categoryText ? '<div class="popup-info-row">' +
                '<span class="popup-label">检测类别</span>' +
                '<span class="popup-value">' + categoryText + '</span>' +
            '</div>' : '') +
            '<div class="popup-info-row">' +
                '<span class="popup-label">检测时间</span>' +
                '<span class="popup-value">' + detectedAt + '</span>' +
            '</div>' +
            '<div class="popup-info-row">' +
                '<span class="popup-label">坐标</span>' +
                '<span class="popup-value">' + coords.lat.toFixed(2) + ', ' + coords.lng.toFixed(2) + '</span>' +
            '</div>';

        marker.bindPopup(popupHtml, { maxWidth: 280 });
        marker.addTo(leafletMap);

        // 8. 自动打开弹出窗口（让评委看到新告警出现）
        setTimeout(function() {
            marker.openPopup();
        }, 300);

        // 9. 扩散波纹动画：用定时器模拟从中心向外扩散
        var rippleInterval = setInterval(function() {
            try {
                var currentRadius = rippleCircle.getRadius();
                if (currentRadius < radius * 1.5) {
                    rippleCircle.setRadius(currentRadius + 800);
                    rippleCircle.setStyle({ opacity: Math.max(0, 0.9 - currentRadius / (radius * 1.5)) });
                } else {
                    clearInterval(rippleInterval);
                    leafletMap.removeLayer(rippleCircle);
                }
            } catch(e) {
                clearInterval(rippleInterval);
            }
        }, 50);

        // 10. 记录到生命周期管理数组
        var markerRecord = {
            marker: marker,
            circle: riskCircle,
            ripple: rippleCircle,
            rippleInterval: rippleInterval,
            alertId: alertId,
            createdAt: Date.now()
        };
        realAlertMarkers.push(markerRecord);

        // 11. 生命周期管理：超过上限时移除最旧的
        trimRealAlertMarkers();

        // 12. 地图平移到新告警位置（轻柔动画）
        leafletMap.flyTo([coords.lat, coords.lng], 8, {
            duration: 1.2,
            easeLinearity: 0.25
        });

        // 【第三阶段-C4】触发聚焦联动效果
        // 地图容器边框聚焦 + 风险点marker强调 + popup已自动打开（步骤8）
        triggerAlertFocusSync(alert, marker, riskCircle);

        console.log('🗺️ 地图联动：新增真实告警风险点', location, level, score.toFixed(1));
    } catch (err) {
        console.error('❌ 地图联动失败:', err);
    }
}

/**
 * 管理真实告警Marker的生命周期
 * 保留最近 MAX_REAL_ALERT_MARKERS 个，超出的移除最旧的
 * 同时清理已过期（超过10分钟）的风险圈
 */
function trimRealAlertMarkers() {
    var now = Date.now();
    var EXPIRE_MS = 10 * 60 * 1000; // 10分钟过期

    // 先移除过期的
    for (var i = realAlertMarkers.length - 1; i >= 0; i--) {
        var record = realAlertMarkers[i];
        if (now - record.createdAt > EXPIRE_MS) {
            try {
                leafletMap.removeLayer(record.marker);
                leafletMap.removeLayer(record.circle);
                if (record.ripple) leafletMap.removeLayer(record.ripple);
                if (record.rippleInterval) clearInterval(record.rippleInterval);
            } catch(e) {}
            realAlertMarkers.splice(i, 1);
        }
    }

    // 再移除超出数量限制的（最旧的先移除）
    while (realAlertMarkers.length > MAX_REAL_ALERT_MARKERS) {
        var oldest = realAlertMarkers.shift();
        try {
            leafletMap.removeLayer(oldest.marker);
            leafletMap.removeLayer(oldest.circle);
            if (oldest.ripple) leafletMap.removeLayer(oldest.ripple);
            if (oldest.rippleInterval) clearInterval(oldest.rippleInterval);
        } catch(e) {}
    }
}

/**
 * 演示模式下向地图添加随机红色闪烁火情点
 * 经纬度在秦岭区域内随机生成
 */
function addDemoFirePoint() {
    try {
        // 秦岭区域随机坐标（经度106~111，纬度33~34.5）
        var lat = 33.0 + Math.random() * 1.5;
        var lng = 106.0 + Math.random() * 5.0;

        var demoNames = [
            '⚠️ 紧急火情预警点',
            '🔥 高温异常区域',
            '🚨 AI识别疑似火点',
            '⚠️ 传感器异常报警',
            '🔥 红外热源检测点'
        ];

        var point = {
            name: demoNames[Math.floor(Math.random() * demoNames.length)],
            level: 'critical',
            score: 85 + Math.random() * 14,
            lat: lat,
            lng: lng
        };

    // 添加到地图
    addFireMarker(point);

    // 【第三阶段-C4】演示模式也触发地图聚焦效果
    triggerMapFocusEffect('critical');

    console.log('🎯 演示模式：地图新增火情点', lat.toFixed(2), lng.toFixed(2));
    } catch (err) {
        console.error('❌ 演示模式添加火情点失败:', err);
    }
}

// ==================== 演示模式增强辅助函数 ====================

/**
 * 演示模式下快速更新统计卡片（模拟活跃告警数快速增长、风险等级跳动）
 * 每次由演示模式定时器调用
 */
function updateDemoStatsCards() {
    try {
        var grid = document.getElementById('stats-card-grid');
        if (!grid) return;

        var cards = grid.querySelectorAll('.stat-card');
        if (cards.length < 4) return;

        // 卡片1：当前风险等级 → 强制显示"极高"
        var riskValue = cards[0].querySelector('.stat-card-value');
        if (riskValue) {
            riskValue.textContent = '极高';
            riskValue.style.color = '#FF3838';
            riskValue.style.textShadow = '0 0 12px rgba(255, 56, 56, 0.4)';
        }
        cards[0].className = 'stat-card card-red';

        // 卡片2：活跃告警数 → 快速增长
        var alertValue = cards[1].querySelector('.stat-card-value');
        if (alertValue) {
            var currentVal = parseInt(alertValue.textContent) || currentAlertCount || 0;
            currentVal += 2 + Math.floor(Math.random() * 3); // 每次+2~4
            alertValue.textContent = currentVal;
            // 数字跳动动画
            alertValue.style.transition = 'transform 0.15s ease-out';
            alertValue.style.transform = 'scale(1.15)';
            setTimeout(function() {
                alertValue.style.transform = 'scale(1)';
            }, 150);
        }

        // 卡片3：AI巡检覆盖率 → 保持高值
        var aiValue = cards[2].querySelector('.stat-card-value');
        if (aiValue) {
            aiValue.textContent = '99.2%';
        }

        // 卡片4：系统在线状态 → 显示"应急响应"
        var sysValue = cards[3].querySelector('.stat-card-value');
        if (sysValue) {
            sysValue.textContent = '应急响应';
            sysValue.style.color = '#FF3838';
            sysValue.style.textShadow = '0 0 10px rgba(255, 56, 56, 0.3)';
        }
        cards[3].className = 'stat-card card-red';
    } catch (err) {
        console.warn('⚠️ 演示模式统计卡片更新失败:', err);
    }
}

/**
 * 演示模式下快速波动风险趋势图
 * 生成高幅波动数据（50~100区间），模拟应急状态下的剧烈风险变化
 */
function demoRapidTrendUpdate() {
    if (!riskTrendChartInstance) return;

    try {
        var chart = riskTrendChartInstance;
        var now = new Date();
        var timeLabel = String(now.getHours()).padStart(2, '0') + ':' +
            String(now.getMinutes()).padStart(2, '0') + ':' +
            String(now.getSeconds()).padStart(2, '0');

        // 生成高幅波动的风险分数（55~99，明显高于正常模式）
        var lastScore = chart.data.datasets[0].data.length > 0
            ? chart.data.datasets[0].data[chart.data.datasets[0].data.length - 1]
            : 70;
        // 在上一个值基础上大幅跳动（±15~30）
        var delta = (Math.random() - 0.35) * 35; // 偏向上升
        var newScore = Math.max(50, Math.min(99, lastScore + delta));

        // 添加新数据点
        chart.data.labels.push(timeLabel);
        chart.data.datasets[0].data.push(newScore);

        // 告警数量也快速增加
        var lastAlertCount = chart.data.datasets[1].data.length > 0
            ? chart.data.datasets[1].data[chart.data.datasets[1].data.length - 1]
            : 0;
        chart.data.datasets[1].data.push(lastAlertCount + 2 + Math.floor(Math.random() * 3));

        // 保持最多24个数据点
        if (chart.data.labels.length > 24) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
            chart.data.datasets[1].data.shift();
        }

        // 无动画更新（快速刷新时关闭动画避免卡顿）
        chart.update('none');
    } catch (err) {
        console.warn('⚠️ 演示模式趋势图更新失败:', err);
    }
}

// ==================== 第三阶段-C4：新告警聚焦优化 ====================

/**
 * 触发地图容器聚焦效果
 * 新告警出现时，地图边框亮一下，青蓝/红橙光微增强，1.5秒后恢复
 * @param {string} level - 风险等级（critical/high/medium/low）
 */
function triggerMapFocusEffect(level) {
    var mapPanel = document.querySelector('.map-panel');
    if (!mapPanel) return;

    // 根据等级选择聚焦类
    var focusClass = (level === 'critical') ? 'map-panel-focus-critical' : 'map-panel-focus';
    mapPanel.classList.add(focusClass);

    // 1.5秒后移除聚焦效果（恢复原状）
    setTimeout(function () {
        mapPanel.classList.remove('map-panel-focus', 'map-panel-focus-critical');
    }, 1500);
}

/**
 * 触发风险点Marker聚焦强调效果
 * marker轻微scale放大一次，风险圈亮度短暂增强，2秒后恢复正常
 * @param {L.Marker} marker - Leaflet marker对象
 * @param {L.Circle} riskCircle - 风险圈对象
 * @param {string} level - 风险等级
 */
function triggerMarkerFocusEffect(marker, riskCircle, level) {
    if (!marker) return;

    // 1. Marker放大效果：找到marker的DOM元素，添加bounce动画
    try {
        var markerEl = marker.getElement();
        if (markerEl) {
            var inner = markerEl.querySelector('.fire-marker') || markerEl;
            inner.classList.add('marker-focus-bounce');

            // 2秒后恢复：先移除bounce，播放恢复动画
            setTimeout(function () {
                inner.classList.remove('marker-focus-bounce');
                inner.classList.add('marker-focus-recover');
                // 0.5秒后移除恢复动画类
                setTimeout(function () {
                    inner.classList.remove('marker-focus-recover');
                }, 500);
            }, 2000);
        }
    } catch (e) {
        // marker DOM可能还未就绪，静默处理
    }

    // 2. 风险圈亮度增强：增加fillOpacity和strokeOpacity
    if (riskCircle) {
        try {
            var circleEl = riskCircle.getElement();
            if (circleEl) {
                circleEl.classList.add('risk-circle-focus');

                // 2秒后恢复
                setTimeout(function () {
                    circleEl.classList.remove('risk-circle-focus');
                    circleEl.classList.add('risk-circle-focus-recover');
                    // 1秒后移除恢复类
                    setTimeout(function () {
                        circleEl.classList.remove('risk-circle-focus-recover');
                    }, 1000);
                }, 2000);
            }
        } catch (e) {
            // SVG元素可能不可用，静默处理
        }
    }
}

/**
 * 告警流新增时的完整聚焦联动
 * 同步触发：地图容器聚焦 + 风险点强调 + popup自动打开
 * 实现"数据流 → 地图响应"的联动感
 * @param {Object} alert - 告警数据
 * @param {L.Marker} marker - 地图marker（可选）
 * @param {L.Circle} riskCircle - 风险圈（可选）
 */
function triggerAlertFocusSync(alert, marker, riskCircle) {
    var level = alert.risk_level || alert.level || 'medium';

    // 1. 地图容器边框聚焦
    triggerMapFocusEffect(level);

    // 2. 风险点Marker强调（如果有）
    if (marker) {
        triggerMarkerFocusEffect(marker, riskCircle, level);
    }
}

// ==================== 演示模式告警生成函数 ====================

/**
 * 生成并插入模拟告警（仅演示模式使用）
 * 从真实SQLite数据中随机选取位置和描述，生成高风险告警条目插入告警流
 * @param {string} mode - 模式标识（'demo'表示演示模式）
 */
function generateAndInsertAlert(mode) {
    try {
        var now = new Date();
        var timeStr = String(now.getHours()).padStart(2, '0') + ':' +
            String(now.getMinutes()).padStart(2, '0') + ':' +
            String(now.getSeconds()).padStart(2, '0');

        // 随机选取地点和描述
        var location = ALERT_LOCATIONS[Math.floor(Math.random() * ALERT_LOCATIONS.length)];
        var description = ALERT_DESCRIPTIONS[Math.floor(Math.random() * ALERT_DESCRIPTIONS.length)];

        // 演示模式下生成高风险告警（critical占比更高，分数更高）
        var levelRand = Math.random();
        var level, score;
        if (levelRand < 0.55) {
            level = 'critical';
            score = 88 + Math.random() * 11;  // 88~99，更高危
        } else if (levelRand < 0.85) {
            level = 'high';
            score = 72 + Math.random() * 15;  // 72~87
        } else {
            level = 'medium';
            score = 55 + Math.random() * 15;  // 55~70
        }

        var alertId = '#DEMO-' + Date.now();

        var alertData = {
            id: alertId,
            level: level,
            score: score,
            time: timeStr,
            location: location,
            description: description
        };

        // 插入告警流顶部
        insertAlertToStream(alertData);

        // 更新今日告警计数
        incrementAlertCount();

        // 向趋势图添加数据点
        addDataPointToTrendChart(level, score);

        console.log('📢 演示模式告警已生成:', location, level, score.toFixed(1));
    } catch (err) {
        console.error('❌ 生成演示告警失败:', err);
    }
}
