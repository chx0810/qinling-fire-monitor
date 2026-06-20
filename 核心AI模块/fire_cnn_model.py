"""
轻量级CNN模型 - 小于100K参数，适应1.3GB内存
专门为秦岭火灾检测优化
"""

import tensorflow as tf
# 设置TensorFlow日志级别为只显示错误，减少冗余输出
tf.get_logger().setLevel('ERROR')
keras = tf.keras  # 创建keras别名，方便使用
layers = tf.keras.layers  # 层模块别名
models = tf.keras.models  # 模型模块别名
from config import config  # 导入配置模块

class FireCNNModel :
    """秦岭火灾检测CNN模型类"""
    
    def __init__(self) :
        """初始化模型构建器"""
        self.input_shape = config.get_model_input_shape()  # 获取模型输入形状(64,64,3)
        self.num_classes = config.get_num_classes()  # 获取类别数量(4)
        self.model_arch = config.MODEL_ARCH  # 获取模型架构配置
        
        # 混合精度训练设置（注意：CPU上应该为False）
        if config.TRAINING['mixed_precision'] :  # 如果配置中启用混合精度
            tf.keras.mixed_precision.set_global_policy('mixed_float16')  # 设置全局混合精度策略
    
    def create_model(self) :
        """创建轻量级CNN模型（主要方法）"""
        print(" 创建轻量级CNN模型...")  # 打印开始信息
        print(f"输入形状: {self.input_shape}")  # 打印输入形状
        print(f"类别数量: {self.num_classes}")  # 打印类别数量
        
        # 创建Sequential模型（线性堆叠层）
        model = models.Sequential(name = "FireDetectionCNN")  # 设置模型名称

        # 输入层
        model.add(layers.Input(shape = self.input_shape))  # 添加输入层，定义输入形状

        # ========== 第一卷积块 ==========
        # 卷积层：提取图像低级特征（边缘、纹理）
        model.add(layers.Conv2D(
            filters = self.model_arch['conv_filters'][0] ,  # 滤波器数量：16个
            kernel_size = self.model_arch['conv_kernel_size'] ,  # 卷积核尺寸：3×3
            padding = 'same' ,  # 填充方式：保持输出尺寸不变
            activation = 'relu' ,  # 激活函数：ReLU（引入非线性）
            name = 'conv1'  # 层名称：便于识别
        ))

        # 批量归一化（可选）：标准化层输出，加速训练
        if self.model_arch['use_batch_norm'] :  # 如果配置中启用了批量归一化
            model.add(layers.BatchNormalization(name = 'bn1'))  # 添加批量归一化层

        # 池化层：降维，减少计算量，增加感受野
        model.add(layers.MaxPooling2D(
            pool_size = self.model_arch['pool_size'] ,  # 池化窗口尺寸：2×2
            name = 'pool1'  # 层名称
        ))
        
        # Dropout层：防止过拟合，随机丢弃神经元
        model.add(layers.Dropout(self.model_arch['dropout_rate'] , name = 'drop1'))  # 丢弃率：0.45

        # ========== 第二卷积块 ==========
        # 更深层次的卷积，提取更复杂的特征
        model.add(layers.Conv2D(
            filters = self.model_arch['conv_filters'][1] ,  # 滤波器数量：32个（增加）
            kernel_size = self.model_arch['conv_kernel_size'] ,  # 卷积核尺寸：3×3
            padding = 'same' ,  # 填充方式：same
            activation = 'relu' ,  # 激活函数：ReLU
            name = 'conv2'  # 层名称
        )) 

        # 批量归一化（可选）
        if self.model_arch['use_batch_norm'] :  # 如果启用批量归一化
            model.add(layers.BatchNormalization(name = 'bn2'))  # 添加批量归一化层

        # 池化层：进一步降维
        model.add(layers.MaxPooling2D(
            pool_size = self.model_arch['pool_size'] ,  # 池化窗口：2×2
            name = 'pool2'  # 层名称
        ))
        
        # Dropout层：防止过拟合
        model.add(layers.Dropout(self.model_arch['dropout_rate'] , name = 'drop2'))  # 丢弃率：0.45

        # ========== 第三卷积块 ==========
        if len(self.model_arch['conv_filters']) > 2 :  # 如果配置中有第三层滤波器
            # 更深层次的卷积，提取高级特征
            model.add(layers.Conv2D(
                filters = self.model_arch['conv_filters'][2] ,  # 滤波器数量：64个
                kernel_size = self.model_arch['conv_kernel_size'] ,  # 卷积核尺寸：3×3
                padding = 'same' ,  # 填充方式：same
                activation = 'relu' ,  # 激活函数：ReLU
                name = 'conv3'  # 层名称
            ))
            
            # 批量归一化（可选）
            if self.model_arch['use_batch_norm'] :  # 如果启用批量归一化
                model.add(layers.BatchNormalization(name = 'bn3'))  # 添加批量归一化层
            
            # 全局平均池化：替代Flatten，减少参数
            model.add(layers.GlobalAveragePooling2D(name = 'gap'))  # 对每个特征图取平均值
            model.add(layers.Dropout(self.model_arch['dropout_rate'] , name = 'drop3'))  # Dropout层
        else :  # 如果没有第三层
            model.add(layers.Flatten(name = 'flatten'))  # 展平层，将3D特征图转为1D向量

        # ========== 全连接层 ==========
        # 全连接层：整合特征，进行分类决策
        model.add(layers.Dense(
            units = self.model_arch['dense_units'] ,  # 神经元数量：32个
            activation = 'relu' ,  # 激活函数：ReLU
            name = 'dense1'  # 层名称
        ))
        
        # Dropout层：防止过拟合（丢弃率减半）
        model.add(layers.Dropout(self.model_arch['dropout_rate'] * 0.5 , name = 'drop4'))  # 丢弃率：0.225

        # ========== 输出层 ==========
        # 输出层：最终分类
        model.add(layers.Dense(
            units = self.num_classes ,  # 输出单元数：4个（对应4个类别）
            activation = 'softmax' ,  # 激活函数：Softmax（输出概率分布）
            name = 'output' ,  # 层名称
            dtype = 'float32'  # 数据类型：确保输出为float32（重要！）
        ))

        return model  # 返回构建好的模型
    
    def compile_model(self , model) :
        """编译模型，配置训练过程"""
        # 创建优化器：Adam优化器（自适应学习率）
        optimizer = keras.optimizers.Adam(
            learning_rate = config.TRAINING['learning_rate']  # 学习率：0.001
        )
        
        # 如果使用混合精度，包装优化器以支持损失缩放
        if config.TRAINING['mixed_precision'] :  # 如果启用混合精度
            optimizer = tf.keras.mixed_precision.LossScaleOptimizer(optimizer)  # 包装优化器
        
        # 编译模型：配置训练过程
        model.compile(
            optimizer = optimizer ,  # 优化器
            loss = 'categorical_crossentropy' ,  # 损失函数：分类交叉熵（多分类）
            metrics = [  # 评估指标列表
                'accuracy' ,  # 准确率
                keras.metrics.Precision(name = 'precision') ,  # 精确率（查准率）
                keras.metrics.Recall(name = 'recall') ,  # 召回率（查全率）
                keras.metrics.AUC(name = 'auc')  # AUC（曲线下面积，衡量分类性能）
            ]
        )
        
        return model  # 返回编译好的模型
    
    def create_model_with_regularization(self) :
        """创建带正则化的模型（防止过拟合的更强版本）"""
        print(" 创建带正则化的CNN模型...")  # 打印开始信息

        # 使用函数式API创建模型（更灵活）
        inputs = layers.Input(shape = self.input_shape)  # 定义输入层

        # ========== 第一卷积块 ==========
        # 卷积层：L2正则化（权重衰减）
        x = layers.Conv2D(
            filters = 32 ,  # 滤波器数量：32个
            kernel_size = 3 ,  # 卷积核尺寸：3×3
            padding = 'same' ,  # 填充方式：same
            kernel_regularizer = keras.regularizers.l2(0.001) ,  # L2正则化，系数0.001
            activation = 'relu'  # 激活函数：ReLU
        )(inputs)  # 将输入传递给该层
        
        x = layers.BatchNormalization()(x)  # 批量归一化
        x = layers.MaxPooling2D(pool_size = 2)(x)  # 最大池化，2×2窗口
        x = layers.Dropout(0.3)(x)  # Dropout，丢弃率0.3

        # ========== 第二卷积块 ==========
        x = layers.Conv2D(
            filters = 64 ,  # 滤波器数量：64个
            kernel_size = 3 ,  # 卷积核尺寸：3×3
            padding = 'same' ,  # 填充方式：same
            kernel_regularizer = keras.regularizers.l2(0.001) ,  # L2正则化
            activation = 'relu'  # 激活函数：ReLU
        )(x)  # 将上一层的输出作为输入
        
        x = layers.BatchNormalization()(x)  # 批量归一化
        x = layers.MaxPooling2D(pool_size = 2)(x)  # 最大池化
        x = layers.Dropout(0.3)(x)  # Dropout，丢弃率0.3
        
        # ========== 第三卷积块 ==========
        x = layers.Conv2D(
            filters = 128 ,  # 滤波器数量：128个
            kernel_size = 3 ,  # 卷积核尺寸：3×3
            padding = 'same' ,  # 填充方式：same
            kernel_regularizer = keras.regularizers.l2(0.001) ,  # L2正则化
            activation = 'relu'  # 激活函数：ReLU
        )(x)  # 将上一层的输出作为输入
        
        x = layers.BatchNormalization()(x)  # 批量归一化
        x = layers.MaxPooling2D(pool_size = 2)(x)  # 最大池化
        x = layers.Dropout(0.4)(x)  # Dropout，丢弃率0.4（提高）

        # ========== 全连接层 ==========
        x = layers.Dense(
            64 ,  # 神经元数量：64个
            activation = 'relu' ,  # 激活函数：ReLU
            kernel_regularizer = keras.regularizers.l2(0.001)  # L2正则化
        )(x)  # 将展平后的特征作为输入
        
        x = layers.Dropout(0.4)(x)  # Dropout，丢弃率0.4

        # ========== 输出层 ==========
        outputs = layers.Dense(
            self.num_classes ,  # 输出单元数：4个
            activation = 'softmax' ,  # 激活函数：Softmax
            dtype = 'float32'  # 数据类型：float32
        )(x)  # 将上一层的输出作为输入

        # 创建模型实例
        model = models.Model(inputs = inputs , outputs = outputs , name = "FireDetectionCNN_L2")

        return model  # 返回模型
    
    def print_model_summary(self , model) :
        """打印模型摘要信息"""
        print("\n" + "=" * 60)  # 打印分隔线
        print("模型架构摘要")  # 标题
        print("=" * 60)  # 打印分隔线

        model.summary()  # 调用TensorFlow的summary方法打印层信息

        # 计算总参数
        total_params = model.count_params()  # 总参数数量
        # 计算可训练参数（梯度更新的参数）
        trainable_params = sum([w.numpy().size for w in model.trainable_weights])
        # 计算不可训练参数（如BatchNorm的移动平均值）
        non_trainable_params = total_params - trainable_params
        
        print(f"\n📊 参数统计:")  # 打印参数统计标题
        print(f"  总参数: {total_params:,}")  # 打印总参数（带千位分隔符）
        print(f"  可训练参数: {trainable_params:,}")  # 打印可训练参数
        print(f"  不可训练参数: {non_trainable_params:,}")  # 打印不可训练参数

        # 检查是否小于100K（轻量化目标）
        if total_params < 100000 :  # 如果小于10万参数
            print(f"✅ 模型轻量化: {total_params:,} < 100,000 参数")  # 打印成功信息
        else :  # 如果大于等于10万参数
            print(f"⚠️  模型稍大: {total_params:,} > 100,000 参数")  # 打印警告信息

        return total_params , trainable_params , non_trainable_params  # 返回参数统计
    
    def create_mobilenet_model(self) :
        """使用MobileNetV2作为基础模型（迁移学习）"""
        print(" 创建MobileNetV2模型(迁移学习)...")  # 打印开始信息

        # 加载预训练的MobileNetV2基础模型
        base_model = keras.applications.MobileNetV2(
            input_shape = self.input_shape ,  # 输入形状
            include_top = False ,  # 不包含顶部分类层
            weights = 'imagenet' ,  # 使用ImageNet预训练权重
            pooling = 'avg'  # 全局平均池化
        )

        # 冻结基础模型（不更新预训练权重）
        base_model.trainable = False

        # 使用函数式API构建新模型
        inputs = layers.Input(shape = self.input_shape)  # 输入层

        # 预处理（MobileNetV2需要的特定预处理）
        x = keras.applications.mobilenet_v2.preprocess_input(inputs)  # 预处理输入

        # 基础模型（特征提取器）
        x = base_model(x , training = False)  # training=False确保冻结权重

        # 添加新的自定义层
        x = layers.Dense(128 , activation = 'relu')(x)  # 全连接层，128个神经元
        x = layers.Dropout(0.5)(x)  # Dropout层，丢弃率0.5
        x = layers.Dense(64 , activation = 'relu')(x)  # 全连接层，64个神经元
        x = layers.Dropout(0.3)(x)  # Dropout层，丢弃率0.3

        # 输出层
        outputs = layers.Dense(self.num_classes , activation = 'softmax')(x)  # 分类层

        # 创建完整模型
        model = models.Model(inputs = inputs , outputs = outputs , name = "FireDetectionMobileNet")

        return model  # 返回模型
    
