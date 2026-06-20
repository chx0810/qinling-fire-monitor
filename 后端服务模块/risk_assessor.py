"""
综合风险评估器
结合AI检测结果和传感器数据进行综合风险评估
"""

# 导入Python标准库
from datetime import datetime  # 日期时间处理
from typing import Dict , Any , Optional  # 类型注解
import numpy as np  # 数值计算库，用于统计分析

class RiskAssessor :
    """综合风险评估器"""
    
    def __init__(self) :
        # 风险权重配置字典，各因素权重总和为1.0
        self.weights = {
            'ai_detection' : 0.6 ,      # AI检测权重（最重要）
            'temperature' : 0.15 ,      # 温度权重
            'humidity' : 0.10 ,         # 湿度权重
            'wind_speed' : 0.10 ,       # 风速权重
            'air_quality' : 0.05        # 空气质量权重
        }
        
        # 风险等级阈值配置（统一标准）：
        # 0-30 低危 | 30-60 中危 | 60-80 高危 | 80+ 严重
        self.risk_thresholds = {
            'critical' : 80 ,  # 紧急阈值：>=80分
            'high' : 60 ,      # 高阈值：60-79分
            'medium' : 30 ,    # 中阈值：30-59分
            'low' : 0          # 低阈值：0-29分
        }
        
        # 秦岭山区风险评估参数，基于秦岭气候特征设定
        self.qinling_params = {
            'temperature_high' : 35.0 ,    # 高温阈值：≥35°C触发高温预警
            'temperature_critical' : 40.0 , # 危险高温阈值：≥40°C触发危险高温
            'humidity_low' : 30.0 ,        # 低湿度阈值：≤30%触发干燥预警
            'humidity_critical' : 20.0 ,   # 危险低湿度阈值：≤20%触发极度干燥
            'wind_high' : 8.0 ,           # 大风阈值：≥8m/s触发大风预警
            'wind_critical' : 12.0 ,      # 危险大风阈值：≥12m/s触发危险大风
            'aqi_high' : 100 ,            # 高污染阈值：≥100AQI触发污染预警
            'aqi_critical' : 150          # 危险污染阈值：≥150AQI触发严重污染
        }
        
        # 历史风险评估记录列表，存储所有评估结果
        self.history = []
    
    def assess_risk(self , 
                    detection_result : Dict[str , Any] , 
                    sensor_data : Optional[Dict[str , Any]] = None) -> Dict[str , Any] :
        """
        综合风险评估
        Args:
            detection_result: AI检测结果
            sensor_data: 传感器数据
        Returns:
            综合风险评估结果
        """
        
        # 1. AI检测风险评估
        ai_risk_score = self._calculate_ai_risk(detection_result)
        
        # 2. 传感器风险评估
        sensor_risk_score = 0  # 初始化传感器风险分数
        sensor_details = {}  # 初始化传感器详细信息字典
        
        if sensor_data :  # 如果提供了传感器数据
            sensor_risk_score , sensor_details = self._calculate_sensor_risk(sensor_data)
        
        # 3. 综合风险评估（加权平均）
        combined_score = (
            ai_risk_score * self.weights['ai_detection'] +  # AI检测贡献
            sensor_risk_score * (1 - self.weights['ai_detection'])  # 传感器贡献
        )
        
        # 限制在0-100范围内，确保分数有效
        combined_score = max(0 , min(100 , combined_score))
        
        # 4. 确定风险等级
        risk_level = self._determine_risk_level(combined_score)
        
        # 5. 生成详细报告
        report = self._generate_risk_report(
            combined_score , 
            risk_level , 
            detection_result , 
            sensor_data ,
            sensor_details
        )
        
        # 6. 记录历史评估结果
        self._record_assessment({
            'score' : combined_score ,  # 综合风险分数
            'level' : risk_level ,  # 风险等级
            'ai_score' : ai_risk_score ,  # AI风险分数
            'sensor_score' : sensor_risk_score ,  # 传感器风险分数
            'detection_class' : detection_result.get('class' , 'unknown') ,  # 检测类别
            'timestamp' : datetime.now().isoformat()  # 评估时间戳
        })
        
        return report  # 返回风险评估报告
    
    def _calculate_ai_risk(self , detection_result : Dict[str , Any]) -> float :
        """计算AI检测风险分数"""
        class_name = detection_result.get('class' , 'normal')  # 获取检测类别，默认为'normal'
        confidence = detection_result.get('confidence' , 0)  # 获取置信度，默认为0
        
        # 基础分数字典：不同检测类别的基础风险分数
        base_scores = {
            'fire' : 85 ,  # 火灾：高风险
            'fire_smoke' : 70 ,  # 烟与火：中高风险
            'smoke' : 50 ,  # 烟雾：中等风险
            'normal' : 10  # 正常：低风险
        }
        
        # 获取基础分数，如果类别不在字典中则使用10分
        base_score = base_scores.get(class_name , 10)
        
        # 根据置信度调整分数
        if confidence < 0.5 :  # 低置信度（<50%）
            adjusted_score = base_score * 0.7  # 降低30%
        elif confidence > 0.9 :  # 高置信度（>90%）
            adjusted_score = base_score * 1.1  # 提高10%
        else :  # 中等置信度（50%-90%）
            adjusted_score = base_score  # 使用基础分数
        
        # 考虑所有类别的概率分布
        all_probs = detection_result.get('all_probabilities' , {})  # 获取所有类别概率
        if all_probs :  # 如果概率数据存在
            # 计算加权风险：每个类别的概率乘以其基础分数
            weighted_risk = 0
            for cls , prob in all_probs.items() :
                weighted_risk += prob * base_scores.get(cls , 10)  # 累加加权分数
            # 取调整后分数和加权分数的较大值
            adjusted_score = max(adjusted_score , weighted_risk)
        
        return min(100 , adjusted_score)  # 返回分数，不超过100
    
    def _calculate_sensor_risk(self , sensor_data : Dict[str , Any]) -> tuple :
        """计算传感器风险分数"""
        details = {}  # 传感器详细信息字典
        total_score = 0  # 总传感器风险分数
        
        # 温度风险评估
        temp = sensor_data.get('temperature' , 25)  # 获取温度，默认25°C
        temp_score = self._assess_temperature(temp)  # 评估温度风险
        details['temperature'] = {  # 存储温度评估详情
            'value' : temp ,  # 温度值
            'score' : temp_score ,  # 风险分数
            'status' : self._get_temperature_status(temp)  # 状态描述
        }
        total_score += temp_score * self.weights['temperature']  # 加权累加
        
        # 湿度风险评估
        humidity = sensor_data.get('humidity' , 50)  # 获取湿度，默认50%
        humidity_score = self._assess_humidity(humidity)  # 评估湿度风险
        details['humidity'] = {  # 存储湿度评估详情
            'value' : humidity ,  # 湿度值
            'score' : humidity_score ,  # 风险分数
            'status' : self._get_humidity_status(humidity)  # 状态描述
        }
        total_score += humidity_score * self.weights['humidity']  # 加权累加
        
        # 风速风险评估
        wind = sensor_data.get('wind_speed' , 2)  # 获取风速，默认2m/s
        wind_score = self._assess_wind_speed(wind)  # 评估风速风险
        details['wind_speed'] = {  # 存储风速评估详情
            'value' : wind ,  # 风速值
            'score' : wind_score ,  # 风险分数
            'status' : self._get_wind_status(wind)  # 状态描述
        }
        total_score += wind_score * self.weights['wind_speed']  # 加权累加
        
        # 空气质量风险评估
        aqi = sensor_data.get('air_quality' , 50)  # 获取AQI，默认50
        aqi_score = self._assess_air_quality(aqi)  # 评估空气质量风险
        details['air_quality'] = {  # 存储空气质量评估详情
            'value' : aqi ,  # AQI值
            'score' : aqi_score ,  # 风险分数
            'status' : self._get_aqi_status(aqi)  # 状态描述
        }
        total_score += aqi_score * self.weights['air_quality']  # 加权累加
        
        return total_score , details  # 返回总分和详细信息
    
    def _assess_temperature(self , temp : float) -> float :
        """评估温度风险"""
        if temp >= self.qinling_params['temperature_critical'] :  # ≥40°C
            return 90 + (temp - self.qinling_params['temperature_critical']) * 2  # 每超过1°C加2分
        elif temp >= self.qinling_params['temperature_high'] :  # 35-39.9°C
            return 60 + (temp - self.qinling_params['temperature_high']) * 3  # 每超过1°C加3分
        elif temp > 30 :  # 30-34.9°C
            return 30 + (temp - 30) * 2  # 每超过1°C加2分
        else :  # <30°C
            return max(0 , (temp - 15) * 2)  # 基于15°C基准计算
    
    def _assess_humidity(self , humidity : float) -> float :
        """评估湿度风险（湿度越低，火灾风险越高）"""
        if humidity <= self.qinling_params['humidity_critical'] :  # ≤20%
            return 90 + (self.qinling_params['humidity_critical'] - humidity) * 2  # 每降低1%加2分
        elif humidity <= self.qinling_params['humidity_low'] :  # 21-30%
            return 60 + (self.qinling_params['humidity_low'] - humidity) * 3  # 每降低1%加3分
        elif humidity < 40 :  # 31-39%
            return 30 + (40 - humidity) * 1.5  # 每降低1%加1.5分
        else :  # ≥40%
            return max(0 , (60 - humidity) * 0.5)  # 基于60%基准计算
    
    def _assess_wind_speed(self , wind : float) -> float :
        """评估风速风险"""
        if wind >= self.qinling_params['wind_critical'] :  # ≥12m/s
            return 90 + (wind - self.qinling_params['wind_critical']) * 5  # 每超过1m/s加5分
        elif wind >= self.qinling_params['wind_high'] :  # 8-11.9m/s
            return 60 + (wind - self.qinling_params['wind_high']) * 5  # 每超过1m/s加5分
        elif wind > 5 :  # 5.1-7.9m/s
            return 30 + (wind - 5) * 6  # 每超过1m/s加6分
        else :  # ≤5m/s
            return max(0 , wind * 2)  # 每1m/s加2分
    
    def _assess_air_quality(self , aqi : float) -> float :
        """评估空气质量风险"""
        if aqi >= self.qinling_params['aqi_critical'] :  # ≥150
            return 80 + (aqi - self.qinling_params['aqi_critical']) * 0.5  # 每超过1AQI加0.5分
        elif aqi >= self.qinling_params['aqi_high'] :  # 100-149
            return 50 + (aqi - self.qinling_params['aqi_high']) * 0.6  # 每超过1AQI加0.6分
        elif aqi > 80 :  # 81-99
            return 30 + (aqi - 80) * 0.7  # 每超过1AQI加0.7分
        else :  # ≤80
            return max(0 , aqi * 0.3)  # 每1AQI加0.3分
    
    def _get_temperature_status(self , temp : float) -> str :
        """获取温度状态"""
        if temp >= 40 :
            return "危险高温"
        elif temp >= 35 :
            return "高温预警"
        elif temp >= 30 :
            return "温度偏高"
        elif temp >= 15 :
            return "正常"
        else :
            return "温度偏低"
    
    def _get_humidity_status(self , humidity : float) -> str :
        """获取湿度状态"""
        if humidity <= 20 :
            return "极度干燥"
        elif humidity <= 30 :
            return "干燥"
        elif humidity <= 70 :
            return "正常"
        else :
            return "潮湿"
    
    def _get_wind_status(self , wind : float) -> str :
        """获取风速状态"""
        if wind >= 12 :
            return "危险大风"
        elif wind >= 8 :
            return "大风"
        elif wind >= 5 :
            return "风速较大"
        else :
            return "正常"
    
    def _get_aqi_status(self , aqi : float) -> str :
        """获取空气质量状态"""
        if aqi >= 150 :
            return "严重污染"
        elif aqi >= 100 :
            return "中度污染"
        elif aqi >= 50 :
            return "轻度污染"
        else :
            return "良好"
    
    def _determine_risk_level(self , score : float) -> str :
        """确定风险等级"""
        if score >= self.risk_thresholds['critical'] :
            return 'critical'
        elif score >= self.risk_thresholds['high'] :
            return 'high'
        elif score >= self.risk_thresholds['medium'] :
            return 'medium'
        else :
            return 'low'
    
    def _generate_risk_report(self , score : float , level : str ,
                             detection_result : Dict[str , Any] ,
                             sensor_data : Optional[Dict[str , Any]] ,
                             sensor_details : Dict[str , Any]) -> Dict[str , Any] :
        """生成风险评估报告"""
        
        # 风险等级描述字典
        level_descriptions = {
            'critical' : '🔥 紧急 ： 检测到明显火灾风险 ， 需要立即处置 ！' ,
            'high' : '⚠️  高危 ： 存在显著火灾风险 ， 建议立即检查' ,
            'medium' : '🔶 中危 ： 存在一定火灾风险 ， 建议密切关注' ,
            'low' : '✅ 低危 ： 情况正常 ， 保持监控'
        }
        
        # 建议措施字典，不同风险等级对应不同建议
        recommendations = {
            'critical' : [
                '立即启动应急预案' ,
                '通知消防部门和应急管理部门' ,
                '组织周边人员撤离' ,
                '切断电源和燃气' ,
                '准备灭火设备'
            ] ,
            'high' : [
                '立即派人前往现场确认' ,
                '加强监控频率' ,
                '准备应急物资' ,
                '通知相关管理人员'
            ] ,
            'medium' : [
                '加强监控 ， 密切关注' ,
                '派人前往检查' ,
                '检查消防设备' ,
                '做好应急准备'
            ] ,
            'low' : [
                '保持正常监控' ,
                '定期巡检' ,
                '维护消防设备' ,
                '加强防火宣传'
            ]
        }
        
        # 结合具体检测结果调整建议
        detection_class = detection_result.get('class' , 'normal')
        if detection_class == 'fire' :  # 如果检测到火灾
            if '立即扑救' not in recommendations[level] :  # 如果建议中没有"立即扑救"
                recommendations[level].insert(0 , '立即扑救')  # 添加到首位
        
        # 构建报告字典
        report = {
            'score' : round(score , 2) ,  # 风险分数，保留2位小数
            'level' : level ,  # 风险等级
            'description' : level_descriptions.get(level , '未知风险') ,  # 风险描述
            'recommendations' : recommendations.get(level , []) ,  # 建议措施列表
            'factors' : {  # 风险因素分析
                'ai_detection' : {  # AI检测因素
                    'class' : detection_class ,  # 检测类别
                    'confidence' : detection_result.get('confidence' , 0) ,  # 置信度
                    'contribution' : f"{self.weights['ai_detection'] * 100 : .0f}%"  # 贡献百分比
                }
            }
        }
        
        # 添加传感器因素（如果存在）
        if sensor_details :
            report['factors']['sensors'] = sensor_details
        
        # 添加时间戳和位置信息
        report['timestamp'] = datetime.now().isoformat()
        report['location'] = sensor_data.get('location' , '秦岭山区') if sensor_data else '秦岭山区'
        
        return report  # 返回完整报告
    
    def _record_assessment(self , assessment : Dict[str , Any]) :
        """记录风险评估"""
        self.history.append(assessment)  # 添加到历史记录
        
        # 限制历史记录数量为100条（先进先出）
        if len(self.history) > 100 :
            self.history = self.history[-100 : ]
    
    def get_risk_history(self , limit : int = 50) -> list :
        """获取风险评估历史"""
        return self.history[-limit : ] if self.history else []  # 返回最近limit条记录
    
    def get_statistics(self) -> Dict[str , Any] :
        """获取风险评估统计"""
        if not self.history :  # 如果没有历史记录
            return {}  # 返回空字典
        
        scores = [item['score'] for item in self.history]  # 提取所有分数
        levels = [item['level'] for item in self.history]  # 提取所有等级
        
        return {
            'total_assessments' : len(self.history) ,  # 总评估次数
            'average_score' : round(np.mean(scores) , 2) if scores else 0 ,  # 平均分数
            'max_score' : round(max(scores) , 2) if scores else 0 ,  # 最高分数
            'min_score' : round(min(scores) , 2) if scores else 0 ,  # 最低分数
            'level_distribution' : {  # 风险等级分布统计
                'critical' : levels.count('critical') ,
                'high' : levels.count('high') ,
                'medium' : levels.count('medium') ,
                'low' : levels.count('low')
            }
        }

