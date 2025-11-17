(function () {
  const root = document.querySelector('[data-order-detail]');
  if (!root || !window.LumiereUI) return;
  const { fetchJSON, toast } = window.LumiereUI;

  const shareEndpoint = root.dataset.shareEndpoint;
  const modal = document.querySelector('[data-share-modal]');

  const closeModal = () => {
    modal?.setAttribute('hidden', 'hidden');
  };

  root.querySelector('[data-share-trigger]')?.addEventListener('click', () => {
    modal?.removeAttribute('hidden');
  });
  modal?.querySelector('[data-share-close]')?.addEventListener('click', closeModal);

  modal?.querySelectorAll('[data-share-option]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!shareEndpoint) return;
      const channel = btn.dataset.shareOption;
      btn.disabled = true;
      try {
        const data = await fetchJSON(shareEndpoint, { body: { channel } });
        closeModal();
        if (navigator.share && channel !== 'email') {
          try {
            await navigator.share({ url: data.share_url, title: document.title });
            toast('Ссылка отправлена');
            return;
          } catch (err) {
            console.debug('web share fallback', err);
          }
        }
        if (channel === 'link') {
          await navigator.clipboard.writeText(data.share_url);
          toast('Ссылка скопирована');
        } else if (channel === 'email') {
          window.location.href = data.share_url;
        } else {
          window.open(data.share_url, '_blank', 'noopener');
          toast('Открыли окно для отправки');
        }
      } catch (err) {
        console.error(err);
        toast('Не удалось поделиться');
      } finally {
        btn.disabled = false;
      }
    });
  });

  root.querySelector('[data-download-receipt]')?.addEventListener('click', (event) => {
    const button = event.currentTarget;
    button?.classList.add('is-loading');
    setTimeout(() => button?.classList.remove('is-loading'), 2000);
  });
})();
