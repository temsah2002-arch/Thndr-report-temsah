/* assets/marketBar.js */
(function(){
  function money(n){ return (typeof n==='number' ? n.toFixed(2) : n) }

  function pill(label, id){
    const w = document.createElement('div');
    w.className = 'stat';
    w.style.cssText = "background:#0f1016;border-radius:8px;padding:6px 10px;flex:1;text-align:center;min-width:110px";
    w.innerHTML = `<b>${label}</b> <span id="${id}" class="pos">...</span>`;
    return w;
  }

  async function pull(){
    try{
      const r = await fetch('data/market.json?_=' + Date.now());
      const j = await r.json();
      const set = (id, pct) => {
        const el = document.getElementById(id);
        if(!el) return;
        el.textContent = (pct>=0?'+':'') + pct.toFixed(2) + '%';
        el.className = pct>=0 ? 'pos' : 'neg';
      };
      set('egx30_val', j.egx30.chg_pct);
      set('egx70_val', j.egx70.chg_pct);
      const usd = document.getElementById('usd_val');
      if(usd) usd.textContent = money(j.usd_egp) + ' ج';
    }catch(e){ console.warn('market.json error', e); }
  }

  // Public API
  window.renderMarketBar = function(targetId){
    const host = document.getElementById(targetId);
    if(!host) return;

    // style helpers (pos/neg)
    const style = document.createElement('style');
    style.textContent = `.pos{color:#26d07c;font-weight:700}.neg{color:#ff6961;font-weight:700}`;
    document.head.appendChild(style);

    host.style.display='flex';
    host.style.gap='10px';
    host.style.flexWrap='wrap';
    host.appendChild(pill('EGX30:', 'egx30_val'));
    host.appendChild(pill('EGX70:', 'egx70_val'));
    const usdWrap = document.createElement('div');
    usdWrap.className='stat';
    usdWrap.style.cssText="background:#0f1016;border-radius:8px;padding:6px 10px;flex:1;text-align:center;min-width:110px";
    usdWrap.innerHTML = `<b>الدولار:</b> <span id="usd_val">--.-- ج</span>`;
    host.appendChild(usdWrap);

    pull();
    setInterval(pull, 5*60*1000); // كل 5 دقائق
  }
})();
