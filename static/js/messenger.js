/**
 * Luma Messenger Core Engine v0.99.1fix1 - Release Build
 * Часть 1: Сквозной логгер, Глобальные переменные и Инициализация Базы IndexedDB
 */

(function() {
    let logBuffer = [];
    const originalLog = console.log;
    const originalWarn = console.warn;
    const originalError = console.error;

    function processLog(type, args) {
        const message = Array.from(args).map(arg =>
            typeof arg === 'object' ? JSON.stringify(arg, null, 2) : arg
        ).join(' ');
        const logLine = `[${new Date().toISOString()}] [${type.toUpperCase()}] ${message}`;
        if (type === 'log') originalLog.apply(console, args);
        if (type === 'warn') originalWarn.apply(console, args);
        if (type === 'error') originalError.apply(console, args);
        logBuffer.push(logLine);
        if (logBuffer.length >= 2 || type === 'error' || type === 'warn') {
            const payload = logBuffer.join('\n') + '\n';
            logBuffer = [];
            fetch('/save_client_logs', { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=UTF-8' }, body: payload }).catch(() => {});
        }
    }
    console.log = function() { processLog('log', arguments); };
    console.warn = function() { processLog('warn', arguments); };
    console.error = function() { processLog('error', arguments); };
    window.onerror = function(m, s, l, c) { processLog('error', [`Глобальный сбой JS: ${m} в ${s}:${l}:${c}`]); return false; };
})();

// Инициализация глобального контекста мессенджера Luma
let chatContainer = document.getElementById('chatMessages');
let TARGET_ID = chatContainer ? parseInt(chatContainer.dataset.targetId) : null;
let CHAT_TYPE = chatContainer ? chatContainer.dataset.chatType : null;

let socket = null;
let db = null;
let localStream = null;
let peerConnection = null;

// Официальный синтаксис STUN без лишних слэшей для стабильной WebRTC P2P-связи
const rtcConfig = { iceServers: [{ urls: 'stun:://google.com' }, { urls: 'stun:://google.com' }] };

// Конфигурирование дисковой базы данных IndexedDB в браузере
const dbRequest = indexedDB.open('LumaMessengerDB', 1);

dbRequest.onupgradeneeded = function(event) {
    console.log("[LUMA DB] Настройка или обновление таблиц IndexedDB...");
    const database = event.target.result;
    if (!database.objectStoreNames.contains('messages')) {
        const store = database.createObjectStore('messages', { keyPath: 'local_id', autoIncrement: true });
        store.createIndex('chat_key', ['chat_type', 'target_id'], { unique: false });
        store.createIndex('msg_id', 'msg_id', { unique: false });
    }
};

dbRequest.onsuccess = function(event) {
    db = event.target.result;
    console.log("[Luma DB] Локальная база IndexedDB успешно инициализирована.");
    initMessengerEngine();
};

dbRequest.onerror = function(event) {
    console.error("[Luma DB] Критическая ошибка IndexedDB:", event.target.error);
};

/**
 * Luma Messenger Core Engine v0.99.1fix1 - Release Build
 * Часть 2: Конвейер инициализации, загрузка кэша и рендеринг карточек с инвентарем
 */

function initMessengerEngine() {
    console.log("[LUMA ENGINE] Запуск главного конвейера инициализации...");

    chatContainer = document.getElementById('chatMessages');
    TARGET_ID = chatContainer ? parseInt(chatContainer.dataset.targetId) : null;
    CHAT_TYPE = chatContainer ? chatContainer.dataset.chatType : null;

    if (!socket) {
        console.log("[LUMA SOCKET] Запуск нативного WebSocket транспорта...");
        socket = io();
        setupSocketListeners(); // Будет описано в Части 3
    }

    if (TARGET_ID && CHAT_TYPE) {
        console.log(`[LUMA FLOW] Обнаружен активный чат: ${CHAT_TYPE} (ID: ${TARGET_ID}). Считывание истории...`);

        loadChatHistory(function() {
            setupFormListeners(); // Будет описано в Части 3

            let curUid = chatContainer.dataset.currentUserId;
            if (!curUid) {
                console.warn("[LUMA FLOW] ID не найден в чате. Попытка вызова глобального контекста...");
                curUid = document.body.innerHTML.match(/data-current-user-id="(\d+)"/);
                curUid = curUid ? curUid[1] : null;
            }

            if (curUid) {
                console.log(`[LUMA SOCKET] Гарантированный запуск авторизации сокета для User ID: ${curUid}`);
                socket.emit('authorize_socket', { user_id: parseInt(curUid) });
            } else {
                console.error("[LUMA SOCKET ERROR] Критическая ошибка: UID пользователя не найден ни в одном блоке страницы Luma!");
            }
        });
    } else {
        console.warn("[LUMA FLOW] Активный чат не выбран. Режим прослушивания фонового сокет-потока.");
    }
}

// 3. Выборка истории сообщений из IndexedDB
function loadChatHistory(callback) {
    if (!db || !chatContainer) {
        console.error("[LUMA FLOW ERROR] Сбой считывания истории: база данных или контейнер верстки недоступны.");
        if (callback) callback();
        return;
    }

    const transaction = db.transaction(['messages'], 'readonly');
    const store = transaction.objectStore('messages');
    const index = store.index('chat_key');

    const requestRange = IDBKeyRange.only([CHAT_TYPE, TARGET_ID]);
    const cursorRequest = index.openCursor(requestRange);

    chatContainer.innerHTML = '';

    let loadedCount = 0;
    cursorRequest.onsuccess = function(event) {
        const cursor = event.target.result;
        if (cursor) {
            renderMessageNode(cursor.value);
            loadedCount++;
            cursor.continue();
        } else {
            console.log(`[LUMA DB] Выведено карточек из локальной истории: ${loadedCount}`);
            scrollToBottom();
            if (callback) callback();
        }
    };

    cursorRequest.onerror = function() {
        console.error("[LUMA DB ERROR] Ошибка выполнения транзакции чтения истории.");
        if (callback) callback();
    };
}

// 4. Построение DOM-карточек сообщений в контейнере (Пункт 3 - Отображение инвентаря)
function renderMessageNode(msg) {
    if (!chatContainer) return;

    const msgElement = document.createElement('div');
    const isMe = msg.is_outgoing === true || msg.sender_id === undefined;

    msgElement.className = `msg-card ${isMe ? 'msg-me align-self-end' : 'msg-other align-self-start'}`;
    msgElement.id = `msg_${msg.msg_id || msg.local_id}`;

    let innerHTML = '';

    // ВЫВОД ВСЕХ ЭЛЕМЕНТОВ ОФОРМЛЕНИЯ ОПТФАВИТЕЛЯ (Пункт 3)
    if (!isMe && (CHAT_TYPE === 'group' || CHAT_TYPE === 'channel')) {
        let roleBadge = '';
        if (msg.sender_role === 1) {
            roleBadge = '<span style="color: #0d6efd; user-select: none; margin-right: 2px; font-weight: bold;">✓</span>';
        } else if (msg.sender_role >= 2) {
            roleBadge = '<span style="color: #0dcaf0; user-select: none; margin-right: 2px;">🛡️</span>';
        }

        let customBadge = msg.sender_badge ? `<span style="user-select: none; margin-left: 2px;">${msg.sender_badge}</span>` : '';

        innerHTML += `<span class="d-inline-flex align-items-center mb-1 style-micro">
            ${roleBadge}
            <span class="fw-bold" style="${msg.sender_name_style || ''}">@${msg.sender_name || 'User'}</span>
            ${customBadge}
        </span>`;
    }

    // Рендеринг медиавложений
    if (msg.message_type === 'image') {
        innerHTML += `<img src="${msg.file_url}" class="img-fluid rounded mb-1" style="max-height: 250px; object-fit: cover;">`;
    } else if (msg.message_type === 'file') {
        innerHTML += `<a href="${msg.file_url}" target="_blank" class="d-flex align-items-center gap-1 style-micro ${isMe ? 'text-white' : 'text-primary'}"><span class="fs-6">📁</span> ${msg.file_name}</a>`;
    }

    if (msg.text) {
        innerHTML += `<p class="m-0 py-1" style="word-break: break-word;">${msg.text}</p>`;
    }

    msgElement.innerHTML = innerHTML;
    chatContainer.appendChild(msgElement);
}

// 5. Сохранение пакета в IndexedDB
function saveMessageToLocalDB(msg, callback) {
    if (!db) return;
    const transaction = db.transaction(['messages'], 'readwrite');
    const store = transaction.objectStore('messages');
    const addRequest = store.add(msg);

    addRequest.onsuccess = function(e) {
        console.log(`[LUMA DB] Пакет успешно сохранен в кэш. local_id=${e.target.result}`);
        if (callback) callback(e.target.result);
    };
}

/**
 * Luma Messenger Core Engine v0.99.1fix1 - Release Build
 * Часть 3: События формы, прием сокет-пакетов, загрузка файлов и WebRTC.
 */

// 6. Инициализация и привязка слушателей событий для формы ввода сообщений
function setupFormListeners() {
    const messageForm = document.getElementById('messageForm');
    if (!messageForm) return;

    console.log("[LUMA INIT] Форма #messageForm найдена. Привязка обработчиков...");

    const newForm = messageForm.cloneNode(true);
    messageForm.parentNode.replaceChild(newForm, messageForm);

    newForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const input = document.getElementById('messageInput');
        const text = input.value.trim();
        if (!text && !currentAttachment) return;

        const activeContainer = document.getElementById('chatMessages');
        const exactTargetId = activeContainer ? parseInt(activeContainer.dataset.targetId) : null;
        const exactChatType = activeContainer ? activeContainer.dataset.chatType : null;
        const currentUserId = activeContainer ? parseInt(activeContainer.dataset.currentUserId) : null;
        const currentUserName = activeContainer ? activeContainer.dataset.currentUserName : null;

        // ПУНКТ 3: Считываем текущее оформление своего профиля из скрытых полей или стилей
        // Эти стили подгружаются сервером в DOM, чтобы сокет сразу отправлял их получателю
        const myNameStyle = activeContainer ? activeContainer.dataset.currentUserStyle || "" : "";
        const myBadge = activeContainer ? activeContainer.dataset.currentUserBadge || null : null;
        const myRole = activeContainer ? parseInt(activeContainer.dataset.currentUserRole || "0") : 0;

        const generatedMsgId = 'local_' + Date.now() + Math.random().toString(36).substr(2, 9);

        const msgPayload = {
            msg_id: generatedMsgId,
            target_id: exactTargetId,
            chat_type: exactChatType,
            message_type: currentAttachment ? currentAttachment.type : 'text',
            text: text,
            file_url: currentAttachment ? currentAttachment.url : null,
            file_name: currentAttachment ? currentAttachment.name : null,
            sender_id: currentUserId,
            sender_name: currentUserName,
            timestamp: new Date().toISOString(),

            // Передаем свое оформление в пакет, чтобы у получателя оно сразу отрендерилось
            sender_name_style: myNameStyle,
            sender_badge: myBadge,
            sender_role: myRole
        };

        console.log("[LUMA SOCKET] Отправка 'send_message' через нативный WS:", msgPayload);
        socket.emit('send_message', msgPayload);

        const localVisualPayload = { ...msgPayload, ...{ is_outgoing: true } };
        saveMessageToLocalDB(localVisualPayload, function() {
            renderMessageNode(localVisualPayload);
            scrollToBottom();
        });

        input.value = '';
        clearAttachment();
    });

    setupFileInput();
}

