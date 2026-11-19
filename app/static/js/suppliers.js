// MemoLedger Suppliers CRUD Module

window.openAddSupplierModal = function() {
  document.getElementById('add-supplier-form')?.reset();
  window.openModal('add-supplier-modal');
};

window.openEditSupplierModal = function(id, name, phone, address, abbreviations) {
  document.getElementById('edit-s-id').value = id;
  document.getElementById('edit-s-name').value = name;
  document.getElementById('edit-s-phone').value = phone || '';
  document.getElementById('edit-s-address').value = address || '';

  // Format abbreviations dict to string "key=val, key2=val2"
  let abbrStr = '';
  if (abbreviations && typeof abbreviations === 'object') {
    abbrStr = Object.entries(abbreviations).map(([k, v]) => `${k}=${v}`).join(', ');
  }
  document.getElementById('edit-s-abbr').value = abbrStr;

  window.openModal('edit-supplier-modal');
};

window.deleteSupplier = async function(id, name) {
  if (!confirm(`আপনি কি "${name}" সরবরাহকারীকে মুছে ফেলতে চান?`)) return;

  try {
    const resp = await fetch(`/api/v1/suppliers/${id}`, { method: 'DELETE' });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Delete failed');
    }
    window.showToast?.(`"${name}" সফলভাবে মুছে ফেলা হয়েছে।`, 'success');
    setTimeout(() => window.location.reload(), 400);
  } catch (err) {
    window.showToast?.(`মুছতে ব্যর্থ: ${err.message}`, 'error');
  }
};

function parseAbbrString(str) {
  const result = {};
  if (!str) return result;
  str.split(',').forEach(item => {
    const parts = item.split('=');
    if (parts.length === 2) {
      const k = parts[0].trim();
      const v = parts[1].trim();
      if (k && v) result[k] = v;
    }
  });
  return result;
}

document.addEventListener('DOMContentLoaded', () => {
  // Search filter
  const searchInput = document.getElementById('supplier-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll('.supplier-card').forEach(card => {
        const name = card.getAttribute('data-name') || '';
        const phone = card.getAttribute('data-phone') || '';
        if (name.includes(q) || phone.includes(q)) {
          card.classList.remove('hidden');
        } else {
          card.classList.add('hidden');
        }
      });
    });
  }

  // Add Supplier Form
  const addForm = document.getElementById('add-supplier-form');
  if (addForm) {
    addForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById('save-supplier-btn');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
      }

      const name = document.getElementById('add-s-name').value.trim();
      const phone = document.getElementById('add-s-phone').value.trim() || null;
      const address = document.getElementById('add-s-address').value.trim() || null;
      const abbrStr = document.getElementById('add-s-abbr').value.trim();
      const abbreviations = parseAbbrString(abbrStr);

      try {
        const resp = await fetch('/api/v1/suppliers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            phone,
            address,
            abbreviations
          })
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Could not save supplier');
        }

        window.showToast?.('নতুন সরবরাহকারী সফলভাবে সংরক্ষিত হয়েছে!', 'success');
        window.closeModal('add-supplier-modal');
        setTimeout(() => window.location.reload(), 400);
      } catch (err) {
        window.showToast?.(`সংরক্ষণে ত্রুটি: ${err.message}`, 'error');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<span>সরবরাহকারী সংরক্ষণ করুন (Save Supplier)</span>`;
        }
      }
    });
  }

  // Edit Supplier Form
  const editForm = document.getElementById('edit-supplier-form');
  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById('save-edit-supplier-btn');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span>সংরক্ষণ হচ্ছে...</span>`;
      }

      const id = document.getElementById('edit-s-id').value;
      const name = document.getElementById('edit-s-name').value.trim();
      const phone = document.getElementById('edit-s-phone').value.trim() || null;
      const address = document.getElementById('edit-s-address').value.trim() || null;
      const abbrStr = document.getElementById('edit-s-abbr').value.trim();
      const abbreviations = parseAbbrString(abbrStr);

      try {
        const resp = await fetch(`/api/v1/suppliers/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            phone,
            address,
            abbreviations
          })
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || 'Update failed');
        }

        window.showToast?.('সরবরাহকারী তথ্য সফলভাবে আপডেট হয়েছে!', 'success');
        window.closeModal('edit-supplier-modal');
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
});
