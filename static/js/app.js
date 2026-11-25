// Online Manim Compiler Client Application

let editor = null;
let currentJobId = null;
let activeWebSocket = null;
let activePollInterval = null;
let renderTimerInterval = null;
let renderStartTime = 0;
let lastRenderedFile = null;

// DOM Elements
const templateSelect = document.getElementById('template-select');
const qualitySelect = document.getElementById('quality-select');
const sceneSelect = document.getElementById('scene-select');
const formatSelect = document.getElementById('format-select');
const btnRun = document.getElementById('btn-run');
const runIcon = document.getElementById('run-icon');
const runLabel = document.getElementById('run-label');
const btnDownload = document.getElementById('btn-download');
const btnHelp = document.getElementById('btn-help');
const btnCloseModal = document.getElementById('btn-close-modal');
const helpModal = document.getElementById('help-modal');
const btnClearConsole = document.getElementById('btn-clear-console');
const btnCopy = document.getElementById('btn-copy');
const btnFormat = document.getElementById('btn-format');

const consoleBody = document.getElementById('console-body');
const stagePlaceholder = document.getElementById('stage-placeholder');
const videoPlayer = document.getElementById('video-player');
const gifPlayer = document.getElementById('gif-player');
const renderOverlay = document.getElementById('render-overlay');
const renderStatusText = document.getElementById('render-status-text');
const renderProgressBar = document.getElementById('render-progress-bar');
const renderTimer = document.getElementById('render-timer');
const statusText = document.getElementById('status-text');
const cursorPos = document.getElementById('cursor-pos');

// Initialize Monaco Editor
function initMonaco() {
  if (typeof require !== 'undefined') {
    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
    require(['vs/editor/editor.main'], function () {
      editor = monaco.editor.create(document.getElementById('editor'), {
        value: '# Loading...',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14,
        fontFamily: "'Fira Code', Consolas, monospace",
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        lineNumbers: 'on',
        tabSize: 4,
        insertSpaces: true,
      });

      // Track cursor position
      editor.onDidChangeCursorPosition((e) => {
        cursorPos.textContent = `Ln ${e.position.lineNumber}, Col ${e.position.column}`;
      });

      // Detect scenes and syntax on change (debounced)
      let debounceTimeout = null;
      editor.onDidChangeModelContent(() => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(analyzeCode, 600);
      });

      // Add hotkey Ctrl+Enter to Run
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
        triggerRender();
      });

      // Load initial templates
      loadTemplates();
    });
  } else {
    console.error("Monaco loader not found, falling back.");
  }
}

// Fetch and populate templates
async function loadTemplates() {
  try {
    const res = await fetch('/api/templates');
    const data = await res.json();
    templateSelect.innerHTML = '';
    
    data.templates.forEach((tmpl, idx) => {
      const opt = document.createElement('option');
      opt.value = tmpl.id;
      opt.textContent = tmpl.name;
      templateSelect.appendChild(opt);
    });

    if (data.templates.length > 0) {
      setEditorTemplate(data.templates[0]);
    }
  } catch (err) {
    appendLog(`Failed to load templates: ${err.message}`, 'error');
  }
}

function setEditorTemplate(tmpl) {
  if (editor && tmpl) {
    editor.setValue(tmpl.code);
    analyzeCode();
  }
}

templateSelect.addEventListener('change', async (e) => {
  const tmplId = e.target.value;
  if (!tmplId) return;
  try {
    const res = await fetch(`/api/templates/${tmplId}`);
    const tmpl = await res.json();
    setEditorTemplate(tmpl);
  } catch (err) {
    appendLog(`Error fetching template: ${err.message}`, 'error');
  }
});

