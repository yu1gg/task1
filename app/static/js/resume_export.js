(() => {
  'use strict';
  const root = document.getElementById('resume-export');
  if (!root) return;
  const base = `/teacher/resume-exports/${root.dataset.taskId}`;
  const progress = document.getElementById('export-progress');
  const error = document.getElementById('export-error');
  const list = document.getElementById('export-items');
  const download = document.getElementById('export-download');
  const retry = document.getElementById('export-retry');
  const refresh = document.getElementById('export-refresh');
  const labels = {queued: '排队中', running: '生成中', pending: '等待生成', processing: '生成中', completed: '已完成', partial: '部分完成', failed: '失败', expired: '已过期，请重新创建任务', invalidated: '联系方式授权已变化，请重新创建任务'};
  let timer;
  async function poll() {
    clearTimeout(timer);
    refresh.hidden = true;
    try {
      const response = await fetch(`${base}/status`, {cache: 'no-store'});
      if (!response.ok || response.redirected) throw new Error('读取任务失败，请确认登录状态后重新读取。');
      const data = await response.json();
      progress.textContent = `${labels[data.status] || data.status}：${data.completed}/${data.total}`;
      error.textContent = data.error || '';
      list.replaceChildren(...data.items.map(item => {
        const li = document.createElement('li');
        li.textContent = `${item.name}：${labels[item.status] || item.status}${item.error ? ` — ${item.error}` : ''}`;
        return li;
      }));
      download.hidden = !data.download_url;
      if (data.download_url) download.href = data.download_url;
      retry.hidden = !data.can_retry;
      if (['queued', 'running', 'processing'].includes(data.status)) timer = setTimeout(poll, 2000);
    } catch (e) {
      error.textContent = e.message || '网络错误，请重新读取状态。';
      refresh.hidden = false;
    }
  }
  refresh.addEventListener('click', poll);
  retry.addEventListener('click', async () => {
    retry.disabled = true;
    try {
      const response = await fetch(`${base}/retry`, {method: 'POST'});
      if (response.status !== 202) throw new Error('重试未成功，请重新读取状态。');
      await poll();
    } catch (e) {
      error.textContent = e.message;
      refresh.hidden = false;
    } finally { retry.disabled = false; }
  });
  poll();
})();
