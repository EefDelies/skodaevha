/* Ennie dashboard-functies. Plaats in /config/www/ennie-dashboard.js en
 * registreer als dashboard-resource (JavaScript-module):
 *   /local/ennie-dashboard.js?v=1
 *
 * Inhoud:
 * - custom:ennie-pdf-button   kaart die de declaratie maakt en de PDF opent
 * - window.enniePopup()       uitleg-pop-up achter de i-iconen op de tegels
 * - window.ennieRitPopup()    invulvenster voor een zakelijke rit
 */
class EnniePdfButton extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (this.shadowRoot) return;
    const root = this.attachShadow({ mode: 'open' });
    const button = document.createElement('button');
    button.type = 'button';
    button.className = config.variant === 'wide' ? 'wide' : 'laptop';
    button.innerHTML = '<ha-icon icon="mdi:file-pdf-box"></ha-icon><span>PDF-declaratie maken</span>';
    button.addEventListener('click', () => this._generate(button));
    const style = document.createElement('style');
    style.textContent = `
      :host { display: block; width: 100%; }
      button { box-sizing: border-box; width: 100%; height: 44px; display: flex;
        align-items: center; justify-content: center; gap: 8px; padding: 6px 12px;
        border-radius: 12px; border: 1px solid var(--ec-175a47, #175a47);
        background: linear-gradient(145deg, var(--ec-09271f, #09271f), var(--ec-0c3327, #0c3327));
        color: var(--ec-eafff2, #eafff2); font: 600 14px/1.3 var(--primary-font-family, sans-serif);
        cursor: pointer; text-align: center; }
      button.laptop { background: var(--ec-103c2c, #103c2c); border-color: var(--ec-276b4c, #276b4c); }
      button:hover { filter: brightness(1.12); }
      button:disabled { opacity: .7; cursor: wait; }
      ha-icon { --mdc-icon-size: 20px; color: var(--ec-40e697, #40e697); flex: none; }
    `;
    root.append(style, button);
  }

  set hass(value) { this._hass = value; }

  async _generate(button) {
    if (!this._hass || button.disabled) return;
    const from = this._hass.states['input_datetime.ennie_kosten_van']?.state?.slice(0, 10);
    const to = this._hass.states['input_datetime.ennie_kosten_tot']?.state?.slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(from || '') ||
        !/^\d{4}-\d{2}-\d{2}$/.test(to || '') || from > to) {
      alert('Selecteer eerst een geldige begin- en einddatum.');
      return;
    }
    // Open het tabblad direct tijdens de klik om pop-upblokkering te voorkomen.
    const pdfTab = window.open('about:blank', '_blank');
    if (!pdfTab) {
      alert('Je browser blokkeert nieuwe tabbladen. Sta pop-ups toe voor Home Assistant en probeer opnieuw.');
      return;
    }
    pdfTab.document.title = 'Ennie PDF-declaratie wordt gemaakt';
    pdfTab.document.body.textContent = 'De PDF-declaratie wordt gemaakt…';
    button.disabled = true;
    const label = button.querySelector('span');
    label.textContent = 'PDF wordt gemaakt…';
    try {
      // De service geeft de URL terug: de bestandsnaam bevat een willekeurig deel.
      const result = await this._hass.callService('ennie_laadkosten', 'maak_declaratie', {}, undefined, false, true);
      const path = result?.response?.url;
      if (!path) throw new Error('Geen PDF-adres ontvangen. Controleer de Home Assistant-melding.');
      // De backend toont fouten in een melding; controleer ook of het PDF-bestand bereikbaar is.
      const response = await fetch(path + '?controle=' + Date.now(), {method: 'HEAD', cache: 'no-store'});
      if (!response.ok || !(response.headers.get('content-type') || '').toLowerCase().includes('pdf')) {
        throw new Error('Het PDF-bestand is niet beschikbaar. Controleer de Home Assistant-melding.');
      }
      pdfTab.location.replace(path + '?t=' + Date.now());
    } catch (error) {
      pdfTab.close();
      alert('PDF kon niet worden geopend: ' + (error?.message || String(error)));
    } finally {
      button.disabled = false;
      label.textContent = 'PDF-declaratie maken';
    }
  }

  getCardSize() { return 1; }
}
// Niet dubbel registreren als het oude bestand (ennie-pdf-button.js) ook nog geladen wordt.
if (!customElements.get('ennie-pdf-button')) {
  customElements.define('ennie-pdf-button', EnniePdfButton);
  window.customCards = window.customCards || [];
  window.customCards.push({type:'ennie-pdf-button', name:'Ennie PDF-knop', description:'Maak en open de Ennie-declaratie automatisch'});
}

