const $ = (id) => document.getElementById(id);

const btn = $('submitBtn');
const messageBox = $('message');
const resultBox = $('result');

function showMessage(text, isLoading = false) {
  messageBox.textContent = text;
  messageBox.className = isLoading ? 'message message--loading' : 'message';
  messageBox.hidden = false;
}

function hideMessage() {
  messageBox.hidden = true;
}

function renderResult(data) {
  $('rBottleneck').textContent = data.bottleneck || '판정 불가';
  $('rScore').textContent = data.score ?? '-';
  $('rReason').textContent = data.reason || '';

  const list = $('rUpgrades');
  list.innerHTML = '';
  (data.upgrades || []).forEach((item) => {
    const li = document.createElement('li');
    const box = document.createElement('div');
    const title = document.createElement('strong');
    const why = document.createElement('p');
    title.textContent = item.part || '';
    why.textContent = item.why || '';
    box.append(title, why);
    li.append(box);
    list.append(li);
  });

  resultBox.hidden = false;
}

async function diagnose() {
  const cpu = $('cpu').value.trim();
  const gpu = $('gpu').value.trim();

  // 실패 처리 1: 빈 입력
  if (!cpu || !gpu) {
    resultBox.hidden = true;
    showMessage('CPU와 그래픽카드는 필수 입력값입니다.');
    return;
  }

  btn.disabled = true;
  btn.textContent = '분석 중...';
  resultBox.hidden = true;
  showMessage('AI가 사양을 분석하고 있습니다...', true);

  // 실패 처리 2: 타임아웃 (15초)
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);

  try {
    const res = await fetch('/api/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cpu,
        gpu,
        ram: $('ram').value.trim(),
        usage: $('usage').value,
      }),
      signal: controller.signal,
    });

    const data = await res.json();

    // 실패 처리 3: API 오류 (4xx/5xx)
    if (!res.ok) {
      showMessage(data.error || '진단에 실패했습니다. 잠시 후 다시 시도해주세요.');
      return;
    }

    hideMessage();
    renderResult(data);
  } catch (err) {
    if (err.name === 'AbortError') {
      showMessage('응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.');
    } else {
      showMessage('네트워크 연결을 확인해주세요.');
    }
  } finally {
    clearTimeout(timer);
    btn.disabled = false;
    btn.textContent = '진단하기';
  }
}

btn.addEventListener('click', diagnose);

// 엔터키로도 제출
['cpu', 'gpu', 'ram'].forEach((id) => {
  $(id).addEventListener('keydown', (e) => {
    if (e.key === 'Enter') diagnose();
  });
});