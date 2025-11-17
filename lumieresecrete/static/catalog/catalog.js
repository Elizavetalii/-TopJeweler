const qs = (sel, ctx=document) => ctx.querySelector(sel);
const qsa = (sel, ctx=document) => ctx.querySelectorAll(sel);
const debounce = (fn, delay=300) => { let t; return (...args) => { clearTimeout(t); t=setTimeout(()=>fn.apply(this,args), delay); }; };

const catalog = {
  init(){
    this.keepPage = false;
    this.form = qs('#catalog-filter-form');
    this.grid = qs('.js-product-grid');
    this.pagination = qs('.js-pagination');
    this.activeFiltersBox = qs('.js-active-filters');
    this.overlay = qs('[data-filters-overlay]');
    this.filtersPanel = qs('[data-filters-panel]');
    this.layout = qs('[data-catalog-layout]');
    this.desktopToggle = qs('[data-filters-toggle-desktop]');
    this.quickModal = qs('[data-quick-view]');
    this.bindEvents();
  },
  bindEvents(){
    if(!this.form) return;
    this.form.addEventListener('change', debounce(()=>this.submitFilters(),200));
    const searchInput = this.form.querySelector('[data-search-input]');
    searchInput?.addEventListener('input', debounce(()=>this.submitFilters(),400));
    this.form.querySelectorAll('[data-slider-min],[data-slider-max]').forEach(slider=>{
      slider.addEventListener('input', ()=>{
        const min = this.form.querySelector('[data-slider-min]').value;
        const max = this.form.querySelector('[data-slider-max]').value;
        this.form.querySelector('[data-price-min]').value = min;
        this.form.querySelector('[data-price-max]').value = max;
      });
      slider.addEventListener('change', ()=>this.submitFilters());
    });
    qsa('[data-accordion]').forEach(btn=>btn.addEventListener('click',()=>btn.parentElement.classList.toggle('is-open')));
    const toggle = qs('[data-filters-toggle]');
    toggle?.addEventListener('click', ()=>this.openDrawer());
    qs('[data-filters-close]')?.addEventListener('click', ()=>this.closeDrawer());
    this.overlay?.addEventListener('click', (e)=>{ if(e.target===this.overlay) this.closeDrawer(); });
    this.desktopToggle?.addEventListener('click', ()=>this.handleToggleClick());
    qsa('[data-remove-filter]').forEach(chip=>chip.addEventListener('click',()=>this.removeFilter(chip)));
    qs('[data-clear-filters]')?.addEventListener('click', ()=>{ this.form.reset(); this.submitFilters(); });
    this.bindPagination();
    const closeQuick = ()=>this.closeQuick();
    qs('[data-quick-close]')?.addEventListener('click', closeQuick);
    if(this.quickModal){
      this.quickModal.addEventListener('click',(e)=>{
        if(e.target === this.quickModal) this.closeQuick();
      });
    }
    document.addEventListener('keydown',(e)=>{
      if(e.key === 'Escape') this.closeQuick();
    });
    const mq = window.matchMedia('(max-width: 1200px)');
    if (mq.addEventListener) {
      mq.addEventListener('change', ()=>this.updateToggleLabel());
    } else if (mq.addListener) {
      mq.addListener(()=>this.updateToggleLabel());
    }
    this.updateToggleLabel();
  },
  openDrawer(){
    this.filtersPanel?.classList.add('is-open');
    this.overlay?.classList.add('is-open');
    document.body.classList.add('no-scroll');
  },
  closeDrawer(){
    this.filtersPanel?.classList.remove('is-open');
    this.overlay?.classList.remove('is-open');
    document.body.classList.remove('no-scroll');
  },
  handleToggleClick(){
    if(window.matchMedia('(max-width: 1200px)').matches){
      this.openDrawer();
      return;
    }
    if(!this.layout) return;
    this.layout.classList.toggle('is-collapsed');
    this.updateToggleLabel();
  },
  updateToggleLabel(){
    const labelEl = qs('[data-filters-toggle-label]');
    if(!labelEl) return;
    const collapsed = this.layout?.classList.contains('is-collapsed');
    labelEl.textContent = collapsed ? 'Показать фильтры' : 'Скрыть фильтры';
  },
  removeFilter(chip){
    const param = chip.dataset.param;
    const value = chip.dataset.value;
    this.form.querySelectorAll(`[name="${param}"]`).forEach(input=>{
      if(!value || input.value===value){
        if(['checkbox','radio'].includes(input.type)) input.checked=false;
        else input.value='';
      }
    });
    this.submitFilters();
  },
  async submitFilters(){
    const pageField = this.form.querySelector('input[name="page"]');
    if(pageField && !this.keepPage){
      pageField.value = 1;
    }
    this.keepPage = false;
    const formData = new FormData(this.form);
    const params = new URLSearchParams(formData);
    const url = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({},'',url);
    try {
      const response = await fetch(`${url}&partial=1`, {headers:{'X-Requested-With':'XMLHttpRequest'}});
      const data = await response.json();
      if(this.grid) this.grid.innerHTML = data.products_html;
      if(this.pagination) this.pagination.innerHTML = data.pagination_html;
      if(this.activeFiltersBox) this.activeFiltersBox.innerHTML = data.active_filters_html;
      this.bindPagination();
      this.attachQuick();
    } catch(err){ console.error('filter error', err); }
  },
  bindPagination(){
    qsa('[data-page-link]', this.pagination).forEach(link=>{
      link.addEventListener('click',(e)=>{
        e.preventDefault();
        const pageField = this.form.querySelector('input[name="page"]');
        if(pageField){
          pageField.value = link.dataset.pageLink;
          this.keepPage = true;
        }
        this.submitFilters();
      });
    });
    qsa('[data-remove-filter]', this.activeFiltersBox).forEach(chip=>chip.addEventListener('click',()=>this.removeFilter(chip)));
    this.attachQuick();
  },
  attachQuick(){
    qsa('[data-quick-view-target]').forEach(btn=>{
      btn.addEventListener('click',()=>this.openQuick(btn));
    });
  },
  closeQuick(){
    const modal = this.quickModal || qs('[data-quick-view]');
    if(modal){
      modal.classList.remove('is-open');
    }
  },
  async openQuick(btn){
    const modal = qs('[data-quick-view]');
    const body = qs('.js-quick-body');
    if(!modal || !body) return;
    modal.classList.add('is-open');
    body.innerHTML = '<p>Загрузка...</p>';
    try {
      const response = await fetch(`${btn.dataset.quickUrl}?format=json`, {headers:{'X-Requested-With':'XMLHttpRequest'}});
      const data = await response.json();
      const variants = (data.variants || []).map(v => `<li>${v.color || 'Цвет'} · ${v.size || 'Размер'} — ${v.price || '-'} ₽</li>`).join('') || '<li>Нет вариантов</li>';
      const favoriteBtn = data.favorite_url ? `
        <button
          type="button"
          class="favorite-btn favorite-btn--ghost quick-view__favorite ${data.is_favorite ? 'is-active' : ''}"
          data-favorite-toggle
          data-url="${data.favorite_url}"
          aria-pressed="${data.is_favorite ? 'true' : 'false'}"
          aria-label="${data.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное'}"
        >
          <span class="heart-icon" aria-hidden="true"></span>
        </button>` : '';
      const detailLink = data.detail_url || btn.dataset.quickUrl || '#';
      body.innerHTML = `<div class="quick-view-card">
        <div class="quick-view-card__media">
          ${favoriteBtn}
          <img src="${data.image || ''}" alt="${data.name || 'Товар'}">
        </div>
        <div class="quick-view-card__info">
          <h3>${data.name || 'Товар'}</h3>
          <ul>${variants}</ul>
          <div class="quick-view-card__actions">
            <a class="btn-primary btn-small" href="${detailLink}">Подробнее</a>
            <button type="button" class="btn-link quick-view-card__close" data-quick-close-link>Закрыть</button>
          </div>
        </div>
      </div>`;
      body.querySelector('[data-quick-close-link]')?.addEventListener('click', ()=>this.closeQuick());
    } catch(err){
      body.innerHTML = 'Не удалось загрузить';
    }
  }
};

window.addEventListener('DOMContentLoaded', ()=>catalog.init());
