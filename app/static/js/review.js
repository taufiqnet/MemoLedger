// MemoLedger Synchronized Review Screen: Interactive BBox Overlay + Editable Line Items + Full CRUD

export function initReview() {
  const container = document.getElementById('review-container');
  if (!container) return;

  const memoId = container.getAttribute('data-memo-id');
  const overlaySvg = document.getElementById('bbox-svg-overlay');
  const tableBody = document.getElementById('lines-table-body');
  const grandTotalEl = document.getElementById('review-grand-total');
  const totalMismatchAlert = document.getElementById('total-mismatch-banner');
  const subtotalEl = document.getElementById('review-calculated-subtotal');
  const editableTotalInput = document.getElementById('review-editable-total');
  const comparisonIndicator = document.getElementById('total-comparison-indicator');
  const footerCurrentTotal = document.getElementById('footer-current-total');

  const saveDraftBtn = document.getElementById('save-draft-btn');
  const bottomSaveDraftBtn = document.getElementById('bottom-save-draft-btn');
  const approveBtn = document.getElementById('one-tap-approve-btn');
  const bottomApproveBtn = document.getElementById('bottom-approve-btn');
  const addLineBtn = document.getElementById('add-table-line-btn');
  const deleteMemoBtn = document.getElementById('delete-memo-btn');

  let activeLineIndex = null;

  // Draw Bounding Boxes on SVG
  function renderBBoxes(lines) {
    if (!overlaySvg || !lines) return;
    overlaySvg.innerHTML = '';

    lines.forEach((line, idx) => {
      if (!line.bbox || line.bbox.length !== 4) return;
      const [ymin, xmin, ymax, xmax] = line.bbox;
      const top = (ymin / 10).toFixed(2);
      const left = (xmin / 10).toFixed(2);
      const height = ((ymax - ymin) / 10).toFixed(2);
      const width = ((xmax - xmin) / 10).toFixed(2);

      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', `${left}%`);
      rect.setAttribute('y', `${top}%`);
      rect.setAttribute('width', `${width}%`);
      rect.setAttribute('height', `${height}%`);
      rect.setAttribute('rx', '4');
      rect.setAttribute('class', `bbox-rect cursor-pointer transition-all ${line.status === 'AUTO_MATCHED' ? 'stroke-emerald-500 fill-emerald-500/10' : 'stroke-amber-500 fill-amber-500/10'
        }`);
      rect.setAttribute('stroke-width', '2');
      rect.setAttribute('data-line-idx', idx);

      rect.addEventListener('click', () => {
        highlightLine(idx);
      });

      overlaySvg.appendChild(rect);
    });
  }

  function highlightLine(idx) {
    activeLineIndex = idx;

    // Highlight SVG rect
    document.querySelectorAll('.bbox-rect').forEach((r) => {
      const lineIdx = parseInt(r.getAttribute('data-line-idx'), 10);
      if (lineIdx === idx) {
        r.setAttribute('stroke', '#0d9488');
        r.setAttribute('stroke-width', '3');
        r.setAttribute('fill', 'rgba(13, 148, 136, 0.25)');
      } else {
        r.setAttribute('stroke', '#10b981');
        r.setAttribute('stroke-width', '2');
        r.setAttribute('fill', 'rgba(16, 185, 129, 0.1)');
      }
    });

    // Highlight and scroll table row
    document.querySelectorAll('.line-item-row').forEach((row) => {
      const rowIdx = parseInt(row.getAttribute('data-line-idx'), 10);
      if (rowIdx === idx) {
        row.classList.add('bg-teal-50', 'border-teal-500');
        row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        row.classList.remove('bg-teal-50', 'border-teal-500');
      }
    });
  }

  // Row input event listeners for live arithmetic recalculation
  function setupLiveCalculations() {
    if (!tableBody) return;

    tableBody.addEventListener('input', (e) => {
      const row = e.target.closest('.line-item-row');
      if (!row) return;

      const idx = parseInt(row.getAttribute('data-line-idx'), 10);
      if (!isNaN(idx)) highlightLine(idx);

      const qtyInput = row.querySelector('.line-qty-input');
      const priceInput = row.querySelector('.line-price-input');
      const totalInput = row.querySelector('.line-total-input');

      const qty = parseFloat(qtyInput ? qtyInput.value : 1) || 0;
      const price = parseFloat(priceInput ? priceInput.value : 0) || 0;

      if (e.target === qtyInput || e.target === priceInput) {
        const lineTotal = qty * price;
        if (totalInput) totalInput.value = lineTotal.toFixed(2);
      }

      recalculateGrandTotal();
    });

    tableBody.addEventListener('focusin', (e) => {
      const row = e.target.closest('.line-item-row');
      if (!row) return;
      const idx = parseInt(row.getAttribute('data-line-idx'), 10);
      if (!isNaN(idx)) highlightLine(idx);
    });

    tableBody.addEventListener('change', (e) => {
      if (e.target.classList.contains('line-variant-select')) {
        const select = e.target;
        const row = select.closest('.line-item-row');
        if (!row) return;
        const nameInput = row.querySelector('.line-name-input');
        if (select.selectedIndex > 0 && nameInput) {
          const optText = select.options[select.selectedIndex].text;
          const cleanName = optText.split('(')[0].split('-')[0].trim();
          if (cleanName) {
            nameInput.value = cleanName;
          }
        }
      }
    });

    if (editableTotalInput) {
      editableTotalInput.addEventListener('input', () => {
        recalculateGrandTotal();
      });
    }
  }

  function recalculateGrandTotal() {
    let subtotal = 0;
    document.querySelectorAll('.line-total-input').forEach((inp) => {
      subtotal += parseFloat(inp.value) || 0;
    });

    if (subtotalEl) {
      subtotalEl.textContent = `৳${subtotal.toFixed(2)}`;
    }

    // Editable total from image (or user edited)
    let currentTotal = subtotal;
    if (editableTotalInput && editableTotalInput.value !== '') {
      currentTotal = parseFloat(editableTotalInput.value) || 0;
    }

    if (grandTotalEl) {
      grandTotalEl.textContent = `৳${currentTotal.toFixed(2)}`;
    }
    if (footerCurrentTotal) {
      footerCurrentTotal.textContent = `৳${currentTotal.toFixed(2)}`;
    }

    // Calculate difference between subtotal and memo total for clarification
    const diff = Math.abs(subtotal - currentTotal);

    if (comparisonIndicator) {
      if (diff < 0.5) {
        comparisonIndicator.className = 'flex flex-wrap items-center justify-between p-2.5 rounded-lg text-xs font-semibold bg-emerald-50 border border-emerald-200 text-emerald-800 transition-all';
        comparisonIndicator.innerHTML = `
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
            <span>উভয় পাশের হিসাব সম্পূর্ণ মিলেছে (আইটেম সাবটোটাল: ৳${subtotal.toFixed(2)} = মেমোর মোট: ৳${currentTotal.toFixed(2)})</span>
          </div>
          <span class="text-[11px] bg-emerald-200 text-emerald-900 px-2.5 py-0.5 rounded-full font-bold">✓ ০.০০ পার্থক্য</span>
        `;
      } else {
        comparisonIndicator.className = 'flex flex-wrap items-center justify-between p-2.5 rounded-lg text-xs font-semibold bg-amber-50 border border-amber-300 text-amber-900 transition-all';
        comparisonIndicator.innerHTML = `
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-amber-500 inline-block"></span>
            <span>পার্থক্য স্পষ্টকরণ: আইটেমগুলোর যোগফল ৳${subtotal.toFixed(2)}, কিন্তু মেমোর মোট ৳${currentTotal.toFixed(2)} (পার্থক্য: ৳${diff.toFixed(2)})</span>
          </div>
          <span class="text-[11px] bg-amber-200 text-amber-950 px-2.5 py-0.5 rounded-full font-bold">পার্থক্য: ৳${diff.toFixed(2)}</span>
        `;
      }
    }

    if (totalMismatchAlert) {
      if (diff > 0.5) {
        totalMismatchAlert.classList.remove('hidden');
      } else {
        totalMismatchAlert.classList.add('hidden');
      }
    }
  }

  function gatherCurrentLines() {
    const lines = [];
    document.querySelectorAll('.line-item-row').forEach((row, idx) => {
      const rawLineId = row.getAttribute('data-line-id');
      const lineId = (rawLineId && rawLineId !== 'null' && rawLineId !== 'undefined' && rawLineId.length === 36) ? rawLineId : null;

      const nameInput = row.querySelector('.line-name-input');
      const variantInput = row.querySelector('.line-variant-input');
      const qtyInput = row.querySelector('.line-qty-input');
      const priceInput = row.querySelector('.line-price-input');
      const totalInput = row.querySelector('.line-total-input');
      const variantSelect = row.querySelector('.line-variant-select');

      const varVal = variantSelect ? variantSelect.value : null;
      const matched_variant_id = (varVal && varVal.length === 36) ? varVal : null;

      lines.push({
        id: lineId,
        line_number: idx + 1,
        parsed_name: nameInput ? nameInput.value.trim() : '',
        parsed_variant: variantInput ? variantInput.value.trim() : null,
        parsed_qty: parseFloat(qtyInput ? qtyInput.value : 1) || 1,
        parsed_unit: 'piece',
        parsed_unit_price: parseFloat(priceInput ? priceInput.value : 0) || 0,
        parsed_line_total: parseFloat(totalInput ? totalInput.value : 0) || 0,
        matched_variant_id: matched_variant_id,
        status: matched_variant_id ? 'AUTO_MATCHED' : 'NEEDS_REVIEW'
      });
    });
    return lines;
  }

  // --- 1. SAVE DRAFT HANDLER ---
  async function handleSaveDraft() {
    const memoStatus = container.getAttribute('data-memo-status');
    if (memoStatus === 'APPROVED') {
      window.showToast?.('এই মেমোটি ইতিমধ্যে অনুমোদিত হয়েছে। অনুমোদিত মেমোর তথ্য পরিবর্তন করা সম্ভব নয়।', 'error');
      return;
    }

    const lines = gatherCurrentLines();
    const btns = [saveDraftBtn, bottomSaveDraftBtn].filter(Boolean);
    btns.forEach(b => {
      b.disabled = true;
      b.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
    });

    const supplierSelect = document.getElementById('review-supplier-select');
    const memoNumberInput = document.getElementById('review-memo-number');
    const memoDateInput = document.getElementById('review-memo-date');

    const suppVal = supplierSelect ? supplierSelect.value : null;
    const supplier_id = (suppVal && suppVal.length === 36) ? suppVal : null;

    const editableTotal = editableTotalInput ? parseFloat(editableTotalInput.value) : null;

    const payload = {
      lines,
      written_total: !isNaN(editableTotal) ? editableTotal : null,
      supplier_id: supplier_id,
      memo_number: memoNumberInput ? (memoNumberInput.value.trim() || null) : null,
      memo_date: memoDateInput ? (memoDateInput.value.trim() || null) : null
    };

    try {
      const resp = await fetch(`/api/v1/memos/${memoId}/lines`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Draft save failed');
      }

      const data = await resp.json();

      // Update title with new memo number
      if (memoNumberInput && memoNumberInput.value.trim()) {
        const titleNum = document.getElementById('memo-title-number');
        if (titleNum) titleNum.textContent = memoNumberInput.value.trim();
      }

      // Sync returned line IDs onto DOM rows
      if (data.lines && Array.isArray(data.lines)) {
        const rows = document.querySelectorAll('.line-item-row');
        data.lines.forEach((l, idx) => {
          if (rows[idx]) {
            rows[idx].setAttribute('data-line-id', l.id);
          }
        });
      }

      window.showToast?.('ড্রাফট সফলভাবে সংরক্ষিত হয়েছে!', 'success');
    } catch (err) {
      window.showToast?.(`সংরক্ষণে ত্রুটি: ${err.message}`, 'error');
    } finally {
      btns.forEach(b => {
        b.disabled = false;
        b.innerHTML = `
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/></svg>
          <span>ড্রাফট সংরক্ষণ করুন</span>
        `;
      });
    }
  }

  if (saveDraftBtn) saveDraftBtn.addEventListener('click', handleSaveDraft);
  if (bottomSaveDraftBtn) bottomSaveDraftBtn.addEventListener('click', handleSaveDraft);

  // --- 2. ADD NEW LINE HANDLER ---
  if (addLineBtn && tableBody) {
    addLineBtn.addEventListener('click', async () => {
      addLineBtn.disabled = true;
      try {
        const resp = await fetch(`/api/v1/memos/${memoId}/lines`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            parsed_name: "নতুন আইটেম",
            parsed_qty: 1,
            parsed_unit: "piece",
            parsed_unit_price: 0,
            parsed_line_total: 0
          })
        });

        if (!resp.ok) throw new Error('Could not add line item');
        const data = await resp.json();

        // Append new row to table
        const rowIdx = tableBody.querySelectorAll('.line-item-row').length;
        const tr = document.createElement('tr');
        tr.className = 'line-item-row transition-all border-l-4 border-amber-400 bg-amber-50/20';
        tr.setAttribute('data-line-id', data.line_id);
        tr.setAttribute('data-line-idx', rowIdx);

        tr.innerHTML = `
          <td class="p-2 text-slate-500 font-bold text-center">${data.line_number}</td>
          <td class="p-2 space-y-1">
            <input type="text" class="line-name-input w-full p-2 border border-slate-300 rounded font-bold text-xs focus:ring-1 focus:ring-teal-500" value="নতুন আইটেম">
            <div class="text-[10px] text-slate-400">ম্যানুয়ালি যোগ করা হয়েছে</div>
          </td>
          <td class="p-2">
            <input type="text" class="line-variant-input w-full p-2 border border-slate-300 rounded text-center text-xs" placeholder="-">
          </td>
          <td class="p-2">
            <input type="number" step="0.5" class="line-qty-input w-full p-2 border border-slate-300 rounded text-right font-bold text-xs" value="1">
          </td>
          <td class="p-2">
            <input type="number" step="1" class="line-price-input w-full p-2 border border-slate-300 rounded text-right font-bold text-xs" value="0">
          </td>
          <td class="p-2">
            <input type="number" step="1" class="line-total-input w-full p-2 border border-slate-200 rounded text-right font-extrabold text-teal-800 bg-slate-50 text-xs" value="0">
          </td>
          <td class="p-2 text-center">
            <button type="button" class="delete-line-row-btn text-slate-400 hover:text-rose-600 p-1.5 transition-colors" title="লাইন মুছুন">✕</button>
          </td>
        `;

        tableBody.appendChild(tr);
        recalculateGrandTotal();
        window.showToast?.('নতুন লাইন যোগ করা হয়েছে। নাম ও দর লিখুন।', 'success');
        tr.querySelector('.line-name-input')?.focus();
      } catch (e) {
        window.showToast?.(`লাইন যোগ করতে ত্রুটি: ${e.message}`, 'error');
      } finally {
        addLineBtn.disabled = false;
      }
    });
  }

  // --- 3. DELETE LINE ROW HANDLER ---
  if (tableBody) {
    tableBody.addEventListener('click', async (e) => {
      if (e.target.classList.contains('delete-line-row-btn')) {
        const row = e.target.closest('.line-item-row');
        const lineId = row.getAttribute('data-line-id');
        if (!confirm('আপনি কি নিশ্চিতভাবে এই লাইনটি মুছে ফেলতে চান?')) return;

        try {
          const resp = await fetch(`/api/v1/memos/${memoId}/lines/${lineId}`, {
            method: 'DELETE'
          });
          if (!resp.ok) throw new Error('Delete line failed');

          row.remove();
          recalculateGrandTotal();
          window.showToast?.('লাইনটি মুছে ফেলা হয়েছে।', 'info');
        } catch (err) {
          window.showToast?.(`মুছতে ব্যর্থ: ${err.message}`, 'error');
        }
      }
    });
  }

  // --- 4. DELETE ENTIRE MEMO HANDLER ---
  if (deleteMemoBtn) {
    deleteMemoBtn.addEventListener('click', async () => {
      if (!confirm('আপনি কি এই মেমোটি সম্পূর্ণ মুছে ফেলতে চান?')) return;
      deleteMemoBtn.disabled = true;

      try {
        const resp = await fetch(`/api/v1/memos/${memoId}`, {
          method: 'DELETE'
        });
        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Could not delete memo');
        }

        window.showToast?.('মেমো সফলভাবে মুছে ফেলা হয়েছে।', 'success');
        setTimeout(() => {
          window.location.href = '/upload';
        }, 500);
      } catch (e) {
        window.showToast?.(`মেমো মুছতে ত্রুটি: ${e.message}`, 'error');
        deleteMemoBtn.disabled = false;
      }
    });
  }

  // --- 5. ONE-TAP APPROVE HANDLER ---
  async function handleApprove() {
    const btns = [approveBtn, bottomApproveBtn].filter(Boolean);
    btns.forEach(b => {
      b.disabled = true;
      b.textContent = "অনুমোদন চলছে...";
    });

    const lines = gatherCurrentLines();
    const editableTotal = editableTotalInput ? parseFloat(editableTotalInput.value) : null;

    try {
      const resp = await fetch(`/api/v1/memos/${memoId}/commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          lines,
          total_amount: !isNaN(editableTotal) ? editableTotal : null,
          written_total: !isNaN(editableTotal) ? editableTotal : null
        })
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Approval failed');
      }

      window.showToast?.('মেমো সফলভাবে অনুমোদিত হয়েছে!', 'success');
      const successModal = document.getElementById('commit-success-modal');
      if (successModal) {
        successModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
      } else {
        window.location.reload();
      }
    } catch (err) {
      window.showToast?.(`অনুমোদনে সমস্যা: ${err.message}`, 'error');
      btns.forEach(b => {
        b.disabled = false;
        b.innerHTML = `
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
          <span>অনুমোদন ও স্টক আপডেট</span>
        `;
      });
    }
  }

  if (approveBtn) approveBtn.addEventListener('click', handleApprove);
  if (bottomApproveBtn) bottomApproveBtn.addEventListener('click', handleApprove);

  // Initialize
  try {
    const scriptEl = document.getElementById('review-lines-json');
    let linesData = [];
    if (scriptEl && scriptEl.textContent) {
      linesData = JSON.parse(scriptEl.textContent);
    } else {
      linesData = JSON.parse(container.getAttribute('data-lines') || '[]');
    }
    renderBBoxes(linesData);
    setupLiveCalculations();
    recalculateGrandTotal();
  } catch (e) {
    console.error("Error initializing review:", e);
  }
}

document.addEventListener('DOMContentLoaded', initReview);
