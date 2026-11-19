// MemoLedger Bilingual Translation Engine (Bangla & English)

const translations = {
  en: {
    app_title: "MemoLedger",
    dashboard: "Dashboard",
    upload: "Capture Memo",
    review: "Review & Approve",
    products: "Products",
    suppliers: "Suppliers",
    stock_ledger: "Stock Ledger",
    reports: "Reports",
    ask_data: "Ask Data",
    login: "Log In",
    logout: "Log Out",
    welcome: "Welcome",
    total_memos: "Total Memos",
    pending_review: "Pending Review",
    total_spent: "Total Purchases (BDT)",
    low_stock: "Low Stock Alerts",
    recent_memos: "Recent Memos",
    supplier: "Supplier",
    date: "Date",
    amount: "Amount",
    status: "Status",
    approved: "Approved",
    processing: "Processing",
    review_required: "Review Required",
    take_photo: "Take Photo / Select Image",
    rotate_left: "Rotate 90° Left",
    rotate_right: "Rotate 90° Right",
    process_memo: "Extract & Process Memo",
    line_items: "Extracted Line Items",
    one_tap_approve: "One-Tap Approve & Update Stock",
    download_pdf: "Download PDF Invoice",
    export_excel: "Export Excel",
    share_whatsapp: "Share on WhatsApp",
    currency_symbol: "৳",
    search: "Search...",
    cancel: "Cancel",
    save: "Save",
    ask_placeholder: "Ask anything about your stock or purchases (e.g. 'How much Sunscreen in stock?')...",
  },
  bn: {
    app_title: "মেমোলেজার",
    dashboard: "ড্যাশবোর্ড",
    upload: "মেমো তুলুন",
    review: "যাচাই ও অনুমোদন",
    products: "পণ্য তালিকা",
    suppliers: "সরবরাহকারী",
    stock_ledger: "স্টক লেজার",
    reports: "রিপোর্ট",
    ask_data: "তথ্য জিজ্ঞাসা",
    login: "লগ ইন",
    logout: "লগ আউট",
    welcome: "স্বাগতম",
    total_memos: "মোট মেমো",
    pending_review: "অপেক্ষমান মেমো",
    total_spent: "মোট ক্রয় (টাকা)",
    low_stock: "কম স্টকের সতর্কতা",
    recent_memos: "সাম্প্রতিক মেমোগুলো",
    supplier: "সরবরাহকারী",
    date: "তারিখ",
    amount: "মোট টাকা",
    status: "অবস্থা",
    approved: "অনুমোদিত",
    processing: "প্রসেসিং হচ্ছে",
    review_required: "যাচাই প্রয়োজন",
    take_photo: "ছবি তুলুন / সিলেক্ট করুন",
    rotate_left: "বামদিকে ৯০° ঘোরান",
    rotate_right: "ডানদিকে ৯০° ঘোরান",
    process_memo: "মেমো প্রসেস করুন",
    line_items: "এক্সট্রাক্ট করা পণ্যের তালিকা",
    one_tap_approve: "এক ট্যাপে অনুমোদন ও স্টক আপডেট",
    download_pdf: "পিডিএফ ইনভয়েস ডাউনলোড",
    export_excel: "এক্সেল এক্সপোর্ট",
    share_whatsapp: "হোয়াটসঅ্যাপে পাঠান",
    currency_symbol: "৳",
    search: "খুঁজুন...",
    cancel: "বাতিল",
    save: "সংরক্ষণ",
    ask_placeholder: "আপনার স্টক বা খরচ সম্পর্কে জিজ্ঞাসা করুন (যেমন: 'সানস্ক্রিনের স্টক কত?')...",
  }
};

let currentLang = localStorage.getItem('memoledger_lang') || 'bn';

export function getLang() {
  return currentLang;
}

export function setLang(lang) {
  if (translations[lang]) {
    currentLang = lang;
    localStorage.setItem('memoledger_lang', lang);
    applyTranslations();
  }
}

export function t(key) {
  return (translations[currentLang] && translations[currentLang][key]) || key;
}

export function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (translations[currentLang] && translations[currentLang][key]) {
      if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {
        el.setAttribute('placeholder', translations[currentLang][key]);
      } else {
        el.textContent = translations[currentLang][key];
      }
    }
  });

  const langBtn = document.getElementById('lang-toggle-btn');
  if (langBtn) {
    langBtn.textContent = currentLang === 'bn' ? 'English' : 'বাংলা';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
  const langBtn = document.getElementById('lang-toggle-btn');
  if (langBtn) {
    langBtn.addEventListener('click', () => {
      setLang(currentLang === 'bn' ? 'en' : 'bn');
    });
  }
});
