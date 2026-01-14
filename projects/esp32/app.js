// ESP32 Universal Constructor - Main JavaScript
// robotpit.com

// Global State
let currentPin = null;
let pinConfigs = {};
let pinActions = {};
let blocks = [];
let ws = null;
let connected = false;

// ESP32 Pin Definitions
const ESP32_PINS = {
    digital: [2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33],
    adc: [32, 33, 34, 35, 36, 39],
    pwm: [2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27],
    disabled: [0, 1, 3, 6, 7, 8, 9, 10, 11],
    inputOnly: [34, 35, 36, 39]
};

// Device Types with Actions
const DEVICE_ACTIONS = {
    'motor_dc': [
        {id: 'speed', name: 'Установить скорость', params: [{name: 'Скорость (%)', type: 'range', min: 0, max: 100}]},
        {id: 'direction', name: 'Сменить направление', params: []},
        {id: 'stop', name: 'Остановить', params: []},
        {id: 'ramp', name: 'Плавный разгон', params: [
            {name: 'От (%)', type: 'range', min: 0, max: 100}, 
            {name: 'До (%)', type: 'range', min: 0, max: 100}, 
            {name: 'Время (мс)', type: 'number', min: 100, max: 10000}
        ]}
    ],
    'servo': [
        {id: 'angle', name: 'Повернуть на угол', params: [{name: 'Угол (°)', type: 'range', min: 0, max: 180}]},
        {id: 'sweep', name: 'Качаться', params: [
            {name: 'От (°)', type: 'range', min: 0, max: 180}, 
            {name: 'До (°)', type: 'range', min: 0, max: 180}, 
            {name: 'Скорость', type: 'range', min: 1, max: 10}
        ]},
        {id: 'center', name: 'В центр (90°)', params: []}
    ],
    'led': [
        {id: 'on', name: 'Включить', params: []},
        {id: 'off', name: 'Выключить', params: []},
        {id: 'blink', name: 'Мигать', params: [{name: 'Интервал (мс)', type: 'number', min: 50, max: 5000}]},
        {id: 'fade', name: 'Плавное затухание', params: [{name: 'Время (мс)', type: 'number', min: 100, max: 5000}]},
        {id: 'brightness', name: 'Яркость', params: [{name: 'Яркость (%)', type: 'range', min: 0, max: 100}]}
    ],
    'relay': [
        {id: 'on', name: 'Включить', params: []},
        {id: 'off', name: 'Выключить', params: []},
        {id: 'toggle', name: 'Переключить', params: []},
        {id: 'pulse', name: 'Импульс', params: [{name: 'Длительность (мс)', type: 'number', min: 100, max: 10000}]}
    ],
    'buzzer': [
        {id: 'beep', name: 'Пищать', params: [
            {name: 'Частота (Hz)', type: 'number', min: 100, max: 5000}, 
            {name: 'Длительность (мс)', type: 'number', min: 50, max: 5000}
        ]},
        {id: 'melody', name: 'Мелодия', params: [{name: 'Тип', type: 'select', options: ['Сирена', 'Звонок', 'Тревога']}]},
        {id: 'off', name: 'Выключить', params: []}
    ]
};

// Initialize
window.onload = function() {
    generatePinList();
    loadFromStorage();
    setupTabSwitching();
};

// Setup Tab Switching
function setupTabSwitching() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

// Tab Switching
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById('tab-' + tabName).classList.add('active');
}

// Generate Pin List
function generatePinList() {
    const pinList = document.getElementById('pinList');
    const allPins = [...new Set([...ESP32_PINS.digital, ...ESP32_PINS.adc])].sort((a,b) => a-b);
    
    let html = '';
    allPins.forEach(pin => {
        const disabled = ESP32_PINS.disabled.includes(pin);
        const config = pinConfigs[pin];
        
        html += `
            <div class="pin-item ${disabled ? 'disabled' : ''} ${config ? 'active' : ''}" 
                 onclick="${disabled ? '' : `selectPin(${pin})`}">
                <div class="pin-info">
                    <div class="pin-circle"></div>
                    <div>
                        <div><strong>GPIO ${pin}</strong></div>
                        ${config ? `<div class="pin-type">${config.deviceName || config.device}</div>` : ''}
                    </div>
                </div>
                ${config ? '<span style="color:#3fb950">✓</span>' : ''}
            </div>
        `;
    });
    
    pinList.innerHTML = html;
}

