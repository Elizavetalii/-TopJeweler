/* Minimal theme sync across admin and site
 * Uses a single localStorage key: ls-theme
 * Applies both: <html data-theme="dark|light"> and body/html class pref-theme-dark
 */
(function(){
  var KEY = 'ls-theme';
  function apply(theme){
    try{
      var root = document.documentElement;
      root.dataset.theme = theme || 'light';
      var dark = theme === 'dark';
      root.classList.toggle('pref-theme-dark', dark);
      root.classList.remove('pref-theme-light');
      if(document.body){
        document.body.classList.toggle('pref-theme-dark', dark);
        document.body.classList.remove('pref-theme-light');
      }
    }catch(e){/* no-op */}
  }
  function get(){
    try{ return localStorage.getItem(KEY) || 'light'; }catch(e){ return 'light'; }
  }
  function set(theme){
    try{ localStorage.setItem(KEY, theme); }catch(e){}
    apply(theme);
    try{ window.dispatchEvent(new CustomEvent('themechange', { detail: theme })); }catch(e){}
  }
  function toggle(){ set(get()==='dark' ? 'light' : 'dark'); }

  // Apply ASAP
  apply(get());

  // Cross-tab sync
  try{
    window.addEventListener('storage', function(ev){
      if(ev.key === KEY){ apply(ev.newValue || 'light'); }
    });
  }catch(e){}

  // Expose API
  window.Theme = { get:get, set:set, toggle:toggle, apply:apply };
})();

