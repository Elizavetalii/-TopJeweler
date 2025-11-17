(function () {
  if (!window.LumiereUI) return;
  const { fetchJSON, toast } = window.LumiereUI;

  class CheckoutUI {
    constructor(root) {
      this.root = root;
      this.form = root.querySelector('[data-checkout-form]');
      this.summary = root.querySelector('[data-checkout-summary]');
      this.countEl = root.querySelector('[data-checkout-count]');
      this.emptyMessage = root.querySelector('[data-checkout-empty]');
      this.promoInput = root.querySelector('[data-promo-input]');
      this.promoApply = root.querySelector('[data-promo-apply]');
      this.promoClear = root.querySelector('[data-promo-clear]');
      this.promoMessage = root.querySelector('[data-promo-message]');
      this.promoApplied = root.querySelector('[data-promo-applied]');
      this.promoForm = root.querySelector('[data-promo-form]');
      this.promoCodeEl = root.querySelector('[data-promo-code]');
      this.promoDiscountEl = root.querySelector('[data-promo-discount]');
      this.promoDescriptionEl = root.querySelector('[data-promo-description]');
      this.summaryEls = {
        subtotal: root.querySelector('[data-summary-subtotal]'),
        discount: root.querySelector('[data-summary-discount]'),
        discountRow: root.querySelector('[data-summary-discount-row]'),
        shipping: root.querySelector('[data-summary-shipping]'),
        total: root.querySelector('[data-summary-total]'),
      };
      this.payNowBlock = root.querySelector('[data-pay-now]');
      this.payLaterBlock = root.querySelector('[data-pay-later]');
      this.cardPreview = {
        number: root.querySelector('[data-card-preview-number]'),
        expiry: root.querySelector('[data-card-preview-expiry]'),
        holder: root.querySelector('[data-card-preview-holder]'),
      };
      this.deliveryBlock = root.querySelector('[data-delivery-block]');
      this.pickupBlock = root.querySelector('[data-pickup-block]');
      this.deliveryFields = Array.from(root.querySelectorAll('[data-delivery-field]'));
      this.pickupFields = Array.from(root.querySelectorAll('[data-pickup-field]'));
      this.cardInputs = {
        number: root.querySelector('[data-card-number]'),
        expiry: root.querySelector('[data-card-expiry]'),
        holder: root.querySelector('[data-card-holder]'),
      };
      this.cardFields = Array.from(root.querySelectorAll('[data-card-field]'));
      this.promoEndpoint = root.dataset.promoEndpoint;
    }

    init() {
      if (!this.form) return;
      this.bindShipping();
      this.bindPayment();
      this.bindCardFormatting();
      this.bindPromo();
      this.bindLines();
      this.updateCount();
    }

    bindShipping() {
      const choices = this.form.querySelectorAll('[data-shipping-choice]');
      choices.forEach((input) => {
        input.addEventListener('change', () => this.toggleShipping(input.value));
      });
      const active = Array.from(choices).find((input) => input.checked);
      this.toggleShipping(active ? active.value : 'delivery');
    }

    toggleShipping(value) {
      const isPickup = value === 'pickup';
      if (this.deliveryBlock) this.deliveryBlock.hidden = isPickup;
      if (this.pickupBlock) this.pickupBlock.hidden = !isPickup;
      this.deliveryFields.forEach((field) => {
        field.disabled = isPickup;
        if (field.dataset.required === 'true') {
          field.required = !isPickup;
        }
      });
      this.pickupFields.forEach((field) => {
        field.disabled = !isPickup;
        if (field.dataset.required === 'true') {
          field.required = isPickup;
        }
      });
    }

    bindPayment() {
      this.form.querySelectorAll('[data-payment-flow]').forEach((input) => {
        input.addEventListener('change', () => this.togglePayment(input.value));
      });
    }

    togglePayment(value) {
      const isPayNow = value !== 'later';
      if (this.payNowBlock) this.payNowBlock.hidden = !isPayNow;
      if (this.payLaterBlock) this.payLaterBlock.hidden = isPayNow;
      this.cardFields.forEach((field) => {
        field.disabled = !isPayNow;
        if (field.dataset.required === 'true') {
          field.required = isPayNow;
        }
      });
    }

    bindCardFormatting() {
      if (this.cardInputs.number) {
        this.cardInputs.number.addEventListener('input', (event) => {
          const digits = event.target.value.replace(/\D/g, '').slice(0, 19);
          const chunks = digits.match(/.{1,4}/g) || [];
          event.target.value = chunks.join(' ').trim();
          if (this.cardPreview.number) {
            this.cardPreview.number.textContent = event.target.value || '0000 0000 0000 0000';
          }
        });
      }
      if (this.cardInputs.expiry) {
        this.cardInputs.expiry.addEventListener('input', (event) => {
          let value = event.target.value.replace(/[^0-9]/g, '').slice(0, 4);
          if (value.length >= 3) {
            value = `${value.slice(0, 2)}/${value.slice(2, 4)}`;
          }
          event.target.value = value;
          if (this.cardPreview.expiry) {
            this.cardPreview.expiry.textContent = value || 'MM/YY';
          }
        });
      }
      if (this.cardInputs.holder) {
        this.cardInputs.holder.addEventListener('input', (event) => {
          event.target.value = event.target.value.toUpperCase();
          if (this.cardPreview.holder) {
            this.cardPreview.holder.textContent = event.target.value || 'IVAN IVANOV';
          }
        });
      }
    }

    bindPromo() {
      if (this.promoApply) {
        this.promoApply.addEventListener('click', () => {
          const code = (this.promoInput ? this.promoInput.value : '').trim();
          if (!code) {
            this.showPromoMessage('Введите промокод', false, true);
            this.promoInput?.focus();
            return;
          }
          this.applyPromo(code);
        });
      }
      if (this.promoClear) {
        this.promoClear.addEventListener('click', () => this.clearPromo());
      }
    }

    bindLines() {
      this.form.querySelectorAll('[data-checkout-line]').forEach((line) => this.attachLine(line));
    }

    attachLine(line) {
      line.querySelectorAll('[data-line-control]').forEach((btn) => {
        btn.addEventListener('click', () => this.handleLineStep(line, btn.dataset.lineControl));
      });
      const removeBtn = line.querySelector('[data-remove-line]');
      if (removeBtn) {
        removeBtn.addEventListener('click', () => this.removeLine(line));
      }
    }

    handleLineStep(line, type) {
      const qtyEl = line.querySelector('[data-line-qty]');
      if (!qtyEl) return;
      const current = parseInt(qtyEl.textContent, 10) || 1;
      const delta = type === 'increase' ? 1 : -1;
      const next = Math.max(1, current + delta);
      this.updateQuantity(line, next);
    }

    async updateQuantity(line, quantity) {
      const url = line.dataset.updateUrl;
      if (!url) return;
      this.setLineLoading(line, true);
      try {
        const data = await fetchJSON(url, { body: { quantity } });
        if (data.item) {
          const qtyEl = line.querySelector('[data-line-qty]');
          const totalEl = line.querySelector('[data-line-total]');
          if (qtyEl) qtyEl.textContent = data.item.quantity;
          if (totalEl) totalEl.textContent = data.item.line_total_display || '';
        }
        if (data.totals) this.updateSummary(data.totals, data.promo);
        this.updateCount();
      } catch (err) {
        console.error(err);
        toast('Не удалось обновить количество');
      } finally {
        this.setLineLoading(line, false);
      }
    }

    async removeLine(line) {
      const url = line.dataset.removeUrl;
      if (!url) {
        line.remove();
        this.updateCount();
        return;
      }
      this.setLineLoading(line, true);
      try {
        const data = await fetchJSON(url, { body: {} });
        line.remove();
        if (data.totals) this.updateSummary(data.totals, data.promo);
        this.updateCount();
      } catch (err) {
        console.error(err);
        toast('Не удалось удалить товар');
        this.setLineLoading(line, false);
      }
    }

    setLineLoading(line, isLoading) {
      line.classList.toggle('is-loading', isLoading);
      line.querySelectorAll('button').forEach((btn) => {
        btn.disabled = isLoading;
      });
    }

    async applyPromo(code) {
      if (!this.promoEndpoint) {
        this.showPromoMessage('Невозможно применить промокод.', false, true);
        return;
      }
      this.togglePromoLoading(true);
      try {
        const data = await fetchJSON(this.promoEndpoint, {
          body: { intent: 'apply', next: 'checkout', promo: code },
        });
        if (data.totals) this.updateSummary(data.totals, data.promo);
        this.updatePromoState(data.promo);
        this.showPromoMessage(data.message || 'Промокод применён', true);
      } catch (err) {
        console.error(err);
        this.showPromoMessage('Не удалось применить промокод', false, true);
      } finally {
        this.togglePromoLoading(false);
      }
    }

    async clearPromo() {
      if (!this.promoEndpoint) return;
      this.togglePromoLoading(true);
      try {
        const data = await fetchJSON(this.promoEndpoint, {
          body: { intent: 'clear', next: 'checkout' },
        });
        if (data.totals) this.updateSummary(data.totals, data.promo);
        this.updatePromoState(data.promo);
        this.showPromoMessage('Промокод удалён');
      } catch (err) {
        console.error(err);
        this.showPromoMessage('Не удалось удалить промокод', false, true);
      } finally {
        this.togglePromoLoading(false);
      }
    }

    togglePromoLoading(isLoading) {
      if (this.promoApply) this.promoApply.disabled = isLoading;
      if (this.promoClear) this.promoClear.disabled = isLoading;
    }

    updatePromoState(promo) {
      const isApplied = promo?.is_applied;
      if (this.promoApplied) this.promoApplied.hidden = !isApplied;
      if (this.promoForm) this.promoForm.hidden = Boolean(isApplied);
      if (this.promoInput && promo?.code) {
        this.promoInput.value = promo.code;
      }
      if (this.promoCodeEl) this.promoCodeEl.textContent = promo?.code || '';
      if (this.promoDiscountEl) this.promoDiscountEl.textContent = promo?.discount_display || '';
      if (this.promoDescriptionEl) this.promoDescriptionEl.textContent = promo?.description || '';
      if (promo?.message) {
        const recoverable = promo.recoverable;
        this.showPromoMessage(promo.message, false, !recoverable);
      } else if (isApplied) {
        this.showPromoMessage(`Промокод ${promo.code} применён`, true);
      } else {
        this.showPromoMessage('', false, false, true);
      }
    }

    showPromoMessage(text, success = false, isError = false, hide = false) {
      if (!this.promoMessage) return;
      if (hide || !text) {
        this.promoMessage.hidden = true;
        this.promoMessage.textContent = '';
        this.promoMessage.classList.remove('is-warning', 'is-error');
        return;
      }
      this.promoMessage.hidden = false;
      this.promoMessage.textContent = text;
      this.promoMessage.classList.toggle('is-warning', !success && !isError);
      this.promoMessage.classList.toggle('is-error', isError);
      if (success) {
        this.promoMessage.classList.remove('is-error');
      }
    }

    updateSummary(totals, promo) {
      if (!totals) return;
      if (this.summaryEls.subtotal) this.summaryEls.subtotal.textContent = totals.subtotal_display || '—';
      if (this.summaryEls.discount) this.summaryEls.discount.textContent = totals.discount_display || '—';
      if (this.summaryEls.discountRow) {
        const hasDiscount = Boolean(totals.discount_display);
        this.summaryEls.discountRow.classList.toggle('is-hidden', !hasDiscount);
      }
      if (this.summaryEls.shipping) this.summaryEls.shipping.textContent = totals.shipping_display || '—';
      if (this.summaryEls.total) this.summaryEls.total.textContent = totals.total_display || '—';
      if (promo) this.updatePromoState(promo);
    }

    updateCount() {
      const lines = Array.from(this.form.querySelectorAll('[data-checkout-line]'));
      let count = 0;
      lines.forEach((line) => {
        const qty = parseInt(line.querySelector('[data-line-qty]')?.textContent || '0', 10);
        count += Number.isFinite(qty) ? qty : 0;
      });
      if (this.countEl) {
        this.countEl.textContent = count
          ? `Выбрано ${count} ${this.formatPositions(count)}`
          : 'Нет товаров для оформления';
      }
      if (this.emptyMessage) {
        this.emptyMessage.hidden = lines.length > 0;
      }
      this.root.classList.toggle('checkout-is-empty', lines.length === 0);
    }

    formatPositions(value) {
      const n = Math.abs(value) % 100;
      const n1 = n % 10;
      if (n > 10 && n < 20) return 'позиций';
      if (n1 > 1 && n1 < 5) return 'позиции';
      if (n1 === 1) return 'позиция';
      return 'позиций';
    }
  }

  const initCheckout = () => {
    const root = document.querySelector('[data-checkout-page]');
    if (!root) return;
    const checkout = new CheckoutUI(root);
    checkout.init();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCheckout);
  } else {
    initCheckout();
  }
})();
