// MemoLedger Canvas-Based Camera Capture & Manual Memo Entry Module

let currentRotation = 0;
let rawImage = null;
let canvas = null;
let ctx = null;

export function initCapture() {
  const fileInput = document.getElementById('camera-file-input');
  canvas = document.getElementById('preview-canvas');
  if (canvas) {
    ctx = canvas.getContext('2d');
  }

  const rotateLeftBtn = document.getElementById('rotate-left-btn');
  const rotateRightBtn = document.getElementById('rotate-right-btn');
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
          renderCanvas();
          if (previewContainer) {
            previewContainer.classList.remove('hidden');
            previewContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
          window.showToast?.('ছবি সফলভাবে লোড হয়েছে। প্রয়োজনে ৯০° ঘুরিয়ে সোজা করুন।', 'info');
        };
        rawImage.src = event.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  if (rotateLeftBtn) {
    rotateLeftBtn.addEventListener('click', () => {
      currentRotation = (currentRotation - 90 + 360) % 360;
      renderCanvas();
    });
  }

  if (rotateRightBtn) {
    rotateRightBtn.addEventListener('click', () => {
      currentRotation = (currentRotation + 90) % 360;
      renderCanvas();
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!canvas) return;

      const statusMsg = document.getElementById('upload-status-msg');
      if (statusMsg) {
        statusMsg.classList.remove('hidden');
        statusMsg.textContent = "মেমো আপলোড ও AI এক্সট্রাকশন চলছে...";
      }
      if (uploadSubmitBtn) {
        uploadSubmitBtn.disabled = true;
        uploadSubmitBtn.innerHTML = `<span>প্রসেসিং হচ্ছে...</span>`;
      }

      // Convert canvas to blob
      canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('file', blob, 'memo_capture.jpg');

        const supplierSelect = document.getElementById('supplier-select');
        if (supplierSelect && supplierSelect.value) {
          formData.append('supplier_id', supplierSelect.value);
        }

        try {
          const resp = await fetch('/api/v1/memos/upload', {
            method: 'POST',
            body: formData
          });

          if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Upload failed');
          }

          const data = await resp.json();
          window.showToast?.('মেমো সফলভাবে প্রসেস হয়েছে!', 'success');
          // Navigate to review screen
          setTimeout(() => {
            window.location.href = `/review/${data.memo_id}`;
          }, 400);
        } catch (error) {
          if (statusMsg) {
            statusMsg.textContent = `সমস্যা: ${error.message}`;
            statusMsg.classList.add('text-rose-600', 'bg-rose-50', 'border-rose-200');
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
        <td class="p-2">
          <input type="text" class="manual-line-name w-full p-2 border border-slate-300 rounded text-xs font-medium focus:ring-1 focus:ring-teal-500" placeholder="পণ্যের নাম" required>
        </td>
        <td class="p-2">
          <input type="text" class="manual-line-variant w-full p-2 border border-slate-300 rounded text-xs text-center" placeholder="-">
        </td>
        <td class="p-2">
          <input type="number" step="1" class="manual-line-qty w-full p-2 border border-slate-300 rounded text-xs text-right font-bold" value="1" required>
        </td>
        <td class="p-2">
          <input type="number" step="1" class="manual-line-price w-full p-2 border border-slate-300 rounded text-xs text-right font-bold" value="0" required>
        </td>
        <td class="p-2">
          <input type="number" step="1" class="manual-line-total w-full p-2 border border-slate-200 rounded text-xs text-right font-bold bg-slate-50 text-teal-700" value="0" readonly>
        </td>
        <td class="p-2 text-center">
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
