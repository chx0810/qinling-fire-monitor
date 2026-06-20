"""
秦岭火灾预警系统 - SQLite数据库持久化模块
所有数据库读写统一封装，api_server.py只调用函数
"""

import sqlite3
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# 数据库文件路径（位于后端服务模块目录下）
DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "fire_alarm.db"

# 线程本地存储，确保每个线程使用独立连接
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """获取当前线程的数据库连接（线程安全）"""
    if not hasattr(_local, 'connection') or _local.connection is None:
        _local.connection = sqlite3.connect(
            str(DB_PATH),
            check_same_thread=False,
            timeout=10
        )
        _local.connection.row_factory = sqlite3.Row
        _local.connection.execute("PRAGMA journal_mode=WAL")
        _local.connection.execute("PRAGMA foreign_keys=ON")
    return _local.connection


def init_database() -> None:
    """初始化数据库，创建所有表（幂等操作，可重复调用）"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 创建detections表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_name TEXT DEFAULT '',
                prediction TEXT DEFAULT '',
                confidence REAL DEFAULT 0.0,
                probabilities TEXT DEFAULT '{}',
                heatmap TEXT DEFAULT '',
                timestamp TEXT DEFAULT '',
                risk_score REAL DEFAULT 0.0,
                risk_level TEXT DEFAULT 'low'
            )
        """)

        # 创建alerts表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_id INTEGER DEFAULT NULL,
                alert_id TEXT DEFAULT '',
                risk_score REAL DEFAULT 0.0,
                risk_level TEXT DEFAULT 'low',
                detection_type TEXT DEFAULT '',
                location TEXT DEFAULT '',
                detected_at TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                acknowledged_by TEXT DEFAULT '',
                acknowledged_time TEXT DEFAULT '',
                resolved_time TEXT DEFAULT '',
                sent_at TEXT DEFAULT ''
            )
        """)

        # 创建sensors表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                temperature REAL DEFAULT 0.0,
                humidity REAL DEFAULT 0.0,
                wind_speed REAL DEFAULT 0.0,
                air_quality REAL DEFAULT 0.0,
                location TEXT DEFAULT '',
                timestamp TEXT DEFAULT ''
            )
        """)

        conn.commit()
        print("✅ 数据库初始化成功，表已创建/确认存在")
        print(f"   数据库路径: {DB_PATH}")

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()


# ==================== detections表操作 ====================

def save_detection(
    image_name: str = '',
    prediction: str = '',
    confidence: float = 0.0,
    probabilities: dict = None,
    heatmap: str = '',
    timestamp: str = '',
    risk_score: float = 0.0,
    risk_level: str = 'low'
) -> Optional[int]:
    """保存检测记录到数据库，返回新记录的id"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        prob_json = json.dumps(probabilities or {}, ensure_ascii=False)
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO detections (image_name, prediction, confidence, probabilities, heatmap, timestamp, risk_score, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (image_name, prediction, confidence, prob_json, heatmap, timestamp, risk_score, risk_level))

        conn.commit()
        record_id = cursor.lastrowid
        print(f"✅ 检测记录已保存，ID: {record_id}")
        return record_id

    except Exception as e:
        print(f"❌ 保存检测记录失败: {e}")
        return None


def get_detection_history(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """获取检测历史记录，按时间倒序"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM detections
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = cursor.fetchall()
        results = []
        for row in rows:
            item = dict(row)
            # 解析JSON字段
            try:
                item['probabilities'] = json.loads(item.get('probabilities', '{}'))
            except (json.JSONDecodeError, TypeError):
                item['probabilities'] = {}
            results.append(item)

        return results

    except Exception as e:
        print(f"❌ 获取检测历史失败: {e}")
        return []


def get_detection_by_id(detection_id: int) -> Optional[Dict[str, Any]]:
    """根据ID获取单条检测记录"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM detections WHERE id = ?", (detection_id,))
        row = cursor.fetchone()
        if row:
            item = dict(row)
            try:
                item['probabilities'] = json.loads(item.get('probabilities', '{}'))
            except (json.JSONDecodeError, TypeError):
                item['probabilities'] = {}
            return item
        return None

    except Exception as e:
        print(f"❌ 获取检测记录失败: {e}")
        return None


def get_detection_count() -> int:
    """获取检测记录总数"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM detections")
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"❌ 获取检测计数失败: {e}")
        return 0


def get_today_detection_count() -> int:
    """获取今日检测数量"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM detections WHERE timestamp LIKE ?", (f"{today}%",))
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"❌ 获取今日检测计数失败: {e}")
        return 0


def get_today_high_risk_count() -> int:
    """获取今日高风险检测数量"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT COUNT(*) FROM detections WHERE timestamp LIKE ? AND (risk_level = 'critical' OR risk_level = 'high')",
            (f"{today}%",)
        )
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"❌ 获取今日高风险计数失败: {e}")
        return 0


def get_avg_confidence() -> float:
    """获取平均置信度"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(confidence) FROM detections")
        result = cursor.fetchone()[0]
        return round(result, 4) if result else 0.0
    except Exception as e:
        print(f"❌ 获取平均置信度失败: {e}")
        return 0.0


def get_risk_trend(hours: int = 24) -> List[Dict[str, Any]]:
    """获取最近N小时的风险趋势数据"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # 按小时分组统计平均风险分数
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00', timestamp) as hour_bucket,
                AVG(risk_score) as avg_score,
                COUNT(*) as count,
                MAX(risk_level) as max_level
            FROM detections
            WHERE timestamp >= datetime('now', ? || ' hours')
            GROUP BY hour_bucket
            ORDER BY hour_bucket ASC
        """, (f"-{hours}",))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except Exception as e:
        print(f"❌ 获取风险趋势失败: {e}")
        return []


def get_today_resolved_alert_count() -> int:
    """获取今日已解决告警数量"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT COUNT(*) FROM alerts WHERE status = 'resolved' AND sent_at LIKE ?",
            (f"{today}%",)
        )
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"❌ 获取今日已解决告警计数失败: {e}")
        return 0


