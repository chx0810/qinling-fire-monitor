"""
火灾检测器 - 加载训练好的模型进行推理
支持单张图片检测和批量检测
"""

import os
# 设置TensorFlow日志级别为只显示错误，减少冗余输出
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np
from pathlib import Path
from PIL import Image
import tensorflow as tf
tf.get_logger().setLevel('ERROR')  # 设置TensorFlow日志级别
from datetime import datetime  # 用于时间戳记录
from config import config  # 导入配置模块
import base64  # 用于将热力图编码为base64字符串
import io  # 用于内存中的字节流操作

class FireDetector :
    """秦岭火灾检测器类"""
    
    def __init__(self , model_path = None) :
        """初始化检测器"""
        self.image_size = config.IMAGE_SIZE  # 图像尺寸(64, 64)
        self.class_names = config.CLASS_NAMES  # 类别名称列表
        self.class_colors = config.CLASS_COLORS  # 类别对应颜色
        
        # 加载模型
        self.model = self._load_model(model_path)  # 调用私有方法加载模型
        
        # 风险评估阈值（从配置中获取）
        self.risk_thresholds = config.RISK_ASSESSMENT  # 风险阈值配置
    
    def _load_model(self , model_path = None) :
        """加载训练好的模型（完全重构版）"""
        if model_path is None :  # 如果没有指定模型路径
            model_path = config.BEST_MODEL_PATH  # 使用配置中的最佳模型路径
        
        print(f"📦 加载模型: {model_path}")  # 打印加载信息
        
        try :
            # 方法1：尝试直接加载（最常用方法）
            try :
                model = tf.keras.models.load_model(model_path , compile = False)  # 不编译，只加载结构
                print("✅ 模型直接加载成功")  # 成功信息
            except Exception as e1 :
                print(f"⚠️  直接加载失败: {e1}")  # 打印失败信息
                print("🔄 尝试重建模型...")  # 提示尝试第二种方法
                
                # 方法2：使用原始代码重建模型（备用方案）
                from fire_cnn_model import FireCNNModel  # 导入模型构建模块
                model_builder = FireCNNModel()  # 创建模型构建器
                model = model_builder.create_model()  # 创建新模型
                
                # 编译模型（保持和训练时一致的配置）
                model_builder.compile_model(model)  # 编译模型
                
                # 加载权重（只加载参数，不加载结构）
                model.load_weights(model_path)  # 加载权重文件
                print("✅ 通过重建+权重加载成功")  # 成功信息
            
            # 安全地获取模型信息
            print(f"   模型类型: {type(model).__name__}")  # 打印模型类型
            
            # 测试模型是否可用（创建随机输入进行推理测试）
            test_input = np.random.randn(1 , *config.IMAGE_SIZE , 3).astype(np.float32)  # 创建随机测试输入
            test_output = model.predict(test_input , verbose = 0)  # 进行推理（verbose=0不显示进度）
            
            print(f"   测试推理成功")  # 成功信息
            print(f"   输出形状: {test_output.shape}")  # 打印输出形状
            print(f"   类别数量: {test_output.shape[1]}")  # 打印类别数量
            
            return model  # 返回加载成功的模型
            
        except Exception as e :
            print(f"❌ 所有加载方式都失败: {e}")  # 打印所有方法都失败的信息
            raise  # 重新抛出异常
    
    def preprocess_image(self , image) :
        """预处理图片，将不同格式的输入转换为模型需要的格式"""
        # 如果是文件路径或Path对象，加载图片
        if isinstance(image , (str , Path)) :  # 检查输入类型
            image = Image.open(image)  # 使用PIL打开图片文件
        
        # 确保是 PIL Image 对象
        if not isinstance(image , Image.Image) :  # 如果不是PIL图片对象
            raise TypeError("输入必须是图片路径或 PIL Image 对象")  # 抛出类型错误
        
        # 转换为 RGB 格式（三通道）
        if image.mode != 'RGB' :  # 检查图片模式
            image = image.convert('RGB')  # 转换为RGB格式
        
        # 调整尺寸到模型要求的尺寸
        image = image.resize(self.image_size , Image.Resampling.LANCZOS)  # 使用LANCZOS算法重采样
        
        # 转换为 numpy 数组并归一化到[0,1]范围
        img_array = np.array(image , dtype = np.float32) / 255.0  # 转换为float32并归一化
        
        # 添加批次维度（模型需要批次的输入）
        img_array = np.expand_dims(img_array , axis = 0)  # 在第0维添加批次维度
        
        return img_array  # 返回处理后的图像数组
    
    def detect_single(self , image) :
        """检测单张图片"""
        # 1. 预处理图片
        processed_image = self.preprocess_image(image)  # 调用预处理方法
        
        # 2. 进行推理（计算推理时间）
        start_time = datetime.now()  # 记录开始时间
        predictions = self.model.predict(processed_image , verbose = 0)  # 模型推理
        inference_time = (datetime.now() - start_time).total_seconds() * 1000  # 计算推理时间（毫秒）
        
        # 3. 获取结果
        pred_probs = predictions[0]  # 获取第一个批次的预测概率（因为是单张图片）
        pred_class_idx = np.argmax(pred_probs)  # 找到最大概率的索引
        pred_class_name = self.class_names[pred_class_idx]  # 根据索引获取类别名称
        confidence = float(pred_probs[pred_class_idx])  # 获取置信度（最大概率值）
        
        # 4. 生成Grad-CAM热力图
        heatmap_base64 = self._generate_gradcam(processed_image , pred_class_idx)
        
        # 5. 创建详细结果字典
        result = {
            'class' : pred_class_name ,  # 预测类别名称
            'confidence' : confidence ,  # 置信度
            'class_index' : int(pred_class_idx) ,  # 类别索引（整数）
            'all_probabilities' : {name : float(prob) for name , prob in zip(self.class_names , pred_probs)} ,  # 所有类别概率
            'inference_time_ms' : inference_time ,  # 推理时间（毫秒）
            'timestamp' : datetime.now().isoformat() ,  # 时间戳（ISO格式）
            'heatmap' : heatmap_base64  # Grad-CAM热力图（base64编码的PNG）
        }
        
        # 5. 进行风险评估
        risk_assessment = self._assess_risk(result)  # 调用风险评估方法
        result['risk_assessment'] = risk_assessment  # 将风险评估结果添加到结果字典
        
        return result  # 返回完整结果
    
    def detect_batch(self , image_list) :
        """批量检测图片（高效处理多张图片）"""
        if not image_list :  # 如果图片列表为空
            return []  # 返回空列表
        
        # 1. 预处理所有图片
        processed_images = []  # 处理后的图片列表
        original_images = []  # 原始图片列表（保存原图用于可能的后续处理）
        
        for img in image_list :  # 遍历图片列表
            if isinstance(img , (str , Path)) :  # 如果是文件路径
                original_img = Image.open(img)  # 加载图片
                original_images.append(original_img)  # 保存到原始图片列表
            else :  # 如果是PIL图片对象
                original_images.append(img)  # 直接保存到原始图片列表
            
            processed_img = self.preprocess_image(original_images[-1])  # 预处理最后一张图片
            processed_images.append(processed_img[0])  # 去掉批次维度，添加到处理后的图片列表
        
        # 2. 将所有图片堆叠成一个批次
        batch_array = np.stack(processed_images , axis = 0)  # 在第0维堆叠
        
        # 3. 批量推理（一次处理所有图片）
        start_time = datetime.now()  # 记录开始时间
        batch_predictions = self.model.predict(batch_array , verbose = 0)  # 批量推理
        total_time = (datetime.now() - start_time).total_seconds() * 1000  # 计算总时间（毫秒）
        
        # 4. 处理每个结果
        results = []  # 结果列表
        for i , predictions in enumerate(batch_predictions) :  # 遍历每个图片的预测结果
            pred_class_idx = np.argmax(predictions)  # 找到最大概率索引
            pred_class_name = self.class_names[pred_class_idx]  # 获取类别名称
            confidence = float(predictions[pred_class_idx])  # 获取置信度
            
            # 创建结果字典
            result = {
                'image_index' : i ,  # 图片索引
                'class' : pred_class_name ,  # 预测类别
                'confidence' : confidence ,  # 置信度
                'class_index' : int(pred_class_idx) ,  # 类别索引
                'all_probabilities' : {name : float(prob) for name , prob in zip(self.class_names , predictions)} ,  # 所有概率
                'inference_time_ms' : total_time / len(batch_predictions) if len(batch_predictions) > 0 else 0 ,  # 平均推理时间
                'timestamp' : datetime.now().isoformat()  # 时间戳
            }
            
            # 风险评估
            risk_assessment = self._assess_risk(result)  # 调用风险评估方法
            result['risk_assessment'] = risk_assessment  # 添加风险评估结果
            
            results.append(result)  # 添加到结果列表
        
        return results  # 返回所有结果
    
    def _generate_gradcam(self , processed_image , class_index) :
        """生成Grad-CAM热力图并返回base64编码的PNG图片"""
        try :
            # 找到最后一个卷积层（用于Grad-CAM计算）
            last_conv_layer = None
            for layer in reversed(self.model.layers) :
                if isinstance(layer , (tf.keras.layers.Conv2D , tf.keras.layers.DepthwiseConv2D)) :
                    last_conv_layer = layer
                    break
            
            if last_conv_layer is None :
                print("⚠️  未找到卷积层，尝试使用简单热力图替代")  # 打印警告
                return self._generate_simple_heatmap(processed_image)  # 使用简单热力图替代
            
            # 创建梯度模型：输入为原模型输入，输出为最后一个卷积层输出和模型最终输出
            grad_model = tf.keras.models.Model(
                inputs = [self.model.inputs] ,
                outputs = [last_conv_layer.output , self.model.output]
            )
            
            # 计算梯度
            with tf.GradientTape() as tape :
                conv_outputs , predictions = grad_model(processed_image)
                loss = predictions[: , class_index]  # 目标类别的预测值
            
            # 计算梯度相对于卷积层输出的梯度
            grads = tape.gradient(loss , conv_outputs)
            
            # 全局平均池化梯度（计算每个通道的重要性权重）
            pooled_grads = tf.reduce_mean(grads , axis = (0 , 1 , 2))
            
            # 加权组合卷积输出（使用tf.tensordot替代@运算符，兼容性更好）
            conv_outputs = conv_outputs[0]  # 去掉批次维度，形状为 (H, W, C)
            # pooled_grads 形状为 (C,)，需要与conv_outputs的最后一个维度做点积
            heatmap = tf.tensordot(conv_outputs , pooled_grads , axes = [[2] , [0]])
            # heatmap 形状为 (H, W)
            
            # ReLU激活（只保留正向贡献）
            heatmap = tf.maximum(heatmap , 0)
            
            # 归一化到[0, 1]
            max_val = tf.reduce_max(heatmap)
            if max_val > 0 :
                heatmap = heatmap / max_val
            
            # 转换为numpy数组
            heatmap = heatmap.numpy()
            
            # 调整热力图大小到模型输入尺寸
            heatmap_resized = np.array(
                Image.fromarray(np.uint8(heatmap * 255)).resize(
                    (self.image_size[1] , self.image_size[0]) ,
                    Image.Resampling.BILINEAR
                )
            ) / 255.0
            
            # 应用颜色映射（JET色图：蓝->绿->黄->红）
            heatmap_colored = self._apply_colormap(heatmap_resized)
            
            # 将原始图片和热力图叠加
            original_img = (processed_image[0] * 255).astype(np.uint8)
            overlay = np.uint8(original_img * 0.6 + heatmap_colored * 0.4)
            
            # 转换为PIL图片并编码为base64
            overlay_img = Image.fromarray(overlay)
            buffer = io.BytesIO()
            overlay_img.save(buffer , format = 'PNG')
            buffer.seek(0)
            heatmap_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            print(f"✅ Grad-CAM热力图生成成功，base64长度: {len(heatmap_base64)}")  # 打印成功信息
            return heatmap_base64
            
        except Exception as e :
            print(f"⚠️  Grad-CAM生成失败: {e}")
            import traceback
            traceback.print_exc()  # 打印详细堆栈
            # 回退到简单热力图
            return self._generate_simple_heatmap(processed_image)

    def _generate_simple_heatmap(self , processed_image) :
        """简单热力图备选方案（当Grad-CAM失败时使用）"""
        try :
            # 基于原图生成一个简单的高斯模糊热力图作为替代
            original_img = (processed_image[0] * 255).astype(np.uint8)
            h , w = original_img.shape[:2]
            
            # 创建中心高亮的简单热力图
            y , x = np.ogrid[:h , :w]
            center_y , center_x = h // 2 , w // 2
            # 高斯分布热力图
            heatmap = np.exp(-((x - center_x)**2 + (y - center_y)**2) / (2 * (min(h,w)/3)**2))
            heatmap = np.uint8(heatmap * 255)
            
            # 应用颜色映射
            heatmap_3ch = np.stack([heatmap , heatmap , heatmap] , axis = -1)
            # 用红色通道表示热力
            heatmap_colored = np.zeros_like(original_img)
            heatmap_colored[: , : , 0] = heatmap  # 红色通道
            
            # 叠加
            overlay = np.uint8(original_img * 0.6 + heatmap_colored * 0.4)
            
            overlay_img = Image.fromarray(overlay)
            buffer = io.BytesIO()
            overlay_img.save(buffer , format = 'PNG')
            buffer.seek(0)
            heatmap_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            print(f"✅ 简单热力图备选方案生成成功，base64长度: {len(heatmap_base64)}")
            return heatmap_base64
        except Exception as e2 :
            print(f"⚠️  简单热力图也失败: {e2}")
            return None
    
    def _apply_colormap(self , heatmap) :
        """将灰度热力图应用JET颜色映射"""
        # JET色图近似实现
        h , w = heatmap.shape
        colored = np.zeros((h , w , 3) , dtype = np.uint8)
        
        for i in range(h) :
            for j in range(w) :
                val = heatmap[i , j]
                if val < 0.25 :
                    r = 0
                    g = int(val * 4 * 255)
                    b = 255
                elif val < 0.5 :
                    r = 0
                    g = 255
                    b = int((0.5 - val) * 4 * 255)
                elif val < 0.75 :
                    r = int((val - 0.5) * 4 * 255)
                    g = 255
                    b = 0
                else :
                    r = 255
                    g = int((1.0 - val) * 4 * 255)
                    b = 0
                colored[i , j] = [r , g , b]
        
        return colored
    
    def _assess_risk(self , detection_result) :
        """根据检测结果评估火灾风险"""
        class_name = detection_result['class']  # 获取预测类别
        confidence = detection_result['confidence']  # 获取置信度
        
        # 1. 风险等级计算（初始化风险分数）
        risk_score = 0  # 初始风险分数
        
        # 2. 根据类别赋予基础分数
        if class_name == 'fire' :  # 如果是火灾
            risk_score = 80 + (confidence * 20)  # 基础80分 + 置信度×20（80-100分）
        elif class_name == 'fire_smoke' :  # 如果是火灾+烟雾
            risk_score = 60 + (confidence * 30)  # 基础60分 + 置信度×30（60-90分）
        elif class_name == 'smoke' :  # 如果是烟雾
            risk_score = 40 + (confidence * 30)  # 基础40分 + 置信度×30（40-70分）
        elif class_name == 'normal' :  # 如果是正常
            risk_score = 10 + (confidence * 10)  # 基础10分 + 置信度×10（10-20分）
        
        # 3. 根据置信度调整风险分数
        if confidence < 0.5 :  # 低置信度（低于50%）
            risk_score *= 0.7  # 降低30%风险（乘以0.7）
        elif confidence > 0.9 :  # 高置信度（高于90%）
            risk_score *= 1.1  # 增加10%风险（乘以1.1）
        
        # 4. 确保分数在 0-100 范围内
        risk_score = max(0 , min(100 , risk_score))  # 使用min和max限制范围
        
        # 5. 根据分数确定风险等级
        risk_levels = self.risk_thresholds['risk_levels']  # 从配置获取等级阈值
        risk_level = 'low'  # 默认低风险
        
        if risk_score >= risk_levels['critical'] :  # 如果分数 >= 70（严重阈值）
            risk_level = 'critical'  # 严重风险
        elif risk_score >= risk_levels['high'] :  # 如果分数 >= 50（高阈值）
            risk_level = 'high'  # 高风险
        elif risk_score >= risk_levels['medium'] :  # 如果分数 >= 30（中阈值）
            risk_level = 'medium'  # 中等风险
        else :  # 否则
            risk_level = 'low'  # 低风险
        
        # 6. 风险描述文本
        risk_descriptions = {
            'critical' : '🔥 紧急 : 检测到明显火灾 ， 需要立即处置 ！' ,  # 严重风险描述
            'high' : '⚠️  高危 : 检测到火灾迹象 ， 建议立即检查' ,  # 高风险描述
            'medium' : '🔶 中危 : 检测到烟雾或疑似火情 ， 建议密切关注' ,  # 中风险描述
            'low' : '✅ 低危 : 情况正常'  # 低风险描述
        }
        
        # 7. 返回风险评估结果
        return {
            'score' : round(risk_score , 2) ,  # 风险分数（保留两位小数）
            'level' : risk_level ,  # 风险等级
            'description' : risk_descriptions.get(risk_level , '未知风险') ,  # 风险描述（获取失败时用默认）
            'recommendation' : self._get_recommendation(risk_level , class_name)  # 获取建议
        }
    
    def _get_recommendation(self , risk_level , class_name) :
        """根据风险等级和类别获取建议"""
        # 基础建议字典
        recommendations = {
            'critical' : '立即启动应急预案 ， 通知消防部门 ， 组织人员撤离' ,  # 严重风险建议
            'high' : '立即派人前往现场确认 ， 准备启动应急预案' ,  # 高风险建议
            'medium' : '加强监控 ， 派人前往检查 ， 准备应急物资' ,  # 中风险建议
            'low' : '保持正常监控 ， 定期巡检'  # 低风险建议
        }
        
        # 根据具体类别添加额外建议
        if class_name == 'fire' :  # 如果是火灾类别
            recommendations['critical'] += ' ， 优先确保人员安全'  # 在严重建议后追加
        elif class_name == 'smoke' :  # 如果是烟雾类别
            recommendations['high'] += ' ， 检查烟雾来源'  # 在高风险建议后追加
        
        # 返回对应等级的建议
        return recommendations.get(risk_level , '保持监控')  # 获取建议，失败时返回默认
    
    def test_with_sample_images(self) :
        """使用样本图片测试检测器功能"""
        print("\n🧪 使用样本图片测试检测器")  # 测试标题
        print("=" * 50)  # 分隔线
        
        samples_dir = config.SAMPLES_DIR  # 获取样本目录路径
        if not samples_dir.exists() :  # 如果目录不存在
            print(f"⚠️  样本目录不存在 : {samples_dir}")  # 打印警告
            print("请创建样本目录并添加测试图片")  # 提示信息
            return  # 退出方法
        
        # 查找样本图片（支持多种格式和大小写）
        sample_images = []  # 样本图片列表
        for ext in ['.jpg' , '.jpeg' , '.png'] :  # 遍历常见图片格式
            sample_images.extend(samples_dir.glob(f"*{ext}"))  # 查找小写格式
            sample_images.extend(samples_dir.glob(f"*{ext.upper()}"))  # 查找大写格式
        
        if not sample_images :  # 如果没有找到图片
            print(f"⚠️  没有找到样本图片 ， 请在 {samples_dir} 中添加图片")  # 打印警告
            return  # 退出方法
        
        print(f"找到 {len(sample_images)} 张样本图片")  # 打印找到的图片数量
        
        # 测试每张图片（最多测试5张，避免太多输出）
        for i , img_path in enumerate(sample_images[:5]) :  # 遍历前5张图片
            print(f"\n[{i + 1}] 测试 : {img_path.name}")  # 打印测试序号和文件名
            
            try :
                result = self.detect_single(img_path)  # 检测单张图片
                
                # 打印主要结果
                print(f"   检测结果 : {result['class']}")  # 打印类别
                print(f"   置信度 : {result['confidence'] : .3f}")  # 打印置信度（3位小数）
                print(f"   推理时间 : {result['inference_time_ms'] : .1f} ms")  # 打印推理时间（1位小数）
                print(f"   风险等级 : {result['risk_assessment']['level']}")  # 打印风险等级
                print(f"   风险描述 : {result['risk_assessment']['description']}")  # 打印风险描述
                
                # 显示所有类别概率（只显示大于1%的概率）
                print(f"   所有类别概率 : ")  # 标题
                for class_name , prob in result['all_probabilities'].items() :  # 遍历所有概率
                    if prob > 0.01 :  # 如果概率大于1%
                        print(f"      {class_name : 12} : {prob : .3f}")  # 打印类别名和概率（12字符宽度，3位小数）
                        
            except Exception as e :  # 捕获异常
                print(f"   ❌ 检测失败 : {e}")  # 打印失败信息
    
    def benchmark_performance(self , num_tests = 10) :
        """性能基准测试（评估模型推理速度）"""
        print("\n⚡ 性能基准测试")  # 测试标题
        print("=" * 50)  # 分隔线
        
        # 1. 创建随机测试图片（与真实图片尺寸相同）
        test_image = np.random.rand(*self.image_size , 3).astype(np.float32)  # 创建随机图像
        test_image = np.clip(test_image , 0 , 1)  # 限制像素值在[0,1]范围内
        
        # 2. 预热模型（让TensorFlow完成初始化和优化）
        print("预热模型 ...")  # 打印预热信息
        for _ in range(3) :  # 预热3次
            _ = self.model.predict(np.expand_dims(test_image , axis = 0) , verbose = 0)  # 不关心输出
        
        # 3. 测试推理速度
        print(f"进行 {num_tests} 次推理测试 ...")  # 打印测试信息
        inference_times = []  # 推理时间列表
        
        for i in range(num_tests) :  # 循环测试指定次数
            start_time = datetime.now()  # 记录开始时间
            _ = self.model.predict(np.expand_dims(test_image , axis = 0) , verbose = 0)  # 推理测试
            end_time = datetime.now()  # 记录结束时间
            
            inference_time = (end_time - start_time).total_seconds() * 1000  # 计算毫秒数
            inference_times.append(inference_time)  # 添加到时间列表
            
            if i % 5 == 0 :  # 每5次测试打印一次进度
                print(f"  测试 {i + 1}/{num_tests} : {inference_time : .1f} ms")  # 打印当前测试时间
        
        # 4. 计算统计数据
        avg_time = np.mean(inference_times)  # 平均时间
        min_time = np.min(inference_times)  # 最短时间
        max_time = np.max(inference_times)  # 最长时间
        std_time = np.std(inference_times)  # 标准差（波动程度）
        
        print(f"\n📊 性能统计 : ")  # 统计标题
        print(f"  平均推理时间 : {avg_time : .1f} ms")  # 平均时间
        print(f"  最快推理时间 : {min_time : .1f} ms")  # 最短时间
        print(f"  最慢推理时间 : {max_time : .1f} ms")  # 最长时间
        print(f"  标准差 : {std_time : .1f} ms")  # 标准差
        print(f"  FPS : {1000 / avg_time : .1f} (帧 / 秒)")  # 计算每秒处理的帧数
        
        # 5. 内存使用估算
        print(f"\n💾 内存估算 : ")  # 内存标题
        print(f"  模型参数 : {self.model.count_params() : ,}")  # 模型参数数量（带千位分隔符）
        # 计算单张图片内存占用（宽×高×通道数×每个像素4字节）
        single_img_mem = self.image_size[0] * self.image_size[1] * 3 * 4 / 1024  # 转换为KB
        print(f"  单张图片内存 : {single_img_mem : .1f} KB")  # 打印内存占用
        
        return {  # 返回性能统计字典
            'avg_inference_time_ms' : avg_time ,  # 平均推理时间
            'fps' : 1000 / avg_time ,  # 帧率
            'model_params' : self.model.count_params()  # 模型参数数量
        }

