let selectedServer = null;
let refreshInterval;

// Загрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    loadServers();
    // Обновляем каждые 60 секунд
    refreshInterval = setInterval(loadServers, 60000);
});

async function loadServers() {
    try {
        const response = await fetch('/api/servers');
        const data = await response.json();
        
        displayServers(data.servers);
        
        // Автоматически выбираем первый сервер если нет выбранного
        if (data.servers.length > 0 && !selectedServer) {
            selectServer(data.servers[0]);
        }
        
        // Обновляем детальную информацию если сервер выбран
        if (selectedServer) {
            loadServerDetail(selectedServer.name);
        }
        
    } catch (error) {
        console.error('Error loading servers:', error);
        showError('Ошибка загрузки списка серверов');
    }
}

function displayServers(servers) {
    const container = document.getElementById('serversContainer');
    container.innerHTML = '';
    
    if (servers.length === 0) {
        container.innerHTML = '<div class="col-12"><p class="text-muted">Нет зарегистрированных серверов</p></div>';
        return;
    }
    
    servers.forEach(server => {
        const isOnline = isServerOnline(server);
        const card = createServerCard(server, isOnline);
        container.appendChild(card);
    });
}

function createServerCard(server, isOnline) {
    const card = document.createElement('div');
    card.className = 'col-md-4 mb-3';
    
    const isSelected = selectedServer && selectedServer.id === server.id;
    const borderClass = isSelected ? 'border-primary border-2' : '';
    const onlineClass = isOnline ? 'text-success' : 'text-danger';
    const onlineText = isOnline ? 'Online' : 'Offline';
    const onlineBadge = isOnline ? 'bg-success' : 'bg-danger';
    
    card.innerHTML = `
        <div class="card ${borderClass} server-card" 
             onclick="selectServer(${JSON.stringify(server).replace(/"/g, '&quot;')})"
             style="cursor: pointer; transition: all 0.3s;">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <h5 class="card-title">
                        <i class="fas fa-server ${onlineClass}"></i>
                        ${server.name}
                    </h5>
                    <span class="badge ${onlineBadge}">${onlineText}</span>
                </div>
                
                <p class="card-text">
                    <small class="text-muted">
                        ${server.description || 'Нет описания'}
                    </small>
                </p>
                
                <div class="server-info">
                    <small class="text-muted">
                        <i class="fas fa-clock"></i>
                        Последний контакт: ${server.last_seen ? 
                            formatDateTime(server.last_seen) : 'Никогда'}
                    </small>
                    <br>
                    <small class="text-muted">
                        <i class="fas fa-calendar"></i>
                        Зарегистрирован: ${formatDateTime(server.created_at)}
                    </small>
                </div>
                
                ${server.system_info ? `
                <div class="mt-2">
                    <small class="text-muted">
                        <i class="fas fa-computer"></i>
                        ${server.system_info.platform || ''} ${server.system_info.architecture || ''}
                    </small>
                </div>
                ` : ''}
            </div>
        </div>
    `;
    
    return card;
}

function isServerOnline(server) {
    if (!server.last_seen) return false;
    
    const lastSeen = new Date(server.last_seen);
    const now = new Date();
    const diffMinutes = (now - lastSeen) / (1000 * 60);
    
    // Считаем онлайн если последний контакт был менее 5 минут назад
    return diffMinutes < 5;
}

function selectServer(server) {
    selectedServer = server;
    loadServers(); // Перерисовываем для выделения
    loadServerDetail(server.name);
}