// Select Pin
function selectPin(pin) {
    currentPin = pin;
    
    const isADC = ESP32_PINS.adc.includes(pin);
    const isPWM = ESP32_PINS.pwm.includes(pin);
    const isInputOnly = ESP32_PINS.inputOnly.includes(pin);
    
    let html = `
        <div class="config-section">
            <h3>Основные настройки</h3>
            
            <div class="form-group">
                <label>Выбранный пин:</label>
                <input type="text" value="GPIO ${pin}" readonly style="background:#1f2937">
            </div>
            
            <div class="form-group">
                <label>Тип устройства:</label>
                <select id="deviceType" onchange="updateDeviceConfig()">
                    <option value="">-- Выбери устройство --</option>
                    ${!isInputOnly ? '<optgroup label="Выходы (OUTPUT)">' : ''}
                    ${isPWM ? '<option value="motor_dc">🚗 Мотор DC (PWM)</option>' : ''}
                    ${isPWM ? '<option value="servo">🎯 Сервопривод</option>' : ''}
                    ${!isInputOnly ? '<option value="led">💡 LED / Светодиод</option>' : ''}
                    ${!isInputOnly ? '<option value="relay">⚡ Реле</option>' : ''}
                    ${isPWM ? '<option value="buzzer">🔊 Пищалка</option>' : ''}
                    ${!isInputOnly ? '</optgroup>' : ''}
                    <optgroup label="Входы (INPUT)">
                        <option value="button">🔘 Кнопка</option>
                        <option value="switch">🎚️ Переключатель</option>
                        ${isADC ? '<option value="potentiometer">🎛️ Потенциометр</option>' : ''}
                        ${isADC ? '<option value="sensor_temp">🌡️ Датчик температуры</option>' : ''}
                        ${isADC ? '<option value="sensor_light">☀️ Датчик освещённости</option>' : ''}
                    </optgroup>
                </select>
            </div>
            
            <div class="form-group">
                <label>Название устройства:</label>
                <input type="text" id="deviceName" placeholder="Например: Вентилятор">
            </div>
            
            <div id="extraParams"></div>
            
            <button class="btn btn-success" style="width:100%; margin-top:10px;" onclick="applyPinConfig()">
                ✓ Применить настройки
            </button>
        </div>
    `;
    
    document.getElementById('pinConfigPanel').innerHTML = html;
    
    // Load existing config
    if (pinConfigs[pin]) {
        document.getElementById('deviceType').value = pinConfigs[pin].device;
        document.getElementById('deviceName').value = pinConfigs[pin].deviceName || '';
        updateDeviceConfig();
    }
}

// Update device-specific config
function updateDeviceConfig() {
    const device = document.getElementById('deviceType').value;
    let html = '';
    
    if (device === 'servo') {
        html = `
            <div class="form-group">
                <label>Минимальный угол:</label>
                <input type="number" id="servoMin" value="0" min="0" max="180">
            </div>
            <div class="form-group">
                <label>Максимальный угол:</label>
                <input type="number" id="servoMax" value="180" min="0" max="180">
            </div>
        `;
    }
    
    document.getElementById('extraParams').innerHTML = html;
}

// Apply Pin Configuration
function applyPinConfig() {
    if (!currentPin) return;
    
    const device = document.getElementById('deviceType').value;
    const deviceName = document.getElementById('deviceName').value;
    
    if (!device) {
        alert('⚠️ Выбери тип устройства!');
        return;
    }
    
    pinConfigs[currentPin] = {
        pin: currentPin,
        device: device,
        deviceName: deviceName || `GPIO${currentPin}`,
        params: {}
    };
    
    // Add device-specific params
    if (device === 'servo') {
        pinConfigs[currentPin].params.min = document.getElementById('servoMin').value;
        pinConfigs[currentPin].params.max = document.getElementById('servoMax').value;
    }
    
    generatePinList();
    showActionsPanel();
    saveToStorage();
    
    alert(`✅ Пин GPIO ${currentPin} настроен как ${deviceName || device}!`);
}

// Show Actions Panel
function showActionsPanel() {
    if (!pinConfigs[currentPin]) {
        document.getElementById('actionsPanel').innerHTML = '<div class="empty-state">Сначала настрой пин ←</div>';
        return;
    }
    
    const device = pinConfigs[currentPin].device;
    const actions = DEVICE_ACTIONS[device];
    
    if (!actions) {
        document.getElementById('actionsPanel').innerHTML = '<div class="empty-state">Для входных устройств настройте условия в блок-схемах →</div>';
        return;
    }
    
    // Initialize actions array if not exists
    if (!pinActions[currentPin]) {
        pinActions[currentPin] = [];
    }
    
    let html = `
        <div style="margin-bottom: 15px;">
            <strong style="color:#58a6ff;">${pinConfigs[currentPin].deviceName}</strong>
            <small style="color:#8b949e; display:block;">GPIO ${currentPin}</small>
        </div>
    `;
    
    // Show existing action steps
    pinActions[currentPin].forEach((action, idx) => {
        html += generateActionStepHTML(idx, action);
    });
    
    // Add new action button
    html += `
        <button class="btn btn-primary" style="width:100%;" onclick="addActionStep()">
            ➕ Добавить действие
        </button>
    `;
    
    document.getElementById('actionsPanel').innerHTML = html;
}