/* Ennie uitleg-pop-up: window.enniePopup(titel, tekst).
 * Wordt gebruikt door de i-iconen op de tegels (data-titel / data-tekst).
 * Tekst is platte tekst; een lege regel begint een nieuwe alinea.
 */
window.enniePopup = (title, text) => {
  document.getElementById('ennie-popup')?.remove();
  const esc = (v) => String(v ?? '').replace(/[&<>"]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const body = String(text ?? '').split(/\n\s*\n/).map((p) => `<p>${esc(p).replace(/\n/g, '<br>')}</p>`).join('');
  const overlay = document.createElement('div');
  overlay.id = 'ennie-popup';
  overlay.innerHTML = `
    <style>
      #ennie-popup { position: fixed; inset: 0; z-index: 10000; display: flex; align-items: center;
        justify-content: center; padding: 16px; box-sizing: border-box; background: rgba(0, 0, 0, .45);
        font-family: var(--primary-font-family, sans-serif); }
      #ennie-popup .ep-panel { width: 100%; max-width: 440px; max-height: 80vh; overflow: auto; box-sizing: border-box;
        background: var(--card-background-color, #fff); color: var(--primary-text-color, #13281f);
        border: 1px solid color-mix(in srgb, #2fae74 45%, transparent); border-radius: 17px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, .35); padding: 18px 20px; }
      #ennie-popup .ep-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
      #ennie-popup .ep-head ha-icon { --mdc-icon-size: 22px; color: #2fae74; flex: none; }
      #ennie-popup .ep-title { flex: 1; font-size: 16px; font-weight: 700; }
      #ennie-popup .ep-close { border: 0; background: transparent; color: var(--secondary-text-color, #555);
        font-size: 22px; line-height: 1; cursor: pointer; padding: 4px 6px; }
      #ennie-popup p { margin: 8px 0 0; font-size: 14px; line-height: 1.5; color: var(--primary-text-color, #13281f); }
    </style>
    <div class="ep-panel" role="dialog" aria-modal="true">
      <div class="ep-head"><ha-icon icon="mdi:information-outline"></ha-icon>
        <div class="ep-title">${esc(title)}</div>
        <button class="ep-close" type="button" aria-label="Sluiten">&times;</button></div>
      ${body}
    </div>`;
  const close = () => { overlay.remove(); document.removeEventListener('keydown', onKey); };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  overlay.querySelector('.ep-close').addEventListener('click', close);
  document.addEventListener('keydown', onKey);
  document.body.appendChild(overlay);
};

/* Ennie zakelijke rit: window.ennieRitPopup(hass).
 * Eén venster voor datum, kilometers en opmerking. Roept het script
 * script.ennie_zakelijke_rit_registreren aan (pakket ennie_kilometers).
 */
window.ennieRitPopup = (hass) => {
  document.getElementById('ennie-rit-popup')?.remove();
  const pad = (n) => String(n).padStart(2, '0');
  const d = new Date();
  const vandaag = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const overlay = document.createElement('div');
  overlay.id = 'ennie-rit-popup';
  overlay.innerHTML = `
    <style>
      #ennie-rit-popup { position: fixed; inset: 0; z-index: 10000; display: flex; align-items: center;
        justify-content: center; padding: 16px; box-sizing: border-box; background: rgba(0, 0, 0, .45);
        font-family: var(--primary-font-family, sans-serif); }
      #ennie-rit-popup .ep-panel { width: 100%; max-width: 440px; max-height: 90vh; overflow: auto; box-sizing: border-box;
        background: var(--card-background-color, #fff); color: var(--primary-text-color, #13281f);
        border: 1px solid color-mix(in srgb, #2fae74 45%, transparent); border-radius: 17px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, .35); padding: 18px 20px; }
      #ennie-rit-popup .ep-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
      #ennie-rit-popup .ep-head ha-icon { --mdc-icon-size: 22px; color: #2fae74; flex: none; }
      #ennie-rit-popup .ep-title { flex: 1; font-size: 16px; font-weight: 700; }
      #ennie-rit-popup .ep-close { border: 0; background: transparent; color: var(--secondary-text-color, #555);
        font-size: 22px; line-height: 1; cursor: pointer; padding: 4px 6px; }
      #ennie-rit-popup label { display: block; margin: 10px 0 4px; font-size: 13px; font-weight: 600;
        color: var(--secondary-text-color, #555); }
      #ennie-rit-popup input { width: 100%; box-sizing: border-box; height: 42px; padding: 8px 12px;
        border-radius: 10px; border: 1px solid color-mix(in srgb, var(--primary-text-color, #13281f) 25%, transparent);
        background: var(--secondary-background-color, #f3f6f4); color: var(--primary-text-color, #13281f);
        font: 16px var(--primary-font-family, sans-serif); color-scheme: light dark; }
      #ennie-rit-popup input:focus { outline: 2px solid #2fae74; outline-offset: 0; }
      #ennie-rit-popup .ep-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      #ennie-rit-popup .ep-msg { min-height: 18px; margin-top: 10px; font-size: 13px; }
      #ennie-rit-popup .ep-msg.fout { color: #e5484d; }
      #ennie-rit-popup .ep-msg.ok { color: #2fae74; }
      #ennie-rit-popup .ep-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px; }
      #ennie-rit-popup .ep-actions button { height: 40px; padding: 0 18px; border-radius: 12px; cursor: pointer;
        font: 600 14px var(--primary-font-family, sans-serif); }
      #ennie-rit-popup .ep-cancel { border: 1px solid color-mix(in srgb, var(--primary-text-color, #13281f) 25%, transparent);
        background: transparent; color: var(--primary-text-color, #13281f); }
      #ennie-rit-popup .ep-add { border: 0; background: #2fae74; color: #fff; }
      #ennie-rit-popup .ep-add:disabled { opacity: .6; cursor: wait; }
    </style>
    <form class="ep-panel" role="dialog" aria-modal="true" novalidate>
      <div class="ep-head"><ha-icon icon="mdi:briefcase-plus-outline"></ha-icon>
        <div class="ep-title">Zakelijke rit toevoegen</div>
        <button class="ep-close" type="button" aria-label="Sluiten">&times;</button></div>
      <div class="ep-row">
        <div><label for="ep-km">Kilometers</label>
          <input id="ep-km" type="number" inputmode="numeric" min="1" max="5000" step="1" placeholder="bijv. 45"></div>
        <div><label for="ep-datum">Datum</label>
          <input id="ep-datum" type="date" value="${vandaag}" max="${vandaag}"></div>
      </div>
      <label for="ep-opm">Opmerking</label>
      <input id="ep-opm" type="text" maxlength="200" placeholder="bijv. Klantbezoek Utrecht">
      <div class="ep-msg"></div>
      <div class="ep-actions">
        <button class="ep-cancel" type="button">Annuleren</button>
        <button class="ep-add" type="submit">Toevoegen</button>
      </div>
    </form>`;
  const form = overlay.querySelector('form');
  const km = overlay.querySelector('#ep-km');
  const datum = overlay.querySelector('#ep-datum');
  const opm = overlay.querySelector('#ep-opm');
  const msg = overlay.querySelector('.ep-msg');
  const add = overlay.querySelector('.ep-add');
  const close = () => { overlay.remove(); document.removeEventListener('keydown', onKey); };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  const toon = (t, cls) => { msg.textContent = t; msg.className = `ep-msg ${cls}`; };
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  overlay.querySelector('.ep-close').addEventListener('click', close);
  overlay.querySelector('.ep-cancel').addEventListener('click', close);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const n = Math.round(Number(km.value));
    if (!Number.isFinite(n) || n < 1 || n > 5000) { toon('Vul het aantal kilometers in (1 tot 5000).', 'fout'); km.focus(); return; }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(datum.value) || datum.value > vandaag) { toon('Kies een datum tot en met vandaag.', 'fout'); datum.focus(); return; }
    add.disabled = true;
    toon('Bezig met toevoegen…', '');
    try {
      await hass.callService('script', 'ennie_zakelijke_rit_registreren',
        { km: n, datum: datum.value, opmerking: opm.value.trim() });
      toon(`${n} km toegevoegd.`, 'ok');
      setTimeout(close, 900);
    } catch (err) {
      add.disabled = false;
      toon(`Toevoegen mislukt: ${err?.message || err}`, 'fout');
    }
  });
  document.addEventListener('keydown', onKey);
  document.body.appendChild(overlay);
  setTimeout(() => km.focus(), 50);
};
