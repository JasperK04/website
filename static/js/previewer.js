/* previewer.js - Code previewer: token renderer + file switching */

(function () {
  "use strict";

  // -----------------------------------------------------------------------
  // Configuration injected by the template via data attributes
  // -----------------------------------------------------------------------
  const previewerEl = document.getElementById("previewer-root");
  if (!previewerEl) return;

  const projectName = previewerEl.dataset.project;
  const mainFile = previewerEl.dataset.mainFile;
  const filesAttr = previewerEl.dataset.files;
  const files = JSON.parse(filesAttr || "[]");

  // DOM targets
  const fileListEl = document.getElementById("file-list");
  const codePane = document.getElementById("code-pane-content");
  const codeFilename = document.getElementById("code-filename");
  const codeLangBadge = document.getElementById("code-lang-badge");

  // -----------------------------------------------------------------------
  // File extension helpers
  // -----------------------------------------------------------------------
  function getExt(filename) {
    const parts = filename.split(".");
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
  }

  function getLang(filename) {
    const ext = getExt(filename);
    const map = {
      py: "Python",
      js: "JavaScript",
      ts: "TypeScript",
      html: "HTML",
      css: "CSS",
      md: "Markdown",
      json: "JSON",
      yaml: "YAML",
      yml: "YAML",
      sh: "Shell",
      txt: "Text",
    };
    return map[ext] || ext.toUpperCase() || "Text";
  }

  function getFileIcon(filename) {
    const ext = getExt(filename);
    const icons = {
      py: "🐍",
      js: "📜",
      ts: "📘",
      html: "🌐",
      css: "🎨",
      md: "📝",
      json: "📋",
      yaml: "📋",
      yml: "📋",
      sh: "⚙️",
    };
    return icons[ext] || "📄";
  }

  // -----------------------------------------------------------------------
  // Build file list sidebar
  // -----------------------------------------------------------------------
  let currentFile = null;

  files.forEach(function (filename) {
    const li = document.createElement("li");
    li.className = "file-item";
    li.dataset.file = filename;
    li.setAttribute("role", "button");
    li.setAttribute("tabindex", "0");

    const icon = document.createElement("span");
    icon.className = "file-icon";
    icon.textContent = getFileIcon(filename);

    const name = document.createElement("span");
    name.textContent = filename;

    li.appendChild(icon);
    li.appendChild(name);

    li.addEventListener("click", function () {
      loadFile(filename);
    });

    li.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        loadFile(filename);
      }
    });

    fileListEl.appendChild(li);
  });

  // -----------------------------------------------------------------------
  // Token renderer
  // -----------------------------------------------------------------------

  /**
   * Render a list of token objects into the code pane with line numbers.
   * Tokens: [{type, value, line, col}, ...]
   * Lines are reconstructed from tokens, then rendered row by row.
   */
  function renderTokens(tokens) {
    // Group tokens by line number, preserving order
    const lineMap = {};
    tokens.forEach(function (tok) {
      if (
        tok.type === "newline" ||
        tok.type === "nl" ||
        tok.type === "endmarker" ||
        tok.type === "dedent" ||
        tok.type === "indent"
      ) {
        return; // skip structural tokens
      }
      const ln = tok.line;
      if (!lineMap[ln]) lineMap[ln] = [];
      lineMap[ln].push(tok);
    });

    const lineNums = Object.keys(lineMap)
      .map(Number)
      .sort((a, b) => a - b);

    if (lineNums.length === 0) {
      codePane.innerHTML = '<div class="code-loading">Empty file</div>';
      return;
    }

    const table = document.createElement("div");
    table.className = "code-table";

    // Fill any gaps (blank lines between functions, etc.)
    const maxLine = lineNums[lineNums.length - 1];
    for (let ln = 1; ln <= maxLine; ln++) {
      const row = document.createElement("div");
      row.className = "code-row";

      const numCell = document.createElement("span");
      numCell.className = "line-num";
      numCell.textContent = ln;

      const codeCell = document.createElement("span");
      codeCell.className = "line-code";

      const lineToks = lineMap[ln] || [];
      lineToks.forEach(function (tok) {
        const span = document.createElement("span");
        span.className = "tok-" + tok.type;
        span.textContent = tok.value;
        codeCell.appendChild(span);
      });

      row.appendChild(numCell);
      row.appendChild(codeCell);
      table.appendChild(row);
    }

    codePane.innerHTML = "";
    codePane.appendChild(table);
  }

  /**
   * Render raw text (non-Python files) with line numbers.
   */
  function renderRaw(source) {
    const lines = source.split("\n");
    // Remove trailing empty line from split
    if (lines[lines.length - 1] === "") lines.pop();

    const table = document.createElement("div");
    table.className = "code-table";

    lines.forEach(function (lineText, idx) {
      const row = document.createElement("div");
      row.className = "code-row";

      const numCell = document.createElement("span");
      numCell.className = "line-num";
      numCell.textContent = idx + 1;

      const codeCell = document.createElement("span");
      codeCell.className = "line-code tok-other";
      codeCell.textContent = lineText;

      row.appendChild(numCell);
      row.appendChild(codeCell);
      table.appendChild(row);
    });

    codePane.innerHTML = "";
    codePane.appendChild(table);
  }

  /**
   * Render a Markdown file as formatted HTML.
   * Uses a simple hand-written Markdown→HTML converter
   * (no external dependencies, pure JS).
   */
  function renderMarkdown(source) {
    const html = markdownToHtml(source);
    const div = document.createElement("div");
    div.className = "md-content";
    div.innerHTML = html;
    codePane.innerHTML = "";
    codePane.appendChild(div);
  }

  // -----------------------------------------------------------------------
  // Minimal Markdown renderer
  // -----------------------------------------------------------------------
  function escHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function markdownToHtml(md) {
    const lines = md.split("\n");
    const out = [];
    let inCode = false;
    let inList = false;
    let inTable = false;

    function closeList() {
      if (inList) { out.push("</ul>"); inList = false; }
    }
    function closeTable() {
      if (inTable) { out.push("</tbody></table>"); inTable = false; }
    }

    lines.forEach(function (line) {
      // Fenced code block
      if (line.trim().startsWith("```")) {
        if (inCode) {
          out.push("</code></pre>");
          inCode = false;
        } else {
          closeList(); closeTable();
          const lang = line.trim().slice(3).trim();
          out.push('<pre><code class="lang-' + escHtml(lang) + '">');
          inCode = true;
        }
        return;
      }

      if (inCode) {
        out.push(escHtml(line));
        return;
      }

      // Headings
      const hMatch = line.match(/^(#{1,6})\s+(.*)/);
      if (hMatch) {
        closeList(); closeTable();
        const level = hMatch[1].length;
        out.push("<h" + level + ">" + inlineFormat(hMatch[2]) + "</h" + level + ">");
        return;
      }

      // Horizontal rule
      if (/^[-*_]{3,}\s*$/.test(line)) {
        closeList(); closeTable();
        out.push("<hr>");
        return;
      }

      // Unordered list
      const liMatch = line.match(/^[\*\-]\s+(.*)/);
      if (liMatch) {
        closeTable();
        if (!inList) { out.push("<ul>"); inList = true; }
        out.push("<li>" + inlineFormat(liMatch[1]) + "</li>");
        return;
      }

      // Table row (simple)
      if (line.includes("|") && line.trim().startsWith("|")) {
        closeList();
        if (!inTable) {
          out.push('<table><tbody>');
          inTable = true;
        }
        // Skip separator row
        if (/^\|[\s\-|:]+\|$/.test(line.trim())) return;
        const cells = line.trim().replace(/^\||\|$/g, "").split("|");
        const isHeader = out.length > 0 && out[out.length - 1] === '<table><tbody>';
        const tag = isHeader ? "th" : "td";
        out.push("<tr>" + cells.map(function (c) {
          return "<" + tag + ">" + inlineFormat(c.trim()) + "</" + tag + ">";
        }).join("") + "</tr>");
        return;
      }

      closeList();
      closeTable();

      // Empty line → paragraph break
      if (line.trim() === "") {
        out.push("<p></p>");
        return;
      }

      out.push("<p>" + inlineFormat(line) + "</p>");
    });

    closeList();
    closeTable();
    if (inCode) out.push("</code></pre>");

    return out.join("\n");
  }

  function inlineFormat(text) {
    // Escape HTML first
    text = escHtml(text);
    // Bold
    text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Italic
    text = text.replace(/\*(.*?)\*/g, "<em>$1</em>");
    // Inline code
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Links
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return text;
  }

  // -----------------------------------------------------------------------
  // Load a file
  // -----------------------------------------------------------------------
  function setActiveFile(filename) {
    currentFile = filename;
    codeFilename.textContent = filename;
    codeLangBadge.textContent = getLang(filename);

    // Update active state in file list
    fileListEl.querySelectorAll(".file-item").forEach(function (li) {
      li.classList.toggle("active", li.dataset.file === filename);
    });
  }

  function showLoading() {
    codePane.innerHTML = '<div class="code-loading">Loading…</div>';
  }

  function showError(msg) {
    codePane.innerHTML = '<div class="code-error">Error: ' + escHtml(msg) + '</div>';
  }

  function buildCodeUrl(filename, suffix) {
    return "/code/" + encodeURIComponent(projectName) + "/" +
           encodeURIComponent(filename) + (suffix || "");
  }

  function loadFile(filename) {
    if (filename === currentFile) return;
    setActiveFile(filename);
    showLoading();

    const ext = getExt(filename);

    if (ext === "py") {
      // Fetch tokenized version for syntax highlighting
      fetch(buildCodeUrl(filename, "/tokens"))
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.json();
        })
        .then(function (data) {
          renderTokens(data.tokens);
        })
        .catch(function (err) {
          showError(err.message);
        });
    } else if (ext === "md") {
      // Fetch raw content and render as Markdown
      fetch(buildCodeUrl(filename))
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.text();
        })
        .then(function (text) {
          renderMarkdown(text);
        })
        .catch(function (err) {
          showError(err.message);
        });
    } else {
      // Fetch raw content and render with line numbers (no highlighting)
      fetch(buildCodeUrl(filename))
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.text();
        })
        .then(function (text) {
          renderRaw(text);
        })
        .catch(function (err) {
          showError(err.message);
        });
    }
  }

  // -----------------------------------------------------------------------
  // Initial load: load main_file on page load
  // -----------------------------------------------------------------------
  if (mainFile) {
    loadFile(mainFile);
  } else if (files.length > 0) {
    loadFile(files[0]);
  }

})();