// Analyze code for scenes & syntax errors
async function analyzeCode() {
  if (!editor) return;
  const code = editor.getValue();
  if (!code.trim()) return;

  try {
    const res = await fetch('/api/detect-scenes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    const data = await res.json();

    const indicator = document.querySelector('.status-indicator');
    if (!data.valid_syntax) {
      indicator.classList.add('error');
      statusText.textContent = `Syntax Error (Ln ${data.error.line})`;
    } else {
      indicator.classList.remove('error');
      statusText.textContent = `Ready (${data.scenes.length} scene${data.scenes.length === 1 ? '' : 's'})`;
    }

    // Update scene select dropdown
    const currentVal = sceneSelect.value;
    sceneSelect.innerHTML = '<option value="">Auto Detect</option>';
    data.scenes.forEach(sceneName => {
      const opt = document.createElement('option');
      opt.value = sceneName;
      opt.textContent = sceneName;
      if (sceneName === currentVal) opt.selected = true;
      sceneSelect.appendChild(opt);
    });
  } catch (err) {
    console.warn("Scene analysis error:", err);
  }
}

// Log Terminal Utility
function appendLog(text, type = 'normal') {
  const line = document.createElement('div');
  line.className = `log-line ${type}`;
  line.textContent = text;
  consoleBody.appendChild(line);
  consoleBody.scrollTop = consoleBody.scrollHeight;
}

btnClearConsole.addEventListener('click', () => {
  consoleBody.innerHTML = '';
  appendLog('Console cleared.', 'info');
});

// Trigger Render
async function triggerRender() {
  if (!editor || btnRun.disabled) return;
  const code = editor.getValue();
  if (!code.trim()) {
    alert("Please write some Manim code first!");
    return;
  }

  const quality = qualitySelect.value;
  const scene_name = sceneSelect.value;
  const output_format = formatSelect.value;

  // Set UI state to running
  btnRun.disabled = true;
  runIcon.textContent = '⏳';
  runLabel.textContent = 'Rendering...';
  renderOverlay.style.display = 'flex';
  renderProgressBar.style.width = '5%';
  renderStatusText.textContent = 'Submitting job...';
  
  renderStartTime = Date.now();
  renderTimerInterval = setInterval(() => {
    const elapsed = ((Date.now() - renderStartTime) / 1000).toFixed(1);
    renderTimer.textContent = `${elapsed}s elapsed`;
  }, 100);

  appendLog(`\n--- Starting Compilation: ${scene_name || 'Auto-Detect'} (${quality}) ---`, 'info');

  try {
    const res = await fetch('/api/compile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        scene_name,
        quality,
        output_format
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Compilation request failed");
    }

    const data = await res.json();
    currentJobId = data.job_id;
    connectWebSocket(currentJobId);

  } catch (err) {
    appendLog(`Failed to start compilation: ${err.message}`, 'error');
    finishRender(false);
  }
}

btnRun.addEventListener('click', triggerRender);

// WebSocket connection for real-time logs & status
function connectWebSocket(jobId) {
  if (activeWebSocket) {
    try { activeWebSocket.close(); } catch (e) {}
    activeWebSocket = null;
  }
  if (activePollInterval) {
    clearInterval(activePollInterval);
    activePollInterval = null;
  }

  let isComplete = false;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/compile/${jobId}`;
  
  try {
    activeWebSocket = new WebSocket(wsUrl);
  } catch (err) {
    console.warn("WebSocket creation failed, falling back to polling:", err);
    pollJobStatus(jobId);
    return;
  }

  activeWebSocket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);

      if (msg.type === 'log') {
        appendLog(msg.message);
        if (msg.progress) {
          renderProgressBar.style.width = `${msg.progress}%`;
          renderStatusText.textContent = `Compiling... ${msg.progress}%`;
        }
      } else if (msg.type === 'heartbeat') {
        if (msg.progress) {
          renderProgressBar.style.width = `${msg.progress}%`;
        }
      } else if (msg.type === 'done') {
        isComplete = true;
        if (msg.status === 'completed') {
          renderProgressBar.style.width = '100%';
          displayOutput(msg.output_file);
          finishRender(true, msg.duration);
        } else {
          finishRender(false);
        }
      }
    } catch (e) {
      console.error("Error parsing WebSocket message:", e);
    }
  };

  activeWebSocket.onerror = (e) => {
    if (!isComplete && btnRun.disabled) {
      console.warn("WebSocket error, switching to polling fallback:", e);
      pollJobStatus(jobId);
    }
  };

  activeWebSocket.onclose = () => {
    // Only fall back to polling if job has not finished and still rendering
    if (!isComplete && btnRun.disabled && !activePollInterval) {
      pollJobStatus(jobId);
    }
  };
}

// Controlled Polling Fallback
function pollJobStatus(jobId) {
  if (activePollInterval) {
    clearInterval(activePollInterval);
    activePollInterval = null;
  }

  let failureCount = 0;
  const MAX_FAILURES = 3;

  activePollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${jobId}`);
      if (!res.ok) {
        failureCount++;
        if (failureCount >= MAX_FAILURES) {
          clearInterval(activePollInterval);
          activePollInterval = null;
          appendLog(`Job status not available (${res.status}). Compilation interrupted.`, 'error');
          finishRender(false);
        }
        return;
      }

      // Reset failure count on valid response
      failureCount = 0;
      const data = await res.json();

      if (data.progress) {
        renderProgressBar.style.width = `${data.progress}%`;
        renderStatusText.textContent = `Compiling... ${data.progress}%`;
      }

      if (data.status === 'completed') {
        clearInterval(activePollInterval);
        activePollInterval = null;
        displayOutput(data.output_file);
        finishRender(true, data.duration);
      } else if (data.status === 'failed') {
        clearInterval(activePollInterval);
        activePollInterval = null;
        finishRender(false);
      }
    } catch (e) {
      failureCount++;
      if (failureCount >= MAX_FAILURES) {
        clearInterval(activePollInterval);
        activePollInterval = null;
        finishRender(false);
      }
    }
  }, 1500);
}

