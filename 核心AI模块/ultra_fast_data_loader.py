# ultra_fast_data_loader.py
"""
极速数据加载器 - 7140张图片，目标：0.3-0.5秒/步
"""

import os
# 设置TensorFlow日志级别为只显示错误，减少冗余输出
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
tf.get_logger().setLevel('ERROR')  # 设置TensorFlow日志级别
import numpy as np
from pathlib import Path
from config import config  # 导入配置模块

class UltraFastFireDataLoader :
    """极速版火灾数据加载器类"""
    
    def __init__(self) :
        """初始化极速数据加载器"""
        self.aug_dir = config.AUG_DATA_DIR  # 增强数据目录
        self.image_size = config.IMAGE_SIZE  # 图片尺寸(64, 64)
        self.num_classes = config.get_num_classes()  # 类别数量(4)
        self.batch_size = config.TRAINING['batch_size']  # 批次大小(24)
        
        # 预加载所有图片路径（内存占用很小，只存储路径不存储图片数据）
        self.all_paths , self.all_labels = self._preload_paths()  # 调用预加载方法
        
        print(f"✅ 预加载 {len(self.all_paths)} 张图片路径")  # 打印预加载完成信息
    
    def _preload_paths(self) :
        """预加载所有图片路径（不加载图片数据本身，只存储文件路径）"""
        paths = []  # 图片路径列表
        labels = []  # 标签列表
        
        # 遍历所有类别
        for class_idx , class_name in enumerate(config.CLASS_NAMES) :
            class_dir = self.aug_dir / class_name  # 当前类别目录
            if class_dir.exists() :  # 如果目录存在
                # 加载所有jpg和JPG文件（大小写敏感，Windows上需要）
                files = list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.JPG"))  # 搜索两种大小写格式
                
                # 去重（大小写不敏感，避免重复加载）
                unique_files = []  # 唯一文件列表
                seen = set()  # 已见过的文件名小写集合
                for file in files :  # 遍历所有找到的文件
                    lower_name = file.name.lower()  # 转换为小写
                    if lower_name not in seen :  # 如果没出现过
                        seen.add(lower_name)  # 添加到已见集合
                        unique_files.append(file)  # 添加到唯一文件列表
                
                # 将当前类别的所有文件路径和标签添加到总列表
                paths.extend([str(f) for f in unique_files])  # 路径转换为字符串并添加
                labels.extend([class_idx] * len(unique_files))  # 添加对应数量的类别标签
                
                print(f"  {class_name}: {len(unique_files)} 张")  # 打印当前类别文件数量
        
        return paths , labels  # 返回路径列表和标签列表
    
    def create_ultra_fast_dataset(self , validation_split = 0.2) :
        """创建极速TensorFlow数据集 - 修复版"""
        print("⚡ 创建极速TF数据集(7140张完整数据) - 修复版...")  # 打印开始信息
        
        AUTOTUNE = tf.data.AUTOTUNE  # TensorFlow自动调优参数
        
        # 转换为TensorFlow张量（常量，TensorFlow可优化）
        paths_tensor = tf.constant(self.all_paths)  # 将路径列表转换为常量张量
        labels_tensor = tf.constant(self.all_labels)  # 将标签列表转换为常量张量
        
        # 创建完整数据集（包含所有样本）
        full_dataset = tf.data.Dataset.from_tensor_slices((paths_tensor , labels_tensor))  # 从张量创建数据集
        
        # 🔥 修复1：先缓存所有路径，避免重复读取
        full_dataset = full_dataset.cache()  # 缓存数据集，避免重复I/O
        
        # 🔥 修复2：先分割再处理，确保数据正确（避免处理和分割的顺序问题）
        dataset_size = len(self.all_paths)  # 数据集总大小
        indices = tf.range(dataset_size)  # 创建索引张量 [0, 1, 2, ..., dataset_size-1]
        
        # 随机打乱索引（保证训练集和验证集的随机性）
        indices = tf.random.shuffle(indices)  # 打乱索引顺序
        
        # 计算训练集和验证集的分割点
        split_idx = int(dataset_size * (1 - validation_split))  # 验证集比例为validation_split
        
        train_indices = indices[:split_idx]  # 训练集索引
        val_indices = indices[split_idx:]  # 验证集索引
        
        # 创建训练集（使用tf.gather从总数据中选取训练集部分）
        train_paths = tf.gather(paths_tensor , train_indices)  # 选取训练集路径
        train_labels = tf.gather(labels_tensor , train_indices)  # 选取训练集标签
        
        train_dataset = tf.data.Dataset.from_tensor_slices((train_paths , train_labels))  # 创建训练数据集
        
        # 创建验证集
        val_paths = tf.gather(paths_tensor , val_indices)  # 选取验证集路径
        val_labels = tf.gather(labels_tensor , val_indices)  # 选取验证集标签
        
        val_dataset = tf.data.Dataset.from_tensor_slices((val_paths , val_labels))  # 创建验证数据集
        
        # 🔥 修复3：优化映射函数（使用@tf.function装饰器加速）
        @tf.function  # TensorFlow图模式装饰器，将Python函数转换为TensorFlow计算图
        def parse_image_fast(path , label) :
            """训练集图片处理函数（带数据增强）"""
            # 1. 读取图片文件
            img = tf.io.read_file(path)  # 读取文件内容
            
            # 2. 解码JPEG图片（使用快速解码方法）
            img = tf.image.decode_jpeg(img , channels = 3 , dct_method = 'INTEGER_FAST')  # 快速JPEG解码
            
            # 3. 快速调整尺寸（双线性插值，速度较快）
            img = tf.image.resize(img , self.image_size , method = 'bilinear')  # 调整到目标尺寸
            
            # 4. 归一化到[0,1]范围
            img = tf.cast(img , tf.float32) / 255.0  # 转换为float32并归一化
            
            # 5. 轻微数据增强（仅训练集，50%概率）
            if tf.random.uniform(()) > 0.5 :  # 生成随机数，大于0.5时执行
                img = tf.image.random_flip_left_right(img)  # 随机水平翻转
            
            # 6. 将标签转换为one-hot编码
            label_onehot = tf.one_hot(label , self.num_classes)  # one-hot编码
            
            return img , label_onehot  # 返回处理后的图片和标签
        
        @tf.function
        def parse_image_val(path , label) :
            """验证集图片处理函数（无数据增强）"""
            # 1. 读取图片文件
            img = tf.io.read_file(path)  # 读取文件
            
            # 2. 解码JPEG图片（使用准确解码方法，验证集需要更准确）
            img = tf.image.decode_jpeg(img , channels = 3 , dct_method = 'INTEGER_ACCURATE')  # 准确JPEG解码
            
            # 3. 调整尺寸
            img = tf.image.resize(img , self.image_size , method = 'bilinear')  # 双线性插值
            
            # 4. 归一化
            img = tf.cast(img , tf.float32) / 255.0  # 转换为float32并归一化
            
            # 5. one-hot编码（无数据增强）
            label_onehot = tf.one_hot(label , self.num_classes)  # one-hot编码
            
            return img , label_onehot  # 返回处理后的图片和标签
        
        # 应用映射函数到训练集
        train_dataset = train_dataset.map(
            parse_image_fast ,  # 训练集使用带增强的处理函数
            num_parallel_calls = AUTOTUNE ,  # 自动并行处理
            deterministic = False  # 非确定性（允许乱序执行，提高性能）
        )
        
        # 应用映射函数到验证集
        val_dataset = val_dataset.map(
            parse_image_val ,  # 验证集使用无增强的处理函数
            num_parallel_calls = AUTOTUNE ,  # 自动并行处理
            deterministic = True  # 确定性（验证集需要可重复的结果）
        )
        
        # 🔥 修复4：优化批次和预取
        train_dataset = train_dataset.shuffle(
            buffer_size = min(2000 , len(train_indices)) ,  # 缓冲区大小（不超过2000）
            reshuffle_each_iteration = True  # 每次迭代重新打乱
        )
        
        train_dataset = train_dataset.batch(
            self.batch_size ,  # 批次大小
            drop_remainder = True  # 丢弃不完整的批次（保证批次大小一致）
        )
        
        val_dataset = val_dataset.batch(
            self.batch_size ,  # 批次大小
            drop_remainder = False  # 不丢弃不完整的批次（验证集可以使用部分批次）
        )
        
        # 🔥 修复5：使用cache和prefetch进一步优化
        train_dataset = train_dataset.cache()  # 缓存训练集（避免重复计算）
        train_dataset = train_dataset.prefetch(AUTOTUNE)  # 预取数据（GPU计算时加载下一批）
        
        val_dataset = val_dataset.cache()  # 缓存验证集
        val_dataset = val_dataset.prefetch(AUTOTUNE)  # 预取验证数据
        
        # 🔥 修复6：重复数据集（无限循环，训练时可以不断取数据）
        train_dataset = train_dataset.repeat()  # 训练集无限重复
        val_dataset = val_dataset.repeat()  # 验证集无限重复
        
        # 计算步数（每个epoch需要多少批次）
        train_steps = len(train_indices) // self.batch_size  # 训练步数 = 训练样本数 // 批次大小
        val_steps = max(1 , len(val_indices) // self.batch_size)  # 验证步数至少为1
        
        print(f"📊 数据集配置 (修复版):")  # 打印配置标题
        print(f"  总图片数: {dataset_size}")  # 总图片数
        print(f"  训练集: {len(train_indices)} 张 ({train_steps}步)")  # 训练集大小和步数
        print(f"  验证集: {len(val_indices)} 张 ({val_steps}步)")  # 验证集大小和步数
        print(f"  批次大小: {self.batch_size}")  # 批次大小
        
        # 性能预估
        estimated_time_per_step = 0.35  # 目标：0.35秒/步（经验值）
        print(f"  🎯 目标速度: {estimated_time_per_step : .2f}秒/步")  # 打印目标速度
        print(f"  ⏱️  预计每轮时间: {train_steps * estimated_time_per_step : .1f}秒")  # 预计每轮时间
        
        return train_dataset , val_dataset , train_steps , val_steps  # 返回数据集和步数
    
    def benchmark_speed(self) :
        """速度基准测试（测量数据加载速度）"""
        print("\n⏱️  速度基准测试...")  # 打印测试标题
        
        # 创建数据集
        train_dataset , val_dataset , train_steps , val_steps = self.create_ultra_fast_dataset()
        
        # 测试一个批次的速度
        import time  # 导入时间模块
        start_time = time.time()  # 记录开始时间
        
        # 获取第一个批次进行速度测试
        for batch in train_dataset.take(1) :  # 只取一个批次（take(1)表示取1个批次）
            images , labels = batch  # 解包批次
            batch_time = time.time() - start_time  # 计算批次处理时间
            break  # 只测试一个批次
        
        time_per_batch = batch_time / 1  # 第一个批次的时间（除以1，保持原值）
        time_per_step = time_per_batch  # 每步时间（一个批次就是一步）
        images_per_second = self.batch_size / time_per_step  # 每秒处理的图片数
        
        print(f"📈 性能指标:")  # 性能指标标题
        print(f"  批次处理时间: {time_per_step : .3f} 秒/步")  # 每步时间
        print(f"  图片处理速度: {images_per_second : .1f} 张/秒")  # 每秒图片数
        print(f"  每轮估计时间: {train_steps * time_per_step : .1f} 秒")  # 每轮时间
        print(f"  25轮估计时间: {25 * train_steps * time_per_step / 60 : .1f} 分钟")  # 25轮时间
        
        return time_per_step  # 返回每步时间

def main() :
    """测试极速数据加载器（主函数）"""
    print("🧪 测试极速数据加载器")  # 测试标题
    print("=" * 50)  # 分隔线
    
    loader = UltraFastFireDataLoader()  # 创建极速加载器实例
    
    # 基准测试
    time_per_step = loader.benchmark_speed()  # 运行速度基准测试
    
    if time_per_step < 0.5 :  # 如果每步时间小于0.5秒
        print(f"\n✅ 极速模式就绪！目标：<0.5秒/步，实际：{time_per_step : .3f}秒/步")  # 成功信息
        print("🎯 现在可以运行训练器了！")  # 下一步提示
    else :  # 如果时间大于等于0.5秒
        print(f"\n⚠️  速度较慢：{time_per_step : .3f}秒/步")  # 警告信息
        print("💡 建议调整批次大小或使用GPU训练")  # 建议

if __name__ == "__main__" :  # 如果直接运行此脚本
    main()  # 执行主函数