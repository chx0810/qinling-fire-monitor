"""
秦岭安全系统 - 核心配置文件
定义所有全局配置参数
"""

import os 
# 设置 TensorFlow 日志级别为只显示错误信息, 减少冗余输出
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
from pathlib import Path
from datetime import datetime 

class FireConfig :
    """项目配置类"""
    # 注意: 类定义中直接声明的是类属性, 所有实例共享这些属性


    # ================== 基础信息 =====================
    PROJECT_NAME = "秦岭火灾预警系统"  # 项目名称
    VERSION = "1.0.0"  # 版本号
    AUTHOR = "古时月常明"  # 作者
    CREATED_DATE = "2026-01"  # 创建日期


    # ================== 路径配置 =====================
    # 获取项目根目录: 当前文件的父目录的父目录(即项目根目录)
    BASE_DIR = Path(__file__).parent.parent 

    # 数据相关路径
    DATA_DIR = BASE_DIR / "数据与模型" / "datasets"  # 数据总目录
    RAW_DATA_DIR = DATA_DIR / "raw_images"  # 原始图像数据目录
    AUG_DATA_DIR = DATA_DIR / "augmented_data"  # 数据增强后图像目录

    # 模型相关路径
    MODEL_DIR = BASE_DIR / "数据与模型" / "models"  # 模型保存目录
    TRAINED_MODEL_PATH = MODEL_DIR / "fire_detection_model.h5"  # 训练后的模型路径
    BEST_MODEL_PATH = MODEL_DIR / "best_model.h5"  # 最佳模型保存路径

    # 样本路径
    SAMPLES_DIR = BASE_DIR / "数据与模型" / "samples"  # 样本数据目录

    # 日志路径
    LOGS_DIR = BASE_DIR / "logs"  # 日志文件目录


    # ================== 数据集配置 ======================
    # 火灾类别: 定义四种检测类别
    CLASS_NAMES = ['fire' , 'smoke' , 'fire_smoke' , 'normal']
    # 类别到索引的映射字典
    CLASS_TO_IDX = {name : idx for idx , name in enumerate(CLASS_NAMES)}
    # 索引到类别的映射字典
    IDX_TO_CLASS = {idx : name for idx , name in enumerate(CLASS_NAMES)}

    # 各类别的可视化颜色(RGB格式)
    CLASS_COLORS = {
        'fire' : (255 , 0 , 0) ,  # 红色: 火灾
        'smoke' : (128 , 128 , 128) ,  # 灰色: 烟雾
        'fire_smoke' : (255 , 165 , 0) ,  # 橙色: 火灾+烟雾
        'normal' : (0 , 255 , 0)  # 绿色: 正常
    }


    # ==================== 图像处理配置 ===========================
    # 输入图像尺寸: 宽度64像素, 高度64像素
    IMAGE_SIZE = (64 , 64) 
    IMAGE_CHANNELS = 3  # 图像通道数: RGB三通道

    # 数据增强配置 
    AUGMENTATION = {
        'target_per_class' : 1250 ,  # 每类目标图像数量
        'total_target' : 5000 ,  # 总目标图像数量(4类×1250)
        'augmentations_per_image' : 50 ,  # 每张原始图像生成的增强图像数量
        'output_size' : (64 , 64)  # 输出图像尺寸
    } 


    # ===================== 模型训练配置 ===============================
    # 训练参数
    TRAINING = {
        'batch_size' : 24 ,  # 批次大小: 每次训练使用的样本数
        'epochs' : 72 ,  # 训练轮数
        'learning_rate' : 0.001 ,  # 学习率
        'validation_split' : 0.15 ,  # 验证集分割比例
        'early_stopping_patience' : 15 ,  # 早停耐心值: 连续多少轮验证集性能不提升就停止
        'reduce_lr_patience' : 8 ,  # 学习率衰减耐心值

        # 内存优化选项
        'use_generator' : True ,  # 是否使用数据生成器(节省内存)
        'mixed_precision' : False ,  # 是否使用混合精度训练
        'max_workers' : 2 ,  # 最大工作线程数
    }


    # ====================== 模型架构配置 ============================
    # 轻量CNN模型参数
    MODEL_ARCH = {
        'conv_filters' : [16 , 32 , 64] ,  # 卷积层滤波器数量(逐层递增)
        'conv_kernel_size' : (3 , 3) ,  # 卷积核尺寸
        'pool_size' : (2 , 2) ,  # 池化窗口尺寸
        'dense_units' : 32 ,  # 全连接层神经元数量
        'dropout_rate' : 0.45 ,  # Dropout比率(防止过拟合)
        'use_batch_norm' : True ,  # 是否使用批量归一化
    }

    # ======================= CPU优化配置 ========================
    CPU_OPTIMIZATION = {
        'enabled': True,  # 是否启用CPU优化
        'num_intra_threads': 2,  # 内部操作线程数
        'num_inter_threads': 2,  # 并行操作线程数
        'disable_mixed_precision': True,  # CPU上关闭混合精度
        'tf_optimization_level': 2,  # TensorFlow优化级别(1-5)
    }

    # ======================= 性能优化配置 ========================
    PERFORMANCE = {
        # TensorFlow 性能优化
        'tf_autotune' : True ,  # 是否启用自动调优
        'prefetch_buffer' : 4 ,  # 预取缓冲区大小
        'shuffle_buffer' : 5000 ,  # 洗牌缓冲区大小
        'num_parallel_calls' : 2 ,  # 并行调用数
        'drop_remainder' : True ,  # 是否丢弃最后不完整的批次
        'cache_dataset' : False ,  # 是否缓存数据集
        'interleave' : True ,  # 是否交错读取数据
        
        # 系统性能限制
        'max_memory_usage_gb' : 1.0 ,  # 最大内存使用量(GB)
        'max_batch_size' : 32 ,  # 最大批次大小
        'inference_timeout' : 5.0 ,  # 推理超时时间(秒)
        'cache_size' : 100 ,  # 缓存大小
    }

    # ======================= 风险评估配置 =============================
    RISK_ASSESSMENT = {
        'temperature_threshold' : 35.0 ,  # 温度阈值(摄氏度)
        'humidity_threshold' : 30.0 ,  # 湿度阈值(百分比)
        'wind_speed_threshold' : 8.0 ,  # 风速阈值(米/秒)
        'fire_confidence_threshold' : 0.7 ,  # 火灾置信度阈值

        # 风险等级阈值 
        'risk_levels' : {
            'critical' : 70 ,  # 严重风险: ≥70分
            'high' : 50 ,  # 高风险: 50-69分
            'medium' : 30 ,  # 中等风险: 30-49分
            'low' : 0  # 低风险: <30分
        }
    }

    # ========================= 日志配置 ======================================
    LOGGING = {
        'level': 'INFO' ,  # 日志级别: INFO及以上级别的日志会被记录
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s' ,  # 日志格式
        'date_format': '%Y-%m-%d %H:%M:%S' ,  # 日期格式
        'log_file': 'fire_detection.log' ,  # 日志文件名
    }

    # ========================== 辅助方法 ====================================
    @classmethod
    def setup_directories(cls) :
        """创建所有必需的目录"""
        # 需要创建的目录列表
        directories = [
            cls.AUG_DATA_DIR ,  # 增强数据目录
            cls.MODEL_DIR ,  # 模型目录
            cls.SAMPLES_DIR ,  # 样本目录
            cls.LOGS_DIR ,  # 日志目录
            cls.RAW_DATA_DIR ,  # 原始数据目录
        ]

        created_dirs = []  # 用于记录成功创建的目录
        for directory in directories : 
            try :
                # 创建目录: parents=True表示创建父目录, exist_ok=True表示目录已存在时不报错
                directory.mkdir(parents = True, exist_ok = True)
                # 记录相对路径(相对于项目根目录)
                created_dirs.append(str(directory.relative_to(cls.BASE_DIR)))
            except Exception as e :
                # 捕获并打印创建目录时的异常
                print(f" 创建目录失败 {directory} : {e}")
        
        # 如果有目录被创建, 则打印成功信息
        if created_dirs:
            print(" 项目目录初始化完成:")
            for dir_path in created_dirs :
                print(f"    {dir_path}")
        
        return created_dirs  # 返回已创建的目录列表
    
    
    @classmethod 
    def get_model_input_shape(cls) :
        """获取模型输入形状"""
        # 返回模型输入形状: (高度, 宽度, 通道数)
        return (*cls.IMAGE_SIZE , cls.IMAGE_CHANNELS)
    

    @classmethod
    def get_num_classes(cls) :
        """获取类别数量"""
        return len(cls.CLASS_NAMES)  # 返回类别列表的长度

    
    @classmethod
    def print_summary(cls) :
        """打印配置摘要信息"""
        print("\n" + "=" * 60)  # 打印分隔线
        print(f" {cls.PROJECT_NAME} v{cls.VERSION}")  # 打印项目名称和版本
        print("=" * 60)
        
        print("\n 数据配置:")
        print(f"  类别: {cls.CLASS_NAMES}")  # 打印所有类别
        print(f"  图片尺寸: {cls.IMAGE_SIZE}")  # 打印图像尺寸
        print(f"  目标总数: {cls.AUGMENTATION['total_target']}张")  # 打印目标图像总数
        
        print("\n 模型配置:")
        print(f"  批次大小: {cls.TRAINING['batch_size']}")  # 打印批次大小
        print(f"  训练轮数: {cls.TRAINING['epochs']}")  # 打印训练轮数
        print(f"  学习率: {cls.TRAINING['learning_rate']}")  # 打印学习率
        
        print("\n 内存优化:")
        print(f"  使用生成器: {cls.TRAINING['use_generator']}")  # 打印是否使用生成器
        print(f"  混合精度: {cls.TRAINING['mixed_precision']}")  # 打印是否使用混合精度
        
        print("\n 主要路径:")
        print(f"  原始数据: {cls.RAW_DATA_DIR.relative_to(cls.BASE_DIR)}")  # 打印原始数据相对路径
        print(f"  增强数据: {cls.AUG_DATA_DIR.relative_to(cls.BASE_DIR)}")  # 打印增强数据相对路径
        print(f"  模型保存: {cls.MODEL_DIR.relative_to(cls.BASE_DIR)}")  # 打印模型保存相对路径
        
        print("\n 作者信息:")
        print(f"  作者: {cls.AUTHOR}")  # 打印作者
        print(f"  创建日期: {cls.CREATED_DATE}")  # 打印创建日期
        
        print("=" * 60)  # 打印结束分隔线


    @classmethod 
    def get_timestamp(cls) :
        """获取当前时间戳"""
        # 返回格式化的时间戳: 年月日_时分秒
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    

    @classmethod 
    def get_model_save_path(cls , model_name = None) :
        """获取模型保存路径"""
        # 如果未提供模型名, 使用时间戳生成默认名称
        if model_name is None :
            model_name = f"fire_model_{cls.get_timestamp()}.h5"
        return cls.MODEL_DIR / model_name  # 拼接完整路径
    

    @classmethod
    def get_log_file_path(cls) :
        """获取日志文件路径"""
        return cls.LOGS_DIR / cls.LOGGING['log_file']  # 拼接日志文件完整路径
    

# 创建全局配置实例
config = FireConfig()

# 当直接运行此文件时执行以下代码
if __name__ == "__main__" :
    print("🔥 秦岭火灾预警系统 - 配置模块测试")
    print("-" * 50)
    
    # 初始化目录
    config.setup_directories()
    
    # 打印配置摘要
    config.print_summary()
    
    # 测试路径和配置
    print("\n🧪 路径测试:")
    print(f"项目根目录: {config.BASE_DIR}")  # 打印项目根目录
    print(f"模型输入形状: {config.get_model_input_shape()}")  # 打印模型输入形状
    print(f"类别数量: {config.get_num_classes()}")  # 打印类别数量
    
    print("\n✅ 配置模块测试完成")  # 打印完成信息