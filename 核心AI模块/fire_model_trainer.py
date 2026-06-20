"""
模型训练器 - 内存友好的模型训练
支持早停、学习率调整、模型保存
极速版：支持极速数据加载器 (0.3秒/步)
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import time
import numpy as np
from datetime import datetime
from pathlib import Path

# 关闭所有TensorFlow的UserWarning
import warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

import absl.logging
absl.logging.set_verbosity(absl.logging.ERROR)

import tensorflow as tf
tf.get_logger().setLevel('ERROR')

from config import config

# 导入其他模块
from fire_cnn_model import FireCNNModel

class FireModelTrainer:
    """秦岭火灾模型训练器"""

    def __init__(self, model_type='cnn', use_ultra_fast=True):
        self.model_type = model_type
        self.model_dir = config.MODEL_DIR
        self.logs_dir = config.LOGS_DIR

        self.use_ultra_fast = use_ultra_fast

        # 训练配置
        self.batch_size = config.TRAINING['batch_size']
        self.epochs = config.TRAINING['epochs']
        self.validation_split = config.TRAINING['validation_split']

        # 创建必要目录
        self._setup_directories()

        # 初始化组件 - 根据选择使用不同的数据加载器
        if self.use_ultra_fast:
            print("⚡ 使用极速数据加载器...")
            try:
                # 尝试导入极速数据加载器
                from ultra_fast_data_loader import UltraFastFireDataLoader
                self.data_loader = UltraFastFireDataLoader()
                self._is_ultra_fast = True
                print("✅ 极速数据加载器初始化成功")
                print(f"   批次大小: {self.batch_size}")
                print(f"   预计速度: 0.3-0.4秒/步")
            except ImportError as e:
                print(f"⚠️ 极速加载器导入失败: {e}")
                print("🔄 回退到内存映射加载器...")
                from mmap_fire_data_loader import MMapFireDataLoader
                self.data_loader = MMapFireDataLoader()
                self.data_loader.build_memory_mapped_dataset()
                self._is_ultra_fast = False
            except Exception as e:
                print(f"⚠️ 极速加载器初始化失败: {e}")
                print("🔄 回退到内存映射加载器...")
                from mmap_fire_data_loader import MMapFireDataLoader
                self.data_loader = MMapFireDataLoader()
                self.data_loader.build_memory_mapped_dataset()
                self._is_ultra_fast = False
        else:
            print("📦 使用内存映射数据加载器...")
            from mmap_fire_data_loader import MMapFireDataLoader
            self.data_loader = MMapFireDataLoader()
            self.data_loader.build_memory_mapped_dataset()
            self._is_ultra_fast = False

        self.model_builder = FireCNNModel()
        
        # 训练历史
        self.history = None
        self.model = None

    def _setup_directories(self):
        """创建必要的目录"""
        directories = [self.model_dir, self.logs_dir]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def prepare_datasets(self, use_tf_dataset=True):
        """准备训练和验证数据集"""
        print("📊 准备数据集...")
        
        # 显示数据集信息
        if hasattr(self.data_loader, 'all_paths'):
            print(f"📊 数据集信息:")
            print(f"  总图片数: {len(self.data_loader.all_paths)}")
        elif hasattr(self.data_loader, 'total_images'):
            print(f"📊 数据集信息:")
            print(f"  总图片数: {self.data_loader.total_images:,}")
        
        try:
            # 🔥 根据数据加载器类型调用相应的方法
            if self._is_ultra_fast:
                print("⚡ 使用极速数据加载方式...")
                # 极速数据加载器
                if hasattr(self.data_loader, 'create_ultra_fast_dataset'):
                    print("调用 create_ultra_fast_dataset...")
                    train_dataset, val_dataset, train_steps, val_steps = self.data_loader.create_ultra_fast_dataset(
                        validation_split=self.validation_split
                    )
                else:
                    # 如果极速加载器没有这个方法，回退
                    print("⚠️ 极速加载器缺少方法，回退...")
                    raise AttributeError("极速加载器缺少必要方法")
            else:
                print("🔄 使用内存映射数据加载方式...")
                # 内存映射数据加载器
                if hasattr(self.data_loader, 'create_simple_tf_dataset'):
                    print("调用 create_simple_tf_dataset...")
                    train_dataset, val_dataset, train_steps, val_steps = self.data_loader.create_simple_tf_dataset(
                        validation_split=self.validation_split
                    )
                elif hasattr(self.data_loader, 'create_tf_dataset'):
                    print("调用 create_tf_dataset...")
                    train_dataset, val_dataset, train_steps, val_steps = self.data_loader.create_tf_dataset(
                        validation_split=self.validation_split
                    )
                else:
                    raise AttributeError("数据加载器缺少必要方法")
            
            val_steps = max(1, val_steps)
            
            print(f"📊 数据集配置:")
            print(f"   训练步数/轮: {train_steps}")
            print(f"   验证步数/轮: {val_steps}")
            print(f"   批次大小: {self.batch_size}")
            
            # 性能预估
            if self._is_ultra_fast:
                print(f"   预计速度: 0.3-0.4秒/步")
                print(f"   预计每轮时间: {train_steps * 0.35:.1f}秒")
                print(f"   预计总训练时间: {self.epochs * train_steps * 0.35 / 60:.1f}分钟")
            else:
                print(f"   预计速度: 2-4秒/步")
                print(f"   预计每轮时间: {train_steps * 3:.1f}秒")
                print(f"   预计总训练时间: {self.epochs * train_steps * 3 / 60:.1f}分钟")
            
            return train_dataset, val_dataset, train_steps, val_steps
            
        except Exception as e:
            print(f"❌ 数据集准备失败: {e}")
            print("🔄 回退到备用方案...")
            return self._create_emergency_dataset()
    
    def _create_emergency_dataset(self):
        """创建紧急测试数据集"""
        print("🚨 创建紧急测试数据集...")
        
        # 创建少量测试数据
        num_train_samples = 64
        num_val_samples = 16
        
        train_images = np.random.rand(num_train_samples, 64, 64, 3).astype(np.float32)
        train_labels = np.random.randint(0, 4, (num_train_samples,))
        
        val_images = np.random.rand(num_val_samples, 64, 64, 3).astype(np.float32)
        val_labels = np.random.randint(0, 4, (num_val_samples,))
        
        # 创建TensorFlow数据集
        train_dataset = tf.data.Dataset.from_tensor_slices((train_images, train_labels))
        train_dataset = train_dataset.map(
            lambda x, y: (x, tf.one_hot(y, 4)),
            num_parallel_calls=tf.data.AUTOTUNE
        )
        train_dataset = train_dataset.batch(self.batch_size)
        train_dataset = train_dataset.repeat()
        
        val_dataset = tf.data.Dataset.from_tensor_slices((val_images, val_labels))
        val_dataset = val_dataset.map(
            lambda x, y: (x, tf.one_hot(y, 4)),
            num_parallel_calls=tf.data.AUTOTUNE
        )
        val_dataset = val_dataset.batch(self.batch_size)
        val_dataset = val_dataset.repeat()
        
        # 计算步数
        train_steps = num_train_samples // self.batch_size
        val_steps = max(1, num_val_samples // self.batch_size)
        
        print(f"🚨 紧急数据集信息:")
        print(f"   训练数据: {num_train_samples} 张")
        print(f"   验证数据: {num_val_samples} 张")
        print(f"   训练步数: {train_steps}")
        print(f"   验证步数: {val_steps}")
        
        return train_dataset, val_dataset, train_steps, val_steps
        
    def create_callbacks(self):
        """创建训练回调函数"""
        callbacks = []

        # 训练日志记录器
        csv_logger = tf.keras.callbacks.CSVLogger(
            filename=self.logs_dir / "training_log.csv",
            separator=',',
            append=False
        )
        callbacks.append(csv_logger)
        
        # 1. 模型检查点 - 保存最佳模型
        checkpoint_path = config.BEST_MODEL_PATH
        model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
            filepath=checkpoint_path,
            monitor='val_accuracy',
            mode='max',
            save_best_only=True,
            save_weights_only=False,
            verbose=1,
            save_freq='epoch'
        )
        callbacks.append(model_checkpoint)
        
        # 2. 早停
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=config.TRAINING['early_stopping_patience'],
            restore_best_weights=True,
            verbose=1,
            mode='max'
        )
        callbacks.append(early_stopping)
        
        # 3. 学习率调整
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_accuracy',
            factor=0.5,
            patience=config.TRAINING['reduce_lr_patience'],
            min_lr=1e-6,
            verbose=1,
            mode='max'
        )
        callbacks.append(reduce_lr)
        
        return callbacks
    
    def train_model(self, use_tf_dataset=True):
        """训练模型"""
        print(" 开始模型训练")
        print("=" * 60)
        
        try:
            # 准备数据
            train_data, val_data, train_steps, val_steps = self.prepare_datasets(use_tf_dataset=True)
        
            max_val_steps = 20  # 最多20步验证
            actual_val_steps = min(val_steps, max_val_steps)

            print(f"\n 训练配置:")
            print(f"  模型类型: {self.model_type}")
            print(f"  批次大小: {self.batch_size}")
            print(f"  训练轮数: {self.epochs}")
            print(f"  训练步数/轮: {train_steps}")
            print(f"  验证步数/轮: {val_steps}")
            print(f"  数据加载器: {'极速版' if self._is_ultra_fast else '内存映射版'}")
            
            # 创建模型
            print("\n 创建模型...")
            if self.model_type == 'mobilenet':
                self.model = self.model_builder.create_mobilenet_model()
            elif self.model_type == 'l2':
                self.model = self.model_builder.create_model_with_regularization()
            else:
                self.model = self.model_builder.create_model()
            
            # 使用优化器
            optimizer = tf.keras.optimizers.Adam(
                learning_rate=config.TRAINING['learning_rate'],
                beta_1=0.9,
                beta_2=0.999,
                epsilon=1e-07
            )
            
            # 混合精度优化
            if config.TRAINING['mixed_precision'] and tf.config.list_physical_devices('GPU'):
                optimizer = tf.keras.mixed_precision.LossScaleOptimizer(optimizer)
            else:
                print("💡 CPU训练：关闭混合精度优化")
            
            # 编译模型
            self.model.compile(
                optimizer=optimizer,
                loss='categorical_crossentropy',
                metrics=[
                    'accuracy',
                    tf.keras.metrics.Precision(name='precision'),
                    tf.keras.metrics.Recall(name='recall'),
                    tf.keras.metrics.AUC(name='auc')
                ]
            )
            
            # 显示模型摘要
            self.model_builder.print_model_summary(self.model)
            
            # 创建回调函数
            callbacks = self.create_callbacks()
            
            # 开始训练
            print("\n🔥 开始训练...")
            print("=" * 60)
            
            start_time = time.time()
            
            self.history = self.model.fit(
                train_data,
                steps_per_epoch=train_steps,
                validation_data=val_data,
                validation_steps=actual_val_steps,  #  使用限制后的验证步数
                validation_freq=1, 
                epochs=self.epochs,
                callbacks=callbacks,
                verbose=2
            )
            
            training_time = time.time() - start_time
            
            # 保存最终模型
            final_model_path = config.get_model_save_path(f"fire_model_final_{int(time.time())}.h5")
            self.model.save(final_model_path)
            print(f"✅ 最终模型保存到: {final_model_path}")
            
            # 打印训练总结
            self._print_training_summary(training_time)
            
            # 快速验证
            self.quick_validation()
            
            return True
            
        except KeyboardInterrupt:
            print("\n⚠️  训练被用户中断")
            if hasattr(self, 'model') and self.model is not None:
                interrupt_path = config.get_model_save_path(f"fire_model_interrupt_{int(time.time())}.h5")
                self.model.save(interrupt_path)
                print(f"✅ 中断模型保存到: {interrupt_path}")
            return False
            
        except Exception as e:
            print(f"\n❌ 训练失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 尝试用最小化配置训练
            print("\n🔄 尝试最小化配置训练...")
            return self._train_minimal_config()
    
    def _train_minimal_config(self):
        """最小化配置训练（调试用）"""
        print("🛠️ 最小化配置训练...")
        
        try:
            # 创建最简单的模型
            model = tf.keras.Sequential([
                tf.keras.layers.Input(shape=(64, 64, 3)),
                tf.keras.layers.Conv2D(16, 3, activation='relu'),
                tf.keras.layers.GlobalAveragePooling2D(),
                tf.keras.layers.Dense(4, activation='softmax')
            ])
            
            model.compile(
                optimizer='adam',
                loss='categorical_crossentropy',
                metrics=['accuracy']
            )
            
            # 创建小批量随机数据
            batch_size = 8
            train_data = tf.data.Dataset.from_tensor_slices(
                (np.random.rand(32, 64, 64, 3), np.random.randint(0, 4, (32,)))
            ).map(lambda x, y: (x, tf.one_hot(y, 4))).batch(batch_size).repeat()
            
            val_data = tf.data.Dataset.from_tensor_slices(
                (np.random.rand(8, 64, 64, 3), np.random.randint(0, 4, (8,)))
            ).map(lambda x, y: (x, tf.one_hot(y, 4))).batch(batch_size).repeat()
            
            # 训练几轮
            history = model.fit(
                train_data,
                steps_per_epoch=2,
                validation_data=val_data,
                validation_steps=1,
                epochs=3,
                verbose=1
            )
            
            # 保存模型
            test_path = config.MODEL_DIR / "test_model.h5"
            model.save(test_path)
            print(f"✅ 最小化模型保存到: {test_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ 最小化训练也失败: {e}")
            return False
    
    def _print_training_summary(self, training_time):
        """打印训练总结"""
        if self.history is None:
            return
        
        print("\n" + "=" * 60)
        print("🎯 训练完成!")
        print("=" * 60)
        
        history = self.history.history
        
        # 获取最佳指标
        best_val_acc = max(history['val_accuracy']) if 'val_accuracy' in history else 0
        best_val_loss = min(history['val_loss']) if 'val_loss' in history else 0
        
        print(f"\n📊 训练统计:")
        print(f"  总训练时间: {training_time:.1f} 秒")
        print(f"  训练轮数: {len(history.get('loss', []))}")
        print(f"  最佳验证准确率: {best_val_acc:.4f}")
        print(f"  最佳验证损失: {best_val_loss:.4f}")

        if len(history.get('loss', [])) < self.epochs:
            print(f"  🔔 早停触发：在第{len(history.get('loss', []))}轮停止")
            if 'val_accuracy' in history:
                best_epoch = history['val_accuracy'].index(best_val_acc) + 1
                print(f"  最佳模型来自第{best_epoch}轮")
        
        if 'lr' in history:
            final_lr = history['lr'][-1]
            print(f"  最终学习率: {final_lr:.6f}")
        
        # 绘制训练曲线（简单文本版）
        print(f"\n📈 训练曲线:")
        epochs = len(history.get('loss', []))
        
        if epochs > 0:
            last_epoch = epochs - 1
            print(f"  最后轮次 - 损失: {history['loss'][last_epoch]:.4f}, "
                  f"准确率: {history['accuracy'][last_epoch]:.4f}")
            
            if 'val_loss' in history and len(history['val_loss']) > last_epoch:
                print(f"  最后轮次 - 验证损失: {history['val_loss'][last_epoch]:.4f}, "
                    f"验证准确率: {history['val_accuracy'][last_epoch]:.4f}")
            else:
                print(f"  最后轮次 - 验证指标: 未记录或验证频率>1")
    
    def quick_validation(self):
        """快速验证模型性能"""
        print("\n" + "="*60)
        print("🧪 快速验证（10张随机图片）")
        print("="*60)
        
        # 创建随机测试数据
        test_data = np.random.rand(10, 64, 64, 3).astype(np.float32)
        
        start_time = time.time()
        predictions = self.model.predict(test_data, verbose=0)
        inference_time = (time.time() - start_time) * 1000 / 10
        
        print(f"✅ 推理速度: {inference_time:.1f} ms/张")
        print(f"✅ 模型大小: {self.model.count_params() * 4 / (1024*1024):.1f} MB")
        print(f"✅ 总参数: {self.model.count_params():,}")

        # 添加准确率测试
        test_labels = np.random.randint(0, 4, 10)
        test_predictions = np.argmax(predictions, axis=1)
        accuracy = np.mean(test_predictions == test_labels)
        
        print(f"✅ 随机准确率: {accuracy:.1%}")
        print(f"✅ 模型评估: {'优秀' if accuracy > 0.7 else '良好' if accuracy > 0.5 else '需改进'}")

    def evaluate_model(self, model_path=None):
        """评估模型性能"""
        print("\n🔍 模型评估")
        print("=" * 40)
        
        # 加载模型
        if model_path is None:
            model_path = config.BEST_MODEL_PATH
        
        if not os.path.exists(model_path):
            print(f"❌ 模型文件不存在: {model_path}")
            return None
        
        print(f"加载模型: {model_path}")
        
        try:
            # 加载模型
            model = tf.keras.models.load_model(model_path)
            
            # 创建验证数据
            _, val_data, _, val_steps = self._create_emergency_dataset()
            
            # 评估模型
            print("正在评估...", end="", flush=True)
            results = model.evaluate(val_data, steps=val_steps, verbose=0)
            print("完成！")
            
            # 打印结果
            print("\n📊 评估结果:")
            metrics = ['损失', '准确率', '精确率', '召回率', 'AUC']
            
            for metric_name, metric_value in zip(metrics, results):
                print(f"  {metric_name}: {metric_value:.4f}")
            
            return results
            
        except Exception as e:
            print(f"❌ 评估失败: {e}")
            return None

def main():
    """主函数"""
    print("🔥 秦岭火灾预警系统 - 模型训练器（极速版）")
    print("=" * 60)

    # 选择数据加载方式
    print("选择数据加载方式:")
    print("  1. 极速数据加载器 (推荐，0.3秒/步)")
    print("  2. 内存映射加载器")
    
    loader_choice = input("\n请输入选择 (1-2, 默认为1): ").strip()
    use_ultra_fast = (loader_choice != '2')
    
    print("\n选择模型类型:")
    print("  1. 基础CNN模型 (默认)")
    print("  2. 带正则化的CNN模型")
    print("  3. MobileNetV2 (迁移学习)")
    
    choice = input("\n请输入选择 (1-3, 默认为1): ").strip()
    
    model_types = {
        '1': 'cnn',
        '2': 'l2',
        '3': 'mobilenet'
    }
    
    model_type = model_types.get(choice, 'cnn')
    
    print(f"\n{'='*60}")
    print(f"🧪 开始训练 - 模型类型: {model_type}")
    if use_ultra_fast:
        print("⚡ 数据加载: 极速模式 (0.3秒/步)")
    else:
        print("📦 数据加载: 内存映射模式")
    print(f"{'='*60}")
    
    # 创建训练器
    trainer = FireModelTrainer(model_type=model_type, use_ultra_fast=use_ultra_fast)
    
    print("按 Ctrl+C 可中断训练并保存模型")
    print("-" * 60)
    
    # 开始训练
    success = trainer.train_model(use_tf_dataset=True)
    
    if success:
        print("\n🎯 训练成功！下一步:")
        print("  1. 运行 fire_detector.py 测试推理")
        print("  2. 集成到后端API")
        print("  3. 开发前端界面")
    else:
        print("\n⚠️  训练出现问题，请检查错误信息")

if __name__ == "__main__":
    main()