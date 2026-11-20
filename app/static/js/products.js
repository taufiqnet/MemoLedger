// MemoLedger Products & Catalog CRUD Module

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

document.addEventListener('DOMContentLoaded', () => {
  // 1. Search Filter
  const searchInput = document.getElementById('product-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll('.product-card').forEach(card => {
        const name = card.getAttribute('data-name') || '';
        const brand = card.getAttribute('data-brand') || '';
        if (name.includes(q) || brand.includes(q)) {
          card.classList.remove('hidden');
        } else {
          card.classList.add('hidden');
        }
      });
    });
  }

  // 2. Add Single Product Form Submit
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

  // 2b. Bulk Add Products Form Submit
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
