"""
虚拟传感器管理器
模拟秦岭山区的环境传感器数据
"""

# 导入Python标准库
import random  # 随机数生成，用于模拟传感器数据波动
import time  # 时间相关操作，用于延时和计时
import json  # JSON数据处理，用于保存历史数据
from datetime import datetime , timedelta  # 日期时间处理
from typing import List , Dict , Any  # 类型注解
from pathlib import Path  # 面向对象的文件路径操作
import hashlib  # 用于基于时间戳生成确定性随机种子

# 固定全局随机种子，保证每次演示数据一致
DEMO_RANDOM_SEED = 42  # 演示用固定随机种子
random.seed(DEMO_RANDOM_SEED)  # 设置全局随机种子

class VirtualSensorManager :
    """虚拟传感器管理器"""
    
    def __init__(self , location : str = "秦岭北麓-监测点1") :
        """初始化传感器管理器"""
        self.location = location  # 传感器位置
        self.sensor_history = []  # 传感器历史数据列表
        self.risk_history = []  # 风险评估历史列表
        self.last_detection_time = None  # 最后检测时间，初始化为None
        
        # 传感器基础配置字典
        self.sensor_config = {
            'temperature' : {  # 温度传感器配置
                'base' : 22.0 ,  # 基础温度值
                'range' : (-5 , 15) ,  # 波动范围（最小值，最大值）
                'trend' : 'cyclic' ,  # 趋势类型：循环
                'unit' : '°C'  # 单位：摄氏度
            } ,
            'humidity' : {  # 湿度传感器配置
                'base' : 65.0 ,  # 基础湿度值
                'range' : (10 , 30) ,  # 波动范围
                'trend' : 'cyclic' ,  # 趋势类型：循环
                'unit' : '%'  # 单位：百分比
            } ,
            'wind_speed' : {  # 风速传感器配置
                'base' : 2.5 ,  # 基础风速值
                'range' : (0 , 6) ,  # 波动范围
                'trend' : 'random' ,  # 趋势类型：随机
                'unit' : 'm/s'  # 单位：米/秒
            } ,
            'air_quality' : {  # 空气质量传感器配置
                'base' : 45.0 ,  # 基础AQI值
                'range' : (10 , 30) ,  # 波动范围
                'trend' : 'random' ,  # 趋势类型：随机
                'unit' : 'AQI'  # 单位：空气质量指数
            }
        }
        
        # 秦岭气象特征配置
        self.qinling_weather = {
            'day_temp_range' : (18 , 28) ,  # 白天温度范围
            'night_temp_range' : (8 , 15) ,  # 夜间温度范围
            'humidity_range' : (55 , 85) ,  # 湿度范围
            'wind_day' : (1 , 4) ,  # 白天风速范围
            'wind_night' : (0.5 , 2) ,  # 夜间风速范围
            'seasonal_adjust' : {  # 季节调整参数
                'spring' : {'temp' : -2 , 'humidity' : 10} ,  # 春季调整
                'summer' : {'temp' : 8 , 'humidity' : 15} ,  # 夏季调整
                'autumn' : {'temp' : 0 , 'humidity' : 5} ,  # 秋季调整
                'winter' : {'temp' : -5 , 'humidity' : -5}  # 冬季调整
            }
        }
        
        # 初始化历史数据
        self._initialize_history()  # 调用历史数据初始化方法
    
    def _initialize_history(self) :
        """初始化历史数据"""
        now = datetime.now()  # 获取当前时间
        
        for i in range(50) :  # 循环50次，生成50条历史数据
            timestamp = now - timedelta(minutes = i * 30)  # 每30分钟一条数据，从当前时间往前推
            data = self._generate_sensor_data(timestamp)  # 生成指定时间戳的传感器数据
            self.sensor_history.append(data)  # 将数据添加到历史列表
    
    def _generate_sensor_data(self , timestamp : datetime = None) -> Dict[str , Any] :
        """生成模拟传感器数据（基于时间戳确定性生成，保证相同时间戳产生相同数据）"""
        if timestamp is None :  # 如果时间戳为None
            timestamp = datetime.now()  # 使用当前时间
        
        # 基于时间戳生成确定性随机种子，确保相同时间戳产生相同数据
        # 将时间戳精确到分钟级别（同一分钟内数据相同）
        seed_str = f"{timestamp.year}-{timestamp.month}-{timestamp.day}-{timestamp.hour}-{timestamp.minute}"
        local_seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8] , 16)
        local_random = random.Random(local_seed)  # 创建独立的随机数生成器
        
        # 获取时间特征
        hour = timestamp.hour  # 获取小时（0-23）
        month = timestamp.month  # 获取月份（1-12）
        
        # 确定季节
        if month in [3 , 4 , 5] :  # 3-5月为春季
            season = 'spring'  # 季节：春季
            season_adj = self.qinling_weather['seasonal_adjust']['spring']  # 春季调整参数
        elif month in [6 , 7 , 8] :  # 6-8月为夏季
            season = 'summer'  # 季节：夏季
            season_adj = self.qinling_weather['seasonal_adjust']['summer']  # 夏季调整参数
        elif month in [9 , 10 , 11] :  # 9-11月为秋季
            season = 'autumn'  # 季节：秋季
            season_adj = self.qinling_weather['seasonal_adjust']['autumn']  # 秋季调整参数
        else :  # 12-2月为冬季
            season = 'winter'  # 季节：冬季
            season_adj = self.qinling_weather['seasonal_adjust']['winter']  # 冬季调整参数
        
        # 日夜模式判断：6点到18点为白天
        is_daytime = 6 <= hour < 18
        
        # 生成温度数据
        if is_daytime :  # 如果是白天
            temp_range = self.qinling_weather['day_temp_range']  # 使用白天温度范围
        else :  # 如果是夜晚
            temp_range = self.qinling_weather['night_temp_range']  # 使用夜间温度范围
        
        # 计算温度：基础温度 + 季节调整
        temperature = local_random.uniform(*temp_range) + season_adj['temp']
        
        # 生成湿度数据
        # 基础湿度范围 + 季节调整
        humidity = local_random.uniform(*self.qinling_weather['humidity_range']) + season_adj['humidity']
        humidity = max(10 , min(95 , humidity))  # 限制湿度在10-95%之间
        
        # 生成风速数据
        if is_daytime :  # 如果是白天
            wind_range = self.qinling_weather['wind_day']  # 使用白天风速范围
        else :  # 如果是夜晚
            wind_range = self.qinling_weather['wind_night']  # 使用夜间风速范围
        
        wind_speed = local_random.uniform(*wind_range)  # 生成随机风速
        
        # 生成空气质量数据
        base_aqi = 30  # 基础AQI值
        
        # 风速越大，空气质量越好（风能吹散污染物）
        aqi_adjust = -wind_speed * 3
        
        # 湿度影响
        if humidity < 30 :  # 干燥天气
            aqi_adjust += 10  # 空气质量较差（容易扬尘）
        elif humidity > 80 :  # 潮湿天气
            aqi_adjust += 5  # 空气质量较差（雾气）
        
        # 计算空气质量指数，确保最小值不低于10
        air_quality = max(10 , base_aqi + aqi_adjust + local_random.uniform(-5 , 15))
        
        # 添加随机波动，模拟真实传感器的微小变化
        temperature += local_random.uniform(-1 , 1)  # 温度波动±1°C
        humidity += local_random.uniform(-3 , 3)  # 湿度波动±3%
        wind_speed += local_random.uniform(-0.5 , 0.5)  # 风速波动±0.5m/s
        air_quality += local_random.uniform(-2 , 2)  # AQI波动±2
        
        # 返回传感器数据字典
        return {
            'temperature' : round(temperature , 1) ,  # 温度，保留1位小数
            'humidity' : round(humidity , 1) ,  # 湿度，保留1位小数
            'wind_speed' : round(wind_speed , 1) ,  # 风速，保留1位小数
            'air_quality' : round(air_quality) ,  # 空气质量，整数
            'location' : self.location ,  # 位置信息
            'timestamp' : timestamp.isoformat() ,  # 时间戳，ISO格式字符串
            'is_daytime' : is_daytime ,  # 是否为白天
            'season' : season  # 季节
        }
    
    def get_current_data(self) -> Dict[str , Any] :
        """获取当前传感器数据"""
        data = self._generate_sensor_data()  # 生成当前时间的数据
        
        # 保存到历史记录
        self.sensor_history.insert(0 , data)  # 插入到列表开头（最新数据在前）
        if len(self.sensor_history) > 200 :  # 限制历史记录数量为200条
            self.sensor_history = self.sensor_history[:200]  # 截取前200条
        
        return data  # 返回当前数据
    
    def get_history(self , hours : int = 24 , limit : int = 100) -> List[Dict[str , Any]] :
        """获取传感器历史数据"""
        cutoff_time = datetime.now() - timedelta(hours = hours)  # 计算截止时间
        
        history = []  # 初始化历史数据列表
        for data in self.sensor_history :  # 遍历所有历史数据
            try :
                # 将时间字符串转换为datetime对象
                data_time = datetime.fromisoformat(data['timestamp'].replace('Z' , ''))
                if data_time >= cutoff_time :  # 如果数据时间在截止时间之后
                    history.append(data)  # 添加到结果列表
            except :  # 如果时间转换失败
                continue  # 跳过这条数据
            
            if len(history) >= limit :  # 如果达到数量限制
                break  # 停止遍历
        
        return history  # 返回历史数据
    
    def simulate_fire_scenario(self) :
        """模拟火灾场景的传感器数据"""
        print("🔥 模拟火灾场景...")  # 打印开始消息
        
        # 修改温度传感器配置，模拟火灾影响
        self.sensor_config['temperature']['base'] = 42.0  # 设置高温基础值
        self.sensor_config['temperature']['range'] = (38 , 48)  # 设置高温范围
        
        # 修改湿度传感器配置，模拟火灾影响
        self.sensor_config['humidity']['base'] = 18.0  # 设置低湿度基础值
        self.sensor_config['humidity']['range'] = (15 , 25)  # 设置低湿度范围
        
        # 修改风速传感器配置，模拟火灾影响
        self.sensor_config['wind_speed']['base'] = 6.8  # 设置大风基础值
        self.sensor_config['wind_speed']['range'] = (5 , 9)  # 设置大风范围
        
        # 修改空气质量传感器配置，模拟火灾影响
        self.sensor_config['air_quality']['base'] = 156  # 设置差空气质量基础值
        self.sensor_config['air_quality']['range'] = (120 , 200)  # 设置差空气质量范围
        
        print("✅ 传感器已调整为火灾场景模式")  # 打印完成消息
    
    def reset_to_normal(self) :
        """重置传感器到正常状态"""
        print("🔄 重置传感器到正常状态...")  # 打印开始消息
        
        # 恢复所有传感器配置到正常值
        self.sensor_config = {
            'temperature' : {'base' : 22.0 , 'range' : (-5 , 15) , 'trend' : 'cyclic' , 'unit' : '°C'} ,
            'humidity' : {'base' : 65.0 , 'range' : (10 , 30) , 'trend' : 'cyclic' , 'unit' : '%'} ,
            'wind_speed' : {'base' : 2.5 , 'range' : (0 , 6) , 'trend' : 'random' , 'unit' : 'm/s'} ,
            'air_quality' : {'base' : 45.0 , 'range' : (10 , 30) , 'trend' : 'random' , 'unit' : 'AQI'}
        }
        
        print("✅ 传感器已重置")  # 打印完成消息
    
    def record_detection(self , detection_result : Dict[str , Any]) :
        """记录检测结果"""
        self.last_detection_time = datetime.now().isoformat()  # 更新最后检测时间
        
        # 记录风险评估
        if 'combined_risk' in detection_result :  # 如果检测结果包含风险评估
            risk_record = {  # 创建风险评估记录
                'timestamp' : self.last_detection_time ,  # 时间戳
                'risk_level' : detection_result['combined_risk'].get('level' , 'unknown') ,  # 风险等级
                'risk_score' : detection_result['combined_risk'].get('score' , 0) ,  # 风险分数
                'detection_class' : detection_result.get('class' , 'unknown') ,  # 检测类别
                'confidence' : detection_result.get('confidence' , 0)  # 置信度
            }
            
            self.risk_history.insert(0 , risk_record)  # 插入到风险历史开头
            if len(self.risk_history) > 100 :  # 限制历史记录数量为100条
                self.risk_history = self.risk_history[:100]  # 截取前100条
    
    def get_risk_history(self , limit : int = 50) -> List[Dict[str , Any]] :
        """获取风险评估历史"""
        return self.risk_history[:limit]  # 返回前limit条风险历史
    
    def save_history_to_file(self , filepath : str = "sensor_history.json") :
        """保存历史数据到文件"""
        try :
            history = {  # 创建历史数据字典
                'sensor_history' : self.sensor_history[:100] ,  # 传感器历史（前100条）
                'risk_history' : self.risk_history ,  # 风险评估历史
                'last_update' : datetime.now().isoformat()  # 最后更新时间
            }
            
            with open(filepath , 'w' , encoding = 'utf-8') as f :  # 打开文件（写入模式，UTF-8编码）
                json.dump(history , f , ensure_ascii = False , indent = 2)  # 写入JSON数据
            
            print(f"✅ 历史数据已保存到 {filepath}")  # 打印成功消息
            return True  # 返回成功标志
            
        except Exception as e :  # 捕获所有异常
            print(f"❌ 保存历史数据失败 : {e}")  # 打印错误消息
            return False  # 返回失败标志

