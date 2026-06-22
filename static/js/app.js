let globalFormat = null;
let uploadData = new FormData();

function formatBytes(bytes, decimals = 2) {
    if (!+bytes) return '0 Bytes';
    const k = 1024, dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function handleFileSelect(index, event) {
    const file = event.target.files[0];
    const infoDiv = document.getElementById(`info-at${index}`);
    const nameEl = infoDiv.querySelector('.filename');
    const metaEl = infoDiv.querySelector('.meta');
    const errEl = infoDiv.querySelector('.error-text');
    const audioEl = infoDiv.querySelector('.preview-audio');
    
    errEl.innerText = "";
    
    if (!file) {
        nameEl.innerText = "Chưa chọn file";
        metaEl.innerText = "";
        audioEl.style.display = "none";
        return;
    }

    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'mp3' && ext !== 'wav') {
        errEl.innerText = `Định dạng không được hỗ trợ: ${ext}`;
        event.target.value = "";
        return;
    }

    if (globalFormat && ext !== globalFormat) {
        errEl.innerText = `Không được trộn lẫn MP3 và WAV! (Format hiện tại: ${globalFormat})`;
        event.target.value = "";
        return;
    }

    if (!globalFormat) globalFormat = ext;

    nameEl.innerText = file.name;
    metaEl.innerText = `Format: ${ext.toUpperCase()} | Size: ${formatBytes(file.size)}`;
    
    const objUrl = URL.createObjectURL(file);
    audioEl.src = objUrl;
    audioEl.style.display = "block";
}

async function validateFiles() {
    const form = document.getElementById('uploadForm');
    const files = [];
    let valid = true;
    const gErr = document.getElementById('global-error');
    gErr.style.display = 'none';
    
    uploadData = new FormData();

    for (let i = 1; i <= 5; i++) {
        const input = document.getElementById(`file-at${i}`);
        if (!input.files[0]) {
            valid = false;
            break;
        }
        uploadData.append(`file${i}`, input.files[0]);
    }

    if (!valid) {
        gErr.innerText = "Vui lòng chọn đủ 5 file âm thanh.";
        gErr.style.display = 'block';
        return;
    }

    try {
        const btn = document.getElementById('btn-validate');
        btn.disabled = true;
        btn.innerText = "Đang kiểm tra...";

        const res = await fetch('/api/validate', {
            method: 'POST',
            body: uploadData
        });
        const data = await res.json();
        
        if (data.error) throw new Error(data.error);

        gErr.className = "status-pass";
        gErr.innerText = "5/5 files hợp lệ! Sẵn sàng mã hóa.";
        gErr.style.display = 'block';
        
        document.getElementById('btn-send').disabled = false;
        // Save audio_id and format for next step
        window.audioId = data.audio_id;
        window.audioFormat = data.format;
        
    } catch (err) {
        gErr.className = "status-fail";
        gErr.innerText = err.message;
        gErr.style.display = 'block';
    } finally {
        const btn = document.getElementById('btn-validate');
        btn.disabled = false;
        btn.innerText = "Kiểm tra 5 đoạn";
    }
}