async function loadServerDetail(serverName) {
    try {
        const detailContainer = document.getElementById('serverDetail');
        detailContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Загрузка...</span>
                </div>
                <p class="mt-2">Загрузка информации о сервере...</p>
            </div>
        `;
        
        // Загружаем метрики CPU
        const cpuResponse = await fetch(`/api/metrics/${serverName}?measurement=cpu&range=1h`);
        const cpuData = await cpuResponse.json();
        
        // Загружаем Memory метрики
        const memoryResponse = await fetch(`/api/metrics/${serverName}?measurement=memory&range=1h`);
        const memoryData = await memoryResponse.json();
        
        // Загружаем оповещения для этого сервера
        const alertsResponse = await fetch('/api/alerts?status=active');
        const alertsData = await alertsResponse.json();
        const serverAlerts = alertsData.alerts.filter(alert => 
            alert.server && alert.server.name === serverName
        );
        
        displayServerDetail(serverName, cpuData, memoryData, serverAlerts);
        
    } catch (error) {
        console.error('Error loading server detail:', error);
        document.getElementById('serverDetail').innerHTML = 
            '<p class="text-danger">Ошибка загрузки информации о сервере</p>';
    }
}

function displayServerDetail(serverName, cpuData, memoryData, alerts) {
    const container = document.getElementById('serverDetail');
    
    const latestCpu = cpuData.metrics && cpuData.metrics.length > 0 ? cpuData.metrics[0] : null;
    const latestMemory = memoryData.metrics && memoryData.metrics.length > 0 ? memoryData.metrics[0] : null;
    
    const cpuPercent = latestCpu ? latestCpu.usage_percent : 0;
    const memoryPercent = latestMemory ? latestMemory.usage_percent : 0;
    const memoryUsed = latestMemory ? latestMemory.used_gb : 0;
    const memoryTotal = latestMemory ? latestMemory.total_gb : 0;
    
    // Обновляем прогресс-бары
    updateProgressBars(cpuPercent, memoryPercent, memoryUsed, memoryTotal);
    
    container.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>Основная информация</h6>
                <ul class="list-unstyled">
                    <li><strong>Имя:</strong> ${serverName}</li>
                    <li><strong>Статус:</strong> <span class="badge bg-success">Online</span></li>
                    <li><strong>CPU:</strong> ${cpuPercent}%</li>
                    <li><strong>Память:</strong> ${memoryPercent}% (${memoryUsed} GB / ${memoryTotal} GB)</li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6>Активные оповещения</h6>
                ${alerts.length > 0 ? `
                    <div class="alert alert-warning">
                        <strong>${alerts.length}</strong> активных оповещений
                    </div>
                    <div style="max-height: 150px; overflow-y: auto;">
                        ${alerts.map(alert => `
                            <div class="mb-1">
                                <small>${alert.metric_type}: ${alert.message}</small>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <div class="alert alert-success">
                        Нет активных оповещений
                    </div>
                `}
            </div>
        </div>
        
        <div class="row mt-3">
            <div class="col-12">
                <small class="text-muted">
                    Последнее обновление: ${new Date().toLocaleString('ru-RU')}
                </small>
            </div>
        </div>
    `;
}

function updateProgressBars(cpuPercent, memoryPercent, memoryUsed, memoryTotal) {
    const cpuProgress = document.getElementById('cpuProgress');
    const memoryProgress = document.getElementById('memoryProgress');
    
    if (cpuProgress) {
        cpuProgress.style.width = `${cpuPercent}%`;
        cpuProgress.textContent = `${cpuPercent}%`;
        cpuProgress.className = `progress-bar ${cpuPercent > 80 ? 'bg-danger' : cpuPercent > 60 ? 'bg-warning' : ''}`;
    }
    
    if (memoryProgress) {
        memoryProgress.style.width = `${memoryPercent}%`;
        memoryProgress.textContent = `${memoryPercent}% (${memoryUsed}GB)`;
        memoryProgress.className = `progress-bar ${memoryPercent > 80 ? 'bg-danger' : memoryPercent > 60 ? 'bg-warning' : 'bg-success'}`;
    }
}

function formatDateTime(dateString) {
    if (!dateString) return 'Никогда';
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU');
}

function refreshServers() {
    loadServers();
    showInfo('Список серверов обновлен');
}

// Очистка интервала при уходе со страницы
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

function showError(message) {
    alert('Ошибка: ' + message);
}

function showInfo(message) {
    console.log('Info: ' + message);
}