"""
数据增强脚本
"""

import os 
# 设置 TensorFlow 日志级别为只显示错误信息, 减少冗余输出
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import random
import numpy as np 
from pathlib import Path 
from PIL import Image , ImageOps , ImageEnhance , ImageFilter
import time 
from datetime import datetime 
from config import config  # 导入配置模块

class FireDataAugmentor :
    """数据增强器"""
    
    def __init__(self) :
        """初始化增强器"""
        self.raw_dir = config.RAW_DATA_DIR  # 原始数据目录
        self.aug_dir = config.AUG_DATA_DIR  # 增强数据目录
        self.target_size = config.IMAGE_SIZE  # 目标图像尺寸

        # 增强配置
        self.augmentations_per_image = config.AUGMENTATION['augmentations_per_image']  # 每张原图增强数量
        self.target_per_class = config.AUGMENTATION['target_per_class']  # 每类目标数量

        # 增强方法列表
        self.augmentation_methods = [
            'rotate' , 'flip' , 'brightness' , 'contrast' , 
            'color' , 'blur' , 'sharpness' , 'zoom' , 'shift' , 'noise'
        ]

        # 统计信息字典
        self.stats = {
            'original_count' : 0 ,  # 原始图片总数
            'augmented_count' : 0 ,  # 增强图片总数
            'total_count' : 0 ,  # 总图片数
            'class_stats' : {}  # 各类别统计信息
        }

    def print_current_stats(self) :
        """打印当前原始数据的统计信息"""
        print("\n  当前原始数据统计:")
        print("-" * 40)  # 打印分隔线

        total_original = 0  # 原始图片总数
        for class_name in config.CLASS_NAMES :  # 遍历所有类别
            class_dir = self.raw_dir / class_name  # 当前类别的原始数据目录

            if class_dir.exists() :  # 如果目录存在
                count = 0  # 当前类别的图片计数
                for item in class_dir.iterdir() :  # 遍历目录中的所有文件
                    if item.is_file() :  # 如果是文件
                        ext_lower = item.suffix.lower()  # 获取小写文件扩展名
                        # 检查是否是支持的图片格式
                        if ext_lower in ['.jpg', '.jpeg', '.png'] :
                            count += 1  # 计数加1

                # 打印当前类别的图片数量
                print(f"  {class_name:12}: {count:3d} 张") 
                total_original += count  # 累加到总数
                # 保存统计信息
                self.stats['class_stats'][class_name] = {
                    'original' : count ,  # 原始图片数
                    'expected_augmented' : count * (self.augmentations_per_image + 1)  # 预期增强总数
                }
            else :  # 如果目录不存在
                print(f"  {class_name:12}: 文件夹不存在") 

        print("-" * 40)  # 打印分隔线
        print(f"  总计原始图片: {total_original} 张")  # 打印原始图片总数
        
        # 计算预期增强总数
        expected_total = total_original * (self.augmentations_per_image + 1)
        print(f"  预期增强总数: {expected_total:,} 张")  # 打印预期总数(带千位分隔符)
        print(f"  项目目标总数: {config.AUGMENTATION['total_target']:,} 张")  # 打印项目目标总数

        self.stats['original_count'] = total_original  # 保存到统计信息
        return total_original  # 返回原始图片总数
    
    def setup_augmentation_folders(self) :
        """创建增强数据的文件夹结构"""
        print(" 创建增强数据文件夹......") 

        created_folders = []  # 已创建的文件夹列表
        for class_name in config.CLASS_NAMES :  # 遍历所有类别
            class_dir = self.aug_dir / class_name  # 当前类别的增强数据目录
            class_dir.mkdir(parents = True , exist_ok = True)  # 创建目录
            # 保存相对路径(相对于项目根目录)
            created_folders.append(str(class_dir.relative_to(config.BASE_DIR)))

        print(f"  创建了 {len(created_folders)} 个增强文件夹:") 
        for folder in created_folders :  # 打印所有创建的文件夹
            print(f"  {folder}")

        return created_folders  # 返回已创建的文件夹列表
    
    def apply_random_augmentation(self , image) :
        """对图片应用随机增强方法"""
        try :
            img = image.copy()  # 创建图片副本, 避免修改原图
            # 随机选择1-3种增强方法
            methods = random.sample(self.augmentation_methods , random.randint(1 , 3))
            for method in methods :  # 依次应用选中的增强方法
                if method == 'rotate' :  # 旋转增强
                    angle = random.uniform(-25 , 25)  # 随机角度(-25到25度)
                    img = img.rotate(angle , resample = Image.BICUBIC , expand = False)  # 执行旋转

                elif method == 'flip' :  # 翻转增强
                    if random.random() > 0.5 :  # 50%概率水平翻转
                        img = ImageOps.mirror(img)
                    else :  # 50%概率垂直翻转
                        img = ImageOps.flip(img) 

                elif method == 'brightness' :  # 亮度增强
                    factor = random.uniform(0.8 , 1.2)  # 随机亮度因子(0.8-1.2)
                    enhancer = ImageEnhance.Brightness(img)  # 创建亮度增强器
                    img = enhancer.enhance(factor)  # 应用亮度增强

                elif method == 'contrast' :  # 对比度增强
                    factor = random.uniform(0.8 , 1.3)  # 随机对比度因子(0.8-1.3)
                    enhancer = ImageEnhance.Contrast(img)  # 创建对比度增强器
                    img = enhancer.enhance(factor) 

                elif method == 'color' :  # 色彩增强
                    factor = random.uniform(0.8 , 1.3)  # 随机色彩因子(0.8-1.3)
                    enhancer = ImageEnhance.Color(img)  # 创建色彩增强器
                    img = enhancer.enhance(factor)

                elif method == 'blur' :  # 模糊增强
                    if random.random() > 0.7 :  # 30%概率应用模糊
                        img = img.filter(ImageFilter.GaussianBlur(radius = random.uniform(0.5 , 1.0)))  # 高斯模糊
 
                elif method == 'sharpness' :  # 锐度增强
                    factor = random.uniform(0.8 , 1.5)  # 随机锐度因子(0.8-1.5)
                    enhancer = ImageEnhance.Sharpness(img)  # 创建锐度增强器
                    img = enhancer.enhance(factor)  # 应用锐度增强

                elif method == 'zoom' :  # 缩放增强
                    zoom_factor = random.uniform(0.9 , 1.1)  # 随机缩放因子(0.9-1.1)
                    new_size = int(self.target_size[0] * zoom_factor)  # 计算新尺寸
                    if new_size != self.target_size[0]:  # 如果尺寸有变化
                        img_resized = img.resize((new_size , new_size) , Image.Resampling.LANCZOS)  # 重新缩放
                        if zoom_factor > 1:  # 如果是放大
                            left = (new_size - self.target_size[0]) // 2  # 计算裁剪左侧位置
                            top = (new_size - self.target_size[1]) // 2  # 计算裁剪顶部位置
                            img = img_resized.crop((left , top , left + self.target_size[0] , top + self.target_size[1]))  # 裁剪
                        else:  # 如果是缩小
                            new_img = Image.new('RGB' , self.target_size , (255 , 255 , 255))  # 创建白色背景
                            left = (self.target_size[0] - new_size) // 2  # 计算粘贴左侧位置
                            top = (self.target_size[1] - new_size) // 2  # 计算粘贴顶部位置
                            new_img.paste(img_resized , (left , top))  # 将缩小图片粘贴到中心
                            img = new_img
                
                elif method == 'shift' :  # 平移增强
                    x_shift = random.randint(-8 , 8)  # 随机水平平移(-8到8像素)
                    y_shift = random.randint(-8 , 8)  # 随机垂直平移(-8到8像素)
                    img = self._image_shift(img , x_shift , y_shift)  # 执行平移
                
                elif method == 'noise':  # 噪声增强
                    if random.random() > 0.8 :  # 20%概率添加噪声
                        img_array = np.array(img)  # 将图片转换为numpy数组
                        noise = np.random.normal(0 , 8 , img_array.shape).astype(np.uint8)  # 生成高斯噪声
                        img_array = np.clip(img_array + noise , 0 , 255)  # 添加噪声并限制像素值范围
                        img = Image.fromarray(img_array.astype(np.uint8))  # 转换回PIL图片
            
            return img  # 返回增强后的图片
        
        except Exception as e :  # 捕获所有异常
            print(f"  增强失败: {e}")  # 打印错误信息
            return image  # 返回原图
        
    def _image_shift(self , img , xoffset , yoffset) :
        """图片平移辅助方法"""
        width , height = img.size  # 获取图片尺寸
        new_img = Image.new('RGB' , (width , height) , (255 , 255 , 255))  # 创建白色背景
        new_img.paste(img , (xoffset , yoffset))  # 粘贴原图到偏移位置
        return new_img  # 返回平移后的图片
    
    def load_and_preprocess_image(self , img_path) :
        """加载并预处理图片"""
        try:
            img = Image.open(img_path)  # 打开图片
            
            # 转换格式
            if img.mode in ('RGBA' , 'LA') :  # 如果有alpha通道
                background = Image.new('RGB' , img.size , (255 , 255 , 255))  # 创建白色背景
                background.paste(img , mask = img.split()[-1])  # 粘贴并保留透明度
                img = background
            elif img.mode != 'RGB' :  # 如果不是RGB模式
                img = img.convert('RGB')  # 转换为RGB
            
            # 调整到目标尺寸
            img = img.resize(self.target_size , Image.Resampling.LANCZOS)  # 使用LANCZOS算法重采样
            
            return img  # 返回处理后的图片
            
        except Exception as e:  # 捕获所有异常
            print(f"    ❌ 加载图片失败 {img_path.name}: {e}")  # 打印错误信息
            return None  # 返回None表示失败
    
    def augment_single_class(self , class_name) :
        """增强单个类别的所有图片"""
        input_dir = self.raw_dir / class_name  # 输入目录(原始图片)
        output_dir = self.aug_dir / class_name  # 输出目录(增强图片)
        
        if not input_dir.exists() :  # 如果输入目录不存在
            print(f"  ⚠️  跳过不存在的文件夹: {input_dir}")  # 打印警告信息
            return 0  # 返回0表示没有增强任何图片
        
        # 获取所有原图（按编号排序）
        image_files = []  # 图片文件列表
        for ext in ['.jpg' , '.jpeg' , '.png'] :  # 遍历支持的扩展名
            # 按 fire_0001.jpg 这样的模式搜索
            pattern = f"{class_name}_*{ext}"  # 构建文件名模式
            image_files.extend(sorted(input_dir.glob(pattern)))  # 添加找到的文件
            image_files.extend(sorted(input_dir.glob(pattern.upper())))  # 添加大写扩展名文件
        
        # 排序确保顺序（按文件名小写排序）
        image_files.sort(key = lambda x: x.name.lower())
        
        if not image_files:  # 如果没有找到文件
            print(f"  ⚠️  文件夹中没有图片: {input_dir}")  # 打印警告
            print(f"    尝试查找任何图片...")  # 打印提示
            # 尝试查找任何图片文件
            for ext in ['.jpg' , '.jpeg' , '.png']:  # 遍历扩展名
                image_files.extend(input_dir.glob(f"*{ext}"))  # 查找所有该扩展名文件
                image_files.extend(input_dir.glob(f"*{ext.upper()}"))  # 查找大写扩展名
            image_files.sort()  # 按文件名排序
        
        if not image_files:  # 如果仍然没有找到
            print(f"  ❌ 仍然没有找到图片")  # 打印错误信息
            return 0  # 返回0
        
        print(f"  📁 {class_name}: 找到 {len(image_files)} 张原图")  # 打印找到的原图数量
        
        class_augmented_count = 0  # 当前类别的增强图片计数
        start_time = time.time()  # 记录开始时间
        
        # 处理每张原图
        for img_idx , img_path in enumerate(image_files , 1) :  # 枚举所有图片(从1开始)
            print(f"    [{img_idx:3d}/{len(image_files)}] 处理: {img_path.name}")  # 打印处理进度
            
            # 加载原图
            original_img = self.load_and_preprocess_image(img_path)  # 加载并预处理
            if original_img is None:  # 如果加载失败
                continue  # 跳过这张图片
            
            # 保存原图（作为增强数据的一部分）
            base_name = img_path.stem  # 获取文件名不带扩展名, 如 fire_0001
            original_output_path = output_dir / f"{base_name}_original.jpg"  # 输出路径
            original_img.save(original_output_path , quality = 95 , optimize = True)  # 保存原图
            class_augmented_count += 1  # 计数加1
            
            # 生成增强图片
            for aug_idx in range(1 , self.augmentations_per_image + 1) :  # 循环生成增强图片
                # 应用随机增强
                augmented_img = self.apply_random_augmentation(original_img)
                
                # 保存增强图片
                output_path = output_dir / f"{base_name}_aug{aug_idx:03d}.jpg"  # 输出路径
                augmented_img.save(output_path , quality = 100 , optimize = False)  # 保存增强图片
                class_augmented_count += 1  # 计数加1
                
                # 每10张显示一次进度
                if aug_idx % 10 == 0 :  # 每10张
                    print(f"      已生成 {aug_idx:3d}/{self.augmentations_per_image} 张增强图片")  # 打印进度
        
        elapsed_time = time.time() - start_time  # 计算耗时
        print(f"  ✅ {class_name}: 生成 {class_augmented_count:,} 张图片，耗时 {elapsed_time:.1f} 秒")  # 打印结果
        print(f"      平均速度: {class_augmented_count/elapsed_time:.1f} 张/秒")  # 打印平均速度
        
        # 更新统计
        if class_name not in self.stats['class_stats'] :  # 如果还没有该类别的统计
            self.stats['class_stats'][class_name] = {}  # 创建空字典
        self.stats['class_stats'][class_name]['augmented'] = class_augmented_count  # 保存增强数量
        
        return class_augmented_count  # 返回当前类别的增强图片数量
    
    def augment_all_classes(self) :
        """增强所有类别的图片"""
        print("\n🚀 开始数据增强...")
        print("=" * 60)  # 打印分隔线
        
        # 创建输出文件夹
        self.setup_augmentation_folders()
        
        total_augmented = 0  # 总增强图片数
        start_total_time = time.time()  # 记录总开始时间
        
        # 增强每个类别
        for class_name in config.CLASS_NAMES :  # 遍历所有类别
            print(f"\n🔄 处理类别: {class_name}")  # 打印当前处理的类别
            
            # 检查是否有原始图片
            class_dir = self.raw_dir / class_name  # 原始数据目录
            if not class_dir.exists():  # 如果目录不存在
                print(f"  ⚠️  跳过: 原始文件夹不存在")  # 打印警告
                continue  # 跳过当前类别
            
            # 执行增强
            count = self.augment_single_class(class_name)  # 增强当前类别
            total_augmented += count  # 累加到总数
        
        total_time = time.time() - start_total_time  # 计算总耗时
        self.stats['augmented_count'] = total_augmented  # 保存增强总数
        self.stats['total_count'] = self.stats['original_count'] + total_augmented  # 计算并保存总图片数
        
        print("\n" + "=" * 60)  # 打印分隔线
        print("🎯 数据增强完成!")  # 打印完成信息
        print("=" * 60)  # 打印分隔线
        
        # 打印详细统计
        self.print_final_stats(total_time)  # 打印最终统计
        
        return total_augmented  # 返回总增强图片数
    
    def print_final_stats(self , total_time) :
        """打印最终的详细统计信息"""
        print("\n📈 增强结果详细统计:")
        print("-" * 60)  # 打印分隔线
        
        # 表头
        print(f"{'类别':12} {'原图':>6} {'增强':>8} {'总计':>8} {'完成度':>8}")  # 打印表格标题
        print("-" * 60)  # 打印分隔线
        
        total_original = 0  # 原始图片总数
        total_augmented = 0  # 增强图片总数
        total_all = 0  # 所有图片总数
        
        for class_name in config.CLASS_NAMES :  # 遍历所有类别
            if class_name in self.stats['class_stats'] :  # 如果有该类别的统计信息
                stats = self.stats['class_stats'][class_name]  # 获取统计信息
                original = stats.get('original' , 0)  # 获取原始图片数
                augmented = stats.get('augmented' , 0)  # 获取增强图片数
                expected = stats.get('expected_augmented' , 0)  # 获取预期总数
                
                total = original + augmented  # 计算当前类别总数
                completion = (total / expected * 100) if expected > 0 else 0  # 计算完成度百分比
                
                # 打印当前类别的统计信息
                print(f"{class_name:12} {original:6d} {augmented:8,d} {total:8,d} {completion:7.1f}%")
                
                total_original += original  # 累加原始图片数
                total_augmented += augmented  # 累加增强图片数
                total_all += total  # 累加总图片数
        
        print("-" * 60)  # 打印分隔线
        # 打印总计行
        print(f"{'总计':12} {total_original:6d} {total_augmented:8,d} {total_all : 8 , d}")
        
        # 计算总体完成度
        expected_total = total_original * (self.augmentations_per_image + 1)  # 计算预期总数
        # 计算完成度百分比(实际总数/预期总数×100)
        overall_completion = (total_all / expected_total * 100) if expected_total > 0 else 0
        
        print(f"\n📊 总体统计:")  # 打印总体统计标题
        print(f"  原始图片: {total_original : , } 张")  # 打印原始图片总数
        print(f"  增强图片: {total_augmented : , } 张")  # 打印增强图片总数
        print(f"  总计图片: {total_all : , } 张")  # 打印所有图片总数
        print(f"  预期总数: {expected_total : , } 张")  # 打印预期总数
        print(f"  完成度: {overall_completion : .1f }%")  # 打印完成度百分比
        print(f"  总耗时: {total_time : .1f } 秒")  # 打印总耗时
        print(f"  处理速度: {total_all/total_time : .1f } 张/秒")  # 打印处理速度
        
        # 检查是否达到项目目标
        target = config.AUGMENTATION['total_target']  # 获取项目目标总数
        if total_all >= target:  # 如果达到或超过目标
            print(f"\n✅ 超额完成目标! (目标: {target : , } 张)")  # 打印成功信息
        else:  # 如果未达到目标
            print(f"\n⚠️  未达到目标，还差 {target - total_all : , } 张")  # 打印差距信息

