#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线程管理器 - 统一管理应用中的所有线程
提供线程池、任务队列、资源清理等功能
"""

import time
from typing import Dict, List, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer
from utils.logger import get_logger

logger = get_logger("thread_manager")


class TaskWorker(QObject):
    """任务工作者 - 在线程池中执行任务"""
    
    # 信号定义
    task_started = pyqtSignal(str)  # 任务ID
    task_progress = pyqtSignal(str, int, str)  # 任务ID, 进度, 状态
    task_completed = pyqtSignal(str, object)  # 任务ID, 结果
    task_failed = pyqtSignal(str, str)  # 任务ID, 错误信息
    
    def __init__(self):
        super().__init__()
        self._tasks = {}  # 存储任务信息
        self._lock = Lock()
    
    def execute_task(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        """
        执行任务
        
        Args:
            task_id: 任务唯一标识
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        
        Returns:
            Any: 任务执行结果
        """
        try:
            with self._lock:
                self._tasks[task_id] = {
                    'status': 'running',
                    'start_time': time.time()
                }
            
            self.task_started.emit(task_id)
            logger.debug(f"开始执行任务: {task_id}")
            
            # 执行实际任务
            result = func(*args, **kwargs)
            
            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]['status'] = 'completed'
                    self._tasks[task_id]['end_time'] = time.time()
                    elapsed = self._tasks[task_id]['end_time'] - self._tasks[task_id]['start_time']
                    logger.debug(f"任务完成: {task_id} (耗时: {elapsed:.2f}s)")
            
            self.task_completed.emit(task_id, result)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"任务执行失败: {task_id} - {error_msg}")
            
            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]['status'] = 'failed'
                    self._tasks[task_id]['error'] = error_msg
            
            self.task_failed.emit(task_id, error_msg)
            raise
        finally:
            # 清理任务记录
            with self._lock:
                if task_id in self._tasks:
                    del self._tasks[task_id]


class ThreadManager(QObject):
    """线程管理器"""
    
    # 信号定义
    task_started = pyqtSignal(str)
    task_completed = pyqtSignal(str, object)
    task_failed = pyqtSignal(str, str)
    pool_status_changed = pyqtSignal(int, int)  # 活跃线程数, 总线程数
    
    def __init__(self):
        super().__init__()
        
        # 线程池配置
        self._max_workers = 5  # 默认最大线程数
        self._executor = None
        self._futures: Dict[str, Future] = {}
        self._task_callbacks: Dict[str, Callable] = {}
        self._cleanup_timer = QTimer()
        
        # 任务统计
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        
        # 工作者
        self._worker = TaskWorker()
        self._worker.task_started.connect(self.task_started)
        self._worker.task_completed.connect(self._on_task_completed)
        self._worker.task_failed.connect(self._on_task_failed)
        
        self._init_thread_pool()
        self._setup_cleanup_timer()
        
        logger.info(f"线程管理器初始化完成 (最大线程数: {self._max_workers})")
    
    def _init_thread_pool(self):
        """初始化线程池"""
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="ZzxWorker"
        )
    
    def _setup_cleanup_timer(self):
        """设置清理定时器"""
        self._cleanup_timer.timeout.connect(self._cleanup_completed_futures)
        self._cleanup_timer.start(30000)  # 每30秒清理一次已完成的Future
    
    def set_max_workers(self, max_workers: int):
        """
        设置最大线程数
        
        Args:
            max_workers: 最大线程数
        """
        if max_workers != self._max_workers:
            logger.info(f"调整线程池大小: {self._max_workers} → {max_workers}")
            
            # 关闭旧线程池
            if self._executor:
                self._executor.shutdown(wait=False)
            
            # 创建新线程池
            self._max_workers = max_workers
            self._init_thread_pool()
            
            self.pool_status_changed.emit(len(self._futures), max_workers)
    
    def submit_task(
        self, 
        task_id: str, 
        func: Callable, 
        callback: Optional[Callable] = None,
        *args, 
        **kwargs
    ) -> str:
        """
        提交任务到线程池
        
        Args:
            task_id: 任务唯一标识
            func: 要执行的函数
            callback: 任务完成回调函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        
        Returns:
            str: 任务ID
        """
        if task_id in self._futures:
            logger.warning(f"任务已存在: {task_id}")
            return task_id
        
        # 保存回调函数
        if callback:
            self._task_callbacks[task_id] = callback
        
        # 提交任务到线程池
        future = self._executor.submit(
            self._worker.execute_task,
            task_id, func, *args, **kwargs
        )
        
        self._futures[task_id] = future
        self._total_tasks += 1
        
        # ⭐ 添加完成回调（关键：确保任务完成后调用回调）
        future.add_done_callback(lambda f: self._on_future_done(task_id, f))
        
        # 更新状态
        self.pool_status_changed.emit(len(self._futures), self._max_workers)
        
        logger.debug(f"任务已提交: {task_id} (队列中任务数: {len(self._futures)})")
        return task_id
    
    def _on_future_done(self, task_id: str, future):
        """
        Future完成时的回调处理
        
        Args:
            task_id: 任务ID
            future: Future对象
        """
        try:
            # 从futures字典中移除
            self._futures.pop(task_id, None)
            
            # 获取任务结果
            result = None
            try:
                result = future.result()
            except Exception as e:
                logger.error(f"任务执行异常: {task_id} - {e}")
            
            # 调用回调函数
            callback = self._task_callbacks.pop(task_id, None)
            if callback:
                try:
                    logger.info(f"🎯 [Future回调] 调用回调: {task_id}")
                    callback(task_id, result)
                except Exception as e:
                    logger.error(f"回调执行失败: {task_id} - {e}")
            
            # 更新状态
            self.pool_status_changed.emit(len(self._futures), self._max_workers)
            
        except Exception as e:
            logger.error(f"Future完成处理失败: {task_id} - {e}")
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否成功取消
        """
        if task_id not in self._futures:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        future = self._futures[task_id]
        success = future.cancel()
        
        if success:
            del self._futures[task_id]
            if task_id in self._task_callbacks:
                del self._task_callbacks[task_id]
            
            logger.info(f"任务已取消: {task_id}")
            self.pool_status_changed.emit(len(self._futures), self._max_workers)
        else:
            logger.warning(f"无法取消任务: {task_id} (可能已在执行中)")
        
        return success
    
    def is_task_running(self, task_id: str) -> bool:
        """
        检查任务是否正在运行
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否正在运行
        """
        if task_id not in self._futures:
            return False
        
        future = self._futures[task_id]
        return not future.done()
    
    def get_running_tasks(self) -> List[str]:
        """
        获取正在运行的任务列表
        
        Returns:
            List[str]: 任务ID列表
        """
        return [
            task_id for task_id, future in self._futures.items()
            if not future.done()
        ]
    
    def get_task_count(self) -> Dict[str, int]:
        """
        获取任务统计信息
        
        Returns:
            Dict[str, int]: 包含总数、运行中、已完成、失败数的字典
        """
        running_count = len([f for f in self._futures.values() if not f.done()])
        
        return {
            'total': self._total_tasks,
            'running': running_count,
            'completed': self._completed_tasks,
            'failed': self._failed_tasks
        }
    
    def _on_task_completed(self, task_id: str, result: Any):
        """任务完成处理"""
        self._completed_tasks += 1
        
        # 调用回调函数
        if task_id in self._task_callbacks:
            try:
                callback = self._task_callbacks[task_id]
                callback(task_id, result)
            except Exception as e:
                logger.error(f"任务回调函数执行失败: {task_id} - {e}")
        
        # 发射信号
        self.task_completed.emit(task_id, result)
        
        # 更新状态
        self.pool_status_changed.emit(len(self._futures), self._max_workers)
    
    def _on_task_failed(self, task_id: str, error_msg: str):
        """任务失败处理"""
        self._failed_tasks += 1
        
        # 调用回调函数
        if task_id in self._task_callbacks:
            try:
                callback = self._task_callbacks[task_id]
                callback(task_id, None)  # 失败时传入None
            except Exception as e:
                logger.error(f"任务回调函数执行失败: {task_id} - {e}")
        
        # 发射信号
        self.task_failed.emit(task_id, error_msg)
        
        # 更新状态
        self.pool_status_changed.emit(len(self._futures), self._max_workers)
    
    def _cleanup_completed_futures(self):
        """清理已完成的Future对象"""
        completed_tasks = []
        
        for task_id, future in list(self._futures.items()):
            if future.done():
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            del self._futures[task_id]
            if task_id in self._task_callbacks:
                del self._task_callbacks[task_id]
        
        if completed_tasks:
            logger.debug(f"清理了 {len(completed_tasks)} 个已完成的任务")
            self.pool_status_changed.emit(len(self._futures), self._max_workers)
    
    def shutdown(self, wait: bool = True):
        """
        关闭线程管理器
        
        Args:
            wait: 是否等待所有任务完成
        """
        logger.info(f"关闭线程管理器 (等待任务完成: {wait})...")
        
        # 停止清理定时器
        if self._cleanup_timer:
            self._cleanup_timer.stop()
        
        # 取消所有未完成的任务
        if not wait:
            for task_id in list(self._futures.keys()):
                self.cancel_task(task_id)
        
        # 关闭线程池
        if self._executor:
            self._executor.shutdown(wait=wait)
            
        # 清理资源
        self._futures.clear()
        self._task_callbacks.clear()
        
        logger.info("线程管理器已关闭")


# 全局实例（延迟初始化）
_thread_manager_instance = None
_thread_manager_lock = Lock()


def get_thread_manager() -> ThreadManager:
    """
    获取线程管理器实例（线程安全的延迟初始化）
    
    Returns:
        ThreadManager: 线程管理器实例
    """
    global _thread_manager_instance
    
    if _thread_manager_instance is None:
        with _thread_manager_lock:
            if _thread_manager_instance is None:
                try:
                    _thread_manager_instance = ThreadManager()
                    logger.info("线程管理器全局实例创建成功")
                except Exception as e:
                    logger.error(f"创建线程管理器失败: {e}")
                    raise
    
    return _thread_manager_instance


def shutdown_thread_manager(wait: bool = True):
    """
    关闭全局线程管理器
    
    Args:
        wait: 是否等待所有任务完成
    """
    global _thread_manager_instance
    
    if _thread_manager_instance:
        try:
            _thread_manager_instance.shutdown(wait)
            logger.info("线程管理器已关闭")
        except Exception as e:
            logger.error(f"关闭线程管理器失败: {e}")
        finally:
            _thread_manager_instance = None