def main() :
    """主函数：测试模型创建"""
    print("🔥 秦岭火灾预警系统 - CNN模型测试")  # 打印标题
    print("=" * 50)  # 打印分隔线
    
    model_builder = FireCNNModel()  # 创建模型构建器实例
    
    # 1. 创建基础CNN模型
    print("\n1. 创建基础CNN模型:")  # 打印步骤标题
    model = model_builder.create_model()  # 创建模型
    model = model_builder.compile_model(model)  # 编译模型
    
    # 打印模型摘要
    total_params, trainable_params, _ = model_builder.print_model_summary(model)
    
    # 2. 测试模型推理
    print("\n2. 测试模型推理:")  # 打印步骤标题
    # 创建随机测试输入（1张64×64×3的图片）
    test_input = tf.random.normal([1 , *model_builder.input_shape])
    # 进行预测（verbose=0不显示进度条）
    prediction = model.predict(test_input , verbose = 0)
    
    print(f"   输入形状: {test_input.shape}")  # 打印输入形状
    print(f"   输出形状: {prediction.shape}")  # 打印输出形状
    print(f"   预测值: {prediction[0]}")  # 打印预测概率分布
    
    # 3. 创建带正则化的模型
    print("\n3. 创建带正则化的CNN模型:")  # 打印步骤标题
    model_l2 = model_builder.create_model_with_regularization()  # 创建带正则化模型
    model_l2 = model_builder.compile_model(model_l2)  # 编译模型
    
    model_builder.print_model_summary(model_l2)  # 打印模型摘要
    
    print("\n✅ 模型创建成功!")  # 打印成功信息
    print("\n🎯 下一步:")  # 打印下一步提示
    print("  运行 fire_model_trainer.py 开始训练")  # 具体步骤

if __name__ == "__main__" :  # 如果直接运行此脚本
    main()  # 执行主函数