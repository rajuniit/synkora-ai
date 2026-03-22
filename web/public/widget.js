/**
 * Synkora Agent Widget
 * Embeddable AI chat widget using Shadow DOM for full CSS isolation.
 * Usage: SynkoraWidget.init({ widgetId, apiKey, containerId, apiUrl })
 */
(function (global) {
  "use strict";

  if (global.SynkoraWidget) return;

  // ─── Helpers ─────────────────────────────────────────────────────────────────

  function uid() {
    return Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  function esc(t) {
    return String(t || "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function hexToRgb(hex) {
    hex = (hex || "").replace(/^#/, "");
    if (hex.length === 3) hex = hex.split("").map(function (c) { return c + c; }).join("");
    if (hex.length !== 6) return "255,68,79";
    var n = parseInt(hex, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(",");
  }

  function darkenHex(hex, amount) {
    hex = (hex || "").replace(/^#/, "");
    if (hex.length === 3) hex = hex.split("").map(function (c) { return c + c; }).join("");
    if (hex.length !== 6) return "#c8102e";
    var n = parseInt(hex, 16);
    var r = Math.max(0, ((n >> 16) & 255) - amount);
    var g = Math.max(0, ((n >> 8) & 255) - amount);
    var b = Math.max(0, (n & 255) - amount);
    return "#" + [r, g, b].map(function (v) { return v.toString(16).padStart(2, "0"); }).join("");
  }

  function timeNow() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // ─── Markdown Parser ─────────────────────────────────────────────────────────

  function inlineMd(raw) {
    if (!raw) return "";
    var ph = [];
    var s = raw;

    // Protect inline code first
    s = s.replace(/`([^`\n]+)`/g, function (_, c) {
      ph.push("<code>" + esc(c) + "</code>");
      return "\x00" + (ph.length - 1) + "\x00";
    });

    // Images
    s = s.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, function (_, alt, src) {
      if (!/^(https?:\/\/|\/|data:image\/)/.test(src)) return esc(alt || "");
      ph.push('<img src="' + esc(src) + '" alt="' + esc(alt) + '" class="snkr-img" loading="lazy">');
      return "\x00" + (ph.length - 1) + "\x00";
    });

    // Links
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_, label, href) {
      if (!/^(https?:\/\/|mailto:|\/)/i.test(href)) return esc(label);
      ph.push('<a href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' + esc(label) + '</a>');
      return "\x00" + (ph.length - 1) + "\x00";
    });

    // Escape remaining text
    s = esc(s);

    // Bold
    s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/__(.+?)__/g, "<strong>$1</strong>");
    // Italic
    s = s.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
    s = s.replace(/_([^_\n\s][^_\n]*)_/g, "<em>$1</em>");
    // Strikethrough
    s = s.replace(/~~(.+?)~~/g, "<del>$1</del>");

    // Restore placeholders
    s = s.replace(/\x00(\d+)\x00/g, function (_, i) { return ph[+i]; });
    return s;
  }

  function parseCells(line) {
    return line.split("|")
      .map(function (c) { return c.trim(); })
      .filter(function (c, i, a) {
        return !(i === 0 && c === "") && !(i === a.length - 1 && c === "");
      });
  }

  function mdParse(text, streaming) {
    if (!text) return "";

    // Close unclosed code fence during streaming for clean partial render
    var fences = (text.match(/^```/gm) || []).length;
    if (streaming && fences % 2 !== 0) text += "\n```";

    var lines = text.split("\n");
    var out = "";
    var i = 0;

    while (i < lines.length) {
      var line = lines[i];

      // ── Fenced code block ──────────────────────────────────────────
      var fm = line.match(/^```(\w*)\s*$/);
      if (fm) {
        var lang = fm[1];
        var codeLines = [];
        i++;
        while (i < lines.length && !lines[i].match(/^```\s*$/)) {
          codeLines.push(lines[i]);
          i++;
        }
        i++; // skip closing ```
        out += '<div class="snkr-pre">' +
          '<div class="snkr-code-hdr">' +
            '<span class="snkr-lang-tag">' + (lang ? esc(lang) : "") + '</span>' +
            '<button class="snkr-copy-btn">Copy</button>' +
          '</div>' +
          '<pre><code>' + esc(codeLines.join("\n")) + '</code></pre>' +
          '</div>';
        continue;
      }

      // ── Table ──────────────────────────────────────────────────────
      if (line.includes("|") && i + 1 < lines.length && /^\|?[\s:\-|]+\|/.test(lines[i + 1])) {
        var headers = parseCells(line);
        i += 2; // skip header + separator
        var tHtml = '<div class="snkr-table-wrap"><table><thead><tr>';
        headers.forEach(function (h) { tHtml += "<th>" + inlineMd(h) + "</th>"; });
        tHtml += "</tr></thead><tbody>";
        while (i < lines.length && lines[i].includes("|")) {
          tHtml += "<tr>";
          parseCells(lines[i]).forEach(function (c) { tHtml += "<td>" + inlineMd(c) + "</td>"; });
          tHtml += "</tr>";
          i++;
        }
        out += tHtml + "</tbody></table></div>";
        continue;
      }

      // ── Heading ────────────────────────────────────────────────────
      var hm = line.match(/^(#{1,6})\s+(.+)$/);
      if (hm) {
        var lvl = hm[1].length;
        out += "<h" + lvl + ">" + inlineMd(hm[2]) + "</h" + lvl + ">";
        i++;
        continue;
      }

      // ── Blockquote ─────────────────────────────────────────────────
      if (/^>\s?/.test(line)) {
        var bqLines = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) {
          bqLines.push(lines[i].replace(/^>\s?/, ""));
          i++;
        }
        out += "<blockquote>" + bqLines.map(inlineMd).join("<br>") + "</blockquote>";
        continue;
      }

      // ── Unordered list ─────────────────────────────────────────────
      if (/^[-*+]\s+/.test(line)) {
        out += "<ul>";
        while (i < lines.length && /^[-*+]\s+/.test(lines[i])) {
          out += "<li>" + inlineMd(lines[i].replace(/^[-*+]\s+/, "")) + "</li>";
          i++;
        }
        out += "</ul>";
        continue;
      }

      // ── Ordered list ───────────────────────────────────────────────
      if (/^\d+\.\s+/.test(line)) {
        out += "<ol>";
        while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
          out += "<li>" + inlineMd(lines[i].replace(/^\d+\.\s+/, "")) + "</li>";
          i++;
        }
        out += "</ol>";
        continue;
      }

      // ── Horizontal rule ────────────────────────────────────────────
      if (/^[-*_]{3,}\s*$/.test(line.trim())) {
        out += "<hr>";
        i++;
        continue;
      }

      // ── Blank line ─────────────────────────────────────────────────
      if (line.trim() === "") { i++; continue; }

      // ── Paragraph ──────────────────────────────────────────────────
      var pLines = [];
      while (
        i < lines.length &&
        lines[i].trim() !== "" &&
        !lines[i].match(/^#{1,6}\s/) &&
        !lines[i].match(/^[-*+]\s+/) &&
        !lines[i].match(/^\d+\.\s+/) &&
        !lines[i].match(/^>\s?/) &&
        !lines[i].match(/^```/) &&
        !/^[-*_]{3,}\s*$/.test(lines[i].trim()) &&
        !lines[i].includes("|")
      ) {
        pLines.push(lines[i]);
        i++;
      }
      if (pLines.length) {
        out += "<p>" + pLines.map(inlineMd).join("<br>") + "</p>";
      }
    }

    return out;
  }

  // ─── Shadow DOM CSS ───────────────────────────────────────────────────────────

  var CSS = `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :host { all: initial; }

    /* ── Toggle Button ─────────── */
    #snkr-toggle {
      position: fixed; bottom: 28px; right: 28px; z-index: 2147483647;
      width: 60px; height: 60px; border-radius: 50%; border: none;
      background: linear-gradient(135deg, var(--snkr-c, #ff444f) 0%, var(--snkr-cd, #c8102e) 100%);
      box-shadow: 0 4px 20px rgba(var(--snkr-rgb, 255,68,79), 0.45), 0 2px 8px rgba(0,0,0,0.2);
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      padding: 0; outline: none;
      transition: transform 0.2s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.2s ease;
    }
    #snkr-toggle:hover {
      transform: scale(1.1);
      box-shadow: 0 8px 28px rgba(var(--snkr-rgb, 255,68,79), 0.55), 0 4px 12px rgba(0,0,0,0.25);
    }
    #snkr-toggle:active { transform: scale(0.96); }
    #snkr-toggle svg { pointer-events: none; }
    #snkr-toggle::before {
      content: ''; position: absolute; inset: -4px; border-radius: 50%;
      border: 2px solid rgba(var(--snkr-rgb, 255,68,79), 0.4);
      animation: snkr-pulse 2.4s ease-out infinite;
    }
    @keyframes snkr-pulse {
      0%   { transform: scale(1);    opacity: 0.7; }
      70%  { transform: scale(1.35); opacity: 0; }
      100% { transform: scale(1.35); opacity: 0; }
    }

    /* ── Panel ─────────────────── */
    #snkr-panel {
      position: fixed; bottom: 104px; right: 28px; z-index: 2147483646;
      width: 390px; height: 580px; background: #fff; border-radius: 20px;
      overflow: hidden; display: none; flex-direction: column;
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      font-size: 14px; line-height: 1.5; color: #0f172a;
      box-shadow: 0 0 0 1px rgba(0,0,0,0.06), 0 24px 64px rgba(0,0,0,0.18),
                  0 8px 24px rgba(var(--snkr-rgb, 255,68,79), 0.1);
      transform-origin: bottom right;
    }
    #snkr-panel.open {
      display: flex;
      animation: snkr-slidein 0.26s cubic-bezier(0.34,1.4,0.64,1) both;
    }
    @keyframes snkr-slidein {
      from { opacity: 0; transform: scale(0.88) translateY(16px); }
      to   { opacity: 1; transform: scale(1)    translateY(0); }
    }

    /* ── Header ────────────────── */
    #snkr-header {
      background: linear-gradient(135deg, var(--snkr-c, #ff444f) 0%, var(--snkr-cd, #c8102e) 100%);
      padding: 16px 18px; display: flex; align-items: center;
      justify-content: space-between; flex-shrink: 0; position: relative;
    }
    #snkr-header::after {
      content: ''; position: absolute; inset: 0; pointer-events: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='4' height='4'%3E%3Ccircle cx='1' cy='1' r='0.6' fill='rgba(255,255,255,0.06)'/%3E%3C/svg%3E");
    }
    #snkr-hdr-left { display: flex; align-items: center; gap: 11px; position: relative; z-index: 1; }
    #snkr-avatar {
      width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0;
      background: rgba(255,255,255,0.2); border: 2px solid rgba(255,255,255,0.3);
      display: flex; align-items: center; justify-content: center;
      font-size: 17px; overflow: hidden; object-fit: cover;
    }
    #snkr-avatar img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }
    #snkr-hdr-info { display: flex; flex-direction: column; gap: 1px; }
    #snkr-hdr-name { font-size: 15px; font-weight: 700; color: #fff; letter-spacing: -0.01em; }
    #snkr-hdr-status {
      font-size: 11px; color: rgba(255,255,255,0.8);
      display: flex; align-items: center; gap: 5px;
    }
    #snkr-hdr-status::before {
      content: ''; width: 6px; height: 6px; border-radius: 50%;
      background: #4ade80; box-shadow: 0 0 5px #4ade80; display: inline-block;
    }
    #snkr-close {
      position: relative; z-index: 1; background: rgba(255,255,255,0.15);
      border: none; cursor: pointer; color: #fff; width: 30px; height: 30px;
      border-radius: 9px; display: flex; align-items: center; justify-content: center;
      padding: 0; outline: none; transition: background 0.15s;
    }
    #snkr-close:hover { background: rgba(255,255,255,0.28); }

    /* ── Messages ──────────────── */
    #snkr-messages {
      flex: 1; overflow-y: auto; padding: 16px; display: flex;
      flex-direction: column; gap: 12px; background: #f8fafc;
    }
    #snkr-messages::-webkit-scrollbar { width: 4px; }
    #snkr-messages::-webkit-scrollbar-track { background: transparent; }
    #snkr-messages::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 4px; }

    .snkr-row { display: flex; flex-direction: column; gap: 3px; animation: snkr-in 0.18s ease both; }
    @keyframes snkr-in { from { opacity:0; transform:translateY(5px); } to { opacity:1; transform:none; } }
    .snkr-row.user  { align-items: flex-end; }
    .snkr-row.agent { align-items: flex-start; }
    .snkr-row.error { align-items: flex-start; }

    .snkr-bubble {
      max-width: 88%; padding: 10px 14px; border-radius: 18px;
      font-size: 14px; line-height: 1.65; word-break: break-word;
    }
    .snkr-row.user .snkr-bubble {
      background: linear-gradient(135deg, var(--snkr-c, #ff444f), var(--snkr-cd, #c8102e));
      color: #fff; border-bottom-right-radius: 4px;
      box-shadow: 0 2px 10px rgba(var(--snkr-rgb, 255,68,79), 0.3);
    }
    .snkr-row.agent .snkr-bubble {
      background: #fff; color: #0f172a; border-bottom-left-radius: 4px;
      border: 1px solid #e8ecf1; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .snkr-row.error .snkr-bubble {
      background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; border-radius: 12px;
    }

    /* ── Bubble Rich Content ────── */
    .snkr-bubble p { margin: 0 0 7px; }
    .snkr-bubble p:last-child { margin-bottom: 0; }
    .snkr-bubble strong { font-weight: 600; }
    .snkr-bubble em { font-style: italic; }
    .snkr-bubble del { text-decoration: line-through; opacity: 0.65; }

    .snkr-bubble h1, .snkr-bubble h2, .snkr-bubble h3,
    .snkr-bubble h4, .snkr-bubble h5, .snkr-bubble h6 {
      font-weight: 700; color: #0f172a; margin: 12px 0 5px; line-height: 1.3;
    }
    .snkr-bubble h1:first-child, .snkr-bubble h2:first-child, .snkr-bubble h3:first-child { margin-top: 0; }
    .snkr-bubble h1 { font-size: 17px; }
    .snkr-bubble h2 { font-size: 15px; }
    .snkr-bubble h3 { font-size: 14px; }
    .snkr-bubble h4, .snkr-bubble h5, .snkr-bubble h6 { font-size: 13px; }

    .snkr-bubble ul, .snkr-bubble ol { margin: 4px 0 7px 18px; padding: 0; }
    .snkr-bubble li { margin: 3px 0; }

    .snkr-bubble blockquote {
      border-left: 3px solid var(--snkr-c, #ff444f);
      padding: 6px 12px; margin: 8px 0; color: #64748b;
      font-style: italic; background: #f8fafc; border-radius: 0 6px 6px 0;
    }

    .snkr-bubble hr { border: none; border-top: 1px solid #e2e8f0; margin: 10px 0; }

    /* Inline code */
    .snkr-bubble code {
      background: rgba(0,0,0,0.07); padding: 2px 5px; border-radius: 4px;
      font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px;
    }
    .snkr-row.user .snkr-bubble code { background: rgba(255,255,255,0.2); }

    /* Code block */
    .snkr-pre { margin: 8px 0; border-radius: 10px; overflow: hidden; background: #0f172a; }
    .snkr-code-hdr {
      background: #1e293b; padding: 7px 12px;
      display: flex; align-items: center; justify-content: space-between;
    }
    .snkr-lang-tag {
      font-size: 11px; color: #64748b;
      font-family: 'SF Mono', 'Fira Code', monospace;
      text-transform: uppercase; letter-spacing: 0.06em;
    }
    .snkr-copy-btn {
      background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
      color: #94a3b8; border-radius: 5px; padding: 2px 9px;
      font-size: 11px; cursor: pointer; font-family: inherit;
      transition: background 0.15s, color 0.15s;
    }
    .snkr-copy-btn:hover { background: rgba(255,255,255,0.18); color: #e2e8f0; }
    .snkr-bubble pre {
      background: #0f172a; color: #e2e8f0; padding: 12px 14px;
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 12px; overflow-x: auto; white-space: pre; line-height: 1.6;
    }
    .snkr-bubble pre code { background: none; padding: 0; color: inherit; font-size: inherit; }

    /* Table */
    .snkr-table-wrap { overflow-x: auto; margin: 8px 0; border-radius: 8px; border: 1px solid #e2e8f0; }
    .snkr-bubble table { border-collapse: collapse; width: 100%; font-size: 13px; }
    .snkr-bubble th, .snkr-bubble td { border-bottom: 1px solid #e2e8f0; padding: 7px 11px; text-align: left; white-space: nowrap; }
    .snkr-bubble th { background: #f1f5f9; font-weight: 600; color: #374151; border-bottom: 2px solid #e2e8f0; }
    .snkr-bubble tr:last-child td { border-bottom: none; }
    .snkr-bubble tr:nth-child(even) td { background: #f8fafc; }

    /* Image */
    .snkr-img {
      max-width: 100%; border-radius: 8px; margin: 6px 0;
      display: block; cursor: zoom-in;
      border: 1px solid #e2e8f0;
    }

    /* Link */
    .snkr-bubble a { color: var(--snkr-c, #ff444f); text-decoration: none; }
    .snkr-bubble a:hover { text-decoration: underline; }

    /* ── Streaming cursor ──────── */
    .snkr-bubble.streaming::after {
      content: '▋'; display: inline;
      animation: snkr-blink 0.7s step-end infinite;
      color: var(--snkr-c, #ff444f); font-size: 0.85em; margin-left: 1px;
    }
    @keyframes snkr-blink { 0%,100%{opacity:1} 50%{opacity:0} }

    .snkr-ts { font-size: 11px; color: #94a3b8; padding: 0 3px; }

    /* ── Typing indicator ──────── */
    #snkr-typing {
      display: flex; align-items: center; gap: 4px; padding: 11px 15px;
      background: #fff; border: 1px solid #e8ecf1; border-radius: 18px;
      border-bottom-left-radius: 4px; width: fit-content;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    #snkr-typing span {
      width: 7px; height: 7px; border-radius: 50%; background: #cbd5e1; display: inline-block;
    }
    #snkr-typing span:nth-child(1) { animation: snkr-dot 1.2s -0.32s infinite ease-in-out; }
    #snkr-typing span:nth-child(2) { animation: snkr-dot 1.2s -0.16s infinite ease-in-out; }
    #snkr-typing span:nth-child(3) { animation: snkr-dot 1.2s 0s    infinite ease-in-out; }
    @keyframes snkr-dot {
      0%,80%,100% { transform: scale(0.6); background: #cbd5e1; }
      40%         { transform: scale(1);   background: var(--snkr-c, #ff444f); }
    }

    /* ── Empty state ───────────── */
    #snkr-empty {
      flex: 1; display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 24px 20px; text-align: center; gap: 20px;
    }
    #snkr-empty-icon {
      width: 56px; height: 56px; border-radius: 50%;
      background: linear-gradient(135deg, var(--snkr-c, #ff444f), var(--snkr-cd, #c8102e));
      display: flex; align-items: center; justify-content: center; font-size: 24px;
      box-shadow: 0 4px 16px rgba(var(--snkr-rgb,255,68,79),0.3);
    }
    #snkr-empty-title { font-size: 16px; font-weight: 700; color: #0f172a; }
    #snkr-empty-desc { font-size: 13px; color: #64748b; line-height: 1.55; max-width: 280px; }
    #snkr-suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; width: 100%; }
    .snkr-chip {
      background: #fff; border: 1.5px solid #e2e8f0; border-radius: 20px;
      padding: 7px 13px; font-size: 12px; font-weight: 500; color: #374151;
      cursor: pointer; transition: border-color 0.15s, color 0.15s, box-shadow 0.15s;
      font-family: inherit; outline: none; text-align: left; max-width: 100%;
    }
    .snkr-chip:hover {
      border-color: var(--snkr-c, #ff444f); color: var(--snkr-c, #ff444f);
      box-shadow: 0 2px 8px rgba(var(--snkr-rgb,255,68,79),0.15);
    }

    /* ── Footer ────────────────── */
    #snkr-footer {
      padding: 10px 12px; background: #fff; border-top: 1px solid #f1f5f9;
      display: flex; align-items: flex-end; gap: 9px; flex-shrink: 0;
    }
    #snkr-input-wrap {
      flex: 1; background: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 14px;
      display: flex; align-items: flex-end; padding: 8px 12px;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    #snkr-input-wrap:focus-within {
      border-color: var(--snkr-c, #ff444f); background: #fff;
      box-shadow: 0 0 0 3px rgba(var(--snkr-rgb,255,68,79),0.1);
    }
    #snkr-input {
      flex: 1; border: none; outline: none; background: transparent;
      font-family: 'Inter', system-ui, sans-serif; font-size: 14px; color: #0f172a;
      resize: none; max-height: 100px; min-height: 22px; line-height: 1.5;
    }
    #snkr-input::placeholder { color: #94a3b8; }
    #snkr-input:disabled { opacity: 0.6; cursor: not-allowed; }
    #snkr-send {
      width: 36px; height: 36px; border-radius: 11px; border: none;
      background: linear-gradient(135deg, var(--snkr-c, #ff444f), var(--snkr-cd, #c8102e));
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      padding: 0; flex-shrink: 0; outline: none;
      box-shadow: 0 2px 8px rgba(var(--snkr-rgb,255,68,79),0.3);
      transition: opacity 0.15s, transform 0.15s;
    }
    #snkr-send:hover:not(:disabled) { opacity: 0.87; transform: scale(1.06); }
    #snkr-send:disabled { opacity: 0.35; cursor: not-allowed; box-shadow: none; }

    /* ── Branding ───────────────── */
    #snkr-branding {
      text-align: center; padding: 6px 0 9px; font-size: 11px; color: #c0cad8;
      font-family: 'Inter', system-ui, sans-serif; background: #fff; flex-shrink: 0;
    }
    #snkr-branding a { color: var(--snkr-c, #ff444f); text-decoration: none; font-weight: 500; }
    #snkr-branding a:hover { text-decoration: underline; }

    /* ── Loading skeleton ─────── */
    #snkr-loading {
      flex: 1; display: flex; align-items: center; justify-content: center;
      background: #f8fafc; flex-direction: column; gap: 12px;
    }
    .snkr-sk { background: #e2e8f0; border-radius: 8px; animation: snkr-sk 1.4s ease-in-out infinite; }
    @keyframes snkr-sk { 0%,100%{opacity:0.5} 50%{opacity:1} }

    /* ── Mobile ─────────────────── */
    @media (max-width: 480px) {
      #snkr-panel { width: calc(100vw - 16px); height: calc(100dvh - 100px); right: 8px; bottom: 88px; border-radius: 16px; }
      #snkr-toggle { right: 16px; bottom: 20px; }
    }
  `;

  // ─── Icons ────────────────────────────────────────────────────────────────────

  var I = {
    chat: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    x:    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    xsm:  '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    send: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13" stroke="#fff" stroke-width="2.5"/><polygon points="22 2 15 22 11 13 2 9 22 2" fill="#fff"/></svg>',
  };

  // ─── Widget ───────────────────────────────────────────────────────────────────

  function Widget(cfg) {
    this.widgetId       = cfg.widgetId;
    this.apiKey         = cfg.apiKey;
    this.apiUrl         = (cfg.apiUrl || "http://localhost:5001/api/v1").replace(/\/$/, "");
    this.sessionId      = uid();
    this.conversationId = null;
    this.streaming      = false;
    this._isOpen        = false;
    this._agentBubble   = null;
    this._agentText     = "";
    this._typingEl      = null;
    this._cfg = {
      agentName: "AI Assistant",
      agentAvatar: "",
      agentDescription: "",
      welcomeMessage: "",
      placeholder: "Type a message…",
      primaryColor: "#ff444f",
      suggestions: [],
    };

    this._mount();
    this._loadConfig();
  }

  Widget.prototype._mount = function () {
    var self = this;
    var color = "#ff444f";

    var host = document.createElement("div");
    host.id = "snkr-" + this.widgetId;
    host.style.setProperty("--snkr-c",   color);
    host.style.setProperty("--snkr-cd",  darkenHex(color, 50));
    host.style.setProperty("--snkr-rgb", hexToRgb(color));
    document.body.appendChild(host);
    this._host = host;

    var shadow = host.attachShadow({ mode: "open" });
    var styleEl = document.createElement("style");
    styleEl.textContent = CSS;
    shadow.appendChild(styleEl);

    // Toggle button
    var toggle = document.createElement("button");
    toggle.id = "snkr-toggle";
    toggle.setAttribute("aria-label", "Open chat");
    toggle.innerHTML = I.chat;
    shadow.appendChild(toggle);

    // Panel
    var panel = document.createElement("div");
    panel.id = "snkr-panel";
    panel.setAttribute("role", "dialog");

    // Header
    var header = document.createElement("div");
    header.id = "snkr-header";
    header.innerHTML =
      '<div id="snkr-hdr-left">' +
        '<div id="snkr-avatar">🤖</div>' +
        '<div id="snkr-hdr-info">' +
          '<div id="snkr-hdr-name">AI Assistant</div>' +
          '<div id="snkr-hdr-status">Online &amp; ready</div>' +
        '</div>' +
      '</div>' +
      '<button id="snkr-close" aria-label="Close">' + I.xsm + '</button>';

    // Body
    var body = document.createElement("div");
    body.id = "snkr-body";
    body.style.cssText = "flex:1;display:flex;flex-direction:column;overflow:hidden;";

    var loading = document.createElement("div");
    loading.id = "snkr-loading";
    loading.innerHTML =
      '<div class="snkr-sk" style="width:120px;height:12px;"></div>' +
      '<div class="snkr-sk" style="width:80px;height:10px;"></div>';
    body.appendChild(loading);

    var messages = document.createElement("div");
    messages.id = "snkr-messages";
    messages.style.display = "none";
    body.appendChild(messages);

    // Footer
    var footer = document.createElement("div");
    footer.id = "snkr-footer";
    var inputWrap = document.createElement("div");
    inputWrap.id = "snkr-input-wrap";
    var input = document.createElement("textarea");
    input.id = "snkr-input";
    input.rows = 1;
    input.placeholder = "Type a message…";
    input.setAttribute("aria-label", "Message");
    var sendBtn = document.createElement("button");
    sendBtn.id = "snkr-send";
    sendBtn.setAttribute("aria-label", "Send");
    sendBtn.innerHTML = I.send;
    inputWrap.appendChild(input);
    footer.appendChild(inputWrap);
    footer.appendChild(sendBtn);

    var branding = document.createElement("div");
    branding.id = "snkr-branding";
    if (cfg.brandingText !== false) {
      var bText = cfg.brandingText || "Powered by AI";
      var bUrl  = cfg.brandingUrl;
      branding.innerHTML = bUrl
        ? bText.replace(/^(Powered by )(.+)$/, '$1<a href="' + esc(bUrl) + '" target="_blank" rel="noopener">$2</a>')
        : esc(bText);
    }

    panel.appendChild(header);
    panel.appendChild(body);
    panel.appendChild(footer);
    panel.appendChild(branding);
    shadow.appendChild(panel);

    // Save refs
    this._shadow   = shadow;
    this._toggle   = toggle;
    this._panel    = panel;
    this._body     = body;
    this._loading  = loading;
    this._messages = messages;
    this._input    = input;
    this._sendBtn  = sendBtn;

    // Copy button handler (event delegation inside shadow DOM)
    messages.addEventListener("click", function (e) {
      if (e.target.classList.contains("snkr-copy-btn")) {
        var btn = e.target;
        var pre = btn.closest(".snkr-pre");
        var code = pre && pre.querySelector("code");
        if (code && navigator.clipboard) {
          navigator.clipboard.writeText(code.innerText).then(function () {
            btn.textContent = "Copied!";
            setTimeout(function () { btn.textContent = "Copy"; }, 1500);
          }).catch(function () {
            btn.textContent = "Failed";
            setTimeout(function () { btn.textContent = "Copy"; }, 1500);
          });
        }
      }
      // Click image to open full size
      if (e.target.classList.contains("snkr-img")) {
        window.open(e.target.src, "_blank");
      }
    });

    // Events
    toggle.addEventListener("click", function (e) {
      e.stopPropagation();
      self._isOpen ? self.close() : self.open();
    });
    shadow.getElementById("snkr-close").addEventListener("click", function (e) {
      e.stopPropagation();
      self.close();
    });
    sendBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      self._send();
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); self._send(); }
    });
    input.addEventListener("input", function () {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 100) + "px";
    });
    document.addEventListener("click", function (e) {
      if (self._isOpen && e.target !== host) self.close();
    });
  };

  // ── Load config ───────────────────────────────────────────────────────────────

  Widget.prototype._loadConfig = function () {
    var self = this;
    fetch(this.apiUrl + "/widgets/config", {
      headers: { "X-Widget-API-Key": this.apiKey },
    })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (!data) { self._applyConfig({}); return; }
        self._applyConfig({
          agentName:        data.agent_name || "",
          agentAvatar:      data.agent_avatar || "",
          agentDescription: data.agent_description || "",
          welcomeMessage:   (data.theme && data.theme.welcome_message) || "",
          placeholder:      (data.theme && data.theme.placeholder) || "",
          primaryColor:     (data.theme && data.theme.primary_color) || "",
          suggestions:      data.suggestion_prompts || [],
        });
      })
      .catch(function () { self._applyConfig({}); });
  };

  Widget.prototype._applyConfig = function (c) {
    var self = this;
    var cfg = this._cfg;
    cfg.agentName        = c.agentName        || "AI Assistant";
    cfg.agentAvatar      = c.agentAvatar      || "";
    cfg.agentDescription = c.agentDescription || "";
    cfg.welcomeMessage   = c.welcomeMessage   || ("Hi! I'm " + cfg.agentName + ". How can I help you today?");
    cfg.placeholder      = c.placeholder      || "Type a message…";
    cfg.primaryColor     = c.primaryColor     || "#ff444f";
    cfg.suggestions      = Array.isArray(c.suggestions) ? c.suggestions : [];

    var color = cfg.primaryColor;
    this._host.style.setProperty("--snkr-c",   color);
    this._host.style.setProperty("--snkr-cd",  darkenHex(color, 50));
    this._host.style.setProperty("--snkr-rgb", hexToRgb(color));

    var nameEl   = this._shadow.getElementById("snkr-hdr-name");
    var avatarEl = this._shadow.getElementById("snkr-avatar");
    if (nameEl) nameEl.textContent = cfg.agentName;
    if (avatarEl) {
      avatarEl.innerHTML = cfg.agentAvatar
        ? '<img src="' + esc(cfg.agentAvatar) + '" alt="' + esc(cfg.agentName) + '">'
        : cfg.agentName.charAt(0).toUpperCase();
    }

    this._input.placeholder = cfg.placeholder;
    if (this._loading) this._loading.style.display = "none";
    this._messages.style.display = "flex";
    this._buildEmptyState();
  };

  Widget.prototype._buildEmptyState = function () {
    var self = this;
    var cfg = this._cfg;

    var old = this._shadow.getElementById("snkr-empty");
    if (old) old.parentNode.removeChild(old);

    var empty = document.createElement("div");
    empty.id = "snkr-empty";

    var icon = document.createElement("div");
    icon.id = "snkr-empty-icon";
    icon.innerHTML = cfg.agentAvatar
      ? '<img src="' + esc(cfg.agentAvatar) + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'
      : cfg.agentName.charAt(0).toUpperCase();

    var title = document.createElement("div");
    title.id = "snkr-empty-title";
    title.textContent = cfg.agentName;

    var desc = document.createElement("div");
    desc.id = "snkr-empty-desc";
    desc.textContent = cfg.welcomeMessage;

    empty.appendChild(icon);
    empty.appendChild(title);
    empty.appendChild(desc);

    if (cfg.suggestions.length > 0) {
      var chips = document.createElement("div");
      chips.id = "snkr-suggestions";
      cfg.suggestions.forEach(function (s) {
        var label = s.title || s.prompt || (typeof s === "string" ? s : "");
        if (!label) return;
        var chip = document.createElement("button");
        chip.className = "snkr-chip";
        chip.textContent = label;
        chip.addEventListener("click", function (e) {
          e.stopPropagation();
          self._input.value = s.prompt || s.title || label;
          self._send();
        });
        chips.appendChild(chip);
      });
      empty.appendChild(chips);
    }

    this._body.insertBefore(empty, this._messages);
    this._emptyState = empty;
  };

  // ── Open / Close ──────────────────────────────────────────────────────────────

  Widget.prototype.open = function () {
    this._isOpen = true;
    this._toggle.innerHTML = I.x;
    this._toggle.setAttribute("aria-label", "Close chat");
    this._panel.classList.add("open");
    this._input.focus();
  };

  Widget.prototype.close = function () {
    this._isOpen = false;
    this._toggle.innerHTML = I.chat;
    this._toggle.setAttribute("aria-label", "Open chat");
    this._panel.classList.remove("open");
  };

  // ── Messages ──────────────────────────────────────────────────────────────────

  Widget.prototype._hideEmpty = function () {
    if (this._emptyState) this._emptyState.style.display = "none";
    this._messages.style.display = "flex";
  };

  Widget.prototype._row = function (type) {
    this._hideEmpty();
    var row = document.createElement("div");
    row.className = "snkr-row " + type;
    var bubble = document.createElement("div");
    bubble.className = "snkr-bubble";
    var ts = document.createElement("div");
    ts.className = "snkr-ts";
    ts.textContent = timeNow();
    row.appendChild(bubble);
    row.appendChild(ts);
    this._messages.appendChild(row);
    this._scroll();
    return bubble;
  };

  Widget.prototype._addAgent = function () {
    return this._row("agent");
  };

  Widget.prototype._addUser = function (text) {
    var b = this._row("user");
    b.textContent = text;
  };

  Widget.prototype._addError = function (text) {
    var b = this._row("error");
    b.textContent = text;
  };

  Widget.prototype._typing = function () {
    this._hideEmpty();
    var wrap = document.createElement("div");
    wrap.className = "snkr-row agent";
    var dots = document.createElement("div");
    dots.id = "snkr-typing";
    dots.innerHTML = "<span></span><span></span><span></span>";
    wrap.appendChild(dots);
    this._messages.appendChild(wrap);
    this._scroll();
    return wrap;
  };

  Widget.prototype._remove = function (el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  };

  Widget.prototype._scroll = function () {
    this._messages.scrollTop = this._messages.scrollHeight;
  };

  Widget.prototype._busy = function (on) {
    this.streaming = on;
    this._sendBtn.disabled = on;
    this._input.disabled = on;
  };

  // ── Send & Stream ─────────────────────────────────────────────────────────────

  Widget.prototype._send = function () {
    var text = this._input.value.trim();
    if (!text || this.streaming) return;

    this._input.value = "";
    this._input.style.height = "auto";
    this._addUser(text);

    var self = this;
    this._typingEl = this._typing();
    this._busy(true);
    this._agentText   = "";
    this._agentBubble = null;

    fetch(this.apiUrl + "/widgets/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Widget-API-Key": this.apiKey,
      },
      body: JSON.stringify({
        message: text,
        session_id: this.sessionId,
        conversation_id: this.conversationId || undefined,
      }),
    })
      .then(function (res) {
        if (!res.ok) {
          return res.text().then(function (t) { throw new Error(t || "HTTP " + res.status); });
        }
        return res;
      })
      .then(function (res) {
        var reader = res.body.getReader();
        var dec    = new TextDecoder();
        var buf    = "";

        function pump() {
          return reader.read().then(function (r) {
            if (r.done) { self._finish(); return; }
            buf += dec.decode(r.value, { stream: true });
            var parts = buf.split("\n\n");
            buf = parts.pop();
            parts.forEach(function (p) {
              p.split("\n").forEach(function (line) {
                if (line.slice(0, 6) === "data: ") self._evt(line.slice(6));
              });
            });
            return pump();
          });
        }
        return pump();
      })
      .catch(function (err) {
        self._remove(self._typingEl);
        self._typingEl = null;
        self._remove(self._agentBubble);
        self._agentBubble = null;
        self._addError("Sorry, something went wrong. Please try again.");
        console.error("[SynkoraWidget]", err.message);
        self._finish();
      });
  };

  Widget.prototype._evt = function (raw) {
    var evt;
    try { evt = JSON.parse(raw); } catch (_) { return; }

    if (evt.type === "chunk" && evt.content) {
      // Remove typing dots on first chunk
      if (this._typingEl) {
        this._remove(this._typingEl);
        this._typingEl = null;
      }
      this._agentText += evt.content;
      if (!this._agentBubble) {
        this._agentBubble = this._addAgent();
        this._agentBubble.classList.add("streaming");
      }
      this._agentBubble.innerHTML = mdParse(this._agentText, true);
      this._scroll();

    } else if (evt.type === "done") {
      if (evt.metadata && evt.metadata.conversation_id) {
        this.conversationId = evt.metadata.conversation_id;
      }

    } else if (evt.type === "error") {
      var msg = evt.error || evt.content || "An error occurred.";
      if (this._agentBubble) {
        this._agentBubble.closest(".snkr-row").className = "snkr-row error";
        this._agentBubble.textContent = msg;
        this._agentBubble.classList.remove("streaming");
      } else {
        this._addError(msg);
      }
    }
  };

  Widget.prototype._finish = function () {
    // Remove typing dots if stream ended before any chunk (error case)
    if (this._typingEl) {
      this._remove(this._typingEl);
      this._typingEl = null;
    }
    // Final clean render without streaming flag, remove cursor
    if (this._agentBubble) {
      this._agentBubble.innerHTML = mdParse(this._agentText, false);
      this._agentBubble.classList.remove("streaming");
    }
    this._busy(false);
    this._agentBubble = null;
    this._agentText   = "";
    this._input.focus();
  };

  // ─── Public API ────────────────────────────────────────────────────────────────

  global.SynkoraWidget = {
    _i: {},
    init: function (cfg) {
      if (!cfg || !cfg.widgetId || !cfg.apiKey) {
        console.error("[SynkoraWidget] widgetId and apiKey are required.");
        return;
      }
      if (this._i[cfg.widgetId]) return;
      var w = new Widget(cfg);
      this._i[cfg.widgetId] = w;
      return w;
    },
    open:  function (id) { var w = this._i[id]; if (w) w.open(); },
    close: function (id) { var w = this._i[id]; if (w) w.close(); },
  };

})(window);
