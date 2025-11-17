(function () {
  if (!window.LumiereUI) return;
  const { fetchJSON, toast } = window.LumiereUI;

  const broadcastWishlist = () => {
    try {
      localStorage.setItem('wishlist-sync', String(Date.now()));
    } catch (err) {
      console.debug('wishlist sync broadcast failed', err);
    }
  };

  const CartUI = {
    init() {
      this.root = document.querySelector('[data-cart-page]');
      if (!this.root) return;
      this.undoUrl = this.root.dataset.undoUrl;
      this.discountRow = this.root.querySelector('[data-discount-row]');
      this.discountLabel = this.root.querySelector('[data-discount-label]');
      this.discountValue = this.root.querySelector('[data-discount]');
      this.promoInput = this.root.querySelector('[data-promo-input]');
      this.promoMessage = this.root.querySelector('[data-promo-message]');
      this.promoRemove = this.root.querySelector('[data-promo-remove]');
      this.bindLines();
    },
    bindLines() {
      this.root.querySelectorAll('[data-cart-item]').forEach((item) => {
        this.attachLine(item);
      });
      this.root.querySelectorAll('[data-remove-line]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const line = btn.closest('[data-cart-item]');
          line && this.removeLine(line);
        });
      });
    },
    attachLine(item) {
      item.querySelector('[data-step-down]')?.addEventListener('click', () => this.changeQty(item, -1));
      item.querySelector('[data-step-up]')?.addEventListener('click', () => this.changeQty(item, 1));
      item.querySelector('[data-qty-input]')?.addEventListener('change', (e) => {
        const value = Math.max(1, parseInt(e.target.value, 10) || 1);
        e.target.value = value;
        this.saveQty(item, value);
      });
    },
    changeQty(item, delta) {
      const input = item.querySelector('[data-qty-input]');
      const next = Math.max(1, (parseInt(input.value, 10) || 1) + delta);
      input.value = next;
      this.saveQty(item, next);
    },
    async saveQty(item, quantity) {
      try {
        const data = await fetchJSON(item.dataset.updateUrl, { body: { quantity } });
        if (data.item && item.querySelector('[data-line-total]')) {
          item.querySelector('[data-line-total]').textContent = data.item.line_total_display;
        }
        if (data.totals) this.updateTotals(data.totals, data.promo);
      } catch (err) {
        console.error(err);
        toast('Не удалось обновить количество');
      }
    },
    async removeLine(item) {
      item.classList.add('is-removing');
      try {
        const data = await fetchJSON(item.dataset.removeUrl, { body: {} });
        setTimeout(() => item.remove(), 180);
        if (data.totals) this.updateTotals(data.totals, data.promo);
        if (data.undo_token && this.undoUrl) {
          toast('Товар удалён', {
            actionLabel: 'Отменить',
            onAction: () => this.undo(data.undo_token),
          });
        }
      } catch (err) {
        console.error(err);
        item.classList.remove('is-removing');
        toast('Не удалось удалить товар');
      }
    },
    async undo(token) {
      if (!this.undoUrl) return;
      try {
        await fetchJSON(this.undoUrl, { body: { token } });
        window.location.reload();
      } catch (err) {
        console.error(err);
        toast('Не удалось вернуть товар');
      }
    },
    updateTotals(totals, promo) {
      this.root.querySelectorAll('[data-subtotal]').forEach((el) => {
        el.textContent = totals.subtotal_display;
      });
      this.root.querySelectorAll('[data-shipping]').forEach((el) => {
        el.textContent = totals.shipping_display;
      });
      this.root.querySelectorAll('[data-total]').forEach((el) => {
        el.textContent = totals.total_display;
      });
      if (this.discountValue) {
        this.discountValue.textContent = totals.discount_display || '';
      }
      if (this.discountRow) {
        this.discountRow.classList.toggle('is-hidden', !totals.discount_display);
      }
      this.updatePromo(promo);
    },
    updatePromo(promo) {
      if (!promo) return;
      if (this.promoInput && typeof promo.code === 'string') {
        this.promoInput.value = promo.code || '';
      }
      if (this.discountLabel) {
        this.discountLabel.textContent = promo.code ? `Скидка (${promo.code})` : 'Скидка';
      }
      if (this.promoRemove) {
        this.promoRemove.classList.toggle('is-hidden', !promo.code);
      }
      if (this.promoMessage) {
        let text = '';
        let success = false;
        if (promo.message) {
          text = promo.message;
        } else if (promo.is_applied && promo.discount_display) {
          text = `Скидка ${promo.discount_display} активна.`;
          success = true;
        } else if (promo.code) {
          const minTotal = promo.min_total_display ? `, он применится от ${promo.min_total_display}` : '';
          text = `Промокод сохранён${minTotal}.`;
        }
        if (text) {
          this.promoMessage.textContent = text;
          this.promoMessage.hidden = false;
          this.promoMessage.classList.toggle('promo-hint--success', success);
        } else {
          this.promoMessage.textContent = '';
          this.promoMessage.hidden = true;
          this.promoMessage.classList.remove('promo-hint--success');
        }
      }
    },
  };

  const WishlistUI = {
    init() {
      this.page = document.querySelector('[data-wishlist-page]');
      this.grid = document.querySelector('[data-wishlist-grid]');
      if (!this.page || !this.grid) return;
      this.cartUrl = this.grid.dataset.cartUrl;
      this.loginUrl = this.grid.dataset.loginUrl;
      this.bulkUrl = this.grid.dataset.bulkUrl;
      this.clearUrl = this.grid.dataset.clearUrl;
      this.canCheckout = this.grid.dataset.canCheckout === 'true';
      this.countEl = document.querySelector('[data-wishlist-count]');
      this.count = this.countEl ? parseInt(this.countEl.textContent.replace(/\D/g, ''), 10) || 0 : 0;
      this.removedBuffer = new Map();
      this.bindFilters();
      this.bindCards();
      this.bindBulkAction();
      window.addEventListener('storage', (event) => {
        if (event.key === 'wishlist-sync') {
          window.location.reload();
        }
      });
    },
    bindFilters() {
      const form = document.getElementById('wishlistFilters');
      if (!form) return;
      form.querySelectorAll('select').forEach((select) => {
        select.addEventListener('change', () => form.submit());
      });
      form.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
        checkbox.addEventListener('change', () => form.submit());
      });
    },
    bindCards() {
      this.grid.querySelectorAll('[data-wishlist-card]').forEach((card) => {
        card.querySelector('[data-wishlist-add-cart]')?.addEventListener('click', (event) => {
          event.preventDefault();
          this.addToCart(card);
        });
        card.querySelector('[data-remove-item]')?.addEventListener('click', (event) => {
          event.preventDefault();
          this.removeCard(card);
        });
        card.querySelector('[data-favorite-toggle]')?.addEventListener('click', (event) => {
          event.preventDefault();
          this.removeCard(card);
        });
      });
    },
    bindBulkAction() {
      const btn = this.page.querySelector('[data-wishlist-add-all]');
      if (!btn) return;
      btn.addEventListener('click', async () => {
        if (!this.bulkUrl) {
          if (this.loginUrl) window.location.href = this.loginUrl;
          return;
        }
        btn.disabled = true;
        btn.textContent = 'Добавляем...';
        try {
          const data = await fetchJSON(this.bulkUrl, { body: {} });
          this.clearGrid();
          const added = data?.added || 0;
          const total = data?.total || 0;
          this.updateCount(-this.count);
          broadcastWishlist();
          toast(`Добавлено ${added} из ${total}.`, {
            actionLabel: 'Перейти в корзину',
            onAction: () => (window.location.href = '/cart/view/'),
          });
        } catch (err) {
          console.error(err);
          toast('Не удалось добавить всё в корзину');
        } finally {
          btn.textContent = 'Добавить всё в корзину';
          btn.disabled = false;
        }
      });
    },
    async addToCart(card) {
      if (!this.canCheckout) {
        if (this.loginUrl) window.location.href = this.loginUrl;
        return;
      }
      if (!this.cartUrl) return;
      const variant = card.dataset.variantId;
      if (!variant) return;
      const button = card.querySelector('[data-wishlist-add-cart]');
      button && (button.disabled = true);
      try {
        await fetchJSON(this.cartUrl, { body: { product_variant_id: variant, quantity: 1 } });
        toast('Товар добавлен в корзину');
        await this.removeCard(card, { quiet: true });
      } catch (err) {
        console.error(err);
        toast('Не удалось добавить в корзину');
        button && (button.disabled = false);
      }
    },
    async removeCard(card, options = {}) {
      const url = card.dataset.favoriteUrl;
      const productId = card.dataset.productId;
      if (!url || !productId) return;
      const entry = this.captureCard(card);
      card.classList.add('is-removing');
      setTimeout(() => card.remove(), 160);
      try {
        await fetchJSON(url, { body: {} });
        if (!options.quiet) {
          this.removedBuffer.set(productId, entry);
          entry.timeout = setTimeout(() => this.removedBuffer.delete(productId), 7000);
          toast('Удалено из избранного', {
            actionLabel: 'Отменить',
            onAction: () => this.undoRemove(productId),
          });
        }
        this.updateCount(-1);
        broadcastWishlist();
      } catch (err) {
        console.error(err);
        this.restoreCard(entry);
        toast('Не удалось обновить избранное');
      }
    },
    captureCard(card) {
      return {
        card,
        parent: card.parentNode,
        nextSibling: card.nextElementSibling,
      };
    },
    restoreCard(entry) {
      if (!entry || !entry.parent) return;
      if (entry.nextSibling && entry.nextSibling.parentNode === entry.parent) {
        entry.parent.insertBefore(entry.card, entry.nextSibling);
      } else {
        entry.parent.appendChild(entry.card);
      }
      entry.card.classList.remove('is-removing');
    },
    async undoRemove(productId) {
      const entry = this.removedBuffer.get(productId);
      if (!entry) return;
      clearTimeout(entry.timeout);
      try {
        await fetchJSON(entry.card.dataset.favoriteUrl, { body: {} });
        this.restoreCard(entry);
        this.updateCount(1);
        broadcastWishlist();
      } catch (err) {
        console.error(err);
        toast('Не удалось вернуть товар');
      } finally {
        this.removedBuffer.delete(productId);
      }
    },
    clearGrid() {
      this.grid.querySelectorAll('[data-wishlist-card]').forEach((card) => card.remove());
      this.removedBuffer.clear();
    },
    updateCount(delta) {
      this.count = Math.max(0, this.count + delta);
      if (this.countEl) {
        this.countEl.textContent = `(${this.count})`;
      }
    },
  };

  document.addEventListener('DOMContentLoaded', () => {
    CartUI.init();
    WishlistUI.init();
  });
})();
