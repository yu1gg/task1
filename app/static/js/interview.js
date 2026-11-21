(() => {
  'use strict';
  const root = document.getElementById('interview-room');
  if (!root) return;
  const el = id => document.getElementById(id);
  const base = `/interviews/${root.dataset.interviewId}`;
  let state, turn, timer, recorder, stream, recording = false, requesting = false;
  let pending = false, selectedFile, previewUrl, questionAudio, recordTimer, historySignature;
  let recordingEpoch = 0, playbackEpoch = 0, refreshSerial = 0, errorKind = '', recordDeadline;
  const maxBytes = 20 * 1024 * 1024;
  const canRecord = window.isSecureContext && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function' && typeof window.MediaRecorder === 'function';
  const editable = t => t && ['waiting', 'ready', 'awaiting_answer', 'failed'].includes(t.status);
  function error(message = '', kind = 'ui') { errorKind = message ? kind : ''; el('room-error').textContent = message; el('room-error').hidden = !message; }
  function invalidateRecording() {
    recordingEpoch++;
    clearInterval(recordTimer); clearTimeout(recordDeadline);
    if (recorder && recorder.state === 'recording') recorder.stop();
    if (stream) stream.getTracks().forEach(track => track.stop());
    recording = false; requesting = false;
    el('record-time').textContent = '';
  }
  async function fetchTimed(url, options) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, { ...options, signal: controller.signal });
      // Read the body within the same deadline; headers alone do not finish a request.
      const body = await response.arrayBuffer();
      return new Response(response.status === 204 ? null : body, { status: response.status, statusText: response.statusText, headers: response.headers });
    }
    finally { clearTimeout(timeout); }
  }
  function stopPlayback() {
    playbackEpoch++;
    if (questionAudio) questionAudio.pause();
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    el('answer-preview').pause();
    document.querySelectorAll('#turn-history audio').forEach(a => a.pause());
  }
  function discard() {
    selectedFile = null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    el('answer-preview').removeAttribute('src');
    el('answer-file').value = '';
    el('preview-panel').hidden = true;
  }
  function selectFile(file) {
    if (!file) return;
    if (!file.size || file.size > 20 * 1024 * 1024) { error('请选择非空且不超过 20 MB 的音频。'); return; }
    discard(); selectedFile = file; previewUrl = URL.createObjectURL(file);
    el('answer-preview').src = previewUrl;
    el('file-label').textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    el('preview-panel').hidden = false; error();
  }
  function lock() {
    const blocked = pending || recording || requesting || !editable(turn) || (state && state.status !== 'in_progress');
    ['start-record', 'answer-file', 'discard-answer', 'submit-answer'].forEach(id => { el(id).disabled = blocked; });
    if (!canRecord) { el('start-record').disabled = true; el('record-hint').textContent = '当前环境不支持录音，请上传音频文件；录音需使用支持 MediaRecorder 的浏览器及 HTTPS / localhost。'; }
    el('stop-record').disabled = !recording;
    ['play-question', 'pause-question', 'replay-question'].forEach(id => { el(id).disabled = recording || requesting; });
    el('answer-preview').controls = !recording;
    el('retry-turn').disabled = pending;
    el('retry-session').disabled = pending;
  }
  function playbackValid(epoch, questionId) {
    return epoch === playbackEpoch && turn && turn.id === questionId && !recording && !requesting;
  }
  function fallbackSpeech(epoch, questionId, question) {
    if (!playbackValid(epoch, questionId)) return;
    if (!('speechSynthesis' in window)) { error('无法播放语音，请阅读题目文字后作答。'); return; }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(question); utterance.lang = 'zh-CN';
    utterance.onerror = event => { if (playbackValid(epoch, questionId) && !['interrupted', 'canceled'].includes(event.error)) error('浏览器朗读失败，请阅读题目文字后作答。'); };
    window.speechSynthesis.speak(utterance);
  }
  function playQuestion(restart = false) {
    if (!turn || recording || requesting) return;
    const epoch = ++playbackEpoch;
    const questionId = turn.id;
    const question = turn.question;
    const fallback = event => {
      if (event && (event.name === 'AbortError' || ['interrupted', 'canceled', 'cancelled'].includes(event.error))) return;
      if (playbackValid(epoch, questionId)) fallbackSpeech(epoch, questionId, question);
    };
    el('answer-preview').pause();
    document.querySelectorAll('#turn-history audio').forEach(a => a.pause());
    if (turn.question_audio_url) {
      const resumeAt = !restart && questionAudio ? questionAudio.currentTime : 0;
      if (questionAudio) questionAudio.pause();
      // Each playback owns its callbacks, so late events cannot adopt a newer epoch.
      questionAudio = new Audio(`${base}/turns/${questionId}/question-audio`);
      questionAudio.onerror = fallback;
      if (resumeAt) questionAudio.currentTime = resumeAt;
      questionAudio.play().catch(fallback);
    } else if (!restart && 'speechSynthesis' in window && window.speechSynthesis.paused) window.speechSynthesis.resume();
    else fallbackSpeech(epoch, questionId, question);
  }
  function history(turns) {
    const signature = JSON.stringify(turns);
    if (historySignature === signature) return;
    historySignature = signature;
    const host = el('turn-history'); host.replaceChildren();
    for (const t of turns) {
      const section = document.createElement('section'); section.className = 'card card-body';
      const add = (tag, text) => { const node = document.createElement(tag); node.textContent = text; node.className = 'interview-text'; section.append(node); };
      add('h3', `第 ${t.seq} 题`); add('p', t.question);
      if (t.transcript) { add('h4', '回答转写'); add('p', t.transcript); }
      if (t.feedback) { add('h4', '反馈'); add('p', typeof t.feedback === 'string' ? t.feedback : JSON.stringify(t.feedback)); }
      if (t.error) add('p', t.error);
      if (t.answer_audio_url) {
        const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none'; audio.src = `${base}/turns/${t.id}/answer-audio`;
        audio.addEventListener('play', () => { if (recording || requesting) audio.pause(); else { playbackEpoch++; if (questionAudio) questionAudio.pause(); if ('speechSynthesis' in window) window.speechSynthesis.cancel(); } }); section.append(audio);
      }
      host.append(section);
    }
  }
  function render(data) {
    state = data;
    const turns = data.turns || []; const next = turns[turns.length - 1];
    const changed = !turn || !next || turn.id !== next.id;
    const locked = !editable(next) || data.status !== 'in_progress';
    if (changed || locked) {
      invalidateRecording(); stopPlayback(); discard();
      if (changed) questionAudio = null;
      if (errorKind !== 'permission') error();
    } else if (errorKind === 'server' && !data.error && !(next && next.error)) error();
    turn = next;
    const labels = { preparing: '正在准备面试题…', preparing_busy: '正在准备面试题…', in_progress: '请听题或阅读题目后作答', completed: '面试已完成，可以查看报告', report_pending: '正在生成面试报告…', report_busy: '正在生成面试报告…', generating_report: '正在生成面试报告…', reporting: '正在生成面试报告…', failed: '处理失败，请重试', report_failed: '报告生成失败，请重试', preparation_failed: '题目准备失败，请重试', prepare_failed: '题目准备失败，请重试' };
    el('room-status').textContent = labels[data.status] || `面试状态：${data.status}`;
    if (data.status === 'setup_failed') el('room-status').textContent = '题目准备失败，请重试';
    el('question-panel').hidden = !turn;
    el('retry-session').hidden = !data.error && !String(data.status).includes('failed');
    el('report-link').hidden = !data.report_url;
    if (data.report_url) el('report-link').href = `${base}/report`;
    if (turn) {
      el('question-heading').textContent = `第 ${turn.seq} / ${data.question_count} 题`;
      el('question-text').textContent = turn.question;
      el('answer-controls').hidden = !editable(turn) || data.status !== 'in_progress';
      el('retry-turn').hidden = !turn.error && !String(turn.status).includes('failed');
      if (!editable(turn) && !turn.error && data.status === 'in_progress') el('room-status').textContent = '正在识别与评估回答，请稍候…';
    }
    if ((data.error || (turn && turn.error)) && errorKind !== 'permission') error(data.error || turn.error, 'server');
    history(turns); lock();
  }
  async function refresh() {
    clearTimeout(timer);
    const serial = ++refreshSerial;
    try { const r = await fetchTimed(`${base}/status`, { headers: { Accept: 'application/json' } }); if (!r.ok) throw new Error(`读取进度失败（${r.status}）`); const data = await r.json(); if (serial === refreshSerial) render(data); }
    catch (e) { if (serial === refreshSerial && errorKind !== 'permission') error(e.name === 'AbortError' ? '读取进度超时，将自动重试。' : `${e.message}，将自动重试。`); }
    finally { if (serial === refreshSerial && (!state || state.status !== 'completed')) timer = setTimeout(refresh, 2000); }
  }
  async function post(path, body) {
    if (pending) return;
    pending = true; lock(); error();
    try {
      const response = await fetchTimed(path, { method: 'POST', body, headers: { Accept: 'application/json' } });
      if (!response.ok) { let message = `提交失败（${response.status}）`; try { const data = await response.json(); if (typeof data.detail === 'string') message = data.detail; } catch (_) {} throw new Error(message); }
      discard(); await refresh();
    } catch (e) {
      if (e.name === 'AbortError') { await refresh(); if (editable(turn)) error('请求超时，已刷新进度；所选音频已保留，请确认状态后重试。'); }
      else error(e.message);
    }
    finally { pending = false; lock(); }
  }
  function stopRecording() { if (recorder && recorder.state === 'recording') recorder.stop(); }
  el('start-record').addEventListener('click', async () => {
    if (recording || requesting || pending || !editable(turn)) return;
    if (!canRecord) { error('当前浏览器无法录音，请使用 HTTPS / localhost 或上传音频文件。'); return; }
    const epoch = ++recordingEpoch;
    const questionId = turn.id;
    const valid = () => epoch === recordingEpoch && turn && turn.id === questionId && editable(turn) && state.status === 'in_progress';
    requesting = true; lock(); stopPlayback();
    let localStream;
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!valid()) { localStream.getTracks().forEach(track => track.stop()); return; }
      discard();
      stream = localStream;
      const mime = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/webm'].find(type => MediaRecorder.isTypeSupported(type));
      const localRecorder = mime ? new MediaRecorder(localStream, { mimeType: mime }) : new MediaRecorder(localStream);
      recorder = localRecorder;
      const chunks = []; let bytes = 0, oversized = false, broken = false;
      const started = performance.now();
      localRecorder.ondataavailable = event => {
        if (!valid()) return;
        if (event.data.size) { bytes += event.data.size; if (bytes >= maxBytes) { oversized = true; stopRecording(); error('录音已达到 20 MB 上限，请缩短回答后重新录制。'); } else chunks.push(event.data); }
        if (performance.now() - started >= 90000) stopRecording();
      };
      localRecorder.onstop = () => {
        localStream.getTracks().forEach(track => track.stop());
        if (!valid()) return;
        clearInterval(recordTimer); clearTimeout(recordDeadline); recording = false;
        el('record-time').textContent = `已录制 ${Math.min(90, Math.floor((performance.now() - started) / 1000))} 秒`;
        const type = localRecorder.mimeType || 'audio/webm'; const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm';
        if (!oversized && !broken) selectFile(new File(chunks, `answer.${ext}`, { type }));
        lock();
      };
      localRecorder.onerror = () => { if (valid()) { broken = true; stopRecording(); error('录音发生错误，请重试或上传音频。'); } };
      localRecorder.start(250); recording = true; el('record-time').textContent = '录音中 0 / 90 秒'; error();
      const updateElapsed = () => { if (!valid()) return; const elapsed = performance.now() - started; el('record-time').textContent = `录音中 ${Math.min(90, Math.floor(elapsed / 1000))} / 90 秒`; if (elapsed >= 90000) stopRecording(); };
      recordTimer = setInterval(updateElapsed, 250);
      recordDeadline = setTimeout(updateElapsed, 90000);
    } catch (e) { if (localStream) localStream.getTracks().forEach(track => track.stop()); if (valid()) error(e.name === 'NotAllowedError' ? '麦克风权限被拒绝，可修改浏览器权限后重试，或上传音频。' : '无法使用麦克风，请检查设备或上传音频。', e.name === 'NotAllowedError' ? 'permission' : 'ui'); }
    finally { if (epoch === recordingEpoch) { requesting = false; lock(); } }
  });
  el('stop-record').addEventListener('click', stopRecording);
  el('answer-file').addEventListener('change', event => selectFile(event.target.files[0]));
  el('discard-answer').addEventListener('click', discard);
  el('submit-answer').addEventListener('click', () => { if (!selectedFile || pending || recording || !editable(turn)) return; const form = new FormData(); form.append('file', selectedFile); post(`${base}/turns/${turn.id}/answer`, form); });
  el('retry-turn').addEventListener('click', () => { if (turn) post(`${base}/turns/${turn.id}/retry`); });
  el('retry-session').addEventListener('click', () => post(`${base}/retry`));
  el('play-question').addEventListener('click', () => playQuestion());
  el('replay-question').addEventListener('click', () => playQuestion(true));
  el('pause-question').addEventListener('click', () => { playbackEpoch++; if (questionAudio) questionAudio.pause(); if ('speechSynthesis' in window) window.speechSynthesis.pause(); });
  el('answer-preview').addEventListener('play', () => { if (recording || requesting) el('answer-preview').pause(); else { playbackEpoch++; if (questionAudio) questionAudio.pause(); if ('speechSynthesis' in window) window.speechSynthesis.cancel(); } });
  document.addEventListener('visibilitychange', () => { if (document.hidden && recording) stopRecording(); });
  window.addEventListener('pagehide', () => { clearTimeout(timer); invalidateRecording(); stopPlayback(); if (previewUrl) URL.revokeObjectURL(previewUrl); });
  lock();
  refresh();
})();