def main() :
    """主函数：提供交互式界面测试检测器"""
    print("🔥 秦岭火灾预警系统 - 火灾检测器")  # 标题
    print("=" * 60)  # 分隔线
    
    # 1. 选择模型文件
    model_files = list(config.MODEL_DIR.glob("*.h5"))  # 查找所有.h5模型文件
    
    if not model_files :  # 如果没有找到模型文件
        print("❌ 没有找到模型文件 ， 请先训练模型")  # 打印错误信息
        return  # 退出程序
    
    # 2. 显示找到的模型文件
    print(f"找到 {len(model_files)} 个模型文件 : ")  # 打印文件数量
    for i , model_file in enumerate(model_files , 1) :  # 遍历模型文件（从1开始编号）
        file_time = datetime.fromtimestamp(os.path.getmtime(model_file))  # 获取文件修改时间
        size_mb = os.path.getsize(model_file) / (1024 * 1024)  # 计算文件大小（MB）
        print(f"  {i}. {model_file.name} ({size_mb : .1f} MB , {file_time : %Y-%m-%d %H : %M})")  # 打印文件信息
    
    # 3. 让用户选择模型
    choice = input(f"\n选择模型 (1-{len(model_files)} , 默认为 1) : ").strip()  # 获取用户输入
    
    if choice and choice.isdigit() :  # 如果输入有效且是数字
        idx = int(choice) - 1  # 转换为索引（减1因为显示从1开始）
        if 0 <= idx < len(model_files) :  # 如果索引有效
            model_path = model_files[idx]  # 使用选择的模型
        else :  # 如果索引无效
            model_path = model_files[0]  # 使用第一个模型
    else :  # 如果输入无效或为空
        model_path = model_files[0]  # 使用第一个模型（默认）
    
    # 4. 创建检测器
    try :
        detector = FireDetector(model_path = model_path)  # 创建检测器实例
        
        # 5. 选择操作
        print("\n选择操作 : ")  # 操作选择标题
        print("  1. 测试样本图片")  # 选项1
        print("  2. 性能基准测试")  # 选项2
        print("  3. 检测单张图片")  # 选项3
        
        op_choice = input("\n请输入选择 (1-3) : ").strip()  # 获取操作选择
        
        if op_choice == '1' :  # 如果选择1
            detector.test_with_sample_images()  # 测试样本图片
        elif op_choice == '2' :  # 如果选择2
            detector.benchmark_performance()  # 性能测试
        elif op_choice == '3' :  # 如果选择3
            img_path = input("请输入图片路径 : ").strip()  # 获取图片路径
            if os.path.exists(img_path) :  # 如果图片存在
                result = detector.detect_single(img_path)  # 检测单张图片
                print(f"\n📊 检测结果 : ")  # 结果标题
                print(f"  类别 : {result['class']}")  # 打印类别
                print(f"  置信度 : {result['confidence'] : .3f}")  # 打印置信度
                print(f"  风险等级 : {result['risk_assessment']['level']}")  # 打印风险等级
                print(f"  风险描述 : {result['risk_assessment']['description']}")  # 打印风险描述
            else :  # 如果图片不存在
                print(f"❌ 图片不存在 : {img_path}")  # 打印错误信息
        else :  # 如果选择无效
            print("✅ 检测器初始化完成 , 可在代码中调用")  # 打印完成信息
            
    except Exception as e :  # 捕获异常
        print(f"❌ 初始化失败 : {e}")  # 打印失败信息

if __name__ == "__main__" :  # 如果直接运行此脚本
    main()  # 执行主函数