# 测试函数
def test_risk_assessment() :
    """测试风险评估"""
    print("🧪 测试风险评估器...")  # 打印测试开始消息
    
    risk_assessor = RiskAssessor()  # 创建风险评估器实例
    
    # 测试数据：模拟检测结果
    test_detection = {
        'class' : 'fire_smoke' ,  # 检测类别：烟与火
        'confidence' : 0.85 ,  # 置信度：85%
        'all_probabilities' : {  # 所有类别概率
            'fire' : 0.15 ,
            'fire_smoke' : 0.85 ,
            'smoke' : 0.0 ,
            'normal' : 0.0
        }
    }
    
    # 测试数据：模拟传感器数据
    test_sensors = {
        'temperature' : 38.5 ,  # 温度：38.5°C
        'humidity' : 22.0 ,  # 湿度：22%
        'wind_speed' : 6.8 ,  # 风速：6.8m/s
        'air_quality' : 120 ,  # AQI：120
        'location' : '秦岭北麓-监测点1'  # 位置
    }
    
    # 进行风险评估
    risk_report = risk_assessor.assess_risk(test_detection , test_sensors)
    
    print(f"\n📊 风险评估报告 : ")  # 打印报告标题
    print(f"  综合风险分数 : {risk_report['score']}")  # 打印风险分数
    print(f"  风险等级 : {risk_report['level']}")  # 打印风险等级
    print(f"  风险描述 : {risk_report['description']}")  # 打印风险描述
    
    print(f"\n📋 建议措施 : ")  # 打印建议标题
    for i , rec in enumerate(risk_report['recommendations'] , 1) :  # 遍历建议列表
        print(f"  {i}. {rec}")  # 打印编号和建议
    
    print(f"\n📈 风险因素分析 : ")  # 打印因素分析标题
    print(f"  AI检测贡献 : {risk_report['factors']['ai_detection']['contribution']}")  # 打印AI贡献
    
    if 'sensors' in risk_report['factors'] :  # 如果有传感器因素
        print(f"  传感器评估 : ")  # 打印传感器评估标题
        for sensor , details in risk_report['factors']['sensors'].items() :  # 遍历传感器详情
            print(f"    {sensor} : {details['value']} → {details['status']} (评分 : {details['score'] : .1f})")
    
    # 获取统计信息
    stats = risk_assessor.get_statistics()  # 获取统计信息
    if stats :  # 如果统计信息存在
        print(f"\n📊 风险评估统计 : ")  # 打印统计标题
        print(f"  总评估次数 : {stats['total_assessments']}")  # 打印总次数
        print(f"  平均风险分数 : {stats['average_score']}")  # 打印平均分数
        print(f"  风险等级分布 : {stats['level_distribution']}")  # 打印等级分布
    
    print("\n✅ 风险评估测试完成 !")  # 打印测试完成消息

if __name__ == "__main__" :  # 如果是直接运行此脚本
    test_risk_assessment()  # 运行测试函数
