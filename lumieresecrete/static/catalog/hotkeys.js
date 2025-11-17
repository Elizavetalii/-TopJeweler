(() => {
  const config = window.hotkeyConfig || {};
  const searchSelector = "[data-hotkey-search]";
  const cheatSheet = document.querySelector("[data-hotkey-cheatsheet]");
  const closeBtn = cheatSheet?.querySelector("[data-hotkey-close]");

  const openUrl = (url) => {
    if (url) {
      window.location.href = url;
    } else {
      toggleCheatsheet(true);
    }
  };

  const focusSearch = () => {
    const input = document.querySelector(searchSelector);
    if (input) {
      input.focus();
      if (typeof input.select === "function") {
        input.select();
      }
    } else {
      toggleCheatsheet(true);
    }
  };

  const toggleCheatsheet = (force) => {
    if (!cheatSheet) {
      return;
    }
    const nextState = typeof force === "boolean" ? force : cheatSheet.hasAttribute("hidden");
    if (nextState) {
      cheatSheet.removeAttribute("hidden");
      cheatSheet.setAttribute("aria-hidden", "false");
    } else {
      cheatSheet.setAttribute("hidden", "");
      cheatSheet.setAttribute("aria-hidden", "true");
    }
  };

  const handlers = {
    f: focusSearch,
    l: () => openUrl(config.catalogUrl),
    a: () => openUrl(config.favoritesUrl),
    c: () => openUrl(config.cartUrl),
    o: () => openUrl(config.ordersUrl),
    p: () => openUrl(config.profileUrl),
    m: () => openUrl(config.managerUrl),
    s: () => openUrl(config.managerStatsUrl),
    r: () => openUrl(config.managerReviewsUrl),
    b: () => openUrl(config.backupUrl),
    d: () => openUrl(config.adminUrl),
    h: () => toggleCheatsheet(),
  };

  document.addEventListener("keydown", (event) => {
    if (event.defaultPrevented) {
      return;
    }
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    if (event.shiftKey === false || event.altKey) {
      return;
    }
    if (isMac) {
      if (!event.metaKey) {
        return;
      }
    } else if (!event.ctrlKey) {
      return;
    }
    const key = event.key.toLowerCase();
    const handler = handlers[key];
    if (handler) {
      event.preventDefault();
      handler();
    }
  });

  closeBtn?.addEventListener("click", () => toggleCheatsheet(false));
  cheatSheet?.addEventListener("click", (event) => {
    if (event.target === cheatSheet) {
      toggleCheatsheet(false);
    }
  });
})();