// Generate Action Step HTML
function generateActionStepHTML(idx, action) {
    const device = pinConfigs[currentPin].device;
    const actions = DEVICE_ACTIONS[device];
    const actionDef = actions.find(a => a.id === action.type);
    
    let html = `
        <div class="action-step">
            <div class="step-header">
                <div class="step-number">${idx + 1}</div>
                <div class="step-actions">
                    <button class="icon-btn" onclick="moveAction(${idx}, -1)" title="Вверх">▲</button>
                    <button class="icon-btn" onclick="moveAction(${idx}, 1)" title="Вниз">▼</button>
                    <button class="icon-btn" onclick="deleteAction(${idx})" title="Удалить">🗑️</button>
                </div>
            </div>
            
            <div class="step-content">
                <div class="form-group">
                    <label>Действие:</label>
                    <select onchange="updateAction(${idx}, this.value)">
                        ${actions.map(a => `<option value="${a.id}" ${a.id === action.type ? 'selected' : ''}>${a.name}</option>`).join('')}
                    </select>
                </div>
    `;
    
    // Add parameter inputs
    if (actionDef && actionDef.params.length > 0) {
        actionDef.params.forEach((param, pidx) => {
            const value = action.params[pidx] || param.min || '';
            
            if (param.type === 'range') {
                html += `
                    <div class="form-group">
                        <label>${param.name}: <span id="val-${idx}-${pidx}" style="color:#58a6ff">${value}</span></label>
                        <input type="range" min="${param.min}" max="${param.max}" value="${value}"
                               oninput="updateActionParam(${idx}, ${pidx}, this.value); document.getElementById('val-${idx}-${pidx}').textContent = this.value"
                               style="width:100%">
                    </div>
                `;
            } else if (param.type === 'number') {
                html += `
                    <div class="form-group">
                        <label>${param.name}:</label>
                        <input type="number" min="${param.min || 0}" max="${param.max || 10000}" value="${value}"
                               onchange="updateActionParam(${idx}, ${pidx}, this.value)">
                    </div>
                `;
            } else if (param.type === 'select') {
                html += `
                    <div class="form-group">
                        <label>${param.name}:</label>
                        <select onchange="updateActionParam(${idx}, ${pidx}, this.value)">
                            ${param.options.map(opt => `<option value="${opt}" ${opt === value ? 'selected' : ''}>${opt}</option>`).join('')}
                        </select>
                    </div>
                `;
            }
        });
    }
    
    html += `
            </div>
        </div>
    `;
    
    return html;
}

// Add Action Step
function addActionStep() {
    if (!currentPin || !pinConfigs[currentPin]) return;
    
    const device = pinConfigs[currentPin].device;
    const actions = DEVICE_ACTIONS[device];
    
    if (!actions || actions.length === 0) return;
    
    pinActions[currentPin].push({
        type: actions[0].id,
        params: []
    });
    
    showActionsPanel();
    saveToStorage();
}

// Update Action
function updateAction(idx, type) {
    if (!pinActions[currentPin]) return;
    
    pinActions[currentPin][idx].type = type;
    pinActions[currentPin][idx].params = [];
    
    showActionsPanel();
    saveToStorage();
}

// Update Action Parameter
function updateActionParam(idx, paramIdx, value) {
    if (!pinActions[currentPin]) return;
    
    if (!pinActions[currentPin][idx].params) {
        pinActions[currentPin][idx].params = [];
    }
    
    pinActions[currentPin][idx].params[paramIdx] = value;
    saveToStorage();
}

// Move Action
function moveAction(idx, direction) {
    if (!pinActions[currentPin]) return;
    
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= pinActions[currentPin].length) return;
    
    [pinActions[currentPin][idx], pinActions[currentPin][newIdx]] = 
    [pinActions[currentPin][newIdx], pinActions[currentPin][idx]];
    
    showActionsPanel();
    saveToStorage();
}

// Delete Action
function deleteAction(idx) {
    if (!pinActions[currentPin]) return;
    
    if (confirm('Удалить это действие?')) {
        pinActions[currentPin].splice(idx, 1);
        showActionsPanel();
        saveToStorage();
    }
}

// ============================================
// BLOCK DIAGRAM FUNCTIONS
// ============================================

// Add Block to Diagram
function addBlock(type) {
    const blockId = Date.now();
    const block = {
        id: blockId,
        type: type,
        params: {}
    };
    
    // Set default params based on type
    if (type === 'condition') {
        block.params = {
            pin: '',
            operator: '>',
            value: '0'
        };
    } else if (type === 'action') {
        block.params = {
            pin: '',
            action: ''
        };
    } else if (type === 'loop') {
        block.params = {
            count: '10'
        };
    } else if (type === 'delay') {
        block.params = {
            time: '1000'
        };
    }
    
    blocks.push(block);
    renderBlocks();
    saveToStorage();
}

// Render All Blocks
function renderBlocks() {
    const container = document.getElementById('blockDiagram');
    
    if (blocks.length === 0) {
        container.innerHTML = '<div class="empty-state">Нажми кнопки ниже, чтобы добавить блоки ↓</div>';
        return;
    }
    
    let html = '';
    blocks.forEach((block, idx) => {
        html += renderBlock(block, idx);
    });
    
    container.innerHTML = html;
}

