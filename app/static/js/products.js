// MemoLedger Products & Catalog CRUD Module with Modern Datatable (Pagination, Search, Sort)

// Global helper functions attached to window for HTML onclick handlers
window.openAddProductModal = function() {
  document.getElementById('add-product-form')?.reset();
  window.openModal('add-product-modal');
};

window.openBulkProductModal = function() {
  document.getElementById('bulk-product-form')?.reset();
  window.openModal('bulk-product-modal');
};

window.openEditProductModal = function(id, name, shortName, brand, type, desc) {
  document.getElementById('edit-p-id').value = id;
  document.getElementById('edit-p-name').value = name;
  const shortInput = document.getElementById('edit-p-short-name');
  if (shortInput) shortInput.value = shortName || '';
  document.getElementById('edit-p-brand').value = brand || '';
  document.getElementById('edit-p-type').value = type || '';
  document.getElementById('edit-p-desc').value = desc || '';
  window.openModal('edit-product-modal');
};

window.openAddVariantModal = function(productId, productName) {
  document.getElementById('add-var-pid').value = productId;
  document.getElementById('add-variant-pname').textContent = `পণ্য: ${productName}`;
  document.getElementById('add-variant-form')?.reset();
  document.getElementById('add-var-pid').value = productId;
  window.openModal('add-variant-modal');
};

window.openEditVariantModal = function(variantId, sku, size, unit, code, cost, retail, stock) {
  document.getElementById('edit-var-id').value = variantId;
  document.getElementById('edit-var-size').value = size;
  document.getElementById('edit-var-unit').value = unit;
  document.getElementById('edit-var-code').value = code;
  document.getElementById('edit-var-cost').value = parseFloat(cost) || 0;
  document.getElementById('edit-var-retail').value = parseFloat(retail) || 0;
  document.getElementById('edit-var-stock').value = parseFloat(stock) || 0;
  window.openModal('edit-variant-modal');
};

window.deleteProduct = async function(productId, productName) {
  if (!confirm(`আপনি কি নিশ্চিতভাবে "${productName}" পণ্যটি মুছে ফেলতে চান?`)) return;

  try {
    const resp = await fetch(`/api/v1/products/${productId}`, { method: 'DELETE' });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Delete failed');
    }
    window.showToast?.(`"${productName}" সফলভাবে মুছে ফেলা হয়েছে।`, 'success');
    setTimeout(() => window.location.reload(), 400);
  } catch (err) {
    window.showToast?.(`মুছতে ব্যর্থ: ${err.message}`, 'error');
  }
};