async function sendFiles() {
    if (!window.audioId) return;
    try {
        const btn = document.getElementById('btn-send');
        btn.disabled = true;
        btn.innerText = "Đang bắt đầu...";

        const res = await fetch('/api/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ audio_id: window.audioId, format: window.audioFormat })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        // Redirect to transfer page
        window.location.href = `/transfer/${window.audioId}`;

    } catch (err) {
        const gErr = document.getElementById('global-error');
        gErr.className = "status-fail";
        gErr.innerText = "Lỗi khi gửi: " + err.message;
        gErr.style.display = 'block';
        document.getElementById('btn-send').disabled = false;
    }
}

function clearForm() {
    document.getElementById('uploadForm').reset();
    globalFormat = null;
    for (let i = 1; i <= 5; i++) {
        document.getElementById(`info-at${i}`).querySelector('.filename').innerText = "Chưa chọn file";
        document.getElementById(`info-at${i}`).querySelector('.meta').innerText = "";
        document.getElementById(`info-at${i}`).querySelector('.error-text').innerText = "";
        const aud = document.getElementById(`info-at${i}`).querySelector('.preview-audio');
        aud.style.display = "none";
        aud.src = "";
    }
    document.getElementById('btn-send').disabled = true;
    const gErr = document.getElementById('global-error');
    gErr.style.display = 'none';
}

// Polling for Transfer Page
let pollInterval = null;

function updateStatusList(i, stateStr) {
    const list = document.getElementById(`status-list-${i}`);
    if (!list) return;
    const items = list.querySelectorAll('li');
    
    // stateStr mapping heuristic based on general progress
    if (stateStr === 'processing' || stateStr === 'success') {
        items[0].className = 'success'; // Uploaded
        items[1].className = 'success'; // Validated
        items[2].className = 'success'; // Hashed
        items[3].className = 'success'; // Encrypted
        items[4].className = 'success'; // Sent
    }
}

async function pollStatus(id) {
    try {
        const res = await fetch(`/api/transfer/${id}/status`);
        const state = await res.json();
        
        document.getElementById('progress-bar').style.width = `${state.progress}%`;
        document.getElementById('status-message').innerText = state.message;
        
        if (state.status === 'success') {
            for(let i=1; i<=5; i++) updateStatusList(i, 'success');
            // Tự động chuyển hướng sang trang kết quả bình thường
            window.location.href = `/result/${id}`;
        } else if (state.status === 'error') {
            document.getElementById('status-message').className = "status-text status-fail";
            // Tự động chuyển hướng sang trang góc nhìn của hacker
            window.location.href = `/hacker-result/${id}`;
        } else {
            // continue polling
            setTimeout(() => pollStatus(id), 1000);
        }
    } catch (e) {
        console.error("Poll error", e);
    }
}

async function startReceive() {
    try {
        await fetch(`/api/transfer/${audioId}/receive`, { method: 'POST' });
        document.getElementById('post-send-actions').style.display = 'none';
        pollStatus(audioId);
    } catch (e) {
        alert("Lỗi khi giải mã: " + e.message);
    }
}

// Result page logic
async function loadResult(id) {
    try {
        const res = await fetch(`/api/transfer/${id}/status`);
        const state = await res.json();
        
        if (state.status === 'error') {
            const errDiv = document.getElementById('result-error');
            errDiv.style.display = 'block';
            errDiv.innerText = "LỖI: " + state.message;
            return;
        }

        if (state.hash_match) {
            document.getElementById('result-container').style.display = 'block';
            document.getElementById('res-audio-id').innerText = id;
            document.getElementById('res-hash-orig').innerText = state.hash_original;
            document.getElementById('res-hash-recon').innerText = state.hash_reconstructed;
            
            const matchEl = document.getElementById('res-hash-match');
            if (state.hash_match === 'PASS') {
                matchEl.innerHTML = `<span class="status-pass">PASS</span> – File sau khi ghép giống với file tham chiếu.`;
            } else {
                matchEl.innerHTML = `<span class="status-fail">FAIL</span> – File sau khi ghép không khớp với file tham chiếu.`;
            }
            
            // Audio player
            const player = document.getElementById('audio-player');
            player.src = `/download/audio/${id}`;
        }
    } catch (e) {}
}

async function loadManifest(id) {
    try {
        const res = await fetch(`/api/transfer/${id}/manifest`);
        if(!res.ok) return;
        const data = await res.json();
        
        document.getElementById('manifest-summary').innerHTML = `
            <p><strong>Session ID:</strong> ${data.session_id}</p>
            <p><strong>Sender:</strong> ${data.sender_id}</p>
            <p><strong>Receiver:</strong> ${data.receiver_id}</p>
            <p><strong>Format:</strong> ${data.format}</p>
        `;
        
        const tbody = document.querySelector('#manifest-table tbody');
        data.segments.forEach(seg => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${seg.sequence_number}</td>
                <td>${seg.original_filename}</td>
                <td>${seg.metadata.duration_ms} ms</td>
                <td class="hash-text" title="${seg.plaintext_hash}">${seg.plaintext_hash.substring(0,8)}...</td>
                <td class="hash-text" title="${seg.ciphertext_hash}">${seg.ciphertext_hash.substring(0,8)}...</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {}
}

// Logs logic
let globalLogs = [];
async function loadLogs(id) {
    try {
        const res = await fetch(`/api/transfer/${id}/logs`);
        const data = await res.json();
        globalLogs = data.logs;
        renderLogs("ALL");
    } catch (e) {}
}

document.addEventListener('DOMContentLoaded', () => {
    fetchLogs();
    setInterval(fetchLogs, 2000);
});

function renderLogs(filterLevel) {
    const tbody = document.querySelector('#log-table tbody');
    if(!tbody) return;
    tbody.innerHTML = '';
    
    globalLogs.forEach(log => {
        if (filterLevel !== "ALL" && !log.level.includes(filterLevel) && !log.event.includes(filterLevel)) {
            return;
        }
        const tr = document.createElement('tr');
        let color = "inherit";
        if (log.level.includes("ERROR")) color = "var(--danger)";
        if (log.level.includes("WARNING")) color = "#f59e0b";
        
        tr.style.color = color;
        tr.innerHTML = `
            <td>${log.time}</td>
            <td>${log.level}</td>
            <td>${log.event}</td>
            <td>${log.message}</td>
        `;
        tbody.appendChild(tr);
    });
}

function filterLogs() {
    const level = document.getElementById('log-filter').value;
    renderLogs(level);
}

// Simulation logic
async function simulateAttack(action, segmentOrOrder) {
    if (!confirm("Hành động này sẽ can thiệp vào file đã mã hóa trên hệ thống. Tiếp tục?")) return;
    
    let body = { audio_id: audioId };
    if (action === 'reorder') body.order = segmentOrOrder;
    else body.segment = segmentOrOrder;

    try {
        const res = await fetch(`/api/simulate/${action}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const data = await res.json();
        
        const msgEl = document.getElementById('sim-msg');
        msgEl.style.display = 'block';
        if (data.error) {
            msgEl.className = 'status-fail mt-2';
            msgEl.innerText = "Lỗi: " + data.error;
        } else {
            msgEl.className = 'status-pass mt-2';
            msgEl.innerText = data.message;
            
            // Cập nhật lại góc nhìn của Hacker
            const hackerAudio = document.getElementById('hacker-audio');
            if (hackerAudio && hackerAudio.getAttribute('data-src')) {
                hackerAudio.src = hackerAudio.getAttribute('data-src') + "?t=" + Date.now();
                hackerAudio.load();
            }
            
            const hackerStatus = document.getElementById('hacker-status');
            if (hackerStatus) {
                hackerStatus.innerText = `🎧 Kênh truyền bị can thiệp (Mô phỏng: ${action})`;
                hackerStatus.style.color = '#eab308'; // màu vàng cảnh báo
            }
        }
    } catch (e) {
        alert(e.message);
    }
}
