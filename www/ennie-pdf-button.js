/* Ennie PDF-knop: genereert de declaratie en opent daarna het PDF-bestand.
 * Plaats in /config/www/ennie-pdf-button.js.
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
customElements.define('ennie-pdf-button', EnniePdfButton);
window.customCards = window.customCards || [];
window.customCards.push({type:'ennie-pdf-button', name:'Ennie PDF-knop', description:'Maak en open de Ennie-declaratie automatisch'});

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
