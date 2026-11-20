// MemoLedger Canvas-Based Camera Capture & Manual Memo Entry Module

let currentRotation = 0;
let rawImage = null;
let canvas = null;
let ctx = null;
let isZoomed = false;

export function initCapture() {
  const fileInput = document.getElementById('camera-file-input');
  canvas = document.getElementById('preview-canvas');
  if (canvas) {
    ctx = canvas.getContext('2d');
  }

  const rotateLeftBtn = document.getElementById('rotate-left-btn');
  const rotateRightBtn = document.getElementById('rotate-right-btn');
  const toggleZoomBtn = document.getElementById('toggle-zoom-btn');
  const previewContainer = document.getElementById('preview-container');
  const uploadForm = document.getElementById('upload-form');
  const uploadSubmitBtn = document.getElementById('upload-submit-btn');

  // --- OCR / File Input Handling ---
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        rawImage = new Image();
        rawImage.onload = () => {
          currentRotation = 0;
          isZoomed = false;
          renderCanvas();
          applyZoomStyles();
          if (previewContainer) {
            previewContainer.classList.remove('hidden');
            previewContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
          window.showToast?.('ছবি লোড হয়েছে। মেমো সম্পূর্ণ ফ্রেমে ফিট করা হয়েছে।', 'info');
        };
        rawImage.src = event.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  if (toggleZoomBtn) {
    toggleZoomBtn.addEventListener('click', () => {
      isZoomed = !isZoomed;
      applyZoomStyles();
    });
  }

  if (rotateLeftBtn) {
    rotateLeftBtn.addEventListener('click', () => {
      currentRotation = (currentRotation - 90 + 360) % 360;
      renderCanvas();
      applyZoomStyles();
    });
  }

  if (rotateRightBtn) {
    rotateRightBtn.addEventListener('click', () => {
      currentRotation = (currentRotation + 90) % 360;
      renderCanvas();
      applyZoomStyles();
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!canvas) return;

      const statusMsg = document.getElementById('upload-status-msg');
      if (statusMsg) {
        statusMsg.classList.add('hidden');
      }

      if (uploadSubmitBtn) {
        uploadSubmitBtn.disabled = true;
        uploadSubmitBtn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span>প্রসেসিং ও এক্সট্রাকশন চলছে...</span>
        `;
      }

      const progressCtrl = createProgressController();

      // Convert canvas to blob
      canvas.toBlob(async (blob) => {
        if (!blob) {
          progressCtrl?.error('ক্যানভাস থেকে ছবি তৈরি ব্যর্থ হয়েছে।');
          if (uploadSubmitBtn) {
            uploadSubmitBtn.disabled = false;
            uploadSubmitBtn.innerHTML = `<span>মেমো প্রসেস ও এক্সট্রাক্ট করুন &rarr;</span>`;
          }
          return;
        }

        const formData = new FormData();
        formData.append('file', blob, 'memo_capture.jpg');
        // Supplier is intentionally not attached: auto-detected from memo image directly

        try {
          const resp = await fetch('/api/v1/memos/upload', {
            method: 'POST',
            body: formData
          });

          if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || 'Upload failed');
          }

          const data = await resp.json();
          progressCtrl?.finish();
          window.showToast?.('মেমো সফলভাবে প্রসেস হয়েছে!', 'success');

          // Navigate to review screen
          setTimeout(() => {
            window.location.href = `/review/${data.memo_id}`;
          }, 450);
        } catch (error) {
          progressCtrl?.error(error.message);
          if (statusMsg) {
            statusMsg.classList.remove('hidden');
            statusMsg.textContent = `সমস্যা: ${error.message}`;
            statusMsg.className = 'text-xs text-center font-bold text-rose-600 p-2.5 bg-rose-50 rounded-lg border border-rose-200 mt-2';
          }
          if (uploadSubmitBtn) {
            uploadSubmitBtn.disabled = false;
            uploadSubmitBtn.innerHTML = `<span>মেমো প্রসেস ও এক্সট্রাক্ট করুন &rarr;</span>`;
          }
          window.showToast?.(`আপলোড ত্রুটি: ${error.message}`, 'error');
        }
      }, 'image/jpeg', 0.92);
    });
  }

  // --- Manual Memo Entry Handling ---
  setupManualMemoForm();
}

function applyZoomStyles() {
  const wrapper = document.getElementById('canvas-wrapper');
  const zoomText = document.getElementById('zoom-text');
  const zoomIcon = document.getElementById('zoom-icon');
  const badge = document.getElementById('viewer-badge');

  if (!canvas || !wrapper) return;

  if (isZoomed) {
    wrapper.classList.remove('flex', 'items-center', 'justify-center', 'overflow-hidden');
    wrapper.classList.add('overflow-auto', 'block', 'cursor-grab');
    wrapper.style.maxHeight = '460px';
    wrapper.style.height = '440px';

    canvas.style.maxHeight = 'none';
    canvas.style.maxWidth = 'none';
    canvas.style.width = '100%';
    canvas.style.height = 'auto';
    canvas.style.margin = '0 auto';
    canvas.style.display = 'block';

    if (zoomText) zoomText.textContent = 'ফিট ভিউ';
    if (zoomIcon) zoomIcon.textContent = '🔲';
    if (badge) {
      badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-400"></span><span>জুম ভিউ (স্ক্রোল করে দেখুন)</span>`;
    }
  } else {
    wrapper.classList.remove('overflow-auto', 'block', 'cursor-grab');
    wrapper.classList.add('flex', 'items-center', 'justify-center', 'overflow-hidden');
    wrapper.style.maxHeight = '460px';
    wrapper.style.height = '440px';

    canvas.style.maxHeight = '420px';
    canvas.style.maxWidth = '100%';
    canvas.style.width = 'auto';
    canvas.style.height = 'auto';
    canvas.style.objectFit = 'contain';
    canvas.style.margin = 'auto';
    canvas.style.display = 'block';

    if (zoomText) zoomText.textContent = 'জুম';
    if (zoomIcon) zoomIcon.textContent = '🔍';
    if (badge) {
      badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span><span>সম্পূর্ণ মেমো ফ্রেম (ফিট ভিউ)</span>`;
    }
  }
}

function createProgressController() {
  const box = document.getElementById('upload-progress-box');
  const title = document.getElementById('progress-title');
  const subtext = document.getElementById('progress-subtext');
  const percent = document.getElementById('progress-percentage');
  const bar = document.getElementById('progress-bar-fill');
  const badges = [
    document.getElementById('step-badge-1'),
    document.getElementById('step-badge-2'),
    document.getElementById('step-badge-3'),
    document.getElementById('step-badge-4')
  ];

  if (!box || !bar) return null;

  box.classList.remove('hidden');
  bar.className = 'h-full bg-gradient-to-r from-teal-400 via-emerald-400 to-teal-300 rounded-full transition-all duration-400 ease-out shadow-sm';
  box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  const stages = [
    { p: 20, stage: 1, title: 'ছবি আপলোড ও ফ্রেম যাচাই...', sub: 'ছবি সার্ভারে নিরাপদে পাঠানো হচ্ছে...' },
    { p: 48, stage: 2, title: 'OpenCV কোণ সংশোধন ও ক্লিয়ারিং...', sub: 'আলো, বৈসাদৃশ্য ও বাঁকা অংশ সোজা করা হচ্ছে...' },
    { p: 75, stage: 3, title: 'AI দিয়ে বাংলা ও ইংরেজি লাইন শনাক্তকরণ...', sub: 'হাতে লেখা মেমোর পণ্য ও দর রূপান্তর হচ্ছে...' },
    { p: 92, stage: 4, title: 'বাংলা সংখ্যা (০-৯) ও স্টক খতিয়ান মিলানো...', sub: 'দর ও পরিমাণের হিসাব মেলানো হচ্ছে...' }
  ];

  let currentStageIdx = 0;

  function setStage(st) {
    if (bar) bar.style.width = `${st.p}%`;
    if (percent) percent.textContent = `${st.p}%`;
    if (title) title.textContent = st.title;
    if (subtext) subtext.textContent = st.sub;

    badges.forEach((b, idx) => {
      if (!b) return;
      if (idx < st.stage - 1) {
        b.className = 'p-1.5 rounded-md bg-teal-500/30 border border-teal-400 text-[10px] md:text-xs font-bold text-teal-200';
      } else if (idx === st.stage - 1) {
        b.className = 'p-1.5 rounded-md bg-teal-500/20 border border-teal-500/50 text-[10px] md:text-xs font-bold text-teal-100 animate-pulse';
      } else {
        b.className = 'p-1.5 rounded-md bg-slate-800/80 border border-slate-700 text-[10px] md:text-xs font-semibold text-slate-400';
      }
    });
  }

  setStage(stages[0]);

  const intervalId = setInterval(() => {
    currentStageIdx++;
    if (currentStageIdx < stages.length) {
      setStage(stages[currentStageIdx]);
    }
  }, 650);

  return {
    finish: () => {
      clearInterval(intervalId);
      if (bar) bar.style.width = '100%';
      if (percent) percent.textContent = '100%';
      if (title) title.textContent = 'মেমো সফলভাবে প্রসেস হয়েছে!';
      if (subtext) subtext.textContent = 'রিভিউ পেজে নিয়ে যাওয়া হচ্ছে...';
      badges.forEach(b => {
        if (b) b.className = 'p-1.5 rounded-md bg-emerald-500/30 border border-emerald-400 text-[10px] md:text-xs font-bold text-emerald-200';
      });
    },
    error: (msg) => {
      clearInterval(intervalId);
      if (bar) {
        bar.style.width = '100%';
        bar.className = 'h-full bg-rose-500 rounded-full transition-all duration-300';
      }
      if (percent) percent.textContent = '!';
      if (title) title.textContent = 'প্রসেসিং ত্রুটি হয়েছে';
      if (subtext) subtext.textContent = msg || 'মেমো প্রসেস সম্পন্ন করা যায়নি।';
    }
  };
}

function renderCanvas() {
  if (!rawImage || !canvas || !ctx) return;

  const isRotated = currentRotation === 90 || currentRotation === 270;
  canvas.width = isRotated ? rawImage.height : rawImage.width;
  canvas.height = isRotated ? rawImage.width : rawImage.height;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate((currentRotation * Math.PI) / 180);
  ctx.drawImage(rawImage, -rawImage.width / 2, -rawImage.height / 2);
  ctx.restore();
}

function setupManualMemoForm() {
  const manualForm = document.getElementById('manual-memo-form');
  const addLineBtn = document.getElementById('add-manual-line-btn');
  const tbody = document.getElementById('manual-lines-tbody');
  const grandTotalEl = document.getElementById('manual-grand-total');
  const lineCountEl = document.getElementById('manual-line-count');

  if (!manualForm || !tbody) return;

  function recalculateManualTotals() {
    let grandTotal = 0;
    const rows = tbody.querySelectorAll('.manual-line-row');
    if (lineCountEl) lineCountEl.textContent = rows.length;

    rows.forEach(row => {
      const qtyInp = row.querySelector('.manual-line-qty');
      const priceInp = row.querySelector('.manual-line-price');
      const totalInp = row.querySelector('.manual-line-total');

      const qty = parseFloat(qtyInp ? qtyInp.value : 0) || 0;
      const price = parseFloat(priceInp ? priceInp.value : 0) || 0;
      const lineTotal = qty * price;

      if (totalInp) totalInp.value = lineTotal.toFixed(2);
      grandTotal += lineTotal;
    });

    if (grandTotalEl) grandTotalEl.textContent = `৳${grandTotal.toFixed(2)}`;
  }

  // Input listener for live arithmetic
  tbody.addEventListener('input', (e) => {
    if (e.target.classList.contains('manual-line-qty') || e.target.classList.contains('manual-line-price')) {
      recalculateManualTotals();
    }
  });

  // Remove row listener
  tbody.addEventListener('click', (e) => {
    if (e.target.classList.contains('remove-line-btn')) {
      const rows = tbody.querySelectorAll('.manual-line-row');
      if (rows.length > 1) {
        e.target.closest('.manual-line-row').remove();
        recalculateManualTotals();
      } else {
        window.showToast?.('কমপক্ষে একটি পণ্য লাইন থাকতে হবে।', 'error');
      }
    }
  });

  // Add new line button
  if (addLineBtn) {
    addLineBtn.addEventListener('click', () => {
      const tr = document.createElement('tr');
      tr.className = 'manual-line-row';
      tr.innerHTML = `
        <td class="p-2 min-w-[260px]">
          <input type="text" class="manual-line-name w-full p-2.5 border border-slate-300 rounded-lg text-xs md:text-sm font-bold focus:ring-2 focus:ring-teal-500" placeholder="পণ্যের নাম" required>
        </td>
        <td class="p-2 w-24">
          <input type="text" class="manual-line-variant w-full p-2.5 border border-slate-300 rounded-lg text-xs font-semibold text-center" placeholder="-">
        </td>
        <td class="p-2 min-w-[100px] w-28">
          <input type="number" step="1" class="manual-line-qty w-full p-2.5 border border-slate-300 rounded-lg text-xs md:text-sm text-right font-black focus:ring-2 focus:ring-teal-500" value="1" required>
        </td>
        <td class="p-2 min-w-[110px] w-32">
          <input type="number" step="1" class="manual-line-price w-full p-2.5 border border-slate-300 rounded-lg text-xs md:text-sm text-right font-black focus:ring-2 focus:ring-teal-500" value="0" required>
        </td>
        <td class="p-2 min-w-[120px] w-36">
          <input type="number" step="1" class="manual-line-total w-full p-2.5 border border-slate-200 rounded-lg text-xs md:text-sm text-right font-black bg-slate-50 text-teal-800" value="0" readonly>
        </td>
        <td class="p-2 text-center w-10">
          <button type="button" class="remove-line-btn text-slate-400 hover:text-rose-600 p-1.5 transition-colors" title="লাইন মুছুন">
            ✕
          </button>
        </td>
      `;
      tbody.appendChild(tr);
      recalculateManualTotals();
      tr.querySelector('.manual-line-name')?.focus();
    });
  }

  // Submit manual memo form
  manualForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const saveBtn = document.getElementById('manual-save-memo-btn');
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.innerHTML = `<span>সংরক্ষণ করা হচ্ছে...</span>`;
    }

    const supplierId = document.getElementById('manual-supplier-id')?.value || null;
    const memoNumber = document.getElementById('manual-memo-number')?.value || null;
    const memoDate = document.getElementById('manual-memo-date')?.value || null;

    const lines = [];
    tbody.querySelectorAll('.manual-line-row').forEach(row => {
      const name = row.querySelector('.manual-line-name')?.value.trim();
      const variant = row.querySelector('.manual-line-variant')?.value.trim();
      const qty = parseFloat(row.querySelector('.manual-line-qty')?.value) || 1;
      const price = parseFloat(row.querySelector('.manual-line-price')?.value) || 0;
      const total = qty * price;

      if (name) {
        lines.push({
          parsed_name: name,
          parsed_variant: variant || null,
          parsed_qty: qty,
          parsed_unit: 'piece',
          parsed_unit_price: price,
          parsed_line_total: total
        });
      }
    });

    if (lines.length === 0) {
      window.showToast?.('অনুগ্রহ করে কমপক্ষে একটি পণ্য যোগ করুন।', 'error');
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<span>মেমো সংরক্ষণ করুন (Save Memo) &rarr;</span>`;
      }
      return;
    }

    try {
      const resp = await fetch('/api/v1/memos/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplier_id: supplierId,
          memo_number: memoNumber,
          memo_date: memoDate,
          lines: lines
        })
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Manual memo creation failed');
      }

      const data = await resp.json();
      window.showToast?.('ম্যানুয়াল মেমো সফলভাবে তৈরি ও সংরক্ষিত হয়েছে!', 'success');
      setTimeout(() => {
        window.location.href = `/review/${data.memo_id}`;
      }, 400);
    } catch (err) {
      window.showToast?.(`সংরক্ষণে ত্রুটি: ${err.message}`, 'error');
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<span>মেমো সংরক্ষণ করুন (Save Memo) &rarr;</span>`;
      }
    }
  });

  recalculateManualTotals();
}

document.addEventListener('DOMContentLoaded', initCapture);