function displayOutput(filename) {
  if (!filename) return;
  lastRenderedFile = filename;
  stagePlaceholder.style.display = 'none';

  const fileUrl = `/api/video/${filename}?t=${Date.now()}`;

  if (filename.endsWith('.gif')) {
    videoPlayer.style.display = 'none';
    gifPlayer.style.display = 'block';
    gifPlayer.src = fileUrl;
  } else {
    gifPlayer.style.display = 'none';
    videoPlayer.style.display = 'block';
    videoPlayer.src = fileUrl;
    videoPlayer.load();
    videoPlayer.play().catch(() => {});
  }

  btnDownload.disabled = false;
}

function finishRender(success, duration = null) {
  clearInterval(renderTimerInterval);
  renderTimerInterval = null;
  
  if (activePollInterval) {
    clearInterval(activePollInterval);
    activePollInterval = null;
  }

  if (activeWebSocket) {
    try { activeWebSocket.close(); } catch (e) {}
    activeWebSocket = null;
  }

  renderOverlay.style.display = 'none';
  btnRun.disabled = false;
  runIcon.textContent = '▶';
  runLabel.textContent = 'Render';

  if (success) {
    appendLog(`🎉 Rendering completed successfully! Duration: ${duration || '0'}s`, 'success');
  } else {
    appendLog('❌ Rendering failed or stopped.', 'error');
  }
}

// Download Button
btnDownload.addEventListener('click', () => {
  if (!lastRenderedFile) return;
  const a = document.createElement('a');
  a.href = `/api/video/${lastRenderedFile}`;
  a.download = lastRenderedFile;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
});

// Copy Code Button
btnCopy.addEventListener('click', () => {
  if (!editor) return;
  navigator.clipboard.writeText(editor.getValue()).then(() => {
    btnCopy.textContent = '✅ Copied!';
    setTimeout(() => { btnCopy.textContent = '📋 Copy'; }, 1500);
  });
});

// Help Modal
btnHelp.addEventListener('click', () => helpModal.classList.add('open'));
btnCloseModal.addEventListener('click', () => helpModal.classList.remove('open'));
helpModal.addEventListener('click', (e) => {
  if (e.target === helpModal) helpModal.classList.remove('open');
});

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
  initMonaco();
});
