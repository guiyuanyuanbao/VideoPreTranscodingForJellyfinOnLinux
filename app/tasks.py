# app/tasks.py
import asyncio
import json
import os
from fastapi import WebSocket
import ffmpeg
from sqlmodel import Session
from .database import engine
from .models import Task
from .utils import OUTPUT_DIR
from .logger import logger

class TaskManager:
    def __init__(self):
        self.connections = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.connections.add(websocket)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            self.connections.remove(websocket)
        logger.info(f"WebSocket 连接断开，当前连接数: {len(self.connections)}")

    async def send_progress(self, message: str):
        async with self.lock:
            to_remove = set()
            for connection in self.connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.exception(f"发送 WebSocket 消息失败: {e}")
                    to_remove.add(connection)
            self.connections -= to_remove

task_manager = TaskManager()

async def transcode_video(task_id: int, input_file: str, output_file: str):
    logger.info(f"开始转码任务 ID: {task_id}, 输入文件: {input_file}, 输出文件: {output_file}")
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if not task:
            logger.error(f"任务 ID: {task_id} 未找到")
            return
        task.status = "processing"
        session.add(task)
        session.commit()

    try:
        # 获取视频总时长
        probe_data = ffmpeg.probe(input_file)
        duration = float(probe_data['format']['duration'])
        logger.info(f"任务 ID: {task_id} 视频时长: {duration} 秒")

        # 启动 FFmpeg 转码进程
        process = (
            ffmpeg
            .input(input_file)
            .output(
                output_file,
                vcodec='libx264',
                acodec='aac',
                strict='experimental',
                threads=44
            )
            .global_args('-progress', 'pipe:1', '-nostats')
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        # 定义协程以读取 stderr
        async def read_stderr(pipe):
            while True:
                line = await asyncio.get_event_loop().run_in_executor(None, pipe.readline)
                if not line:
                    break
                decoded_line = line.decode('utf-8').strip()
                if decoded_line:
                    logger.error(f"FFmpeg 错误输出 (任务 ID: {task_id}): {decoded_line}")

        # 启动协程读取 stderr
        stderr_task = asyncio.create_task(read_stderr(process.stderr))

        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, process.stdout.readline)
            if not line:
                break
            decoded_line = line.decode('utf-8').strip()
            logger.debug(f"任务 ID: {task_id} FFmpeg 输出: {decoded_line}")

            if decoded_line.startswith("out_time_ms"):
                out_time_ms = float(decoded_line.split('=')[1])
                progress = min(out_time_ms / (duration * 1e6), 1.0) * 100

                with Session(engine) as session:
                    task = session.get(Task, task_id)
                    if task:
                        task.progress = progress
                        session.add(task)
                        session.commit()
                        logger.info(f"任务 ID: {task.id} 进度: {task.progress:.2f}%")
                        # 发送进度到前端
                        progress_message = {
                            "task_id": task.id,
                            "progress": task.progress,
                            "status": task.status
                        }
                        await task_manager.send_progress(json.dumps(progress_message))

        process.wait()
        await stderr_task  # 确保 stderr 已被读取

        with Session(engine) as session:
            task = session.get(Task, task_id)
            if task:
                if process.returncode == 0:
                    task.status = "completed"
                    task.progress = 100.0
                    task.output_file = output_file
                    logger.info(f"任务 ID: {task.id} 转码完成")
                else:
                    task.status = "failed"
                    logger.error(f"任务 ID: {task.id} 转码失败，返回码: {process.returncode}")
                session.add(task)
                session.commit()
                # 发送完成状态到前端
                completion_message = {
                    "task_id": task.id,
                    "progress": task.progress,
                    "status": task.status
                }
                await task_manager.send_progress(json.dumps(completion_message))

    except Exception as e:
        logger.exception(f"任务 ID: {task_id} 转码过程中发生异常: {e}")
        with Session(engine) as session:
            task = session.get(Task, task_id)
            if task:
                task.status = "failed"
                session.add(task)
                session.commit()
                # 发送失败状态到前端
                failure_message = {
                    "task_id": task.id,
                    "status": task.status,
                    "error": str(e)
                }
                await task_manager.send_progress(json.dumps(failure_message))

