"""
内存映射数据加载器 - 保留所有数据，极速访问
修复版本：解决shape<unknown>问题
"""

import os
# 设置TensorFlow日志级别为只显示错误，减少冗余输出
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np
from pathlib import Path
import tensorflow as tf
tf.get_logger().setLevel('ERROR')  # 设置TensorFlow日志级别
from config import config  # 导入配置模块

class MMapFireDataLoader :
    """内存映射数据加载器类 - 7140张图片的极速解决方案（修复版）"""
    
    def __init__(self) :
        """初始化内存映射数据加载器"""
        self.aug_dir = config.AUG_DATA_DIR  # 增强数据目录
        self.image_size = config.IMAGE_SIZE  # 图片尺寸(64, 64)
        self.num_classes = config.get_num_classes()  # 类别数量(4)
        self.batch_size = config.TRAINING['batch_size']  # 批次大小(24)
        
        # 内存映射缓存（核心优化：避免重复读取文件）
        self._mmap_cache = None  # 图片数据内存映射缓存
        self._labels_cache = None  # 标签数据缓存
        self._indices_cache = None  # 索引缓存
        
        # 统计信息
        self.total_images = 0  # 总图片数
        self.class_distribution = {}  # 类别分布统计
        
    def build_memory_mapped_dataset(self) :
        """
        构建内存映射数据集
        将所有图片预处理后存入内存映射文件，避免重复IO（一次性操作）
        """
        print("🧠 构建内存映射数据集...")  # 打印开始信息
        
        # 1. 收集所有图片路径
        all_paths = []  # 所有图片路径列表
        all_labels = []  # 所有标签列表
        
        # 遍历所有类别
        for class_idx , class_name in enumerate(config.CLASS_NAMES) :
            class_dir = self.aug_dir / class_name  # 当前类别目录
            if not class_dir.exists() :  # 如果目录不存在
                continue  # 跳过当前类别
                
            files = list(class_dir.glob("*.jpg"))  # 获取所有jpg文件
            self.class_distribution[class_name] = len(files)  # 记录类别分布
            self.total_images += len(files)  # 累加总图片数
            
            # 将当前类别的所有文件路径和标签添加到列表
            for file_path in files :
                all_paths.append(str(file_path))  # 添加文件路径（转换为字符串）
                all_labels.append(class_idx)  # 添加类别索引作为标签
            
            print(f"  {class_name}: {len(files)} 张")  # 打印当前类别数量
        
        print(f"✅ 总共 {self.total_images} 张图片")  # 打印总图片数
        
        # 2. 创建内存映射文件存放预处理后的图片数据
        mmap_file = Path("fire_data_mmap.dat")  # 内存映射文件名
        
        if mmap_file.exists() and mmap_file.stat().st_size > 0 :  # 如果内存映射文件已存在且非空
            # 如果已存在内存映射文件，直接加载（节省时间）
            print("📂 加载已存在的内存映射文件...")  # 打印加载信息
            self._load_existing_mmap(mmap_file , all_labels)  # 调用加载方法
        else :
            # 创建新的内存映射文件（第一次运行或文件不存在）
            print("⚡ 创建新的内存映射文件（一次性操作）...")  # 打印创建信息
            self._create_new_mmap(mmap_file , all_paths , all_labels)  # 调用创建方法
        
        return self  # 返回自身以支持链式调用
    
    def _create_new_mmap(self , mmap_file , paths , labels) :
        """创建新的内存映射文件（将所有图片预处理后存入文件）"""
        import time  # 导入时间模块用于计时
        start_time = time.time()  # 记录开始时间
        
        # 图片尺寸和数据类型
        img_height , img_width = self.image_size  # 解包图片尺寸
        channels = 3  # RGB三通道
        dtype = np.float32  # 数据类型：32位浮点数
        
        # 创建内存映射文件（在磁盘上创建文件，可以像内存数组一样访问）
        shape = (len(paths) , img_height , img_width , channels)  # 形状：(图片数, 高, 宽, 通道)
        mmap_array = np.memmap(  # 创建内存映射数组
            mmap_file ,  # 文件路径
            dtype = dtype ,  # 数据类型
            mode = 'w+' ,  # 读写模式（创建新文件）
            shape = shape  # 数组形状
        )
        
        # 预处理并存储所有图片
        from PIL import Image  # 导入PIL用于图片处理
        
        for i , (img_path , label) in enumerate(zip(paths , labels)) :  # 同时遍历路径和标签
            try :
                # 1. 加载图片
                img = Image.open(img_path)  # 打开图片
                if img.mode != 'RGB' :  # 如果不是RGB格式
                    img = img.convert('RGB')  # 转换为RGB
                
                # 2. 调整尺寸（使用最近邻插值，最快速度）
                img = img.resize(self.image_size , Image.NEAREST)  # 调整到目标尺寸
                img_array = np.array(img , dtype = dtype) / 255.0  # 转换为numpy数组并归一化
                
                # 3. 存储到内存映射文件（直接写入磁盘）
                mmap_array[i] = img_array  # 将处理后的图片存入数组第i个位置
                
                # 进度显示（每处理500张显示一次）
                if (i + 1) % 500 == 0 :  # 如果处理了500的倍数张
                    elapsed = time.time() - start_time  # 计算已用时间
                    speed = (i + 1) / elapsed  # 计算处理速度
                    print(f"  已处理 {i + 1}/{len(paths)} 张，速度: {speed : .1f}张/秒")  # 打印进度
                    
            except Exception as e :  # 捕获所有异常
                print(f"  跳过图片 {img_path}: {e}")  # 打印错误信息
                continue  # 跳过当前图片，继续处理下一张
        
        # 强制写入磁盘（确保所有数据都写入文件）
        mmap_array.flush()  # 刷新缓冲区
        del mmap_array  # 删除引用，释放内存
        
        # 保存标签到单独的文件
        labels_file = Path("fire_labels.npy")  # 标签文件名
        np.save(labels_file , np.array(labels , dtype = np.int32))  # 保存为numpy二进制文件
        
        # 保存索引（用于随机打乱）
        indices = np.arange(len(paths))  # 创建索引数组[0, 1, 2, ..., n-1]
        indices_file = Path("fire_indices.npy")  # 索引文件名
        np.save(indices_file , indices)  # 保存索引
        
        total_time = time.time() - start_time  # 计算总耗时
        print(f"✅ 内存映射文件创建完成，耗时: {total_time : .1f}秒")  # 打印耗时
        print(f"   文件大小: {mmap_file.stat().st_size / 1024 / 1024 : .1f} MB")  # 打印文件大小
        
        # 加载到缓存（创建完成后立即加载）
        self._load_existing_mmap(mmap_file , labels)  # 调用加载方法
    
    def _load_existing_mmap(self , mmap_file , labels = None) :
        """加载已存在的内存映射文件（快速启动）"""
        img_height , img_width = self.image_size  # 解包图片尺寸
        channels = 3  # RGB三通道
        
        shape = (self.total_images , img_height , img_width , channels)  # 形状
        
        # 加载内存映射文件（只读模式，避免修改）
        self._mmap_cache = np.memmap(  # 创建只读内存映射
            mmap_file ,  # 文件路径
            dtype = np.float32 ,  # 数据类型
            mode = 'r' ,  # 只读模式
            shape = shape  # 数组形状
        )
        
        # 加载标签
        if labels is None :  # 如果没有传入标签
            labels_file = Path("fire_labels.npy")  # 标签文件名
            if labels_file.exists() :  # 如果标签文件存在
                self._labels_cache = np.load(labels_file)  # 加载标签文件
            else :  # 如果标签文件不存在
                raise FileNotFoundError("标签文件不存在")  # 抛出异常
        else :  # 如果传入了标签
            self._labels_cache = np.array(labels , dtype = np.int32)  # 将标签转换为numpy数组
        
        # 加载或创建索引
        indices_file = Path("fire_indices.npy")  # 索引文件名
        if indices_file.exists() :  # 如果索引文件存在
            self._indices_cache = np.load(indices_file)  # 加载索引文件
        else :  # 如果索引文件不存在
            self._indices_cache = np.arange(self.total_images)  # 创建新索引
        
        print(f"✅ 内存映射文件加载完成")  # 打印完成信息
        print(f"   图片数据: {self._mmap_cache.shape}")  # 打印图片数据形状
        print(f"   标签数据: {self._labels_cache.shape}")  # 打印标签数据形状
    
    def create_optimized_tf_dataset(self , validation_split = 0.15) :
        """
        创建优化的TensorFlow数据集
        修复版：解决shape<unknown>问题
        """
        print("⚡ 创建优化TF数据集（内存映射版）...")  # 打印开始信息
        
        # 1. 分割索引
        num_samples = self.total_images  # 总样本数
        indices = self._indices_cache.copy()  # 复制索引（避免修改原数据）
        np.random.shuffle(indices)  # 随机打乱索引
        
        split_idx = int(num_samples * (1 - validation_split))  # 计算训练集分割点
        train_indices = indices[:split_idx]  # 训练集索引
        val_indices = indices[split_idx:]  # 验证集索引
        
        print(f"📊 数据集分割:")  # 打印分割信息
        print(f"  训练集: {len(train_indices)} 张")  # 打印训练集大小
        print(f"  验证集: {len(val_indices)} 张")  # 打印验证集大小
        
        # 2. 修复关键：使用tf.py_function而不是tf.numpy_function
        # 并且手动设置输出形状（解决TensorFlow的shape<unknown>问题）
        
        def get_batch(indices_batch) :
            """直接从内存映射获取批次数据"""
            # 从内存映射读取（使用numpy索引）
            batch_images = self._mmap_cache[indices_batch.numpy()]  # 通过索引获取图片批次
            batch_labels = self._labels_cache[indices_batch.numpy()]  # 通过索引获取标签批次
            
            # 转换为one-hot编码
            batch_labels_onehot = tf.one_hot(batch_labels , self.num_classes)  # 转换为one-hot
            
            return batch_images , batch_labels_onehot  # 返回批次数据
        
        def tf_get_batch_wrapper(indices_batch) :
            """TensorFlow包装函数 - 关键修复点"""
            # 使用tf.py_function，保持TensorFlow上下文
            images , labels = tf.py_function(  # 将Python函数包装为TensorFlow操作
                func = get_batch ,  # Python函数
                inp = [indices_batch] ,  # 输入参数（索引批次）
                Tout = [tf.float32 , tf.float32]  # 输出类型
            )
            
            # 🔥 关键修复：手动设置形状信息（解决shape<unknown>问题）
            batch_size = tf.shape(indices_batch)[0]  # 获取动态批次大小
            image_shape = (*self.image_size , 3)  # 图片形状：64x64x3
            label_shape = (self.num_classes ,)  # 标签形状：4
            
            # 设置静态形状（告诉TensorFlow预期的形状）
            images.set_shape([None , *image_shape])  # 动态批次维度 + 图片形状
            labels.set_shape([None , *label_shape])  # 动态批次维度 + 标签形状
            
            # 轻微数据增强（仅在训练时，提高模型鲁棒性）
            if tf.random.uniform(()) > 0.5 :  # 50%概率
                images = tf.image.random_flip_left_right(images)  # 随机水平翻转
            
            return images , labels  # 返回处理后的批次
        
        # 3. 创建TF数据集
        # 训练集
        train_dataset = tf.data.Dataset.from_tensor_slices(train_indices)  # 从索引创建数据集
        train_dataset = train_dataset.shuffle(  # 打乱数据
            buffer_size = min(5000 , len(train_indices)) ,  # 缓冲区大小（最大5000）
            reshuffle_each_iteration = True ,  # 每次迭代重新打乱
            seed = 42  # 随机种子（保证可重复性）
        )
        train_dataset = train_dataset.batch(self.batch_size , drop_remainder = True)  # 批次化
        train_dataset = train_dataset.map(  # 映射处理函数
            tf_get_batch_wrapper ,  # 包装函数
            num_parallel_calls = tf.data.AUTOTUNE ,  # 自动并行数
            deterministic = False  # 非确定性（允许乱序执行）
        )
        train_dataset = train_dataset.prefetch(tf.data.AUTOTUNE)  # 预取数据（优化性能）
        
        # 验证集
        val_dataset = tf.data.Dataset.from_tensor_slices(val_indices)  # 从索引创建验证集
        val_dataset = val_dataset.batch(self.batch_size , drop_remainder = True)  # 批次化
        val_dataset = val_dataset.map(  # 映射处理函数
            tf_get_batch_wrapper ,  # 包装函数
            num_parallel_calls = tf.data.AUTOTUNE ,  # 自动并行数
            deterministic = False  # 非确定性
        )
        val_dataset = val_dataset.prefetch(tf.data.AUTOTUNE)  # 预取数据
        
        # 计算步数
        train_steps = len(train_indices) // self.batch_size  # 训练步数 = 训练样本数 // 批次大小
        val_steps = max(1 , len(val_indices) // self.batch_size)  # 验证步数至少为1
        
        print(f"📈 批次配置:")  # 打印批次配置
        print(f"  训练步数/轮: {train_steps}")  # 打印训练步数
        print(f"  验证步数/轮: {val_steps}")  # 打印验证步数
        
        return train_dataset , val_dataset , train_steps , val_steps  # 返回数据集和步数
    
    def create_simple_tf_dataset(self , validation_split = 0.15) :
        """
        创建简化TensorFlow数据集（修复版）
        使用所有7140张图片
        """
        print("📦 创建简化TF数据集（修复版，使用全部数据）...")  # 打印开始信息
        
        # 使用所有数据（直接访问内存映射数组）
        all_images = self._mmap_cache  # 内存映射数组（引用，不复制数据）
        all_labels = self._labels_cache  # 标签数组
        
        print(f"✅ 从内存映射加载 {len(all_images)} 张图片")  # 打印加载信息
        
        # 分割数据集
        num_samples = len(all_images)  # 总样本数
        indices = np.arange(num_samples)  # 创建索引数组[0, 1, ..., n-1]
        np.random.shuffle(indices)  # 随机打乱索引
        
        split_idx = int(num_samples * (1 - validation_split))  # 计算分割点
        train_indices = indices[:split_idx]  # 训练集索引
        val_indices = indices[split_idx:]  # 验证集索引
        
        print(f"📊 数据集分割:")  # 打印分割信息
        print(f"  训练集: {len(train_indices)} 张")  # 训练集大小
        print(f"  验证集: {len(val_indices)} 张")  # 验证集大小
        
        # 创建TensorFlow数据集
        def create_dataset(indices) :
            """创建数据集子集"""
            # 直接从内存映射读取（不复制数据，使用tf.constant引用）
            images = tf.constant(all_images[indices])  # 创建常量Tensor（引用数据）
            labels = tf.constant(all_labels[indices])  # 创建常量Tensor（引用数据）
            
            dataset = tf.data.Dataset.from_tensor_slices((images , labels))  # 从张量创建数据集
            dataset = dataset.shuffle(buffer_size = len(indices))  # 打乱数据
            
            # 数据增强函数
            def augment_image(image , label) :
                # 随机水平翻转（50%概率）
                if tf.random.uniform(()) > 0.5 :
                    image = tf.image.random_flip_left_right(image)
                
                # 随机亮度调整（50%概率）
                if tf.random.uniform(()) > 0.5 :
                    image = tf.image.random_brightness(image , max_delta = 0.1)
                
                # 转换为one-hot编码
                label_onehot = tf.one_hot(label , self.num_classes)
                
                return image , label_onehot
            
            dataset = dataset.map(augment_image , num_parallel_calls = tf.data.AUTOTUNE)  # 应用增强
            dataset = dataset.batch(self.batch_size)  # 批次化
            dataset = dataset.prefetch(tf.data.AUTOTUNE)  # 预取
            dataset = dataset.repeat()  # 重复（无限循环）
            
            return dataset  # 返回数据集
        
        train_dataset = create_dataset(train_indices)  # 创建训练集
        val_dataset = create_dataset(val_indices)  # 创建验证集
        
        # 计算步数
        train_steps = len(train_indices) // self.batch_size  # 训练步数
        val_steps = max(1 , len(val_indices) // self.batch_size)  # 验证步数
        
        print(f"📈 批次配置:")  # 打印批次配置
        print(f"  训练步数/轮: {train_steps}")  # 训练步数
        print(f"  验证步数/轮: {val_steps}")  # 验证步数
        print(f"  批次大小: {self.batch_size}")  # 批次大小
        
        return train_dataset , val_dataset , train_steps , val_steps  # 返回数据集和步数

def main() :
    """测试内存映射加载器（主函数）"""
    print("🧪 测试内存映射数据加载器")  # 测试标题
    print("=" * 50)  # 分隔线
    
    loader = MMapFireDataLoader()  # 创建内存映射加载器实例
    
    # 构建数据集
    loader.build_memory_mapped_dataset()  # 构建内存映射数据集
    
    # 测试数据集创建
    print("\n测试简化数据集...")  # 测试信息
    train_dataset , val_dataset , train_steps , val_steps = loader.create_simple_tf_dataset()  # 创建数据集
    
    print(f"✅ 数据集创建成功")  # 成功信息
    print(f"  训练步数: {train_steps}")  # 打印训练步数
    print(f"  验证步数: {val_steps}")  # 打印验证步数
    
    # 测试批次获取（获取第一个批次）
    print("\n测试批次获取...")  # 批次测试信息
    for images , labels in train_dataset.take(1) :  # 从数据集中取第一个批次
        print(f"  图片形状: {images.shape}")  # 打印图片形状
        print(f"  标签形状: {labels.shape}")  # 打印标签形状
        print(f"  数据类型: {images.dtype}")  # 打印数据类型
        break  # 只取一个批次
    
    print("\n✅ 内存映射加载器测试完成")  # 完成信息

if __name__ == "__main__" :  # 如果直接运行此脚本
    main()  # 执行主函数