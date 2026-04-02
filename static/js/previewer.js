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
  const assetRoot = previewerEl.dataset.assetRoot;
  const filesAttr = previewerEl.dataset.files;
  const files = JSON.parse(filesAttr || "[]");

  const storagePrefix = "previewer:" + projectName + ":";

  function getStorage(key) {
    try {
      return window.localStorage.getItem(storagePrefix + key);
    } catch (err) {
      return null;
    }
  }

  function setStorage(key, value) {
    try {
      window.localStorage.setItem(storagePrefix + key, value);
    } catch (err) {
      return;
    }
  }

  function clearProjectState() {
    try {
      const keys = [];
      for (let i = 0; i < window.localStorage.length; i++) {
        const key = window.localStorage.key(i);
        if (key && key.startsWith(storagePrefix)) {
          keys.push(key);
        }
      }
      keys.forEach(function (key) {
        window.localStorage.removeItem(key);
      });
    } catch (err) {
      return;
    }
  }

  (function handleNavigationReset() {
    const navEntries = window.performance && window.performance.getEntriesByType
      ? window.performance.getEntriesByType("navigation")
      : [];
    const navType = navEntries.length > 0 ? navEntries[0].type : "navigate";
    if (navType !== "reload") {
      clearProjectState();
    }
  })();

  // DOM targets
  const fileListEl = document.getElementById("file-list");
  const codePane = document.getElementById("code-pane-content");
  const codeFilename = document.getElementById("code-filename");
  const codeLangBadge = document.getElementById("code-lang-badge");
  const copyBtn = document.getElementById("copy-code-btn");

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
      xml: "XML",
      asm: "ASM",
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
      java: "☕",
      html: "🌐",
      css: "🎨",
      md: "📝",
      json: "📋",
      yaml: "📋",
      xml: "🧩",
      asm: "🧠",
      sh: "⚙️",
    };
    return icons[ext] || "📄";
  }

  // -----------------------------------------------------------------------
  // Build file list sidebar (tree view)
  // -----------------------------------------------------------------------
  let currentFile = null;

  function createNode(name) {
    return { name: name, children: new Map(), files: [] };
  }

  function insertPath(root, filepath) {
    const parts = filepath.split("/");
    let node = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;
      if (isFile) {
        node.files.push(filepath);
        return;
      }
      if (!node.children.has(part)) {
        node.children.set(part, createNode(part));
      }
      node = node.children.get(part);
    }
  }

  function compressTree(node) {
    const children = Array.from(node.children.values()).map(compressTree);
    node.children = new Map(children.map(function (child) {
      return [child.name, child];
    }));

    while (node.files.length === 0 && node.children.size === 1) {
      const onlyChild = node.children.values().next().value;
      node.name = node.name ? node.name + "/" + onlyChild.name : onlyChild.name;
      node.files = onlyChild.files;
      node.children = onlyChild.children;
    }
    return node;
  }

  function buildTree(fileList) {
    const root = createNode("");
    fileList.forEach(function (filepath) {
      insertPath(root, filepath);
    });
    return compressTree(root);
  }

  function renderTree(node, container, depth, parentPath) {
    const entries = [];
    node.children.forEach(function (child) {
      entries.push({ type: "dir", node: child });
    });
    node.files.forEach(function (filepath) {
      entries.push({ type: "file", filepath: filepath });
    });

    entries.sort(function (a, b) {
      if (a.type !== b.type) {
        return a.type === "dir" ? -1 : 1;
      }
      const nameA = a.type === "dir" ? a.node.name : a.filepath.split("/").pop();
      const nameB = b.type === "dir" ? b.node.name : b.filepath.split("/").pop();
      return nameA.localeCompare(nameB);
    });

    entries.forEach(function (entry) {
      if (entry.type === "dir") {
        const folderPath = parentPath ? parentPath + "/" + entry.node.name : entry.node.name;
        const li = document.createElement("li");
        li.className = "file-folder";

        const header = document.createElement("button");
        header.type = "button";
        header.className = "file-folder-toggle";
        const saved = getStorage("folder:" + folderPath);
        const isExpanded = saved === "expanded";
        header.setAttribute("aria-expanded", isExpanded ? "true" : "false");

        const caret = document.createElement("span");
        caret.className = "folder-caret";
        caret.textContent = isExpanded ? "▾" : "▸";

        const folderIcon = document.createElement("span");
        folderIcon.className = "folder-icon";
        folderIcon.textContent = "📁";

        const name = document.createElement("span");
        name.className = "folder-name";
        name.textContent = entry.node.name;

        header.appendChild(caret);
        header.appendChild(folderIcon);
        header.appendChild(name);

        const childList = document.createElement("ul");
        childList.className = "file-list";
        childList.dataset.depth = depth + 1;
        if (!isExpanded) {
          childList.classList.add("collapsed");
        }

        header.addEventListener("click", function () {
          const expanded = header.getAttribute("aria-expanded") === "true";
          header.setAttribute("aria-expanded", expanded ? "false" : "true");
          childList.classList.toggle("collapsed", expanded);
          caret.textContent = expanded ? "▸" : "▾";
          setStorage("folder:" + folderPath, expanded ? "collapsed" : "expanded");
        });

        li.appendChild(header);
        li.appendChild(childList);
        container.appendChild(li);

        renderTree(entry.node, childList, depth + 1, folderPath);
      } else {
        const filename = entry.filepath;
        const li = document.createElement("li");
        li.className = "file-item";
        li.dataset.file = filename;
        li.setAttribute("role", "button");
        li.setAttribute("tabindex", "0");

        const icon = document.createElement("span");
        icon.className = "file-icon";
        icon.textContent = getFileIcon(filename);

        const name = document.createElement("span");
        name.textContent = filename.split("/").pop();

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

        container.appendChild(li);
      }
    });
  }

  const tree = buildTree(files);
  renderTree(tree, fileListEl, 0, "");

  // -----------------------------------------------------------------------
  // Token renderer
  // -----------------------------------------------------------------------

  /**
   * Render a list of token objects into the code pane with line numbers.
   * Tokens: [{type, value, line, col}, ...]
   * Lines are reconstructed from tokens, then rendered row by row.
   */
  function renderTokensInto(tokens, container, opts) {
    const config = opts || {};
    const showLineNumbers = config.lineNumbers !== false;
    const padBlankLines = config.padBlankLines !== false;
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
      container.innerHTML = '<div class="code-loading">Empty file</div>';
      return;
    }

    const table = document.createElement("div");
    table.className = "code-table";

    // Fill any gaps (blank lines between functions, etc.)
    let bracketStack = [];
    const maxLine = lineNums[lineNums.length - 1];
    const startLine = padBlankLines ? 0 : 1;
    const endLine = padBlankLines ? maxLine + 1 : maxLine;
    for (let ln = startLine; ln <= endLine; ln++) {
      const row = document.createElement("div");
      row.className = "code-row";

      const codeCell = document.createElement("span");
      codeCell.className = "line-code";

      const lineToks = (padBlankLines && (ln === 0 || ln === maxLine + 1))
        ? []
        : (lineMap[ln] || []);
      let cursor = 0;
      lineToks.forEach(function (tok) {
        if (tok.col > cursor) {
          codeCell.appendChild(document.createTextNode(" ".repeat(tok.col - cursor)));
        }
        appendTokenWithBrackets(codeCell, tok, bracketStack);
        cursor = tok.col + tok.value.length;
      });

      if (showLineNumbers) {
        const numCell = document.createElement("span");
        numCell.className = "line-num";
        numCell.textContent = ln + 1;
        row.appendChild(numCell);
      }
      row.appendChild(codeCell);
      table.appendChild(row);
    }

    container.innerHTML = "";
    container.appendChild(table);
  }

  function renderTokens(tokens) {
    renderTokensInto(tokens, codePane, { lineNumbers: true, padBlankLines: true });
  }

  function appendTokenWithBrackets(container, tok, bracketStack) {
    if (tok.type !== "op") {
      const span = document.createElement("span");
      span.className = "tok-" + tok.type;
      span.textContent = tok.value;
      container.appendChild(span);
      return;
    }

    const chars = tok.value.split("");
    chars.forEach(function (ch) {
      if (!"()[]{}".includes(ch)) {
        const span = document.createElement("span");
        span.className = "tok-" + tok.type;
        span.textContent = ch;
        container.appendChild(span);
        return;
      }

      const isOpening = "([{".includes(ch);
      const depth = isOpening ? bracketStack.length + 1 : bracketStack.length;
      const level = depth === 0 ? 1 : ((depth - 1) % 3) + 1;
      const span = document.createElement("span");
      span.className = "tok-bracket-" + level;
      span.textContent = ch;
      container.appendChild(span);

      if (isOpening) {
        bracketStack.push(ch);
      } else if (bracketStack.length > 0) {
        bracketStack.pop();
      }
    });
  }

  /**
   * Render raw text (non-Python files) with line numbers.
   */
  function renderRaw(source) {
    const lines = source.split("\n");
    // Remove trailing empty line from split
    if (lines[lines.length - 1] === "") lines.pop();
    lines.unshift("");
    lines.push("");

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
  function renderMarkdown(source, filename) {
    const html = window.renderMarkdownEnhanced
      ? window.renderMarkdownEnhanced(source, {
        projectName: projectName,
        assetRoot: assetRoot,
        currentFile: filename,
      })
      : markdownToHtml(source);
    const div = document.createElement("div");
    div.className = "md-content";
    div.innerHTML = html;
    codePane.innerHTML = "";
    codePane.appendChild(div);
    renderMarkdownCodeBlocks(div);
  }

  function renderMarkdownCodeBlocks(container) {
    const blocks = Array.from(container.querySelectorAll(".md-codeblock[data-lang][data-code]"));
    if (blocks.length === 0) return;

    blocks.forEach(function (block) {
      const lang = block.dataset.lang || "";
      const encoded = block.dataset.code || "";
      let source = "";
      try {
        source = decodeURIComponent(encoded);
      } catch (err) {
        source = "";
      }

      if (!source) {
        block.innerHTML = '<div class="code-loading">Empty code block</div>';
        return;
      }

      fetch("/code/" + encodeURIComponent(projectName) + "/snippet/tokens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: source, language: lang }),
      })
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.json();
        })
        .then(function (data) {
          renderTokensInto(data.tokens || [], block, { lineNumbers: false, padBlankLines: false });
          const badge = document.createElement("span");
          badge.className = "md-code-lang";
          badge.textContent = lang;
          block.appendChild(badge);
        })
        .catch(function () {
          const escaped = escHtml(source);
          block.innerHTML = "<pre><code>" + escaped + "</code></pre>";
        });
    });
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
    if (copyBtn) copyBtn.disabled = false;

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

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      try {
        const ok = document.execCommand("copy");
        document.body.removeChild(textarea);
        if (ok) resolve(); else reject(new Error("Copy failed"));
      } catch (err) {
        document.body.removeChild(textarea);
        reject(err);
      }
    });
  }

  function copyCurrentFile() {
    if (!currentFile) return;
    fetch(buildCodeUrl(currentFile))
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.text();
      })
      .then(function (text) {
        return copyText(text);
      })
      .then(function () {
        if (!copyBtn) return;
        const prev = copyBtn.textContent;
        copyBtn.textContent = "Copied";
        setTimeout(function () {
          copyBtn.textContent = prev;
        }, 1200);
      })
      .catch(function () {
        if (!copyBtn) return;
        const prev = copyBtn.textContent;
        copyBtn.textContent = "Copy failed";
        setTimeout(function () {
          copyBtn.textContent = prev;
        }, 1200);
      });
  }

  function loadFile(filename) {
    if (filename === currentFile) return;
    setActiveFile(filename);
    setStorage("lastFile", filename);
    showLoading();

    const ext = getExt(filename);

    if (ext === "py" || ext === "js" || ext === "asm" || ext === "json" ||
      ext === "yaml" || ext === "yml" || ext === "xml" || ext === "html") {
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
          renderMarkdown(text, filename);
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
  const storedFile = getStorage("lastFile");
  const initialFile = storedFile && files.includes(storedFile)
    ? storedFile
    : (mainFile || files[0]);
  if (initialFile) {
    loadFile(initialFile);
  }

  if (copyBtn) {
    copyBtn.addEventListener("click", copyCurrentFile);
  }

})();