// 7. Регистрация WebSocket-слушателей (Нативный прием текстовых фреймов)
function setupSocketListeners() {
    if (!socket) return;

    socket.on('connect', function() {
        console.log("[LUMA SOCKET] Нативный WebSocket-канал успешно open.");
    });

    socket.on('receive_message', function(data) {
        console.log("[LUMA SOCKET] Получен входящий пакет от WebSocket:", data);

        const currentChatContainer = document.getElementById('chatMessages');
        if (!currentChatContainer) return;

        const currentTargetId = parseInt(currentChatContainer.dataset.targetId);
        const currentChatType = currentChatContainer.dataset.chatType;
        const currentUserId = parseInt(currentChatContainer.dataset.currentUserId);

        const isCurrentPrivate = currentChatType === 'private' &&
            (parseInt(data.sender_id) === currentTargetId || parseInt(data.target_id) === currentTargetId);

        const isCurrentGroup = (currentChatType === 'group' || currentChatType === 'channel') &&
            parseInt(data.target_id) === currentTargetId;

        if (isCurrentPrivate || isCurrentGroup) {
            if (document.getElementById(`msg_${data.msg_id}`)) return;

            if (parseInt(data.sender_id) === currentUserId) {
                console.log("[LUMA FLOW] Перехвачено собственное эхо. Фиксация ID карточки...");
                const localNode = document.querySelector(`[id^="msg_local_"]`);
                if (localNode) {
                    localNode.id = `msg_${data.msg_id}`;
                    return;
                }
            }

            const incomingPayload = {
                msg_id: data.msg_id,
                target_id: currentTargetId,
                chat_type: currentChatType,
                message_type: data.message_type,
                text: data.text,
                file_url: data.file_url,
                file_name: data.file_name,
                sender_id: data.sender_id,
                sender_name: data.sender_name,
                is_outgoing: (parseInt(data.sender_id) === currentUserId),
                timestamp: data.timestamp || new Date().toISOString(),

                // Кэшируем полученное оформление собеседника в локальную базу истории
                sender_name_style: data.sender_name_style,
                sender_badge: data.sender_badge,
                sender_role: data.sender_role
            };

            saveMessageToLocalDB(incomingPayload, function() {
                renderMessageNode(incomingPayload);
                scrollToBottom();
            });
        } else {
            const backgroundPayload = {
                msg_id: data.msg_id,
                target_id: parseInt(data.chat_type === 'private' ? data.sender_id : data.target_id),
                chat_type: data.chat_type,
                message_type: data.message_type,
                text: data.text,
                file_url: data.file_url,
                file_name: data.file_name,
                sender_id: data.sender_id,
                sender_name: data.sender_name,
                is_outgoing: false,
                timestamp: data.timestamp || new Date().toISOString(),

                sender_name_style: data.sender_name_style,
                sender_badge: data.sender_badge,
                sender_role: data.sender_role
            };
            saveMessageToLocalDB(backgroundPayload);
        }
    });

    setupWebRTCSignalling();
}

