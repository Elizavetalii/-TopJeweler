(function () {
  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  };

  const fetchJSON = async (url, options = {}) => {
    const opts = { method: 'POST', headers: {}, ...options };
    opts.headers = {
      'X-Requested-With': 'XMLHttpRequest',
      'Content-Type': 'application/json',
      ...opts.headers,
    };
    if (!('X-CSRFToken' in opts.headers)) {
      opts.headers['X-CSRFToken'] = getCookie('csrftoken');
    }
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
    }
    const response = await fetch(url, opts);
    if (!response.ok) {
      throw new Error('Request failed');
    }
    return response.json();
  };

  const toastStack = document.createElement('div');
  toastStack.className = 'toast-stack';
  const mountToastStack = () => {
    if (!document.body.contains(toastStack)) {
      document.body.appendChild(toastStack);
    }
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountToastStack);
  } else {
    mountToastStack();
  }

  const toast = (message, options = {}) => {
    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    const msg = document.createElement('span');
    msg.textContent = message;
    toastEl.appendChild(msg);
    if (options.actionLabel && typeof options.onAction === 'function') {
      const actionBtn = document.createElement('button');
      actionBtn.type = 'button';
      actionBtn.textContent = options.actionLabel;
      actionBtn.addEventListener('click', () => {
        options.onAction();
        toastEl.remove();
      });
      toastEl.appendChild(actionBtn);
    }
    toastStack.appendChild(toastEl);
    setTimeout(() => {
      toastEl.classList.add('is-visible');
    }, 10);
    setTimeout(() => {
      toastEl.remove();
    }, options.duration || 4000);
  };

  const handleFavoriteClick = (event) => {
    const btn = event.target.closest('[data-favorite-toggle]');
    if (!btn) return;
    if (btn.dataset.manualFavorite === 'true') return;
    event.preventDefault();
    if (btn.dataset.loading === 'true') return;
    const url = btn.dataset.url;
    if (!url) return;
    btn.dataset.loading = 'true';
    fetchJSON(url, { method: 'POST' })
      .then((data) => {
        const isAdded = data.state === 'added';
        btn.classList.toggle('is-active', isAdded);
        btn.setAttribute('aria-pressed', isAdded ? 'true' : 'false');
        toast(isAdded ? 'Добавлено в избранное' : 'Удалено из избранного');
      })
      .catch(() => {
        toast('Не удалось обновить избранное');
      })
      .finally(() => {
        btn.dataset.loading = 'false';
      });
  };

  document.addEventListener('click', handleFavoriteClick);

  window.LumiereUI = {
    getCookie,
    fetchJSON,
    toast,
  };
})();
