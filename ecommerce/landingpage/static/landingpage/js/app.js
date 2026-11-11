(function () {
  'use strict';

  function showToast(msg, type = 'info') {
    let stack = document.getElementById('ccToastStack');
    if (!stack) {
      stack = document.createElement('div');
      stack.id = 'ccToastStack';
      stack.className = 'cc-toast-stack';
      document.body.appendChild(stack);
    }
    const el = document.createElement('div');
    el.className = `cc-toast ${type}`;
    el.innerHTML = `<span>${msg}</span><button type="button" style="background:none;border:none;color:#aaa;cursor:pointer;font-size:16px;" onclick="this.parentElement.remove()">×</button>`;
    stack.appendChild(el);
    setTimeout(() => {
      if (el.parentElement) el.remove();
    }, 3600);
  }
  window.ccShowToast = showToast;

  setTimeout(() => {
    document.querySelectorAll('.cc-toast[data-auto="1"]').forEach((t) => t.remove());
  }, 4200);

  const track = document.getElementById('heroCarouselTrack');
  if (track) {
    const slides = track.querySelectorAll('.cc-carousel-slide');
    const dots = document.querySelectorAll('.cc-carousel-dot');
    let idx = 0;
    function goTo(i) {
      idx = (i + slides.length) % slides.length;
      track.style.transform = `translateX(-${idx * 100}%)`;
      dots.forEach((d, di) => d.classList.toggle('active', di === idx));
    }
    document.getElementById('heroPrev')?.addEventListener('click', () => goTo(idx - 1));
    document.getElementById('heroNext')?.addEventListener('click', () => goTo(idx + 1));
    dots.forEach((d, di) => d.addEventListener('click', () => goTo(di)));
    setInterval(() => goTo(idx + 1), 4500);
  }

  const timerEl = document.getElementById('dealCountdown');
  if (timerEl) {
    let remaining = 5 * 3600 + 42 * 60 + 18;
    setInterval(() => {
      if (remaining <= 0) remaining = 6 * 3600;
      remaining -= 1;
      const h = String(Math.floor(remaining / 3600)).padStart(2, '0');
      const m = String(Math.floor((remaining % 3600) / 60)).padStart(2, '0');
      const s = String(remaining % 60).padStart(2, '0');
      timerEl.textContent = `${h}h : ${m}m : ${s}s Left`;
    }, 1000);
  }

  const searchInput = document.getElementById('ccSearchInput');
  const searchDrop = document.getElementById('ccSearchDropdown');
  let searchTimer = null;
  if (searchInput && searchDrop) {
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimer);
      const q = searchInput.value.trim();
      if (!q) {
        searchDrop.classList.remove('open');
        searchDrop.innerHTML = '';
        return;
      }
      searchTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/search-suggest/?q=${encodeURIComponent(q)}`);
          const data = await res.json();
          if (!data.suggestions || !data.suggestions.length) {
            searchDrop.innerHTML = `<div style="padding:12px 14px;color:#666;font-size:13px;">No quick matches for "${q}" — Press Enter to search all items</div>`;
            searchDrop.classList.add('open');
            return;
          }
          searchDrop.innerHTML = data.suggestions.map((item) => `
            <a href="${item.url}" class="cc-suggest-item">
              <img src="${item.image}" alt="" />
              <div class="cc-suggest-meta">
                <div class="cc-suggest-title">${item.title}</div>
                <div class="cc-suggest-sub">${item.type}</div>
              </div>
              ${item.price ? `<span style="font-weight:700;color:#212121;font-size:13px;">${item.price}</span>` : ''}
            </a>
          `).join('');
          searchDrop.classList.add('open');
        } catch (err) {
          console.error(err);
        }
      }, 180);
    });
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.cc-search-wrap')) searchDrop.classList.remove('open');
    });
  }

  document.addEventListener('click', async (e) => {
    const wishBtn = e.target.closest('[data-wish-url]');
    if (wishBtn) {
      e.preventDefault();
      try {
        const res = await fetch(wishBtn.dataset.wishUrl + '?ajax=1');
        const data = await res.json();
        if (data.ok) {
          wishBtn.classList.toggle('active', data.added);
          wishBtn.innerHTML = data.added ? '♥' : '♡';
          const badge = document.getElementById('headerWishCount');
          if (badge) badge.textContent = data.wishlist_count;
          showToast(data.message, 'success');
        }
      } catch (err) {
        window.location.href = wishBtn.dataset.wishUrl;
      }
    }

    const cmpBtn = e.target.closest('[data-compare-url]');
    if (cmpBtn) {
      e.preventDefault();
      try {
        const res = await fetch(cmpBtn.dataset.compareUrl + '?ajax=1');
        const data = await res.json();
        if (data.ok) {
          cmpBtn.classList.toggle('active', data.added);
          const badge = document.getElementById('headerCompareCount');
          if (badge) {
            badge.textContent = data.compare_count;
            badge.style.display = data.compare_count > 0 ? 'inline-flex' : 'none';
          }
          showToast(data.message, 'info');
        }
      } catch (err) {
        window.location.href = cmpBtn.dataset.compareUrl;
      }
    }
  });

  const pincodeModal = document.getElementById('ccPincodeModal');
  document.querySelectorAll('[data-open-pincode]').forEach((btn) => btn.addEventListener('click', () => pincodeModal?.classList.add('open')));
  document.querySelectorAll('[data-close-pincode]').forEach((btn) => btn.addEventListener('click', () => pincodeModal?.classList.remove('open')));

  const pdpPincodeBtn = document.getElementById('pdpCheckPincodeBtn');
  if (pdpPincodeBtn) {
    pdpPincodeBtn.addEventListener('click', async () => {
      const inp = document.getElementById('pdpPincodeInput');
      const out = document.getElementById('pdpPincodeResult');
      if (!inp || !out) return;
      const res = await fetch(`/api/check-pincode/?ajax=1&pincode=${encodeURIComponent(inp.value.trim())}`);
      const data = await res.json();
      if (!data.ok) {
        out.innerHTML = `<span style="color:#D32F2F;font-weight:600;">${data.error}</span>`;
        return;
      }
      const d = data.data;
      const headerPin = document.getElementById('headerPincodeText');
      if (headerPin) headerPin.textContent = `${d.pincode} · ${d.city}`;
      out.innerHTML = `<span style="color:#388E3C;font-weight:600;">✓ Delivery by ${d.estimated_date} to ${d.city}, ${d.state}</span> · ${d.cod_available ? 'Cash on Delivery available' : 'Prepaid only'}`;
    });
  }

  document.querySelectorAll('.cc-pdp-thumb').forEach((thumb) => {
    thumb.addEventListener('click', () => {
      const mainImg = document.getElementById('pdpMainImage');
      if (mainImg && thumb.dataset.src) {
        mainImg.src = thumb.dataset.src;
        document.querySelectorAll('.cc-pdp-thumb').forEach((t) => t.classList.remove('active'));
        thumb.classList.add('active');
      }
    });
  });

  const variantButtons = document.querySelectorAll('.cc-variant-chip');
  if (variantButtons.length) {
    const priceEl = document.getElementById('pdpDisplayPrice');
    const mrpEl = document.getElementById('pdpDisplayMrp');
    const hiddenInputs = document.querySelectorAll('.pdp-variant-input');
    const basePrice = Number(document.getElementById('pdpBasePrice')?.value || 0);
    const baseMrp = Number(document.getElementById('pdpBaseMrp')?.value || 0);

    variantButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        variantButtons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const vid = btn.dataset.variantId;
        const delta = Number(btn.dataset.priceDelta || 0);
        hiddenInputs.forEach((inp) => (inp.value = vid));
        const newPrice = Math.max(1, basePrice + delta);
        const newMrp = Math.max(newPrice, baseMrp + Math.max(0, delta));
        if (priceEl) priceEl.textContent = `₹${newPrice.toLocaleString('en-IN')}`;
        if (mrpEl) mrpEl.textContent = `₹${newMrp.toLocaleString('en-IN')}`;
      });
    });
  }

  const exchToggle = document.getElementById('pdpExchangeToggle');
  if (exchToggle) {
    exchToggle.addEventListener('change', () => {
      document.querySelectorAll('.pdp-exchange-input').forEach((inp) => {
        inp.value = exchToggle.checked ? '1' : '0';
      });
    });
  }
})();