function escapeHtml(text) {
  if (text == null) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ================= MODERN DATATABLE CONTROLLER =================
class ProductDataTable {
  constructor() {
    this.rawProducts = [];
    this.filteredProducts = [];
    this.currentPage = 1;
    this.pageSize = 25;
    this.sortKey = 'name';
    this.sortOrder = 'asc';
    this.searchQuery = '';
    this.categoryFilter = '';

    this.tableBody = document.getElementById('products-table-body');
    this.paginationInfo = document.getElementById('pagination-info');
    this.paginationControls = document.getElementById('pagination-controls');
    this.searchInput = document.getElementById('product-search-input');
    this.searchClearBtn = document.getElementById('search-clear-btn');
    this.categorySelect = document.getElementById('product-category-filter');
    this.pageSizeSelect = document.getElementById('product-page-size');

    this.init();
  }

  init() {
    const scriptEl = document.getElementById('products-data-json');
    if (scriptEl && scriptEl.textContent) {
      try {
        this.rawProducts = JSON.parse(scriptEl.textContent);
      } catch (e) {
        console.error('Failed to parse products JSON island:', e);
        this.rawProducts = [];
      }
    }

    this.setupCategoryFilter();
    this.setupEventListeners();
    this.filterAndRender();
  }

  setupCategoryFilter() {
    if (!this.categorySelect) return;
    const categories = new Set();
    this.rawProducts.forEach(p => {
      if (p.product_type && p.product_type.trim()) {
        categories.add(p.product_type.trim());
      }
    });

    Array.from(categories).sort().forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat;
      opt.textContent = cat;
      this.categorySelect.appendChild(opt);
    });
  }

  setupEventListeners() {
    // Search input
    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        if (this.searchClearBtn) {
          if (this.searchQuery) {
            this.searchClearBtn.classList.remove('hidden');
          } else {
            this.searchClearBtn.classList.add('hidden');
          }
        }
        this.currentPage = 1;
        this.filterAndRender();
      });
    }

    if (this.searchClearBtn) {
      this.searchClearBtn.addEventListener('click', () => {
        if (this.searchInput) this.searchInput.value = '';
        this.searchQuery = '';
        this.searchClearBtn.classList.add('hidden');
        this.currentPage = 1;
        this.filterAndRender();
        this.searchInput?.focus();
      });
    }

    // Category filter
    if (this.categorySelect) {
      this.categorySelect.addEventListener('change', (e) => {
        this.categoryFilter = e.target.value.trim().toLowerCase();
        this.currentPage = 1;
        this.filterAndRender();
      });
    }

    // Page size selector (default 25)
    if (this.pageSizeSelect) {
      this.pageSizeSelect.addEventListener('change', (e) => {
        this.pageSize = parseInt(e.target.value, 10) || 25;
        this.currentPage = 1;
        this.filterAndRender();
      });
    }

    // Column sorting clicks
    document.querySelectorAll('#products-table th[data-sort]').forEach(th => {
      th.addEventListener('click', () => {
        const key = th.getAttribute('data-sort');
        if (this.sortKey === key) {
          this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
          this.sortKey = key;
          this.sortOrder = 'asc';
        }
        this.currentPage = 1;
        this.updateSortIcons();
        this.filterAndRender();
      });
    });
  }

  updateSortIcons() {
    document.querySelectorAll('#products-table th[data-sort]').forEach(th => {
      const key = th.getAttribute('data-sort');
      const icon = th.querySelector('.sort-icon');
      if (!icon) return;

      if (key === this.sortKey) {
        icon.textContent = this.sortOrder === 'asc' ? '▲' : '▼';
        icon.className = 'sort-icon text-teal-700 font-mono text-[11px] font-bold';
      } else {
        icon.textContent = '⇅';
        icon.className = 'sort-icon text-slate-400 font-mono text-[11px]';
      }
    });
  }

  filterAndRender() {
    // 1. Filter
    this.filteredProducts = this.rawProducts.filter(p => {
      const name = (p.name || '').toLowerCase();
      const shortName = (p.short_name || '').toLowerCase();
      const brand = (p.brand || '').toLowerCase();
      const ptype = (p.product_type || '').toLowerCase();

      const matchesSearch = !this.searchQuery ||
        name.includes(this.searchQuery) ||
        shortName.includes(this.searchQuery) ||
        brand.includes(this.searchQuery) ||
        ptype.includes(this.searchQuery);

      const matchesCategory = !this.categoryFilter || ptype === this.categoryFilter;

      return matchesSearch && matchesCategory;
    });

    // 2. Sort
    this.filteredProducts.sort((a, b) => {
      let valA = a[this.sortKey];
      let valB = b[this.sortKey];

      if (typeof valA === 'string') valA = valA.toLowerCase();
      if (typeof valB === 'string') valB = valB.toLowerCase();

      if (valA < valB) return this.sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return this.sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    // 3. Paginate
    const total = this.filteredProducts.length;
    const totalPages = Math.ceil(total / this.pageSize) || 1;
    if (this.currentPage > totalPages) this.currentPage = totalPages;

    const startIdx = (this.currentPage - 1) * this.pageSize;
    const endIdx = Math.min(startIdx + this.pageSize, total);
    const pageItems = this.filteredProducts.slice(startIdx, endIdx);

    this.renderTable(pageItems, startIdx);
    this.renderPagination(total, startIdx, endIdx, totalPages);
  }

  renderTable(items, startIdx) {
    if (!this.tableBody) return;

    if (items.length === 0) {
      this.tableBody.innerHTML = `
        <tr>
          <td colspan="9" class="p-8 text-center text-slate-400">
            <div class="space-y-2">
              <span class="text-3xl">🔍</span>
              <div class="text-sm font-semibold text-slate-600">কোনো পণ্য পাওয়া যায়নি</div>
              <div class="text-xs text-slate-400">ভিন্ন কোনো নাম বা ক্যাটাগরি দিয়ে চেষ্টা করুন</div>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    const rowsHtml = items.map((p, idx) => {
      const serial = startIdx + idx + 1;
      const shortBadge = p.short_name
        ? `<span class="inline-block bg-amber-50 text-amber-800 font-mono font-bold px-2 py-0.5 rounded border border-amber-200 text-[11px]">${escapeHtml(p.short_name)}</span>`
        : `<span class="text-slate-300">-</span>`;

      const brandBadge = p.brand
        ? `<span class="text-[10px] font-bold text-teal-800 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded uppercase tracking-wider">${escapeHtml(p.brand)}</span>`
        : `<span class="text-slate-400 text-[11px]">General</span>`;

      const stockBadge = p.total_stock > 0
        ? `<span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">${p.total_stock}</span>`
        : `<span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">০ (স্টক শেষ)</span>`;

      // Variants badges
      const variantsBadges = (p.variants && p.variants.length > 0)
        ? p.variants.map(v => {
            const vLabel = `${v.size_value || ''}${v.size_unit || ''} ${v.variant_code ? '(' + v.variant_code + ')' : ''}`.trim() || 'Default';
            return `
              <span class="inline-flex items-center gap-1 bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-0.5 rounded text-[11px] font-medium border border-slate-200 cursor-pointer transition-colors"
                    onclick="openEditVariantModal('${v.id}', '${escapeHtml(v.sku || '')}', '${escapeHtml(v.size_value || '')}', '${escapeHtml(v.size_unit || '')}', '${escapeHtml(v.variant_code || '')}', '${v.cost_price}', '${v.retail_price}', '${v.current_stock}')"
                    title="ভ্যারিয়েন্ট এডিট: স্টক ${v.current_stock}, দর ৳${v.cost_price.toFixed(2)}">
                <span>${escapeHtml(vLabel)}</span>
                <span class="text-teal-700 font-bold">৳${v.cost_price.toFixed(0)}</span>
                <span class="text-slate-400 text-[9px]">✎</span>
              </span>
            `;
          }).join('')
        : `<span class="text-slate-400 text-[11px]">কোনো ভ্যারিয়েন্ট নেই</span>`;

      return `
        <tr class="hover:bg-teal-50/20 transition-colors border-b border-slate-100 group">
          <td class="p-3 text-center text-slate-400 font-bold">${serial}</td>
          <td class="p-3">
            <div class="font-bold text-slate-800 text-xs md:text-sm">${escapeHtml(p.name)}</div>
            ${p.description ? `<div class="text-[10px] text-slate-400 truncate max-w-xs">${escapeHtml(p.description)}</div>` : ''}
          </td>
          <td class="p-3">${shortBadge}</td>
          <td class="p-3">${brandBadge}</td>
          <td class="p-3 text-slate-600 font-medium">${escapeHtml(p.product_type || 'General')}</td>
          <td class="p-3">
            <div class="flex flex-wrap items-center gap-1">
              ${variantsBadges}
              <button type="button" 
                      onclick="openAddVariantModal('${p.id}', '${escapeHtml(p.name)}')"
                      class="text-[10px] text-teal-700 hover:text-teal-900 font-bold hover:underline bg-teal-50 border border-teal-200 px-1.5 py-0.5 rounded"
                      title="নতুন ভ্যারিয়েন্ট যোগ">+ যোগ</button>
            </div>
          </td>
          <td class="p-3 text-right font-black text-slate-800 text-xs">
            ৳${p.cost_price.toFixed(2)}
          </td>
          <td class="p-3 text-center">${stockBadge}</td>
          <td class="p-3 text-right">
            <div class="flex items-center justify-end gap-1">
              <!-- Edit Product -->
              <button type="button" 
                      onclick="openEditProductModal('${p.id}', '${escapeHtml(p.name)}', '${escapeHtml(p.short_name || '')}', '${escapeHtml(p.brand || '')}', '${escapeHtml(p.product_type || '')}', '${escapeHtml(p.description || '')}')"
                      class="p-1.5 text-slate-400 hover:text-teal-700 hover:bg-slate-100 rounded-lg transition-colors" 
                      title="পণ্য এডিট করুন">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
              </button>
              <!-- Delete Product -->
              <button type="button" 
                      onclick="deleteProduct('${p.id}', '${escapeHtml(p.name)}')"
                      class="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors" 
                      title="পণ্য মুছুন">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    this.tableBody.innerHTML = rowsHtml;
  }

  renderPagination(total, startIdx, endIdx, totalPages) {
    if (this.paginationInfo) {
      if (total === 0) {
        this.paginationInfo.textContent = 'কোনো পণ্য নেই';
      } else {
        this.paginationInfo.innerHTML = `
          <span>মোট <b>${total}</b> টি পণ্যের মধ্যে <b>${startIdx + 1} - ${endIdx}</b> দেখাচ্ছে</span>
        `;
      }
    }

    if (!this.paginationControls) return;

    if (totalPages <= 1) {
      this.paginationControls.innerHTML = '';
      return;
    }

    let buttonsHtml = '';

    // First & Prev
    buttonsHtml += `
      <button type="button" class="px-2.5 py-1.5 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 disabled:pointer-events-none font-bold"
              ${this.currentPage === 1 ? 'disabled' : ''} onclick="window.productTable.goToPage(1)">«</button>
      <button type="button" class="px-2.5 py-1.5 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 disabled:pointer-events-none font-semibold"
              ${this.currentPage === 1 ? 'disabled' : ''} onclick="window.productTable.goToPage(${this.currentPage - 1})">‹ পূর্ববর্তী</button>
    `;

    // Dynamic page numbers
    let startPage = Math.max(1, this.currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) {
      startPage = Math.max(1, endPage - 4);
    }

    for (let p = startPage; p <= endPage; p++) {
      const activeClass = p === this.currentPage
        ? 'bg-teal-700 text-white font-bold border-teal-700'
        : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200 font-semibold';

      buttonsHtml += `
        <button type="button" class="w-8 h-8 rounded border text-xs transition-colors ${activeClass}"
                onclick="window.productTable.goToPage(${p})">${p}</button>
      `;
    }

    // Next & Last
    buttonsHtml += `
      <button type="button" class="px-2.5 py-1.5 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 disabled:pointer-events-none font-semibold"
              ${this.currentPage === totalPages ? 'disabled' : ''} onclick="window.productTable.goToPage(${this.currentPage + 1})">পরবর্তী ›</button>
      <button type="button" class="px-2.5 py-1.5 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 disabled:pointer-events-none font-bold"
              ${this.currentPage === totalPages ? 'disabled' : ''} onclick="window.productTable.goToPage(${totalPages})">»</button>
    `;

    this.paginationControls.innerHTML = buttonsHtml;
  }

  goToPage(page) {
    this.currentPage = page;
    this.filterAndRender();
    document.getElementById('products-table')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

// ================= MODAL SUBMISSIONS & DOM READY =================
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Datatable
  window.productTable = new ProductDataTable();

  // 1. Add Single Product Form Submit
  const addForm = document.getElementById('add-product-form');
  if (addForm) {
    addForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById('save-product-btn');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
      }

      const name = document.getElementById('add-p-name').value.trim();
      const shortName = document.getElementById('add-p-short-name')?.value.trim();
      const brand = document.getElementById('add-p-brand')?.value.trim();
      const ptype = document.getElementById('add-p-type')?.value.trim();
      
      const cost = parseFloat(document.getElementById('add-v-cost')?.value) || 0;
      const retail = parseFloat(document.getElementById('add-v-retail')?.value) || 0;
      const stock = parseFloat(document.getElementById('add-v-stock')?.value) || 0;

      const payload = {
        name: name,
        short_name: shortName || null,
        brand: brand || null,
        product_type: ptype || null,
        variants: []
      };
      if (cost > 0 || retail > 0 || stock > 0) {
        payload.variants.push({
          cost_price: cost,
          retail_price: retail,
          initial_stock: stock
        });
      }

      try {
        const resp = await fetch('/api/v1/products', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Could not save product');
        }

        window.showToast?.('নতুন পণ্য সফলভাবে তৈরি ও সংরক্ষিত হয়েছে!', 'success');
        window.closeModal('add-product-modal');
        setTimeout(() => window.location.reload(), 400);
      } catch (err) {
        window.showToast?.(`সংরক্ষণে ত্রুটি: ${err.message}`, 'error');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<span>পণ্য সংরক্ষণ করুন (Save Product)</span>`;
        }
      }
    });
  }

  // 2. Bulk Add Products Form Submit
  const bulkForm = document.getElementById('bulk-product-form');
  if (bulkForm) {
    bulkForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById('save-bulk-btn');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
      }

      const rawText = document.getElementById('bulk-p-names').value;
      const names = rawText.split('\n').map(n => n.trim()).filter(n => n.length > 0);

      if (names.length === 0) {
        window.showToast?.('অন্তত একটি পণ্যের নাম লিখুন', 'warning');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<span>একসাথে সবগুলো সংরক্ষণ করুন</span>`;
        }
        return;
      }

      try {
        const resp = await fetch('/api/v1/products/bulk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ names: names })
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Could not import products');
        }

        const data = await resp.json();
        window.showToast?.(`${data.created_count} টি পণ্য সফলভাবে যুক্ত হয়েছে!`, 'success');
        window.closeModal('bulk-product-modal');
        setTimeout(() => window.location.reload(), 400);
      } catch (err) {
        window.showToast?.(`যুক্ত করতে ত্রুটি: ${err.message}`, 'error');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<span>একসাথে সবগুলো সংরক্ষণ করুন</span>`;
        }
      }
    });
  }

  // 3. Edit Product Form Submit
  const editForm = document.getElementById('edit-product-form');
  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById('save-edit-product-btn');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
      }

      const id = document.getElementById('edit-p-id').value;
      const payload = {
        name: document.getElementById('edit-p-name').value.trim(),
        short_name: document.getElementById('edit-p-short-name')?.value.trim() || null,
        brand: document.getElementById('edit-p-brand').value.trim() || null,
        product_type: document.getElementById('edit-p-type').value.trim() || null,
        description: document.getElementById('edit-p-desc').value.trim() || null,
      };

      try {
        const resp = await fetch(`/api/v1/products/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Update failed');
        }

        window.showToast?.('পণ্য তথ্য সফলভাবে আপডেট হয়েছে!', 'success');
        window.closeModal('edit-product-modal');
        setTimeout(() => window.location.reload(), 400);
      } catch (err) {
        window.showToast?.(`আপডেটে ত্রুটি: ${err.message}`, 'error');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<span>পরিবর্তন সংরক্ষণ করুন (Save Changes)</span>`;
        }
      }
    });
  }

  // 4. Add Variant Form Submit
  const addVarForm = document.getElementById('add-variant-form');
  if (addVarForm) {
    addVarForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById('save-variant-btn');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
      }

      const pid = document.getElementById('add-var-pid').value;
      const payload = {
        size_value: document.getElementById('add-var-size').value.trim() || null,
        size_unit: document.getElementById('add-var-unit').value.trim() || null,
        variant_code: document.getElementById('add-var-code').value.trim() || null,
        cost_price: parseFloat(document.getElementById('add-var-cost').value) || 0,
        retail_price: parseFloat(document.getElementById('add-var-retail').value) || 0,
        initial_stock: parseFloat(document.getElementById('add-var-stock').value) || 0
      };

      try {
        const resp = await fetch(`/api/v1/products/${pid}/variants`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Could not add variant');
        }

        window.showToast?.('নতুন ভ্যারিয়েন্ট সফলভাবে যোগ করা হয়েছে!', 'success');
        window.closeModal('add-variant-modal');
        setTimeout(() => window.location.reload(), 400);
      } catch (err) {
        window.showToast?.(`ত্রুটি: ${err.message}`, 'error');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<span>ভ্যারিয়েন্ট সংরক্ষণ করুন (Save Variant)</span>`;
        }
      }
    });
  }

  // 5. Edit Variant Form Submit & Delete
  const editVarForm = document.getElementById('edit-variant-form');
  if (editVarForm) {
    editVarForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById('save-edit-variant-btn');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
      }

      const vid = document.getElementById('edit-var-id').value;
      const payload = {
        size_value: document.getElementById('edit-var-size').value.trim() || null,
        size_unit: document.getElementById('edit-var-unit').value.trim() || null,
        variant_code: document.getElementById('edit-var-code').value.trim() || null,
        cost_price: parseFloat(document.getElementById('edit-var-cost').value) || 0,
        retail_price: parseFloat(document.getElementById('edit-var-retail').value) || 0,
        current_stock: parseFloat(document.getElementById('edit-var-stock').value) || 0
      };

      try {
        const resp = await fetch(`/api/v1/products/variants/${vid}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Variant update failed');
        }

        window.showToast?.('ভ্যারিয়েন্ট সফলভাবে হালনাগাদ হয়েছে!', 'success');
        window.closeModal('edit-variant-modal');
        setTimeout(() => window.location.reload(), 400);
      } catch (err) {
        window.showToast?.(`আপডেটে ত্রুটি: ${err.message}`, 'error');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<span>সংরক্ষণ করুন (Save)</span>`;
        }
      }
    });

    const deleteVarBtn = document.getElementById('delete-variant-btn');
    if (deleteVarBtn) {
      deleteVarBtn.addEventListener('click', async () => {
        const vid = document.getElementById('edit-var-id').value;
        if (!confirm('আপনি কি এই ভ্যারিয়েন্টটি মুছে ফেলতে চান?')) return;

        try {
          const resp = await fetch(`/api/v1/products/variants/${vid}`, { method: 'DELETE' });
          if (!resp.ok) throw new Error('Delete failed');
          window.showToast?.('ভ্যারিয়েন্ট মুছে ফেলা হয়েছে।', 'success');
          window.closeModal('edit-variant-modal');
          setTimeout(() => window.location.reload(), 400);
        } catch (err) {
          window.showToast?.(`মুছতে ব্যর্থ: ${err.message}`, 'error');
        }
      });
    }
  }
});
