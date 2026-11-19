// MemoLedger Canvas-Based Camera Capture & Transformation Module

let currentRotation = 0;
let rawImage = null;
let canvas = null;
let ctx = null;

export function initCapture() {
  const fileInput = document.getElementById('camera-file-input');
  canvas = document.getElementById('preview-canvas');
  if (!canvas) return;
  ctx = canvas.getContext('2d');

  const rotateLeftBtn = document.getElementById('rotate-left-btn');
  const rotateRightBtn = document.getElementById('rotate-right-btn');
  const uploadBtn = document.getElementById('upload-submit-btn');
  const previewContainer = document.getElementById('preview-container');
  const uploadForm = document.getElementById('upload-form');

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
          if (previewContainer) previewContainer.classList.remove('hidden');
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
        statusMsg.textContent = "Uploading & processing memo...";
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
          // Navigate to review screen
          window.location.href = `/review/${data.memo_id}`;
        } catch (error) {
          if (statusMsg) {
            statusMsg.textContent = `Error: ${error.message}`;
            statusMsg.classList.add('text-rose-500');
          }
        }
      }, 'image/jpeg', 0.92);
    });
  }
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

document.addEventListener('DOMContentLoaded', initCapture);
