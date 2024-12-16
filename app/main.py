# app/main.py
from fastapi import FastAPI, UploadFile, File, Depends, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles  # 导入 StaticFiles
from sqlmodel import Session, select, delete
from typing import List
import shutil
import os
from .database import create_db_and_tables, get_session
from .models import Task
from .schemas import TaskRead
from .tasks import transcode_video, task_manager
from .utils import UPLOAD_DIR, OUTPUT_DIR, ZIP_DIR, create_zip
from .logger import logger
import uuid
import json

app = FastAPI()

# 挂载静态文件
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("应用启动，数据库表已创建")

@app.post("/upload/", response_model=List[TaskRead])
async def upload_files(
    background_tasks: BackgroundTasks,  # 正确声明，放在前面
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_session)
):
    logger.info(f"收到上传请求，共 {len(files)} 个文件")
    tasks = []
    for file in files:
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        task = Task(filename=unique_filename, status="pending")
        session.add(task)
        session.commit()
        session.refresh(task)
        tasks.append(task)
        logger.info(f"文件 {unique_filename} 已上传，任务 ID: {task.id}")

    # Enqueue transcoding tasks
    for task in tasks:
        input_file = os.path.join(UPLOAD_DIR, task.filename)
        output_filename = f"transcoded_{task.filename}.mp4"
        output_file = os.path.join(OUTPUT_DIR, output_filename)
        background_tasks.add_task(transcode_video, task.id, input_file, output_file)
        logger.info(f"任务 ID: {task.id} 已加入后台任务队列")

    return tasks

@app.get("/tasks/", response_model=List[TaskRead])
def get_tasks(session: Session = Depends(get_session)):
    tasks = session.exec(select(Task)).all()
    logger.info(f"获取任务列表，共 {len(tasks)} 个任务")
    return tasks

@app.get("/download/{task_id}")
def download_file(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if task and task.output_file and os.path.exists(task.output_file):
        logger.info(f"任务 ID: {task_id} 的输出文件已下载")
        return FileResponse(task.output_file, media_type='application/octet-stream', filename=os.path.basename(task.output_file))
    logger.warning(f"任务 ID: {task_id} 的输出文件未找到")
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/download_zip/")
def download_zip(session: Session = Depends(get_session)):
    tasks = session.exec(select(Task).where(Task.status == "completed")).all()
    file_paths = [task.output_file for task in tasks if task.output_file]
    if not file_paths:
        logger.warning("没有可打包的文件")
        raise HTTPException(status_code=404, detail="No files to zip")
    zip_name = f"transcoded_{uuid.uuid4()}.zip"
    zip_path = create_zip(file_paths, zip_name)
    logger.info(f"创建 ZIP 文件: {zip_path}")
    return FileResponse(zip_path, media_type='application/zip', filename=zip_name)

@app.delete("/files/{file_type}/{filename}")
def delete_file(file_type: str, filename: str, session: Session = Depends(get_session)):
    if file_type == "upload":
        path = os.path.join(UPLOAD_DIR, filename)
        task = session.exec(select(Task).where(Task.filename == filename)).first()
    elif file_type == "output":
        path = os.path.join(OUTPUT_DIR, filename)
        task = session.exec(select(Task).where(Task.output_file == path)).first()
    elif file_type == "zip":
        path = os.path.join(ZIP_DIR, filename)
        task = None  # ZIP 文件没有对应的任务
    else:
        logger.error(f"无效的文件类型: {file_type}")
        raise HTTPException(status_code=400, detail="Invalid file type")

    if os.path.exists(path):
        os.remove(path)
        logger.info(f"删除文件: {path}")
        if task:
            session.delete(task)
            session.commit()
            logger.info(f"删除任务 ID: {task.id} 对应的文件")
        return {"status": "deleted"}
    logger.warning(f"删除失败，文件未找到: {path}")
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/clear_all/")
def clear_all(session: Session = Depends(get_session)):
    try:
        # 定义要清空的目录
        directories = [UPLOAD_DIR, OUTPUT_DIR, ZIP_DIR]
        for directory in directories:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                        logger.info(f"删除文件: {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        logger.info(f"删除目录: {file_path}")
                logger.info(f"已清空目录: {directory}")

        # 删除所有任务记录
        delete_stmt = delete(Task)
        session.exec(delete_stmt)
        session.commit()
        logger.info("已删除所有任务记录")

        return {"status": "success", "message": "所有文件和任务记录已清空"}
    except Exception as e:
        logger.exception("清空所有文件和任务记录时发生异常")
        raise HTTPException(status_code=500, detail="清空失败")

@app.get("/list_zip/")
def list_zip_files():
    try:
        files = os.listdir(ZIP_DIR)
        zip_files = [file for file in files if file.endswith('.zip')]
        logger.info(f"列出 ZIP 文件，共 {len(zip_files)} 个")
        return zip_files
    except Exception as e:
        logger.exception(f"列出 ZIP 文件时发生异常: {e}")
        raise HTTPException(status_code=500, detail="Unable to list ZIP files")

@app.get("/task_id/{output_filename}")
def get_task_id(output_filename: str, session: Session = Depends(get_session)):
    output_file_path = os.path.join(OUTPUT_DIR, output_filename)
    task = session.exec(select(Task).where(Task.output_file == output_file_path)).first()
    if task:
        logger.info(f"根据输出文件名 {output_filename} 获取任务 ID: {task.id}")
        return {"task_id": task.id}
    logger.warning(f"根据输出文件名 {output_filename} 未找到任务")
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/", response_class=HTMLResponse)
async def get_home():
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html"), encoding='utf-8') as f:
        logger.info("加载主页")
        return HTMLResponse(content=f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await task_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 可以根据需要处理来自前端的消息
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        await task_manager.disconnect(websocket)

