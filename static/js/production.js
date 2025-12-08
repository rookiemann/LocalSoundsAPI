// static/js/production.js

const $ = s => document.querySelector(s);

let currentProjectDir = '';
let currentAudioFile = null;

function setStatus(text, type = 'info') {
    const el = $('#uploadStatus');
    if (el) {
        el.textContent = text;
        el.className = `text-${type} small text-center mt-3`;
    }
}

function resolveProjectDir() {
    const input = $('#projectDir').value.trim();
    if (!input) return '';
    return 'projects_output/' + input.split(/[\\/]/).pop();
}

function getFileUrl(filename) {
    if (currentProjectDir) {
        const full = (currentProjectDir + '\\' + filename).replace(/\\/g, '/');
        return `/file/${encodeURIComponent(filename)}?rel=${encodeURIComponent(full)}`;
    }
    return `/file/${encodeURIComponent(filename)}`;
}

$('#mediaDropZone')?.addEventListener('click', () => $('#mediaInput')?.click());
$('#mediaInput')?.addEventListener('change', () => {
    if ($('#mediaInput').files.length) handleFiles($('#mediaInput').files);
    $('#mediaInput').value = '';
});

['dragover', 'dragenter'].forEach(ev => {
    $('#mediaDropZone')?.addEventListener(ev, e => {
        e.preventDefault();
        $('#mediaDropZone').classList.add('dragover');
    });
});
['dragleave', 'dragend', 'drop'].forEach(ev => {
    $('#mediaDropZone')?.addEventListener(ev, e => {
        e.preventDefault();
        $('#mediaDropZone').classList.remove('dragover');
    });
});
$('#mediaDropZone')?.addEventListener('drop', e => {
    e.preventDefault();
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
});


async function handleFiles(files) {
    currentProjectDir = resolveProjectDir();

    const fd = new FormData();
    Array.from(files).forEach(f => fd.append('file', f));
    if (currentProjectDir) fd.append('project_dir', currentProjectDir);

    setStatus(`Uploading ${files.length} file(s)...`, 'info');

    try {
        const r = await fetch('/production/upload_media', { method: 'POST', body: fd });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || 'Upload failed');

        setStatus(`Uploaded ${files.length} file(s)`, 'success');
        await refreshFileList();

        const audio = Array.from(files).find(f => /\.(wav|mp3|flac|ogg|m4a)$/i.test(f.name));
        if (audio && $('#prod_autoTranscribe')?.checked) {
            currentAudioFile = audio.name;
            $('#mediaSelect').value = currentAudioFile;
            selectMediaFile(currentAudioFile);
            await transcribeCurrent();  // await so it finishes
        }
    } catch (e) {
        setStatus(e.message, 'danger');
    }
}

async function refreshFileList() {
    const dir = currentProjectDir || '';
    const ts = Date.now();
    const [audioRes, imgRes] = await Promise.all([
        fetch(`/production/list_audio?dir=${encodeURIComponent(dir)}&t=${ts}`).then(r => r.json()),
        fetch(`/production/list_images?dir=${encodeURIComponent(dir)}&t=${ts}`).then(r => r.json())
    ]);

    const all = [...new Set([...audioRes, ...imgRes])].sort();
    $('#mediaSelect').innerHTML = all.map(f => `<option value="${f}">${f}</option>`).join('');
}

$('#mediaSelect')?.addEventListener('change', () => {
    const f = $('#mediaSelect').value;
    if (!f) return;
    selectMediaFile(f);

    if (/\.(wav|mp3|flac|ogg|m4a)$/i.test(f) && $('#prod_autoTranscribe')?.checked) {
        transcribeCurrent();
    }
});

function selectMediaFile(filename) {
    const url = getFileUrl(filename);
    const isVideo = /\.(mp4|webm|mov|avi|mkv)$/i.test(filename);
    const isAudio = /\.(wav|mp3|flac|ogg|m4a)$/i.test(filename);

    $('#previewName').textContent = filename;

    if (isVideo) {
        $('#previewArea').innerHTML = `<video controls loop autoplay class="img-fluid rounded shadow" style="max-height:100%;max-width:100%"><source src="${url}"></video>`;
    } else if (isAudio) {
        $('#previewArea').innerHTML = `
            <audio controls class="w-100 mb-3"><source src="${url}"></audio>
            <div class="text-center text-muted small">Selected audio — will be used for final video</div>`;
        currentAudioFile = filename;
        $('#transcribeBtn').disabled = false;
        $('#createVideoBtn').disabled = false;
    } else {
        $('#previewArea').innerHTML = `<img src="${url}" class="img-fluid rounded shadow" style="max-height:100%">`;
    }
}