# 测试函数
def test_sensors() :
    """测试虚拟传感器"""
    print("🧪 测试虚拟传感器...")  # 打印测试开始消息
    
    sensor_manager = VirtualSensorManager()  # 创建传感器管理器实例
    
    # 测试正常数据
    print("\n🌤️  正常模式传感器数据 : ")  # 打印测试标题
    for i in range(3) :  # 循环3次
        data = sensor_manager.get_current_data()  # 获取当前传感器数据
        print(f"  第{i+1}次读取 : ")  # 打印读取次数
        print(f"    温度 : {data['temperature']}°C")  # 打印温度
        print(f"    湿度 : {data['humidity']}%")  # 打印湿度
        print(f"    风速 : {data['wind_speed']}m/s")  # 打印风速
        print(f"    空气质量 : {data['air_quality']} AQI")  # 打印空气质量
        print()  # 打印空行
        time.sleep(1)  # 暂停1秒
    
    # 测试火灾场景
    print("\n🔥 模拟火灾场景 : ")  # 打印测试标题
    sensor_manager.simulate_fire_scenario()  # 模拟火灾场景
    
    fire_data = sensor_manager.get_current_data()  # 获取火灾场景数据
    print(f"  火灾场景数据 : ")  # 打印数据标题
    print(f"    温度 : {fire_data['temperature']}°C (高温预警 !)")  # 打印温度（带预警）
    print(f"    湿度 : {fire_data['humidity']}% (极度干燥 !)")  # 打印湿度（带预警）
    print(f"    风速 : {fire_data['wind_speed']}m/s (大风助燃 !)")  # 打印风速（带预警）
    print(f"    空气质量 : {fire_data['air_quality']} AQI (严重污染 !)")  # 打印空气质量（带预警）
    
    # 重置传感器
    print("\n🔄 重置传感器 : ")  # 打印测试标题
    sensor_manager.reset_to_normal()  # 重置传感器到正常状态
    
    normal_data = sensor_manager.get_current_data()  # 获取正常数据
    print(f"  正常模式数据 : ")  # 打印数据标题
    print(f"    温度 : {normal_data['temperature']}°C")  # 打印温度
    print(f"    湿度 : {normal_data['humidity']}%")  # 打印湿度
    print(f"    风速 : {normal_data['wind_speed']}m/s")  # 打印风速
    print(f"    空气质量 : {normal_data['air_quality']} AQI")  # 打印空气质量
    
    print("\n✅ 虚拟传感器测试完成 !")  # 打印测试完成消息

if __name__ == "__main__" :  # 如果是直接运行此脚本
    test_sensors()  # 运行测试函数