// Render Single Block
function renderBlock(block, idx) {
    const typeClass = `block-${block.type}`;
    let typeIcon = '';
    let typeName = '';
    
    switch(block.type) {
        case 'condition':
            typeIcon = '❓';
            typeName = 'Условие (Если)';
            break;
        case 'action':
            typeIcon = '⚙️';
            typeName = 'Действие';
            break;
        case 'loop':
            typeIcon = '🔁';
            typeName = 'Цикл';
            break;
        case 'delay':
            typeIcon = '⏱️';
            typeName = 'Задержка';
            break;
    }
    
    let html = `
        <div class="block-item ${typeClass}">
            <div class="block-header">
                <span class="block-title">${typeIcon} ${typeName}</span>
                <div class="block-controls">
                    <button class="icon-btn" onclick="moveBlock(${idx}, -1)">▲</button>
                    <button class="icon-btn" onclick="moveBlock(${idx}, 1)">▼</button>
                    <button class="icon-btn" onclick="deleteBlock(${idx})">🗑️</button>
                </div>
            </div>
            <div style="margin-top: 10px;">
    `;
    
    // Render block-specific content
    if (block.type === 'condition') {
        const pins = Object.keys(pinConfigs).filter(p => {
            const dev = pinConfigs[p].device;
            return ['button', 'switch', 'potentiometer', 'sensor_temp', 'sensor_light'].includes(dev);
        });
        
        html += `
            <select onchange="updateBlockParam(${idx}, 'pin', this.value)" style="width:100%; margin-bottom:5px;">
                <option value="">-- Выбери датчик --</option>
                ${pins.map(p => `<option value="${p}" ${block.params.pin == p ? 'selected' : ''}>
                    ${pinConfigs[p].deviceName} (GPIO ${p})
                </option>`).join('')}
            </select>
            <div style="display:flex; gap:5px;">
                <select onchange="updateBlockParam(${idx}, 'operator', this.value)">
                    <option value=">" ${block.params.operator === '>' ? 'selected' : ''}>></option>
                    <option value="<" ${block.params.operator === '<' ? 'selected' : ''}><</option>
                    <option value="==" ${block.params.operator === '==' ? 'selected' : ''}>=</option>
                    <option value="!=" ${block.params.operator === '!=' ? 'selected' : ''}>≠</option>
                </select>
                <input type="number" value="${block.params.value}" 
                       onchange="updateBlockParam(${idx}, 'value', this.value)" 
                       style="flex:1;" placeholder="Значение">
            </div>
        `;
    } else if (block.type === 'action') {
        const pins = Object.keys(pinConfigs).filter(p => DEVICE_ACTIONS[pinConfigs[p].device]);
        
        html += `
            <select onchange="updateBlockParam(${idx}, 'pin', this.value); updateBlockActionOptions(${idx})" 
                    style="width:100%; margin-bottom:5px;">
                <option value="">-- Выбери устройство --</option>
                ${pins.map(p => `<option value="${p}" ${block.params.pin == p ? 'selected' : ''}>
                    ${pinConfigs[p].deviceName} (GPIO ${p})
                </option>`).join('')}
            </select>
            <select id="action-select-${idx}" onchange="updateBlockParam(${idx}, 'action', this.value)" 
                    style="width:100%;">
                <option value="">-- Выбери действие --</option>
            </select>
        `;
    } else if (block.type === 'loop') {
        html += `
            <div style="display:flex; gap:5px; align-items:center;">
                <label style="color:#8b949e;">Повторить:</label>
                <input type="number" value="${block.params.count}" min="1" max="1000"
                       onchange="updateBlockParam(${idx}, 'count', this.value)" 
                       style="flex:1;">
                <label style="color:#8b949e;">раз</label>
            </div>
        `;
    } else if (block.type === 'delay') {
        html += `
            <div style="display:flex; gap:5px; align-items:center;">
                <label style="color:#8b949e;">Задержка:</label>
                <input type="number" value="${block.params.time}" min="10" max="60000"
                       onchange="updateBlockParam(${idx}, 'time', this.value)" 
                       style="flex:1;">
                <label style="color:#8b949e;">мс</label>
            </div>
        `;
    }
    
    html += `
            </div>
        </div>
    `;
    
    // Update action options after render
    if (block.type === 'action' && block.params.pin) {
        setTimeout(() => updateBlockActionOptions(idx), 10);
    }
    
    return html;
}

// Update Block Parameter
function updateBlockParam(idx, param, value) {
    if (blocks[idx]) {
        blocks[idx].params[param] = value;
        saveToStorage();
    }
}

// Update Action Options for Block
function updateBlockActionOptions(idx) {
    const block = blocks[idx];
    if (!block || !block.params.pin) return;
    
    const device = pinConfigs[block.params.pin].device;
    const actions = DEVICE_ACTIONS[device];
    
    const select = document.getElementById(`action-select-${idx}`);
    if (!select) return;
    
    select.innerHTML = '<option value="">-- Выбери действие --</option>' +
        actions.map(a => `<option value="${a.id}" ${block.params.action === a.id ? 'selected' : ''}>${a.name}</option>`).join('');
}

// Move Block
function moveBlock(idx, direction) {
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= blocks.length) return;
    
    [blocks[idx], blocks[newIdx]] = [blocks[newIdx], blocks[idx]];
    
    renderBlocks();
    saveToStorage();
}

// Delete Block
function deleteBlock(idx) {
    if (confirm('Удалить этот блок?')) {
        blocks.splice(idx, 1);
        renderBlocks();
        saveToStorage();
    }
}

// Clear All Blocks
function clearBlocks() {
    if (blocks.length === 0) return;
    
    if (confirm('Удалить все блоки?')) {
        blocks = [];
        renderBlocks();
        saveToStorage();
    }
}

// ============================================
// CODE GENERATION
// ============================================