def main():
    """主函数"""
    print("🔥 秦岭火灾预警系统 - 数据增强器")  # 打印标题
    print("=" * 60)  # 打印分隔线
    # 打印配置信息
    print(f"配置: 每张原图生成 {config.AUGMENTATION['augmentations_per_image']} 张增强图片")
    print(f"目标: {config.AUGMENTATION['total_target'] : ,} 张训练数据")
    print("=" * 60)  # 打印分隔线
    
    augmentor = FireDataAugmentor()  # 创建增强器实例
    
    # 显示当前原始数据统计
    total_original = augmentor.print_current_stats()
    
    if total_original == 0:  # 如果没有原始图片
        print("\n❌ 没有找到原始图片!")  # 打印错误信息
        print(f"请将图片放入: {config.RAW_DATA_DIR}")  # 打印提示信息
        return  # 退出程序
    
    # 询问用户确认
    print(f"\n⚠️  即将生成约 {total_original * (config.AUGMENTATION['augmentations_per_image'] + 1):,} 张图片")
    print(f"   输出目录: {config.AUG_DATA_DIR}")
    
    response = input("\n是否开始数据增强? (y/n): ").strip().lower()  # 获取用户输入
    
    if response == 'y':  # 如果用户确认
        print("\n" + "=" * 60)  # 打印分隔线
        
        # 开始增强所有类别
        total_augmented = augmentor.augment_all_classes()
        
        print("\n🎯 下一步:")  # 打印下一步提示
        print(f"1. 增强图片保存在: {config.AUG_DATA_DIR}")  # 提示1
        print("2. 运行 fire_data_loader.py 测试数据加载")  # 提示2
        print("3. 开始训练模型")  # 提示3
        
        # 显示最终文件夹结构
        print(f"\n📁 最终文件夹结构 : ")  # 打印标题
        for class_name in config.CLASS_NAMES :  # 遍历所有类别
            aug_dir = config.AUG_DATA_DIR / class_name  # 增强数据目录
            if aug_dir.exists():  # 如果目录存在
                count = len(list(aug_dir.glob("*.jpg")))  # 统计jpg文件数量
                print(f"  {aug_dir.relative_to(config.BASE_DIR)} : {count:,} 张")  # 打印路径和数量
    else:  # 如果用户取消
        print("操作已取消")  # 打印取消信息

if __name__ == "__main__" :  # 如果直接运行此文件
    main()  # 执行主函数