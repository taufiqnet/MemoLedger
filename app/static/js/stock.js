// MemoLedger Stock Ledger & Adjustment Module

window.openAdjustStockModal = function(variantId, variantLabel, costPrice) {
  const form = document.getElementById('adjust-stock-form');
  if (form) form.reset();

  const varSelect = document.getElementById('adj-variant-id');
  if (varSelect && variantId) {
    varSelect.value = variantId;
  }
  const costInput = document.getElementById('adj-cost');
  if (costInput && costPrice) {
    costInput.value = parseFloat(costPrice) || 0;
  }

  window.openModal('adjust-stock-modal');
};

document.addEventListener('DOMContentLoaded', () => {
  // 1. Variant Select change updates cost input
  const varSelect = document.getElementById('adj-variant-id');
  if (varSelect) {
    varSelect.addEventListener('change', (e) => {
      const opt = e.target.selectedOptions[0];
      const cost = opt?.getAttribute('data-cost');
      const costInput = document.getElementById('adj-cost');
      if (costInput && cost) {
        costInput.value = parseFloat(cost) || 0;
      }
    });
  }

  // 2. Search Filter
  const searchInput = document.getElementById('stock-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll('.stock-variant-row').forEach(row => {
        const name = row.getAttribute('data-name') || '';
        const brand = row.getAttribute('data-brand') || '';
        if (name.includes(q) || brand.includes(q)) {
          row.classList.remove('hidden');
        } else {
          row.classList.add('hidden');
        }
      });
    });
  }

  // 3. Status Filter Pills
  document.querySelectorAll('.filter-pill-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.filter-pill-btn').forEach(b => {
        b.classList.remove('bg-teal-800', 'text-white', 'font-bold');
        b.classList.add('bg-slate-100', 'text-slate-600');
      });

      btn.classList.remove('bg-slate-100', 'text-slate-600');
      btn.classList.add('bg-teal-800', 'text-white', 'font-bold');

      const filter = btn.getAttribute('data-filter');
      document.querySelectorAll('.stock-variant-row').forEach(row => {
        const status = row.getAttribute('data-status');
        if (filter === 'all' || status === filter) {
          row.classList.remove('hidden');
        } else {
          row.classList.add('hidden');
        }
      });
    });
  });

  // 4. Adjust Stock Form Submit
  const adjustForm = document.getElementById('adjust-stock-form');
  if (adjustForm) {
    adjustForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById('save-adjust-stock-btn');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
      }

      const variantId = document.getElementById('adj-variant-id').value;
      const mtype = document.getElementById('adj-movement-type').value;
      const qtyChange = parseFloat(document.getElementById('adj-qty').value) || 0;
      const unitCost = parseFloat(document.getElementById('adj-cost').value) || 0;
      const notes = document.getElementById('adj-notes').value.trim() || null;

      if (!variantId) {
        window.showToast?.('অনুগ্রহ করে একটি পণ্য ভ্যারিয়েন্ট নির্বাচন করুন।', 'error');
        if (saveBtn) saveBtn.disabled = false;
        return;
      }

      try {
        const resp = await fetch('/api/v1/stock/adjust', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            variant_id: variantId,
            movement_type: mtype,
            quantity_change: qtyChange,
            unit_cost: unitCost,
            notes: notes
          })
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Stock adjustment failed');
        }

        window.showToast?.('স্টক সমন্বয় সফলভাবে লেজারে রেকর্ড হয়েছে!', 'success');
        window.closeModal('adjust-stock-modal');
        setTimeout(() => window.location.reload(), 400);
      } catch (err) {
        window.showToast?.(`সমন্বয়ে ত্রুটি: ${err.message}`, 'error');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<span>স্টক সংরক্ষণ করুন (Save Stock Adjustment)</span>`;
        }
      }
    });
  }
});