function generateCode() {
    let code = `// Auto-generated by ESP32 Universal Constructor
// robotpit.com
// Generated: ${new Date().toLocaleString('ru-RU')}

#include <Arduino.h>

// ==========================================
// PIN DEFINITIONS
// ==========================================
`;
    
    // Define pins
    for (let pin in pinConfigs) {
        const cfg = pinConfigs[pin];
        const pinName = cfg.deviceName.toUpperCase().replace(/\s+/g, '_');
        code += `#define ${pinName} ${pin}  // ${cfg.device}\n`;
    }
    
    code += `
// ==========================================
// SETUP
// ==========================================
void setup() {
    Serial.begin(115200);
    Serial.println("ESP32 Universal Constructor Started!");
    
    // Initialize pins
`;
    
    for (let pin in pinConfigs) {
        const cfg = pinConfigs[pin];
        const pinName = cfg.deviceName.toUpperCase().replace(/\s+/g, '_');
        
        if (['motor_dc', 'led', 'relay', 'buzzer'].includes(cfg.device)) {
            code += `    pinMode(${pinName}, OUTPUT);\n`;
        } else if (['button', 'switch'].includes(cfg.device)) {
            code += `    pinMode(${pinName}, INPUT_PULLUP);\n`;
        } else if (['potentiometer', 'sensor_temp', 'sensor_light'].includes(cfg.device)) {
            code += `    pinMode(${pinName}, INPUT);\n`;
        }
    }
    
    if (Object.keys(pinConfigs).some(p => pinConfigs[p].device === 'servo')) {
        code += `\n    // Initialize servos\n`;
        code += `    // TODO: Add servo library and initialization\n`;
    }
    
    code += `}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
`;
    
    // Generate code from blocks if exists
    if (blocks.length > 0) {
        code += `    // Block diagram logic\n`;
        blocks.forEach(block => {
            code += generateBlockCode(block, '    ');
        });
    }
    
    // Generate code from action sequences
    let hasSequences = false;
    for (let pin in pinActions) {
        if (pinActions[pin].length > 0) {
            if (!hasSequences) {
                code += `\n    // Action sequences\n`;
                hasSequences = true;
            }
            
            const cfg = pinConfigs[pin];
            const pinName = cfg.deviceName.toUpperCase().replace(/\s+/g, '_');
            code += `\n    // ${cfg.deviceName} - GPIO ${pin}\n`;
            
            pinActions[pin].forEach(action => {
                code += generateActionCode(pin, action, '    ');
            });
        }
    }
    
    if (!hasSequences && blocks.length === 0) {
        code += `    // TODO: Add your code here\n`;
        code += `    delay(1000);\n`;
    }
    
    code += `}`;
    
    // Add helper functions if needed
    if (Object.keys(pinConfigs).some(p => pinConfigs[p].device === 'motor_dc')) {
        code += `

// ==========================================
// HELPER FUNCTIONS
// ==========================================
void setMotorSpeed(int pin, int speed) {
    // Speed: 0-100%
    int pwmValue = map(speed, 0, 100, 0, 255);
    analogWrite(pin, pwmValue);
}

void motorRamp(int pin, int speedFrom, int speedTo, int duration) {
    int steps = 50;
    int delayTime = duration / steps;
    for (int i = 0; i <= steps; i++) {
        int speed = map(i, 0, steps, speedFrom, speedTo);
        setMotorSpeed(pin, speed);
        delay(delayTime);
    }
}`;
    }
    
    // Display with syntax highlighting
    const highlighted = highlightCode(code);
    document.getElementById('codePreview').innerHTML = highlighted;
    
    // Store for download
    window.generatedCode = code;
    
    switchTab('code');
}

// Generate code for a single block
function generateBlockCode(block, indent) {
    let code = '';
    
    if (block.type === 'condition') {
        if (!block.params.pin) return '';
        
        const cfg = pinConfigs[block.params.pin];
        const pinName = cfg.deviceName.toUpperCase().replace(/\s+/g, '_');
        
        if (['button', 'switch'].includes(cfg.device)) {
            code += `${indent}if (digitalRead(${pinName}) ${block.params.operator} ${block.params.value}) {\n`;
            code += `${indent}    // TODO: Add action here\n`;
            code += `${indent}}\n`;
        } else if (ESP32_PINS.adc.includes(parseInt(block.params.pin))) {
            code += `${indent}int ${pinName}_value = analogRead(${pinName});\n`;
            code += `${indent}if (${pinName}_value ${block.params.operator} ${block.params.value}) {\n`;
            code += `${indent}    // TODO: Add action here\n`;
            code += `${indent}}\n`;
        }
    } else if (block.type === 'action') {
        if (!block.params.pin || !block.params.action) return '';
        
        const cfg = pinConfigs[block.params.pin];
        code += generateActionCode(block.params.pin, {type: block.params.action, params: []}, indent);
    } else if (block.type === 'loop') {
        code += `${indent}for (int i = 0; i < ${block.params.count}; i++) {\n`;
        code += `${indent}    // TODO: Add loop content\n`;
        code += `${indent}}\n`;
    } else if (block.type === 'delay') {
        code += `${indent}delay(${block.params.time});\n`;
    }
    
    return code;
}

