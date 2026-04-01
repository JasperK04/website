/* markdown_renderer.js - Enhanced Markdown rendering with math/admonitions/images */

(function () {
  "use strict";

  function normalizePath(path) {
    const parts = path.split("/");
    const out = [];
    parts.forEach(function (part) {
      if (!part || part === ".") return;
      if (part === "..") {
        if (out.length > 0) out.pop();
        return;
      }
      out.push(part);
    });
    return out.join("/");
  }

  function encodePath(path) {
    return path
      .split("/")
      .map(function (part) {
        return encodeURIComponent(part);
      })
      .join("/");
  }

  function isExternalUrl(url) {
    return /^(https?:|data:|mailto:|#)/i.test(url);
  }

  function resolveImageUrl(url, projectName, assetRoot, currentFile) {
    if (!url || isExternalUrl(url) || url.startsWith("/")) return url;
    const baseDir = currentFile ? currentFile.split("/").slice(0, -1).join("/") : "";
    const joined = baseDir ? baseDir + "/" + url : url;
    const normalized = normalizePath(joined);
    const rawRoot = assetRoot || projectName || "";
    const safeRoot = normalizePath(String(rawRoot));
    const projectSegment = encodePath(safeRoot || projectName || "");
    const encodedPath = encodePath(normalized);
    return "/static/projects/" + projectSegment + "/" + encodedPath;
  }

  function preprocessAdmonitions(md) {
    const lines = md.split("\n");
    const out = [];
    const re = /^\s*>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$/i;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const match = line.match(re);
      if (!match) {
        out.push(line);
        continue;
      }

      const type = match[1].toLowerCase();
      const firstLine = match[2];
      out.push("::: " + type);
      if (firstLine) out.push(firstLine);

      i += 1;
      for (; i < lines.length; i++) {
        const next = lines[i];
        if (!/^\s*>/.test(next)) {
          i -= 1;
          break;
        }
        out.push(next.replace(/^\s*>\s?/, ""));
      }
      out.push(":::");
    }

    return out.join("\n");
  }

  function stripHtmlComments(md) {
    return md.replace(/<!--[\s\S]*?-->/g, "");
  }

  function normalizeInlineMath(md) {
    const lines = md.split("\n");
    const out = [];
    let buffer = null;

    function countDollar(line) {
      const matches = line.match(/\$/g);
      return matches ? matches.length : 0;
    }

    lines.forEach(function (line) {
      if (buffer !== null) {
        buffer += " " + line.trim();
        if (countDollar(buffer) % 2 === 0) {
          out.push(buffer);
          buffer = null;
        }
        return;
      }

      if (countDollar(line) % 2 === 1) {
        buffer = line.trim();
        return;
      }

      out.push(line);
    });

    if (buffer !== null) out.push(buffer);
    return out.join("\n");
  }

  function createMarkdownIt() {
    if (!window.markdownit) return null;

    const md = window.markdownit({
      html: false,
      linkify: true,
      breaks: false,
    });

    if (window.texmath && window.katex) {
      md.use(window.texmath, {
        engine: window.katex,
        delimiters: "dollars",
        katexOptions: { throwOnError: false },
      });
    }

    if (window.markdownitContainer) {
      const types = ["note", "tip", "important", "warning", "caution"];
      types.forEach(function (type) {
        md.use(window.markdownitContainer, type, {
          render: function (tokens, idx) {
            if (tokens[idx].nesting === 1) {
              const title = type.charAt(0).toUpperCase() + type.slice(1);
              return (
                '<div class="admonition ' + type + '">' +
                '<div class="admonition-title">' + title + "</div>\n"
              );
            }
            return "</div>\n";
          },
        });
      });
    }

    const defaultImage = md.renderer.rules.image || function (tokens, idx, options, env, self) {
      return self.renderToken(tokens, idx, options);
    };

    md.renderer.rules.image = function (tokens, idx, options, env, self) {
      const token = tokens[idx];
      const srcIndex = token.attrIndex("src");
      if (srcIndex >= 0) {
        const src = token.attrs[srcIndex][1];
        const projectName = env && env.projectName ? env.projectName : "";
        const assetRoot = env && env.assetRoot ? env.assetRoot : "";
        const currentFile = env && env.currentFile ? env.currentFile : "";
        token.attrs[srcIndex][1] = resolveImageUrl(src, projectName, assetRoot, currentFile);
      }
      return defaultImage(tokens, idx, options, env, self);
    };

    return md;
  }

  window.renderMarkdownEnhanced = function (source, opts) {
    const md = createMarkdownIt();
    const env = opts || {};
    let input = stripHtmlComments(source || "");
    input = preprocessAdmonitions(input);
    input = normalizeInlineMath(input);
    if (!md) {
      const escaped = (input || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      return "<pre><code>" + escaped + "</code></pre>";
    }
    return md.render(input, env);
  };
})();