def get_alert_count_by_hour(hours: int = 24) -> List[Dict[str, Any]]:
    """获取最近N小时按小时聚合的告警数量"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00', detected_at) as hour_bucket,
                COUNT(*) as alert_count
            FROM alerts
            WHERE detected_at >= datetime('now', ? || ' hours')
            GROUP BY hour_bucket
            ORDER BY hour_bucket ASC
        """, (f"-{hours}",))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ 获取告警按小时统计失败: {e}")
        return []


def get_risk_score_by_hour(hours: int = 24) -> List[Dict[str, Any]]:
    """获取最近N小时按小时聚合的平均风险分数"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00', timestamp) as hour_bucket,
                AVG(risk_score) as avg_risk_score
            FROM detections
            WHERE timestamp >= datetime('now', ? || ' hours')
            GROUP BY hour_bucket
            ORDER BY hour_bucket ASC
        """, (f"-{hours}",))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ 获取风险分数按小时统计失败: {e}")
        return []


# ==================== alerts表操作 ====================

def save_alert(
    alert_id: str = '',
    detection_id: int = None,
    risk_score: float = 0.0,
    risk_level: str = 'low',
    detection_type: str = '',
    location: str = '',
    detected_at: str = '',
    sent_at: str = ''
) -> Optional[int]:
    """保存告警记录到数据库"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if not sent_at:
            sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO alerts (alert_id, detection_id, risk_score, risk_level, detection_type, location, detected_at, status, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (alert_id, detection_id, risk_score, risk_level, detection_type, location, detected_at, sent_at))

        conn.commit()
        record_id = cursor.lastrowid
        print(f"✅ 告警记录已保存，DB ID: {record_id}, Alert ID: {alert_id}")
        return record_id

    except Exception as e:
        print(f"❌ 保存告警记录失败: {e}")
        return None


def get_alert_history(limit: int = 50, status: str = None) -> List[Dict[str, Any]]:
    """获取告警历史记录"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT * FROM alerts
                WHERE status = ?
                ORDER BY id DESC
                LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT * FROM alerts
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except Exception as e:
        print(f"❌ 获取告警历史失败: {e}")
        return []


def get_alert_by_id(alert_db_id: int) -> Optional[Dict[str, Any]]:
    """根据数据库ID获取告警记录"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_db_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ 获取告警记录失败: {e}")
        return None


def acknowledge_alert(alert_db_id: int, acknowledged_by: str = 'admin') -> bool:
    """确认告警"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ack_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE alerts
            SET status = 'acknowledged', acknowledged_by = ?, acknowledged_time = ?
            WHERE id = ? AND status = 'pending'
        """, (acknowledged_by, ack_time, alert_db_id))

        conn.commit()
        if cursor.rowcount > 0:
            print(f"✅ 告警 {alert_db_id} 已确认，确认人: {acknowledged_by}")
            return True
        else:
            print(f"⚠️ 告警 {alert_db_id} 不存在或状态不是pending")
            return False

    except Exception as e:
        print(f"❌ 确认告警失败: {e}")
        return False


def resolve_alert(alert_db_id: int) -> bool:
    """解决告警"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        resolve_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE alerts
            SET status = 'resolved', resolved_time = ?
            WHERE id = ? AND status IN ('pending', 'acknowledged')
        """, (resolve_time, alert_db_id))

        conn.commit()
        if cursor.rowcount > 0:
            print(f"✅ 告警 {alert_db_id} 已解决")
            return True
        else:
            print(f"⚠️ 告警 {alert_db_id} 不存在或状态不正确")
            return False

    except Exception as e:
        print(f"❌ 解决告警失败: {e}")
        return False


def get_today_alert_count() -> int:
    """获取今日告警数量"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE sent_at LIKE ?", (f"{today}%",))
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"❌ 获取今日告警计数失败: {e}")
        return 0


# ==================== sensors表操作 ====================

def save_sensor_data(
    temperature: float = 0.0,
    humidity: float = 0.0,
    wind_speed: float = 0.0,
    air_quality: float = 0.0,
    location: str = '',
    timestamp: str = ''
) -> Optional[int]:
    """保存传感器数据"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO sensors (temperature, humidity, wind_speed, air_quality, location, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (temperature, humidity, wind_speed, air_quality, location, timestamp))

        conn.commit()
        return cursor.lastrowid

    except Exception as e:
        print(f"❌ 保存传感器数据失败: {e}")
        return None


def get_sensor_history(hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
    """获取传感器历史数据"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sensors
            WHERE timestamp >= datetime('now', ? || ' hours')
            ORDER BY id DESC
            LIMIT ?
        """, (f"-{hours}", limit))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except Exception as e:
        print(f"❌ 获取传感器历史失败: {e}")
        return []


def get_db_stats() -> Dict[str, Any]:
    """获取数据库统计信息"""
    try:
        return {
            "detection_count": get_detection_count(),
            "alert_count": get_today_alert_count(),
            "today_detection_count": get_today_detection_count(),
            "today_high_risk_count": get_today_high_risk_count(),
            "avg_confidence": get_avg_confidence(),
            "db_path": str(DB_PATH),
            "db_size_kb": round(os.path.getsize(DB_PATH) / 1024, 2) if DB_PATH.exists() else 0
        }
    except Exception as e:
        print(f"❌ 获取数据库统计失败: {e}")
        return {}


# 模块加载时自动初始化数据库
print("📦 数据库模块加载中...")
init_database()
