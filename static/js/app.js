let globalFormat = null;
let uploadData = new FormData();
let globalLogs = [];

function formatBytes(bytes, decimals = 2) {
    if (!+bytes) return "0 Bytes";
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function handleFileSelect(index, event) {
    const file = event.target.files[0];
    const infoDiv = document.getElementById(`info-at${index}`);
    const nameEl = infoDiv.querySelector(".filename");
    const metaEl = infoDiv.querySelector(".meta");
    const errEl = infoDiv.querySelector(".error-text");
    const audioEl = infoDiv.querySelector(".preview-audio");

    errEl.innerText = "";

    if (!file) {
        nameEl.innerText = "Chưa chọn file";
        metaEl.innerText = "";
        audioEl.style.display = "none";
        return;
    }

    const ext = file.name.split(".").pop().toLowerCase();
    if (ext !== "mp3" && ext !== "wav") {
        errEl.innerText = `Định dạng không được hỗ trợ: ${ext}`;
        event.target.value = "";
        return;
    }

    if (globalFormat && ext !== globalFormat) {
        errEl.innerText = `Không được trộn MP3 và WAV. Định dạng hiện tại: ${globalFormat.toUpperCase()}`;
        event.target.value = "";
        return;
    }

    if (!globalFormat) globalFormat = ext;

    nameEl.innerText = file.name;
    metaEl.innerText = `${ext.toUpperCase()} · ${formatBytes(file.size)}`;

    audioEl.src = URL.createObjectURL(file);
    audioEl.style.display = "block";
}

async function validateFiles() {
    const gErr = document.getElementById("global-error");
    gErr.style.display = "none";
    uploadData = new FormData();

    for (let i = 1; i <= 5; i++) {
        const input = document.getElementById(`file-at${i}`);
        if (!input.files[0]) {
            gErr.className = "status-fail";
            gErr.innerText = "Vui lòng chọn đủ 5 file âm thanh.";
            gErr.style.display = "block";
            return;
        }
        uploadData.append(`file${i}`, input.files[0]);
    }

    const btn = document.getElementById("btn-validate");
    try {
        btn.disabled = true;
        btn.innerText = "Đang kiểm tra...";

        const res = await fetch("/api/validate", { method: "POST", body: uploadData });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        gErr.className = "status-pass";
        gErr.innerText = "5/5 file hợp lệ. Có thể bắt đầu mã hóa.";
        gErr.style.display = "block";

        document.getElementById("btn-send").disabled = false;
        window.audioId = data.audio_id;
        window.audioFormat = data.format;
    } catch (err) {
        gErr.className = "status-fail";
        gErr.innerText = err.message;
        gErr.style.display = "block";
    } finally {
        btn.disabled = false;
        btn.innerText = "Kiểm tra 5 đoạn";
    }
}

async function sendFiles() {
    if (!window.audioId) return;

    const btn = document.getElementById("btn-send");
    try {
        btn.disabled = true;
        btn.innerText = "Đang gửi...";

        const res = await fetch("/api/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ audio_id: window.audioId, format: window.audioFormat })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        window.location.href = `/transfer/${window.audioId}`;
    } catch (err) {
        const gErr = document.getElementById("global-error");
        gErr.className = "status-fail";
        gErr.innerText = "Lỗi khi gửi: " + err.message;
        gErr.style.display = "block";
        btn.disabled = false;
        btn.innerText = "Mã hóa và gửi";
    }
}

function clearForm() {
    document.getElementById("uploadForm").reset();
    globalFormat = null;
    window.audioId = null;
    window.audioFormat = null;

    for (let i = 1; i <= 5; i++) {
        const info = document.getElementById(`info-at${i}`);
        info.querySelector(".filename").innerText = "Chưa chọn file";
        info.querySelector(".meta").innerText = "";
        info.querySelector(".error-text").innerText = "";
        const audio = info.querySelector(".preview-audio");
        audio.style.display = "none";
        audio.src = "";
    }

    document.getElementById("btn-send").disabled = true;
    const gErr = document.getElementById("global-error");
    gErr.style.display = "none";
}

function updateStatusList(i, stateStr) {
    const list = document.getElementById(`status-list-${i}`);
    if (!list) return;
    const items = list.querySelectorAll("li");
    if (stateStr === "processing" || stateStr === "success") {
        items.forEach(item => item.className = "success");
    }
}

async function pollStatus(id) {
    try {
        const res = await fetch(`/api/transfer/${id}/status`);
        const state = await res.json();

        const progressBar = document.getElementById("progress-bar");
        const statusMessage = document.getElementById("status-message");
        if (progressBar) progressBar.style.width = `${state.progress || 0}%`;
        if (statusMessage) statusMessage.innerText = state.message || "Đang xử lý...";

        if (state.status === "success") {
            for (let i = 1; i <= 5; i++) updateStatusList(i, "success");

            if (window.isReceiving) {
                window.location.href = `/result/${id}`;
            } else {
                const actions = document.getElementById("post-send-actions");
                if (actions) actions.style.display = "flex";
                refreshHackerAudio();
            }
        } else if (state.status === "error") {
            if (statusMessage) statusMessage.className = "status-fail";
            if (window.isReceiving) {
                window.location.href = `/hacker-result/${id}`;
            } else {
                const actions = document.getElementById("post-send-actions");
                if (actions) actions.style.display = "flex";
            }
        } else {
            setTimeout(() => pollStatus(id), 1000);
        }
    } catch (e) {
        console.error("Poll error", e);
        setTimeout(() => pollStatus(id), 1500);
    }
}

async function startReceive() {
    try {
        window.isReceiving = true;
        await fetch(`/api/transfer/${audioId}/receive`, { method: "POST" });
        const actions = document.getElementById("post-send-actions");
        if (actions) actions.style.display = "none";
        pollStatus(audioId);
    } catch (e) {
        alert("Lỗi khi giải mã: " + e.message);
    }
}

async function loadResult(id) {
    try {
        const res = await fetch(`/api/transfer/${id}/status`);
        const state = await res.json();

        if (state.status === "error") {
            const errDiv = document.getElementById("result-error");
            errDiv.style.display = "block";
            errDiv.innerText = "Lỗi: " + state.message;
            return;
        }

        if (state.hash_match) {
            document.getElementById("result-container").style.display = "block";
            document.getElementById("res-audio-id").innerText = id;
            document.getElementById("res-hash-orig").innerText = state.hash_original;
            document.getElementById("res-hash-recon").innerText = state.hash_reconstructed;

            const matchEl = document.getElementById("res-hash-match");
            if (state.hash_match === "PASS") {
                matchEl.innerHTML = `<span class="status-pass">PASS · File sau khi ghép khớp file tham chiếu.</span>`;
            } else {
                matchEl.innerHTML = `<span class="status-fail">FAIL · File sau khi ghép không khớp file tham chiếu.</span>`;
            }

            document.getElementById("audio-player").src = `/download/audio/${id}`;
        }
    } catch (e) {}
}

async function loadManifest(id) {
    try {
        const res = await fetch(`/api/transfer/${id}/manifest`);
        if (!res.ok) return;
        const data = await res.json();

        const summary = document.getElementById("manifest-summary");
        if (summary) {
            summary.innerHTML = `
                <div class="metric"><span>Session</span><strong class="text-sm mono">${data.session_id}</strong></div>
                <div class="metric"><span>Sender</span><strong>${data.sender_id}</strong></div>
                <div class="metric"><span>Receiver</span><strong>${data.receiver_id}</strong></div>
                <div class="metric"><span>Format</span><strong>${data.format.toUpperCase()}</strong></div>
            `;
        }

        const tbody = document.querySelector("#manifest-table tbody");
        if (!tbody) return;
        tbody.innerHTML = "";

        data.segments.forEach(seg => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${seg.sequence_number}</td>
                <td>${seg.original_filename}</td>
                <td>${Number(seg.duration).toFixed(2)} s</td>
                <td><span class="hash-text" title="${seg.plaintext_hash}">${seg.plaintext_hash.substring(0, 12)}...</span></td>
                <td><span class="hash-text" title="${seg.ciphertext_hash}">${seg.ciphertext_hash.substring(0, 12)}...</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {}
}

async function loadLogs(id) {
    try {
        const res = await fetch(`/api/transfer/${id}/logs`);
        const data = await res.json();
        globalLogs = data.logs || [];
        renderLogs("ALL");
    } catch (e) {}
}

function renderLogs(filterLevel) {
    const tbody = document.querySelector("#log-table tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    globalLogs.forEach(log => {
        if (filterLevel !== "ALL" && !log.level.includes(filterLevel) && !log.event.includes(filterLevel)) return;

        const tr = document.createElement("tr");
        if (log.level.includes("ERROR")) tr.style.color = "var(--danger)";
        if (log.level.includes("WARNING")) tr.style.color = "var(--warning)";

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
    const level = document.getElementById("log-filter").value;
    renderLogs(level);
}

function refreshHackerAudio() {
    const hackerAudio = document.getElementById("hacker-audio");
    if (hackerAudio && hackerAudio.getAttribute("data-src")) {
        hackerAudio.src = `${hackerAudio.getAttribute("data-src")}?t=${Date.now()}`;
        hackerAudio.load();
    }
}

async function simulateAttack(action, segmentOrOrder) {
    if (!confirm("Hành động này sẽ thay đổi dữ liệu trên kênh truyền. Tiếp tục?")) return;

    const body = { audio_id: audioId };
    if (action === "reorder") body.order = segmentOrOrder;
    else body.segment = segmentOrOrder;

    try {
        const res = await fetch(`/api/simulate/${action}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await res.json();

        const msgEl = document.getElementById("sim-msg");
        msgEl.style.display = "block";
        if (data.error) {
            msgEl.className = "status-fail mt-4";
            msgEl.innerText = "Lỗi: " + data.error;
        } else {
            msgEl.className = "status-pass mt-4";
            msgEl.innerText = data.message;
            refreshHackerAudio();

            const hackerStatus = document.getElementById("hacker-status");
            if (hackerStatus) {
                hackerStatus.innerText = `Kênh truyền đã bị can thiệp: ${action}`;
                hackerStatus.style.color = "var(--warning)";
            }
        }
    } catch (e) {
        alert(e.message);
    }
}