// 8. Логика асинхронного прикрепления файлов через Fetch API
let currentAttachment = null;
function setupFileInput() {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput) return;

    fileInput.addEventListener('change', function() {
        if (!fileInput.files.length) return;
        console.log("[LUMA UPLOAD] Выбран файл для загрузки...");

        const file = fileInput.files[0]; // Жестко берем первый файл из массива
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload_file', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            currentAttachment = { url: data.file_url, name: data.file_name, type: data.message_type };
            const msgInput = document.getElementById('messageInput');
            if (msgInput) msgInput.placeholder = `📎 Файл готов: ${data.file_name}`;
        })
        .catch(err => console.error('[LUMA UPLOAD ERROR]', err));
    });
}

function clearAttachment() {
    currentAttachment = null;
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    const msgInput = document.getElementById('messageInput');
    if (msgInput) msgInput.placeholder = 'Напишите сообщение...';
}

function scrollToBottom() {
    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 9. Настройка сигнальных WebRTC шлюзов сокета (Медиастриминг)
function setupWebRTCSignalling() {
    if (!socket) return;

    const callBtn = document.getElementById('callBtn');
    const hangupBtn = document.getElementById('hangupBtn');
    const webrtcContainer = document.getElementById('webrtcContainer');

    if (callBtn) {
        callBtn.addEventListener('click', async function() {
            if (!TARGET_ID) return;
            if (webrtcContainer) webrtcContainer.classList.remove('d-none');
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
                peerConnection = new RTCPeerConnection(rtcConfig);
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

                peerConnection.onicecandidate = function(e) {
                    if (e.candidate) socket.emit('ice_candidate', { target_id: TARGET_ID, candidate: e.candidate });
                };

                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                socket.emit('call_user', { target_id: TARGET_ID, offer: offer });
            } catch (err) {
                console.error('[WebRTC ERROR]', err);
                if (webrtcContainer) webrtcContainer.classList.add('d-none');
            }
        });
    }

    socket.on('incoming_call', async function(data) {
        if (webrtcContainer) webrtcContainer.classList.remove('d-none');
        try {
            localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
            peerConnection = new RTCPeerConnection(rtcConfig);
            localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

            peerConnection.onicecandidate = function(e) {
                if (e.candidate) socket.emit('ice_candidate', { target_id: data.from_id, candidate: e.candidate });
            };
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            socket.emit('answer_call', { target_id: data.from_id, answer: answer });
        } catch (err) {console.error('[WebRTC ERROR]', err);}
    });
    socket.on('call_answered', function(data) {
        if (peerConnection) {
            peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer)).catch(() => {});
    }});
    socket.on('ice_candidate', function(data) {
        if (peerConnection && data.candidate) {
            peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate)).catch(() => {});
    }});
    if (hangupBtn) {
        hangupBtn.addEventListener('click', function() {
            if (peerConnection) {
                peerConnection.close(); peerConnection = null;
            }
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
            if (webrtcContainer) webrtcContainer.classList.add('d-none');
            clearAttachment();});}}