// Generate code for action
function generateActionCode(pin, action, indent) {
    const cfg = pinConfigs[pin];
    const pinName = cfg.deviceName.toUpperCase().replace(/\s+/g, '_');
    let code = '';
    
    const device = cfg.device;
    
    if (device === 'led') {
        if (action.type === 'on') {
            code += `${indent}digitalWrite(${pinName}, HIGH);\n`;
        } else if (action.type === 'off') {
            code += `${indent}digitalWrite(${pinName}, LOW);\n`;
        } else if (action.type === 'blink') {
            const interval = action.params[0] || 500;
            code += `${indent}digitalWrite(${pinName}, HIGH);\n`;
            code += `${indent}delay(${interval});\n`;
            code += `${indent}digitalWrite(${pinName}, LOW);\n`;
            code += `${indent}delay(${interval});\n`;
        } else if (action.type === 'brightness') {
            const brightness = Math.round((action.params[0] || 50) * 255 / 100);
            code += `${indent}analogWrite(${pinName}, ${brightness});\n`;
        }
    } else if (device === 'motor_dc') {
        if (action.type === 'speed') {
            const speed = action.params[0] || 0;
            code += `${indent}setMotorSpeed(${pinName}, ${speed});\n`;
        } else if (action.type === 'stop') {
            code += `${indent}analogWrite(${pinName}, 0);\n`;
        } else if (action.type === 'ramp') {
            code += `${indent}motorRamp(${pinName}, ${action.params[0]}, ${action.params[1]}, ${action.params[2]});\n`;
        }
    } else if (device === 'relay') {
        if (action.type === 'on') {
            code += `${indent}digitalWrite(${pinName}, HIGH);\n`;
        } else if (action.type === 'off') {
            code += `${indent}digitalWrite(${pinName}, LOW);\n`;
        } else if (action.type === 'toggle') {
            code += `${indent}digitalWrite(${pinName}, !digitalRead(${pinName}));\n`;
        } else if (action.type === 'pulse') {
            const duration = action.params[0] || 1000;
            code += `${indent}digitalWrite(${pinName}, HIGH);\n`;
            code += `${indent}delay(${duration});\n`;
            code += `${indent}digitalWrite(${pinName}, LOW);\n`;
        }
    } else if (device === 'buzzer') {
        if (action.type === 'beep') {
            const freq = action.params[0] || 1000;
            const duration = action.params[1] || 500;
            code += `${indent}tone(${pinName}, ${freq}, ${duration});\n`;
            code += `${indent}delay(${duration});\n`;
        } else if (action.type === 'off') {
            code += `${indent}noTone(${pinName});\n`;
        }
    } else if (device === 'servo') {
        if (action.type === 'angle') {
            const angle = action.params[0] || 90;
            code += `${indent}// servo_${pinName}.write(${angle});\n`;
        } else if (action.type === 'center') {
            code += `${indent}// servo_${pinName}.write(90);\n`;
        }
    }
    
    return code;
}

