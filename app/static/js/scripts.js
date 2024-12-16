// app/static/js/scripts.js

let websocket = null;

window.onload = function() {
    fetchTasks();
    fetchFiles();
    setupWebSocket();
};

function setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    websocket = new WebSocket(`${protocol}://${window.location.host}/ws`);
    
    websocket.onopen = function() {
        console.log("WebSocket 连接已建立");
    };
    
    websocket.onmessage = function(event) {
        const message = JSON.parse(event.data);
        console.log("收到WebSocket消息:", message);

        // 如果收到的是清空所有文件和任务记录的消息
        if (message.clear_all) {
            console.log("收到清空所有文件和任务记录的通知");
            fetchTasks();
            fetchFiles();
            return;
        }

        // 如果收到的是任务完成或失败的消息
        if (message.task_id && (message.status === 'completed' || message.status === 'failed')) {
            console.log(`任务 ID: ${message.task_id} 已完成，状态: ${message.status}`);
            // 自动刷新任务列表和文件管理部分
            fetchTasks();
            fetchFiles();
        }

        // 如果收到的是任务处理中的进度更新
        if (message.task_id && message.status === 'processing') {
            updateTaskProgress(message);
        }
    };
    
    websocket.onclose = function() {
        console.log("WebSocket 连接已关闭，尝试重新连接...");
        setTimeout(setupWebSocket, 5000);  // 5秒后重连
    };
    
    websocket.onerror = function(error) {
        console.error("WebSocket 发生错误:", error);
        websocket.close();
    };
}

function uploadFiles() {
    const input = document.getElementById('fileInput');
    const files = input.files;
    if (files.length === 0) {
        alert("请选择要上传的文件");
        console.log("没有选择文件");
        return;
    }

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload/', true);

    // 添加调试日志
    console.log("开始上传文件...");

    xhr.upload.onprogress = function(event) {
        if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            console.log(`上传进度: ${percentComplete.toFixed(2)}%`);
            // 更新进度条
            document.getElementById('uploadProgressContainer').style.display = 'block';
            document.getElementById('uploadProgress').style.width = percentComplete + '%';
            document.getElementById('uploadProgress').innerText = Math.round(percentComplete) + '%';
        }
    };

    xhr.onloadstart = function() {
        // 显示进度条
        document.getElementById('uploadProgressContainer').style.display = 'block';
        document.getElementById('uploadProgress').style.width = '0%';
        document.getElementById('uploadProgress').innerText = '0%';
        console.log("上传开始...");
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            console.log("上传成功");
            // 清空文件选择
            document.getElementById('fileInput').value = "";
            // 自动刷新任务列表和文件管理部分
            fetchTasks();
            fetchFiles();
        } else {
            console.error("上传失败");
            alert("上传失败");
        }
        // 隐藏进度条
        document.getElementById('uploadProgressContainer').style.display = 'none';
    };

    xhr.onerror = function() {
        console.error("上传过程中发生错误");
        alert("上传失败");
        // 隐藏进度条
        document.getElementById('uploadProgressContainer').style.display = 'none';
    };

    xhr.send(formData);
}

async function fetchTasks() {
    const response = await fetch('/tasks/');
    if (response.ok) {
        const tasks = await response.json();
        updateTasksTable(tasks);
    } else {
        console.error("获取任务列表失败");
    }
}

function updateTasksTable(tasks) {
    const tbody = document.getElementById('tasksTable').getElementsByTagName('tbody')[0];
    tbody.innerHTML = '';
    tasks.forEach(task => {
        const row = tbody.insertRow();
        row.id = `task-${task.id}`;  // 添加 ID 以便更新
        row.insertCell(0).innerText = task.id;
        row.insertCell(1).innerText = task.filename;
        row.insertCell(2).innerText = task.status;
        row.insertCell(3).innerText = `${task.progress.toFixed(2)}%`;
        const actionCell = row.insertCell(4);
        if (task.status === 'completed') {
            const downloadLink = document.createElement('a');
            downloadLink.href = `/download/${task.id}`;
            downloadLink.innerText = '下载';
            actionCell.appendChild(downloadLink);
        }
        // 添加详细进度信息的单元格
        const detailCell = row.insertCell(5);
        detailCell.id = `detail-${task.id}`;
        detailCell.innerText = '';
    });
}

