// MemoLedger Synchronized Review Screen: Interactive BBox Overlay + Editable Line Items

export function initReview() {
  const container = document.getElementById('review-container');
  if (!container) return;

  const memoId = container.getAttribute('data-memo-id');
  const overlaySvg = document.getElementById('bbox-svg-overlay');
  const memoImage = document.getElementById('review-memo-img');
  const tableBody = document.getElementById('lines-table-body');
  const approveBtn = document.getElementById('one-tap-approve-btn');
  const grandTotalEl = document.getElementById('review-grand-total');
  const totalMismatchAlert = document.getElementById('total-mismatch-banner');

  let activeLineIndex = null;

  // Draw Bounding Boxes on SVG
  function renderBBoxes(lines) {
    if (!overlaySvg || !lines) return;
    overlaySvg.innerHTML = '';

    lines.forEach((line, idx) => {
      if (!line.bbox || line.bbox.length !== 4) return;
      const [ymin, xmin, ymax, xmax] = line.bbox;
      // Convert 0..1000 scale to percentage
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
      rect.setAttribute('class', `bbox-rect cursor-pointer transition-all ${
        line.status === 'AUTO_MATCHED' ? 'stroke-emerald-500 fill-emerald-500/10' : 'stroke-amber-500 fill-amber-500/10'
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
        r.setAttribute('stroke', '#06b6d4');
        r.setAttribute('stroke-width', '3');
        r.setAttribute('fill', 'rgba(6, 182, 212, 0.25)');
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
        row.classList.add('bg-teal-50', 'dark:bg-teal-950/40', 'border-teal-500');
        row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        row.classList.remove('bg-teal-50', 'dark:bg-teal-950/40', 'border-teal-500');
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
      highlightLine(idx);

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
      highlightLine(idx);
    });
  }

  function recalculateGrandTotal() {
    let sum = 0;
    document.querySelectorAll('.line-total-input').forEach((inp) => {
      sum += parseFloat(inp.value) || 0;
    });

    if (grandTotalEl) {
      grandTotalEl.textContent = `৳${sum.toFixed(2)}`;
    }

    const writtenTotalAttr = container.getAttribute('data-written-total');
    if (writtenTotalAttr) {
      const writtenTotal = parseFloat(writtenTotalAttr);
      const diff = Math.abs(sum - writtenTotal);
      if (totalMismatchAlert) {
        if (diff > 0.5) {
          totalMismatchAlert.classList.remove('hidden');
          totalMismatchAlert.textContent = `Warning: Lines sum to ৳${sum.toFixed(2)} vs written total of ৳${writtenTotal.toFixed(2)}`;
        } else {
          totalMismatchAlert.classList.add('hidden');
        }
      }
    }
  }

  // One-Tap Approve Button
  if (approveBtn) {
    approveBtn.addEventListener('click', async () => {
      approveBtn.disabled = true;
      approveBtn.textContent = "Approving & Committing...";

      const lines = [];
      document.querySelectorAll('.line-item-row').forEach((row) => {
        const lineId = row.getAttribute('data-line-id');
        const nameInput = row.querySelector('.line-name-input');
        const variantInput = row.querySelector('.line-variant-input');
        const qtyInput = row.querySelector('.line-qty-input');
        const priceInput = row.querySelector('.line-price-input');
        const totalInput = row.querySelector('.line-total-input');
        const variantSelect = row.querySelector('.line-variant-select');

        lines.push({
          id: lineId,
          parsed_name: nameInput ? nameInput.value : '',
          parsed_variant: variantInput ? variantInput.value : '',
          parsed_qty: parseFloat(qtyInput ? qtyInput.value : 1) || 1,
          parsed_unit: 'piece',
          parsed_unit_price: parseFloat(priceInput ? priceInput.value : 0) || 0,
          parsed_line_total: parseFloat(totalInput ? totalInput.value : 0) || 0,
          matched_variant_id: variantSelect ? variantSelect.value : null,
          status: 'AUTO_MATCHED'
        });
      });

      try {
        const resp = await fetch(`/api/v1/memos/${memoId}/commit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lines })
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Approval failed');
        }

        // Show success actions (PDF, WhatsApp)
        const successModal = document.getElementById('commit-success-modal');
        if (successModal) {
          successModal.classList.remove('hidden');
        } else {
          window.location.reload();
        }
      } catch (err) {
        alert(`Error committing memo: ${err.message}`);
        approveBtn.disabled = false;
        approveBtn.textContent = "One-Tap Approve & Update Stock";
      }
    });
  }

  // Load initial lines data from embedded JSON attribute
  try {
    const linesData = JSON.parse(container.getAttribute('data-lines') || '[]');
    renderBBoxes(linesData);
    setupLiveCalculations();
  } catch (e) {
    console.error("Error initializing review:", e);
  }
}

document.addEventListener('DOMContentLoaded', initReview);