// Syntax highlighting
function highlightCode(code) {
    return code
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/(#include|#define|void|int|pinMode|digitalWrite|analogWrite|digitalRead|analogRead|delay|if|else|for|while|return)/g, '<span class="keyword">$1</span>')
        .replace(/(setup|loop|Serial\.begin|Serial\.println|tone|noTone)/g, '<span class="function">$1</span>')
        .replace(/\b(\d+)\b/g, '<span class="number">$1</span>')
        .replace(/(\/\/.*)/g, '<span class="comment">$1</span>');
}

// Copy Code
function copyCode() {
    if (!window.generatedCode) {
        generateCode();
    }
    
    navigator.clipboard.writeText(window.generatedCode).then(() => {
        alert('✅ Код скопирован в буфер обмена!');
    }).catch(() => {
        alert('❌ Ошибка копирования');
    });
}

// Download Code
function downloadCode() {
    if (!window.generatedCode) {
        generateCode();
    }
    
    const blob = new Blob([window.generatedCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'esp32_program.ino';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    alert('✅ Файл esp32_program.ino скачан!');
}

// ============================================
// OTHER FUNCTIONS
// ============================================

function connectESP32() {
    const ip = prompt('Введи IP адрес твоего ESP32:\n(например: 192.168.1.100)');
    if (!ip) return;
    
    try {
        ws = new WebSocket(`ws://${ip}:81`);
        
        ws.onopen = function() {
            connected = true;
            document.getElementById('statusIndicator').className = 'status-indicator connected';
            document.getElementById('statusText').textContent = `Подключено: ${ip}`;
            document.getElementById('wsStatus').textContent = 'Активен';
            alert('✅ Успешно подключено к ESP32!');
        };
        
        ws.onclose = function() {
            connected = false;
            document.getElementById('statusIndicator').className = 'status-indicator disconnected';
            document.getElementById('statusText').textContent = 'Не подключено';
            document.getElementById('wsStatus').textContent = 'Неактивен';
        };
        
        ws.onmessage = function(event) {
            console.log('Получено:', event.data);
        };
        
    } catch(e) {
        alert('❌ Ошибка подключения: ' + e.message);
    }
}

function testProgram() {
    if (Object.keys(pinConfigs).length === 0) {
        alert('⚠️ Сначала настрой хотя бы один пин!');
        return;
    }
    
    if (!connected) {
        alert('⚠️ Сначала подключись к ESP32!');
        return;
    }
    
    alert('🚧 Тестирование в разработке!');
}

function saveProject() {
    const name = prompt('Название проекта:');
    if (!name) return;
    
    const project = {
        name: name,
        date: new Date().toISOString().split('T')[0],
        configs: pinConfigs,
        actions: pinActions,
        blocks: blocks
    };
    
    let projects = JSON.parse(localStorage.getItem('esp32_projects') || '[]');
    projects.push(project);
    localStorage.setItem('esp32_projects', JSON.stringify(projects));
    
    alert('✅ Проект "' + name + '" сохранён!');
}

function flashOTA() {
    if (Object.keys(pinConfigs).length === 0) {
        alert('⚠️ Сначала настрой пины!');
        return;
    }
    
    if (!connected) {
        alert('⚠️ Сначала подключись к ESP32!');
        return;
    }
    
    alert('🚧 OTA прошивка в разработке!');
}

function resetAll() {
    if (confirm('Удалить всю конфигурацию? Это действие необратимо!')) {
        pinConfigs = {};
        pinActions = {};
        blocks = [];
        currentPin = null;
        saveToStorage();
        generatePinList();
        renderBlocks();
        document.getElementById('pinConfigPanel').innerHTML = '<div class="empty-state">← Выбери пин из списка слева</div>';
        document.getElementById('actionsPanel').innerHTML = '<div class="empty-state">Сначала настрой пин ←</div>';
        alert('🔄 Всё сброшено!');
    }
}

// Storage Functions
function saveToStorage() {
    localStorage.setItem('esp32_pin_configs', JSON.stringify(pinConfigs));
    localStorage.setItem('esp32_pin_actions', JSON.stringify(pinActions));
    localStorage.setItem('esp32_blocks', JSON.stringify(blocks));
}

function loadFromStorage() {
    const configs = localStorage.getItem('esp32_pin_configs');
    const actions = localStorage.getItem('esp32_pin_actions');
    const storedBlocks = localStorage.getItem('esp32_blocks');
    
    if (configs) pinConfigs = JSON.parse(configs);
    if (actions) pinActions = JSON.parse(actions);
    if (storedBlocks) blocks = JSON.parse(storedBlocks);
    
    generatePinList();
    renderBlocks();
}

// Download Firmware
function downloadFirmware() {
    // Запросить WiFi данные у пользователя
    const ssid = prompt('Введи название твоего WiFi (SSID):');
    if (!ssid) {
        alert('❌ Отменено - не указан SSID');
        return;
    }
    
    const password = prompt('Введи пароль от WiFi:\n(или оставь пустым если сеть открытая)');
    
    const firmwareCode = `/*
 * ESP32 Universal Constructor - Firmware v1.0
 * https://www.robutpit.com/projects/esp32-constructor/
 * 
 * WiFi настроен для автоматического подключения!
 * SSID: ${ssid}
 */

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>

// WiFi настройки (прописаны в прошивке)
const char* WIFI_SSID = "${ssid}";
const char* WIFI_PASSWORD = "${password || ''}";

// WebSocket сервер на порту 81
WebSocketsServer wsServer(81);

bool wifiConnected = false;
bool wsConnected = false;
unsigned long startTime = 0;

// Конфигурация пинов
struct PinConfig {
    int pin;
    String type;
    String device;
    String name;
    int value;
    int pwmChannel;
};

PinConfig pins[40];
int configuredPins = 0;

void setup() {
    Serial.begin(115200);
    delay(2000);
    
    Serial.println("\\n\\n╔════════════════════════════════════════════╗");
    Serial.println("║  ESP32 Universal Constructor v1.0         ║");
    Serial.println("║  www.robutpit.com                          ║");
    Serial.println("╚════════════════════════════════════════════╝\\n");
    
    startTime = millis();
    pinMode(LED_BUILTIN, OUTPUT);
    
    // Подключение к WiFi
    connectToWiFi();
    
    if (wifiConnected) {
        wsServer.begin();
        wsServer.onEvent(webSocketEvent);
        Serial.println("✅ WebSocket сервер запущен на порту 81\\n");
        printConnectionInfo();
    } else {
        Serial.println("❌ Не удалось подключиться к WiFi!");
    }
    
    Serial.println("✅ Система готова!\\n");
}

void loop() {
    // Проверка WiFi
    if (WiFi.status() != WL_CONNECTED) {
        if (wifiConnected) {
            Serial.println("⚠️  WiFi отключён! Переподключаюсь...");
            wifiConnected = false;
        }
        connectToWiFi();
        delay(5000);
        return;
    }
    
    wsServer.loop();
    
    // Статус каждые 5 секунд
    static unsigned long lastStatus = 0;
    if (millis() - lastStatus > 5000) {
        sendStatus();
        lastStatus = millis();
    }
    
    // Мигание LED
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 1000) {
        digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
        lastBlink = millis();
    }
}

void connectToWiFi() {
    Serial.println("📡 Подключаюсь к WiFi...");
    Serial.print("   SSID: ");
    Serial.println(WIFI_SSID);
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    Serial.print("   ");
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 60) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    Serial.println();
    
    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        Serial.println("✅ WiFi подключён!");
        Serial.print("   IP адрес: ");
        Serial.println(WiFi.localIP());
        Serial.print("   Signal: ");
        Serial.print(WiFi.RSSI());
        Serial.println(" dBm");
    } else {
        wifiConnected = false;
        Serial.println("❌ Не удалось подключиться");
    }
}

void printConnectionInfo() {
    Serial.println("┌──────────────────────────────────────────────┐");
    Serial.println("│  КАК ПОДКЛЮЧИТЬСЯ:                           │");
    Serial.println("├──────────────────────────────────────────────┤");
    Serial.println("│  1. Открой: robutpit.com/projects/esp32-...  │");
    Serial.println("│  2. Нажми: 🔌 Подключить ESP32               │");
    Serial.print("│  3. Введи IP: ");
    Serial.print(WiFi.localIP());
    Serial.println("                      │");
    Serial.println("└──────────────────────────────────────────────┘\\n");
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.printf("🔌 [%u] Отключился\\n", num);
            wsConnected = false;
            break;
            
        case WStype_CONNECTED: {
            IPAddress ip = wsServer.remoteIP(num);
            Serial.printf("🔌 [%u] Подключён: %d.%d.%d.%d\\n", num, ip[0], ip[1], ip[2], ip[3]);
            wsConnected = true;
            String welcome = "{\\"type\\":\\"connected\\",\\"message\\":\\"ESP32 готов!\\",\\"version\\":\\"1.0\\"}";
            wsServer.sendTXT(num, welcome);
            break;
        }
            
        case WStype_TEXT: {
            Serial.printf("📨 [%u] %s\\n", num, payload);
            
            DynamicJsonDocument doc(2048);
            DeserializationError error = deserializeJson(doc, payload);
            if (error) return;
            
            String cmdType = doc["type"].as<String>();
            
            if (cmdType == "ping") {
                handlePing(num);
            } else if (cmdType == "digital") {
                handleDigital(num, doc);
            } else if (cmdType == "pwm") {
                handlePWM(num, doc);
            } else if (cmdType == "read") {
                handleRead(num, doc);
            } else if (cmdType == "config") {
                handleConfig(num, doc);
            }
            break;
        }
    }
}

void handlePing(uint8_t num) {
    unsigned long uptime = (millis() - startTime) / 1000;
    String pong = "{\\"type\\":\\"pong\\",\\"uptime\\":" + String(uptime) + "}";
    wsServer.sendTXT(num, pong);
}

void handleDigital(uint8_t num, JsonDocument& doc) {
    int pin = doc["pin"];
    int value = doc["value"];
    pinMode(pin, OUTPUT);
    digitalWrite(pin, value);
    Serial.printf("💡 GPIO %d = %s\\n", pin, value ? "HIGH" : "LOW");
    String response = "{\\"type\\":\\"digital_response\\",\\"pin\\":" + String(pin) + ",\\"value\\":" + String(value) + "}";
    wsServer.sendTXT(num, response);
}

void handlePWM(uint8_t num, JsonDocument& doc) {
    int pin = doc["pin"];
    int value = doc["value"];
    int channel = doc["channel"] | 0;
    int freq = doc["frequency"] | 5000;
    
    ledcSetup(channel, freq, 8);
    ledcAttachPin(pin, channel);
    ledcWrite(channel, value);
    
    Serial.printf("🎛️ PWM GPIO %d = %d (%d%%)\\n", pin, value, (value * 100) / 255);
    String response = "{\\"type\\":\\"pwm_response\\",\\"pin\\":" + String(pin) + ",\\"value\\":" + String(value) + "}";
    wsServer.sendTXT(num, response);
}

void handleRead(uint8_t num, JsonDocument& doc) {
    int pin = doc["pin"];
    String readType = doc["readType"] | "digital";
    int value = 0;
    
    if (readType == "analog" || (pin >= 32 && pin <= 39)) {
        pinMode(pin, INPUT);
        value = analogRead(pin);
    } else {
        pinMode(pin, INPUT);
        value = digitalRead(pin);
    }
    
    String response = "{\\"type\\":\\"read_response\\",\\"pin\\":" + String(pin) + ",\\"value\\":" + String(value) + "}";
    wsServer.sendTXT(num, response);
}

void handleConfig(uint8_t num, JsonDocument& doc) {
    Serial.println("⚙️ Применяю конфигурацию...");
    configuredPins = 0;
    JsonObject config = doc["config"];
    
    for (JsonPair kv : config) {
        if (configuredPins >= 40) break;
        
        int pin = String(kv.key().c_str()).toInt();
        JsonObject pinData = kv.value();
        
        pins[configuredPins].pin = pin;
        pins[configuredPins].type = pinData["type"].as<String>();
        pins[configuredPins].device = pinData["device"].as<String>();
        pins[configuredPins].name = pinData["name"].as<String>();
        pins[configuredPins].pwmChannel = configuredPins;
        
        String type = pins[configuredPins].type;
        if (type == "digital_out") {
            pinMode(pin, OUTPUT);
        } else if (type == "pwm") {
            ledcSetup(configuredPins, 5000, 8);
            ledcAttachPin(pin, configuredPins);
        } else if (type == "digital_in") {
            pinMode(pin, INPUT_PULLUP);
        } else if (type == "adc") {
            pinMode(pin, INPUT);
        }
        
        Serial.printf("  📍 GPIO %d: %s\\n", pin, pins[configuredPins].name.c_str());
        configuredPins++;
    }
    
    Serial.printf("✅ Настроено %d пинов\\n", configuredPins);
    String response = "{\\"type\\":\\"config_response\\",\\"status\\":\\"ok\\"}";
    wsServer.sendTXT(num, response);
}

void sendStatus() {
    if (!wsConnected) return;
    unsigned long uptime = (millis() - startTime) / 1000;
    String status = "{\\"type\\":\\"status\\",\\"uptime\\":" + String(uptime) + 
                   ",\\"heap\\":" + String(ESP.getFreeHeap()) + 
                   ",\\"rssi\\":" + String(WiFi.RSSI()) + "}";
    wsServer.broadcastTXT(status);
}
`;
    
    const blob = new Blob([firmwareCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'esp32_universal.ino';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    alert('✅ Прошивка скачана!\\n\\nWiFi SSID: ' + ssid + '\\n\\nТеперь:\\n1. Открой файл в Arduino IDE\\n2. Установи библиотеки (WebSockets, ArduinoJson)\\n3. Прошей ESP32\\n4. IP адрес появится в Serial Monitor');
}

function downloadInstructions() {
    const instructions = `ESP32 Universal Constructor - Инструкция

1. Установка Arduino IDE
2. Установка библиотек
3. Прошивка через USB
4. Настройка WiFi
5. Подключение к веб-интерфейсу

Подробности на robotpit.com
`;
    
    const blob = new Blob([instructions], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'README.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