$('#loadProjectBtn')?.addEventListener('click', () => {
    currentProjectDir = resolveProjectDir().replace(/\\+$/, '');
    refreshFileList();
    $('#previewArea').innerHTML = '<small class="text-muted">Click a file to preview</small>';
    $('#previewName').textContent = '';
    currentAudioFile = null;
    $('#transcribeBtn').disabled = true;
    $('#createVideoBtn').disabled = true;
    setStatus(currentProjectDir ? `Project: ${currentProjectDir}` : 'Temporary mode');
});

async function transcribeCurrent() {
    if (!currentAudioFile) return;

    $('#transcribeBtn').disabled = true;
    setStatus('Checking for existing transcription...', 'info');

    // Step 1: Fast cache check first
    try {
        const statusRes = await fetch('/production/transcribe_status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: currentAudioFile, project_dir: currentProjectDir })
        });
        const statusData = await statusRes.json();

        if (statusData.cached) {
            // Cache exists → load the text from the existing JSON (fast)
            const r = await fetch('/production/transcribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: currentAudioFile, project_dir: currentProjectDir })
            });
            const d = await r.json();
            $('#transcriptionText').value = (d.text || '').trim();
            setStatus('Transcription loaded from cache', 'success');

            if ($('#prod_autoMakeVideo')?.checked) {
                setTimeout(() => $('#createVideoBtn').click(), 800);
            }
            return;
        }
    } catch (e) {
        console.warn("Cache check failed, continuing...", e);
    }

    setStatus('No cache found → ensuring Whisper is ready...', 'info');

    let whisperReady = false;
    try {
        const status = await fetch('/whisper_status').then(r => r.json());
        if (status.loaded) {
            console.log("[WHISPER] Already loaded in memory");
            setStatus('Whisper already loaded', 'success');
            whisperReady = true;
        }
    } catch (e) {}

    if (!whisperReady) {
        setStatus('Loading Whisper model...', 'info');
        const device = $('#whisperDeviceSelect').value;

        try {
            const r = await fetch('/whisper_load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device })
            });
            if (!r.ok) throw new Error();
            console.log("[WHISPER] Load request sent successfully");
            await new Promise(r => setTimeout(r, 800)); // give server a moment
        } catch (e) {
            setStatus('GPU failed → falling back to CPU', 'warning');
            await fetch('/whisper_load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device: 'cpu' })
            });
        }
    }

    setStatus('Transcribing audio...', 'info');
    try {
        const r = await fetch('/production/transcribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: currentAudioFile, project_dir: currentProjectDir })
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || 'Failed');

        $('#transcriptionText').value = d.text.trim();
        setStatus('Transcription complete', 'success');

        if ($('#prod_autoMakeVideo')?.checked) {
            setTimeout(() => $('#createVideoBtn').click(), 800);
        }
    } catch (e) {
        setStatus('Transcription failed: ' + e.message, 'danger');
    } finally {
        $('#transcribeBtn').disabled = false;
    }
}

$('#transcribeBtn')?.addEventListener('click', transcribeCurrent);
$('#createVideoBtn')?.addEventListener('click', async () => {
    if (!currentAudioFile) return;
    $('#createVideoBtn').disabled = true;
    setStatus('Creating video...', 'info');

    // Parse the single dropdown value
    const bgValue = $('#bgModeSelect').value;    
    const [bg_mode, chroma_color] = bgValue.includes('|') 
        ? bgValue.split('|') 
        : [bgValue, 'red'];     

    const payload = {
        audio_file: currentAudioFile,
        project_dir: currentProjectDir,
        resolution: $('#resolution').value,
        bg_mode: bg_mode,    
        chroma_color: chroma_color  
    };

    try {
        const r = await fetch('/production/make_video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || 'Failed');

        const url = getFileUrl(d.video_file);
        $('#resultVideo').src = url;
        $('#downloadLink').href = url;
        $('#downloadLink').download = d.video_file;
        $('#videoResult').style.display = 'block';
        setStatus('Video ready!', 'success');
        window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
    } catch (e) {
        setStatus('Video failed: ' + e.message, 'danger');
    } finally {
        $('#createVideoBtn').disabled = false;
    }
});


$('#folderLabel')?.addEventListener('click', () => $('#folderPicker').click());
$('#folderPicker')?.addEventListener('change', e => {
    const files = e.target.files;
    if (!files.length) return;

    const diskPath = files[0].path;
    if (diskPath && diskPath.includes('\\')) {
        $('#projectDir').value = diskPath.split('\\').slice(0, -1).join('\\');
    } else {
        $('#projectDir').value = files[0].webkitRelativePath.split('/')[0];
    }

    $('#loadProjectBtn').click();
    $('#folderPicker').value = '';
});

$('#transcribeBtn').disabled = true;
$('#createVideoBtn').disabled = true;
setStatus('Ready — drop files or scan folder');

fetch('/whisper_status')
    .then(r => r.json())
    .then(data => {
        if (data.loaded && $('#whisperStatusBadge')) {
            $('#whisperStatusBadge').className = 'badge bg-success';
            $('#whisperStatusBadge').textContent = 'Whisper ready';
        }
    })
    .catch(() => {});

