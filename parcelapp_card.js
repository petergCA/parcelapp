/* ParcelApp Lovelace Card (Shadow DOM isolated) */
(() => {
  const TAG = "parcelapp-card";
  const VERSION = "20260416.01";

  console.debug(`ParcelApp Card ${VERSION} loaded`);

  if (customElements.get(TAG)) return;

  class ParcelAppCard extends HTMLElement {
    constructor() {
      super();
      // Track expanded rows by a stable id (tracking_number), not by list index
      this._expandedKeys = new Set();
    }

    _warn(msg, ...args) {
      console.warn(`[ParcelApp Card ${VERSION}] ${msg}`, ...args);
    }

    setConfig(config) {
      if (!config) throw new Error("ParcelApp Card: no config provided");

      try {
        this._applyConfig(config);
      } catch (err) {
        this._warn("setConfig failed — config received:", config);
        this._warn("Error details:", err);
        throw err;
      }
    }

    _applyConfig(config) {
      this._config = {
        ...config,

        // Apply validated defaults after spread so ?? logic is not overwritten by undefined
        title: config.title ?? "Parcel Deliveries",
        hide_delivered: config.hide_delivered ?? false,
        show_delivered: config.show_delivered ?? true,

        // view controls
        show_today_only: config.show_today_only ?? false,
        show_icon: config.show_icon ?? true,
        show_description: config.show_description ?? true,
        show_status: config.show_status ?? true,
        show_timing: config.show_timing ?? true,
        show_events: config.show_events ?? true,
        highlight_today: config.highlight_today ?? true,

        // list / layout controls
        max_items: config.max_items ?? null,     // number | null
        sort: config.sort ?? "soonest",          // soonest | today | carrier
        compact: config.compact ?? false,
      };

      if (!this._root) {
        this._root = this.attachShadow({ mode: "open" });
        this._root.innerHTML = `
          <style>
            :host { display:block; }

            ha-card {
              border-radius: var(--ha-card-border-radius, 12px);
              overflow: hidden;
            }

            .wrap { padding: 12px; }

            .header {
              font-size: 16px;
              font-weight: 600;
              padding: 12px 16px 0 16px;
            }

            .row {
              display: flex;
              align-items: stretch;
              gap: 12px;
              width: 100%;
              box-sizing: border-box;
              padding: 8px 12px;
              border-radius: 16px;
              background: rgba(0,0,0,0.18);
              border: 1px solid rgba(255,255,255,0.05);
              margin: 0 0 6px 0;
              cursor: pointer;

              transition:
                transform 0.08s ease,
                opacity 0.2s ease,
                box-shadow 0.18s ease;
            }

            .wrap.compact .row {
              padding: 6px 10px;
              gap: 8px;
            }

            .row:active { transform: scale(0.995); }

            .row.expanded {
              box-shadow: 0 4px 10px rgba(0,0,0,0.25);
            }

            .row.delivered { opacity: 0.55; }

            .row.today {
              outline: 1px solid var(--primary-color);
            }

            .icon {
              flex: 0 0 auto;
              width: 42px;
              height: 42px;
              border-radius: 50%;
              overflow: hidden;
              background: rgba(0,0,0,0.15);
              display: grid;
              place-items: center;

              align-self: center;
            }

            .wrap.compact .icon {
              width: 32px;
              height: 32px;
            }

            .icon img {
              width: 100%;
              height: 100%;
              object-fit: cover;
            }

            .info {
              flex: 1 1 auto;
              min-width: 0;

              display: flex;
              flex-direction: column;
              justify-content: center;
            }

            .wrap.compact .info {
              min-height: 32px;
            }

            .title {
              font-weight: 600;
              font-size: 16px;
              line-height: 1.2;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }

            .wrap.compact .title { font-size: 14px; }

            .status,
            .timing {
              font-size: 14px;
              margin-top: 0; /* spacing handled by sibling selectors below */
            }

            .title + .status,
            .title + .timing,
            .status + .timing {
              margin-top: 4px;
            }

            .status { opacity: 0.72; }

            .timing {
              color: var(--primary-color);
              font-weight: 500;
            }

            /* Expandable timeline section */
            .events {
              max-height: 0;
              overflow: hidden;

              /* remove it from layout flow */
              position: relative;

              margin-top: 0;

              font-size: 13px;
              opacity: 0;
              transform: translateY(-6px);

              padding-left: 18px;

              transition:
                max-height 0.83s cubic-bezier(.25,.8,.25,1),
                opacity 0.52s ease,
                transform 0.52s ease;
            }

            .row.expanded .events {
              max-height: 600px;
              margin-top: 10px;
              opacity: 0.95;
              transform: translateY(0);
            }

            .event {
              margin-top: 8px;
              opacity: 0;
              transform: translateY(-6px);

              position: relative;
              padding-left: 12px;

              transition:
                opacity 0.52s ease,
                transform 0.52s ease;
            }

            /* Timeline vertical line */
            .events::before {
              content: "";
              position: absolute;
              left: 6px;
              top: 4px;
              bottom: 4px;
              width: 2px;
              background: rgba(255,255,255,0.15);
            }

            /* Timeline dots */
            .event::before {
              content: "";
              position: absolute;
              left: -7px;
              top: 6px;
              width: 8px;
              height: 8px;
              border-radius: 50%;
              background: rgba(255,255,255,0.6);
            }

            /* Highlight newest event */
            .event:first-child::before {
              background: var(--primary-color);
              width: 10px;
              height: 10px;
              left: -8px;
            }

            .row.expanded .event {
              opacity: 1;
              transform: translateY(0);
            }

            /* Stagger animation */
            .row.expanded .event:nth-child(1) { transition-delay: 0.08s; }
            .row.expanded .event:nth-child(2) { transition-delay: 0.15s; }
            .row.expanded .event:nth-child(3) { transition-delay: 0.23s; }
            .row.expanded .event:nth-child(4) { transition-delay: 0.30s; }
            .row.expanded .event:nth-child(5) { transition-delay: 0.38s; }
            .row.expanded .event:nth-child(6) { transition-delay: 0.45s; }
            .row.expanded .event:nth-child(7) { transition-delay: 0.53s; }
            .row.expanded .event:nth-child(8) { transition-delay: 0.60s; }
            .row.expanded .event:nth-child(9) { transition-delay: 0.68s; }
            .row.expanded .event:nth-child(10) { transition-delay: 0.75s; }

            .event-text {
              font-size: 13px;
              font-weight: 500;
            }

            .event-location {
              font-size: 12px;
              opacity: 0.65;
            }

            .empty {
              padding: 16px;
              text-align: center;
              opacity: 0.65;
            }
          </style>

          <ha-card>
            <div class="header"></div>
            <div class="wrap"></div>
          </ha-card>
        `;

        // Assign element refs once, immediately after shadow DOM is created
        this._headerEl = this._root.querySelector(".header");
        this._wrapEl   = this._root.querySelector(".wrap");
      }

      // Safely update header and compact class — guard against any unexpected null
      if (this._headerEl) {
        this._headerEl.textContent = this._config.title || "";
      }
      if (this._wrapEl) {
        this._wrapEl.classList.toggle("compact", !!this._config.compact);
      }
    }

    set hass(hass) {
      if (!this._config || !this._wrapEl) return;

      try {
        this._renderHass(hass);
      } catch (err) {
        const entity = hass?.states?.[this._config?.entity];
        this._warn("Render error — config:", this._config);
        this._warn("Render error — entity state:", entity ?? "(not found)");
        this._warn("Error details:", err);
        this._wrapEl.innerHTML = `<div class="empty">Render error — check browser console</div>`;
      }
    }

    _renderHass(hass) {

      if (!this._config.entity) {
        this._wrapEl.innerHTML = `<div class="empty">Set <code>entity:</code> in card config</div>`;
        return;
      }

      const entity = hass.states[this._config.entity];

      if (!entity) {
        this._wrapEl.innerHTML = `<div class="empty">Entity not found: ${this._escape(this._config.entity)}</div>`;
        return;
      }

      const deliveries = entity.attributes.deliveries;
      if (!Array.isArray(deliveries)) {
        this._warn(
          `Entity '${this._config.entity}' has no 'deliveries' array attribute.`,
          "attributes:", entity.attributes
        );
      }
      let list = [...(Array.isArray(deliveries) ? deliveries : [])];

      // Filters
      if (this._config.hide_delivered || !this._config.show_delivered) {
        list = list.filter(d => !this._isDelivered(d));
      }
      if (this._config.show_today_only) {
        const showDel = this._config.show_delivered && !this._config.hide_delivered;
        list = list.filter(d => {
          if (this._isDelivered(d)) return showDel;
          return d.days_to_delivery === 0;
        });
      }

      // Sort
      const sortMode = String(this._config.sort || "soonest").toLowerCase();

      list.sort((a, b) => {
        const aDelivered = this._isDelivered(a);
        const bDelivered = this._isDelivered(b);

        // Always push delivered to bottom
        if (aDelivered !== bDelivered) {
          return aDelivered ? 1 : -1;
        }

        if (sortMode === "carrier") {
          return String(a.carrier_code || "")
            .localeCompare(String(b.carrier_code || ""));
        }

        if (sortMode === "today") {
          const at = (a.days_to_delivery === 0 && !aDelivered) ? 0 : 1;
          const bt = (b.days_to_delivery === 0 && !bDelivered) ? 0 : 1;

          if (at !== bt) return at - bt;
        }

        return (a.days_to_delivery ?? 999) - (b.days_to_delivery ?? 999);
      });

      // Limit
      const maxItems = this._config.max_items;
      if (typeof maxItems === "number" && Number.isFinite(maxItems) && maxItems > 0) {
        list = list.slice(0, maxItems);
      }

      if (!list.length) {
        this._wrapEl.innerHTML = `<div class="empty">No active deliveries</div>`;
        return;
      }

      // Render
      this._wrapEl.innerHTML = list.map(d => this._renderRow(d)).join("");

      // Bind interactions
      const rows = this._wrapEl.querySelectorAll(".row");
      rows.forEach(row => {
        const key = row.dataset.key;

        // Restore expanded visual state
        row.classList.toggle("expanded", this._expandedKeys.has(key));

        let pressTimer = null;
        let longPressTriggered = false;

        const delivery = list.find(x => this._rowKey(x) === key);
        const trackingUrl = delivery ? this._trackingUrl(delivery) : null;

        const startPress = () => {
          longPressTriggered = false;
          pressTimer = setTimeout(() => {
            longPressTriggered = true;
            if (trackingUrl) window.open(trackingUrl, "_blank");
          }, 900);
        };

        const cancelPress = () => clearTimeout(pressTimer);

        row.addEventListener("mousedown", startPress);
        row.addEventListener("touchstart", startPress, { passive: true });

        row.addEventListener("mouseup", cancelPress);
        row.addEventListener("mouseleave", cancelPress);
        row.addEventListener("touchend", cancelPress);
        row.addEventListener("touchcancel", cancelPress);

        row.addEventListener("click", (e) => {
          clearTimeout(pressTimer);

          if (longPressTriggered) {
            e.preventDefault();
            return;
          }

          // If events are disabled, don't toggle expansion
          if (!this._config.show_events) return;

          if (this._expandedKeys.has(key)) {
            this._expandedKeys.delete(key);
            row.classList.remove("expanded");
          } else {
            this._expandedKeys.add(key);
            row.classList.add("expanded");
          }
        });
      });
    }

    _renderRow(d) {
      const icon = this._carrierIcon(d);
      const timing = this._timingText(d);
      const key = this._rowKey(d);

      const isDelivered = this._isDelivered(d);
      const classes = [
        "row",
        isDelivered ? "delivered" : "",
        (this._config.highlight_today && d.days_to_delivery === 0 && !isDelivered) ? "today" : ""
      ].filter(Boolean).join(" ");

      const eventsHtml = (d.events || [])
        .slice(0, 10)
        .map(e => {

          const text = e.event || e.description || "";

          const rawDate =
            e.date ||
            e.datetime ||
            e.timestamp ||
            e.time ||
            null;

          let formattedDate = "";

          if (rawDate) {
            const dt = new Date(rawDate);
            if (!isNaN(dt)) {
              const mm = String(dt.getMonth() + 1).padStart(2,"0");
              const dd = String(dt.getDate()).padStart(2,"0");
              formattedDate = `${mm}/${dd} `;
            }
          }

          const location =
            e.location ||
            e.place ||
            [e.city, e.state].filter(Boolean).join(", ") ||
            "";

          return `
            <div class="event">
              <div class="event-text">
                ${formattedDate}${this._escape(text)}
              </div>
              ${location ? `<div class="event-location">${this._escape(location)}</div>` : ""}
            </div>
          `;
        })
        .join("");

      // If show_events is false, don't render the events container at all.
      const eventsBlock = this._config.show_events
        ? `<div class="events">${eventsHtml}</div>`
        : ``;

      return `
        <div class="${classes}" data-key="${this._escapeAttr(key)}">
          ${this._config.show_icon ? `
            <div class="icon">
              <img src="${icon}" alt="${this._escapeAttr(d.carrier_code || "carrier")}">
            </div>
          ` : ``}

          <div class="info">
            ${this._config.show_description ? `
              <div class="title">${this._escape(d.description || "Package")}</div>
            ` : ``}

            ${this._config.show_status ? `
              <div class="status">${this._escape(d.latest_event || d.status_code || "")}</div>
            ` : ``}

            ${this._config.show_timing ? `
              <div class="timing">${this._escape(timing)}</div>
            ` : ``}

            ${eventsBlock}
          </div>
        </div>
      `;
    }

    _rowKey(d) {
      // Prefer tracking_number; fall back to a stable-ish composite
      const tn = (d.tracking_number || "").trim();
      if (tn) return tn;
      return `${(d.carrier_code || "")}|${(d.description || "")}|${(d.latest_event || "")}`.trim();
    }

    _escapeAttr(str) {
      // For data-* attributes (minimal escaping)
      return String(str)
        .replaceAll("&","&amp;")
        .replaceAll('"',"&quot;")
        .replaceAll("<","&lt;")
        .replaceAll(">","&gt;");
    }

    _timingText(d) {
      if (this._isDelivered(d)) return "Delivered";
      if (d.days_to_delivery === 0) return "Today is Delivery Day";

      if (typeof d.days_to_delivery === "number" && d.days_to_delivery > 0) {
        return `${d.days_to_delivery} Day${d.days_to_delivery === 1 ? "" : "s"} until Delivery`;
      }
      return "";
    }

    _isDelivered(d) {
      return (
        Number(d.status_code) === 0 ||
        d.delivered === true ||
        d.delivered === "true"
      );
    }

    _carrierIcon(delivery) {
      const base = "/parcelapp/images";

      if (this._isDelivered(delivery)) {
        return `${base}/delivered.png`;
      }

      const code = String(delivery.carrier_code || "").toLowerCase().trim();

      if (code === "ups") return `${base}/ups.png`;
      if (code === "usps") return `${base}/usps.jpg`;
      if (code === "fedex") return `${base}/fedex.png`;
      if (code === "amzlus") return `${base}/amazon_orange_v3.png`;
      if (code === "gofous") return `${base}/gofous.png`;
      if (code === "abf") return `${base}/abf.png`;
      if (code === "speedx") return `${base}/speedx_v2.png`;
      if (code === "uniuni") return `${base}/uniuni.png`;
      if (code === "ontrac") return `${base}/ontrac.png`;
      if (code === "ont") return `${base}/ontrac.png`;
      if (code === "gso") return `${base}/gls.png`;
      if (code === "yun" || code === "yunexpress") return `${base}/yunexpress.png`;
      if (code === "veho") return `${base}/veho.png`;

      return `${base}/package.png`;
    }

    _trackingUrl(delivery) {
      const tracking = delivery.tracking_number || "";
      const carrier = (delivery.carrier_code || "").toLowerCase();

      if (!tracking) return null;

      const t = encodeURIComponent(tracking);

      switch (carrier) {
        case "ups":
          return `https://www.ups.com/track?tracknum=${t}`;
        case "usps":
          return `https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1=${t}`;
        case "fedex":
          return `https://www.fedex.com/fedextrack/?trknbr=${t}`;
        case "ontrac":
          return `https://www.ontrac.com/trackingres.asp?tracking_number=${t}`;
        case "ont":
          return `https://www.ontrac.com/trackingres.asp?tracking_number=${t}`;
        case "uniuni":
          return `https://www.ordertracker.com/track/${t}`;
        case "gso":
          return `https://gls-group.com/US/en/home/?TrackingNumbers=${t}`;
        case "amzlus":
          return `https://www.amazon.com/your-orders/order-details?orderID=${t}`;
        default:
          return null;
      }
    }

    _escape(str) {
      return String(str)
        .replaceAll("&","&amp;")
        .replaceAll("<","&lt;")
        .replaceAll(">","&gt;")
        .replaceAll('"',"&quot;");
    }

    getCardSize() { return 3; }
  }

  if (!customElements.get(TAG)) {
    customElements.define(TAG, ParcelAppCard);
  }
})();