function updateTaskProgress(message) {
    const taskId = message.task_id;
    const row = document.getElementById(`task-${taskId}`);
    if (row) {
        // 更新进度
        row.cells[3].innerText = `${message.progress.toFixed(2)}%`;
        // 更新状态
        row.cells[2].innerText = message.status;
        // 更新详细信息
        const detailCell = document.getElementById(`detail-${taskId}`);
        if (message.frame_info) {
            detailCell.innerText = message.frame_info;
        } else {
            detailCell.innerText = 'N/A';
        }
    }
}

async function fetchFiles() {
    console.log("开始获取文件列表...");
    // 获取上传的文件
    const uploadFilesList = document.getElementById('uploadFilesList');
    uploadFilesList.innerHTML = '';
    const uploadFiles = await getFiles('upload');
    console.log("上传文件列表:", uploadFiles);
    uploadFiles.forEach(file => {
        const li = document.createElement('li');
        li.innerText = file;
        const deleteBtn = document.createElement('button');
        deleteBtn.innerText = '删除';
        deleteBtn.onclick = () => deleteFile('upload', file);
        li.appendChild(deleteBtn);
        uploadFilesList.appendChild(li);
    });

    // 获取转码后的文件
    const outputFilesList = document.getElementById('outputFilesList');
    outputFilesList.innerHTML = '';
    const outputFiles = await getFiles('output');
    console.log("转码后文件列表:", outputFiles);
    for (let file of outputFiles) {
        const taskId = await getTaskIdFromFilename(file);
        console.log(`文件 ${file} 对应的任务 ID: ${taskId}`);
        if (taskId !== null) {
            const li = document.createElement('li');
            li.innerText = file;
            const downloadLink = document.createElement('a');
            downloadLink.href = `/download/${taskId}`;
            downloadLink.innerText = '下载';
            const deleteBtn = document.createElement('button');
            deleteBtn.innerText = '删除';
            deleteBtn.onclick = () => deleteFile('output', file);
            li.appendChild(downloadLink);
            li.appendChild(deleteBtn);
            outputFilesList.appendChild(li);
        }
    }

    // 获取ZIP文件
    const zipFilesList = document.getElementById('zipFilesList');
    zipFilesList.innerHTML = '';
    const zipFiles = await getFiles('zip');
    console.log("ZIP文件列表:", zipFiles);
    zipFiles.forEach(file => {
        const li = document.createElement('li');
        li.innerText = file;
        const downloadLink = document.createElement('a');
        downloadLink.href = `/download_zip/`;
        downloadLink.innerText = '下载';
        const deleteBtn = document.createElement('button');
        deleteBtn.innerText = '删除';
        deleteBtn.onclick = () => deleteFile('zip', file);
        li.appendChild(downloadLink);
        li.appendChild(deleteBtn);
        zipFilesList.appendChild(li);
    });
    console.log("文件列表更新完成");
}

async function getFiles(file_type) {
    if (file_type === 'zip') {
        const response = await fetch('/list_zip/');
        if (response.ok) {
            return await response.json();
        }
        return [];
    }

    const response = await fetch('/tasks/');
    if (response.ok) {
        const tasks = await response.json();
        if (file_type === 'upload') {
            return tasks.map(task => task.filename);
        } else if (file_type === 'output') {
            return tasks.filter(task => task.output_file).map(task => task.output_file.split('/').pop());
        }
    }
    return [];
}

async function deleteFile(type, filename) {
    if (!confirm(`确定要删除 "${filename}" 吗？`)) {
        return;
    }

    const response = await fetch(`/files/${type}/${filename}`, {
        method: 'DELETE'
    });
    if (response.ok) {
        alert("删除成功");
        fetchTasks();
        fetchFiles();
    } else {
        alert("删除失败");
    }
}

async function downloadZip() {
    window.location.href = '/download_zip/';
}

// 新增的清空所有文件和任务记录函数
async function clearAll() {
    if (!confirm("确定要清空所有文件和任务记录吗？此操作无法撤销。")) {
        return;
    }

    const response = await fetch('/clear_all/', {
        method: 'POST'
    });

    if (response.ok) {
        const result = await response.json();
        alert(result.message);
        fetchTasks();
        fetchFiles();
    } else {
        try {
            const error = await response.json();
            alert(`清空失败: ${error.detail}`);
        } catch (e) {
            alert("清空失败: 未知错误");
        }
    }
}

async function getTaskIdFromFilename(filename) {
    const response = await fetch(`/task_id/${filename}`);
    if (response.ok) {
        const data = await response.json();
        return data.task_id;
    }
    return null;
}

