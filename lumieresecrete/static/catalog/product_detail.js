(function () {
  const detail = document.querySelector('[data-product-detail]');
  if (!detail || !window.LumiereUI) return;

  const { fetchJSON, toast } = window.LumiereUI;
  const variantsDataEl = document.getElementById('variant-data');
  const rawVariants = variantsDataEl ? JSON.parse(variantsDataEl.textContent || '[]') : [];
  if (!rawVariants.length) return;

  const toKey = (value) => (value === null || value === undefined ? null : String(value));
  const toStoreKey = (variant) => {
    if (variant.store_key !== undefined && variant.store_key !== null) {
      return String(variant.store_key);
    }
    if (variant.store_id !== undefined && variant.store_id !== null) {
      return String(variant.store_id);
    }
    if (variant.store) {
      return `name:${variant.store.toLowerCase().trim()}`;
    }
    return null;
  };
  const variants = rawVariants.map((variant) => ({
    ...variant,
    color_id: toKey(variant.color_id),
    size_id: toKey(variant.size_id),
    store_key: toStoreKey(variant),
  }));

  let currentVariant =
    variants.find((variant) => String(variant.id) === detail.dataset.selectedVariant) || variants[0];
  let currentColor = currentVariant ? currentVariant.color_id : null;
  let currentSize = currentVariant ? currentVariant.size_id : null;
  let currentStore = currentVariant ? currentVariant.store_key || null : null;

  const priceDisplay = detail.querySelector('[data-price-display]');
  const stickyPrice = detail.querySelector('[data-sticky-price]');
  const stockHint = detail.querySelector('[data-stock-hint]');
  const variantInput = detail.querySelector('[data-variant-input]');
  const colorLabel = detail.querySelector('[data-color-label]');
  const sizeLabel = detail.querySelector('[data-size-label]');
  const storeLabel = detail.querySelector('[data-store-label]');
  const mainImage = detail.querySelector('[data-gallery-main]');
  const thumbsContainer = detail.querySelector('[data-gallery-thumbs]');
  const thumbsWrapper = detail.querySelector('[data-thumb-track]') || thumbsContainer;
  const thumbPrev = detail.querySelector('[data-thumb-prev]');
  const thumbNext = detail.querySelector('[data-thumb-next]');
  const messageEl = detail.querySelector('[data-form-message]');
  const qtyInput = detail.querySelector('[data-qty-input]');
  const quantityPanel = detail.querySelector('[data-quantity-panel]');
  const addToCartBtn = detail.querySelector('[data-add-to-cart]');
  const cartUpdateTemplate = detail.dataset.cartUpdateTemplate || '';
  let cartItemId = null;
  const specNodes = {
    structure: detail.querySelector('[data-spec="structure"]'),
    store: detail.querySelector('[data-spec="store"]'),
  };
  const specDefaults = Object.fromEntries(
    Object.entries(specNodes).map(([key, node]) => [key, node ? node.textContent.trim() : ''])
  );
  const charNodes = {
    size: detail.querySelector('[data-char="size"]'),
    material: detail.querySelector('[data-char="material"]'),
    color: detail.querySelector('[data-char="color"]'),
  };
  const charDefaults = Object.fromEntries(
    Object.entries(charNodes).map(([key, node]) => [key, node ? node.textContent.trim() : ''])
  );
  const cartUrl = detail.dataset.cartUrl;
  const loginUrl = detail.dataset.loginUrl;
  const colorButtons = [...detail.querySelectorAll('[data-color-id]')];
  const sizeButtons = [...detail.querySelectorAll('[data-size-id]')];
  const storeButtons = [...detail.querySelectorAll('[data-store-key]')];
  const fallbackGalleryEl = document.getElementById('product-gallery-fallback');
  const fallbackGallery = fallbackGalleryEl ? JSON.parse(fallbackGalleryEl.textContent || '[]') : [];
  if (!fallbackGallery.length && mainImage && mainImage.src) {
    fallbackGallery.push({ url: mainImage.src, alt: mainImage.alt || '' });
  }

  const updateThumbNav = () => {
    if (!thumbsWrapper || !thumbPrev || !thumbNext) return;
    const hasOverflow = thumbsWrapper.scrollHeight - 2 > thumbsWrapper.clientHeight;
    thumbPrev.classList.toggle('is-hidden', !hasOverflow);
    thumbNext.classList.toggle('is-hidden', !hasOverflow);
    if (!hasOverflow) return;
    thumbPrev.disabled = thumbsWrapper.scrollTop <= 4;
    const maxScroll = thumbsWrapper.scrollHeight - thumbsWrapper.clientHeight - 4;
    thumbNext.disabled = thumbsWrapper.scrollTop >= maxScroll;
  };

  const scrollThumbs = (direction) => {
    if (!thumbsWrapper) return;
    const amount = thumbsWrapper.clientHeight * 0.8 || 240;
    thumbsWrapper.scrollBy({ top: direction * amount, behavior: 'smooth' });
  };
  const showQuantityPanel = (quantity) => {
    if (!quantityPanel) return;
    quantityPanel.classList.remove('is-hidden');
    addToCartBtn?.setAttribute('hidden', 'hidden');
    qtyInput.value = quantity;
  };

  const hideQuantityPanel = () => {
    if (!quantityPanel) return;
    quantityPanel.classList.add('is-hidden');
    addToCartBtn?.removeAttribute('hidden');
    qtyInput.value = 1;
    cartItemId = null;
  };

  const buildUpdateUrl = () => {
    if (!cartUpdateTemplate || cartItemId === null) return null;
    return cartUpdateTemplate.replace(/0\/?$/, `${cartItemId}/`);
  };

  const syncCartQuantity = (quantity) => {
    if (!cartItemId) return Promise.resolve();
    const url = buildUpdateUrl();
    if (!url) return Promise.resolve();
    return fetchJSON(url, { body: { quantity } }).catch((err) => {
      console.error(err);
      messageEl && (messageEl.textContent = 'Не удалось обновить количество.');
      throw err;
    });
  };

  const setColorLabel = (text) => {
    if (colorLabel) colorLabel.textContent = text || '';
  };
  const setSizeLabel = (text) => {
    if (sizeLabel) sizeLabel.textContent = text || '';
  };
  const setStoreLabel = (text) => {
    if (storeLabel) storeLabel.textContent = text || '';
  };

  const updateSizeStates = () => {
    if (!sizeButtons.length) return;
    const relevant = currentColor
      ? variants.filter((variant) => variant.color_id === currentColor)
      : variants;
    const availableIds = new Set(relevant.map((variant) => variant.size_id));
    sizeButtons.forEach((button) => {
      const available = availableIds.has(button.dataset.sizeId);
      button.disabled = !available;
      button.classList.toggle('is-disabled', !available);
    });
  };

  const updateColorStates = () => {
    if (!colorButtons.length) return;
    const relevant = currentSize
      ? variants.filter((variant) => variant.size_id === currentSize)
      : variants;
    const availableIds = new Set(relevant.map((variant) => variant.color_id));
    colorButtons.forEach((button) => {
      const available = availableIds.has(button.dataset.colorId);
      button.dataset.available = available ? 'true' : 'false';
      button.classList.toggle('is-disabled', !available);
    });
  };

  const updateStoreStates = () => {
    if (!storeButtons.length) return;
    const relevant = variants.filter((variant) => {
      if (currentColor && variant.color_id !== currentColor) return false;
      if (currentSize && variant.size_id !== currentSize) return false;
      return true;
    });
    const hasRelevant = relevant.length > 0;
    const availableKeys = new Set(relevant.map((variant) => variant.store_key).filter(Boolean));
    storeButtons.forEach((button) => {
      const key = button.dataset.storeKey || null;
      const available = !hasRelevant || availableKeys.has(key);
      button.disabled = !available;
      button.classList.toggle('is-disabled', !available);
    });
  };

  const setMainImage = (image) => {
    if (!mainImage || !image) return;
    const url = typeof image === 'string' ? image : image.url;
    if (url) {
      mainImage.src = url;
    }
    if (typeof image === 'object' && image.alt) {
      mainImage.alt = image.alt;
    }
  };

  const renderGallery = (images) => {
    if (!thumbsWrapper) return;
    const list = images && images.length ? images : fallbackGallery;
    if (!list.length) return;
    thumbsWrapper.innerHTML = '';
    thumbsWrapper.scrollTop = 0;
    list.forEach((image, index) => {
      if (!image.url) return;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `gallery-thumb${index === 0 ? ' is-active' : ''}`;
      button.dataset.galleryThumb = '1';
      button.dataset.src = image.url;
      button.innerHTML = `<img src=\"${image.url}\" alt=\"${image.alt || ''}\">`;
      button.addEventListener('click', () => {
        thumbsWrapper.querySelectorAll('.gallery-thumb').forEach((thumb) => thumb.classList.remove('is-active'));
        button.classList.add('is-active');
        setMainImage(image);
      });
      thumbsWrapper.appendChild(button);
    });
    setMainImage(list[0]);
    updateThumbNav();
  };

  const updateVariantMeta = (variant) => {
    if (!variant) return;
    if (specNodes.structure) {
      specNodes.structure.textContent = variant.structure || specDefaults.structure;
    }
    if (specNodes.store) {
      specNodes.store.textContent = variant.store || specDefaults.store;
    }
    if (charNodes.size) {
      charNodes.size.textContent = variant.size_label || charDefaults.size;
    }
    if (charNodes.material) {
      charNodes.material.textContent = variant.structure || charDefaults.material;
    }
    if (charNodes.color) {
      charNodes.color.textContent = variant.color_name || charDefaults.color;
    }
  };

  const setActiveVariant = (variant) => {
    if (!variant) return;
    if (quantityPanel && !quantityPanel.hidden) {
      hideQuantityPanel();
    }
    currentVariant = variant;
    currentColor = variant.color_id;
    currentSize = variant.size_id;
    currentStore = variant.store_key || null;
    if (variantInput) variantInput.value = variant.id;
    if (priceDisplay) {
      priceDisplay.textContent = variant.price ? `${variant.price} ₽` : 'Цена уточняется';
    }
    if (stickyPrice) {
      stickyPrice.textContent = variant.price ? `${variant.price} ₽` : 'Цена уточняется';
    }
    setColorLabel(variant.color_name);
    setSizeLabel(variant.size_label);
    setStoreLabel(variant.store);
    if (stockHint) {
      stockHint.textContent = variant.is_available ? 'В наличии' : 'Нет в наличии';
    }
    renderGallery(variant.images);
    colorButtons.forEach((button) => {
      button.classList.toggle('is-active', button.dataset.colorId === variant.color_id);
    });
    sizeButtons.forEach((button) => {
      button.classList.toggle('is-active', button.dataset.sizeId === variant.size_id);
    });
    storeButtons.forEach((button) => {
      button.classList.toggle('is-active', button.dataset.storeKey === currentStore);
    });
    updateSizeStates();
    updateColorStates();
    updateStoreStates();
    updateVariantMeta(variant);
  };

  const findVariant = (colorId, sizeId, storeKey) => {
    const matchAll = variants.find(
      (entry) =>
        (!colorId || entry.color_id === colorId) &&
        (!sizeId || entry.size_id === sizeId) &&
        (!storeKey || entry.store_key === storeKey)
    );
    if (matchAll) return matchAll;
    if (colorId && sizeId) {
      const byColorSize = variants.find(
        (entry) => entry.color_id === colorId && entry.size_id === sizeId
      );
      if (byColorSize) return byColorSize;
    }
    if (storeKey) {
      const byStore = variants.find((entry) => entry.store_key === storeKey);
      if (byStore) return byStore;
    }
    if (colorId) {
      const byColor = variants.find((entry) => entry.color_id === colorId);
      if (byColor) return byColor;
    }
    if (sizeId) {
      const bySize = variants.find((entry) => entry.size_id === sizeId);
      if (bySize) return bySize;
    }
    return variants[0];
  };

  colorButtons.forEach((button) => {
    button.addEventListener('click', () => {
      if (button.classList.contains('is-disabled')) return;
      if (button.dataset.available === 'false') return;
      currentColor = button.dataset.colorId;
      updateSizeStates();
      setActiveVariant(findVariant(currentColor, currentSize, currentStore));
    });
  });

  sizeButtons.forEach((button) => {
    button.addEventListener('click', () => {
      if (button.classList.contains('is-disabled')) return;
      currentSize = button.dataset.sizeId;
      updateColorStates();
      setActiveVariant(findVariant(currentColor, currentSize, currentStore));
    });
  });

  storeButtons.forEach((button) => {
    button.addEventListener('click', () => {
      if (button.classList.contains('is-disabled')) return;
      currentStore = button.dataset.storeKey || null;
      setActiveVariant(findVariant(currentColor, currentSize, currentStore));
    });
  });

  thumbPrev?.addEventListener('click', () => scrollThumbs(-1));
  thumbNext?.addEventListener('click', () => scrollThumbs(1));
  thumbsWrapper?.addEventListener('scroll', updateThumbNav);

  const adjustQuantity = (delta) => {
    if (!quantityPanel || quantityPanel.classList.contains('is-hidden')) return;
    const current = parseInt(qtyInput.value, 10) || 1;
    const next = Math.max(0, current + delta);
    if (next === 0) {
      const promise = syncCartQuantity(0);
      if (promise && promise.finally) {
        promise.finally(() => hideQuantityPanel());
      } else {
        hideQuantityPanel();
      }
      return;
    }
    qtyInput.value = next;
    syncCartQuantity(next);
  };

  quantityPanel?.querySelector('[data-step-down]')?.addEventListener('click', () => adjustQuantity(-1));
  quantityPanel?.querySelector('[data-step-up]')?.addEventListener('click', () => adjustQuantity(1));


  const addToCart = async () => {
    if (!detail.dataset.canAdd || detail.dataset.canAdd === 'false') {
      window.location.href = loginUrl;
      return;
    }
    if (!currentVariant) {
      toast('Выберите вариант');
      return;
    }
    const quantity = Math.max(1, parseInt(qtyInput.value, 10) || 1);
    const payload = { product_variant_id: currentVariant.id, quantity };
    const addBtn = detail.querySelector('[data-add-to-cart]');
    const stickyBtn = detail.querySelector('[data-sticky-add]');
    addBtn && (addBtn.dataset.loading = 'true');
    stickyBtn && (stickyBtn.dataset.loading = 'true');
    messageEl && (messageEl.textContent = 'Добавляем в корзину…');
    try {
      const data = await fetchJSON(cartUrl, { body: payload });
      cartItemId = data?.id ?? cartItemId;
      const serverQty = data?.quantity ?? quantity;
      messageEl && (messageEl.textContent = 'Готово! Украшение в корзине.');
      toast('Добавили в корзину');
      showQuantityPanel(serverQty);
    } catch (err) {
      console.error(err);
      messageEl && (messageEl.textContent = 'Не удалось добавить в корзину.');
      toast('Ошибка при добавлении');
    } finally {
      addBtn && (addBtn.dataset.loading = 'false');
      stickyBtn && (stickyBtn.dataset.loading = 'false');
    }
  };

  detail.querySelector('[data-add-to-cart]')?.addEventListener('click', addToCart);
  detail.querySelector('[data-sticky-add]')?.addEventListener('click', addToCart);

  setActiveVariant(currentVariant);
  updateSizeStates();
  updateColorStates();
  updateStoreStates();
  if (!currentVariant || !currentVariant.images || !currentVariant.images.length) {
    renderGallery(fallbackGallery);
  }
})();
