/**
 * Resurface Content Script
 * Detects Save actions on Instagram and LinkedIn and sends extracted data
 * to background.js for local processing.
 */

console.log("[Resurface] Content script initialized on:", window.location.href);

// ============================================================================
// SELECTORS CONFIGURATION (Easily inspectable and editable in DevTools)
// ============================================================================
const SELECTORS = {
  instagram: {
    // Keywords to identify Save control in aria-label, title, or button text
    saveKeywords: ["save", "save reel", "save post", "save to collection"],
    // Ignore unsave / remove toggles
    ignoredKeywords: ["remove", "unsave", "saved"],
    // Standard post container; if absent (e.g. in Reels viewer), fallback logic activates
    postContainer: "article, div[role='dialog'] article, main article",
    // Author element
    author: "header a, a[role='link'] span, h2 a, span[dir='auto'] a",
    // URL matching patterns for Instagram post permalinks
    permalinkPatterns: ["/p/", "/reel/"],
  },
  linkedin: {
    // Button or dropdown menu item with "Save" text / label
    saveKeywords: ["save", "save for later", "save post"],
    // Ignore already saved / unsave actions
    ignoredKeywords: ["unsave", "saved", "remove"],
    // Enclosing update container
    postContainer: ".feed-shared-update-v2, div[data-urn], [role='article'], .occludable-update",
    // Author name element
    author: ".update-components-actor__name, .feed-shared-actor__name, .feed-shared-actor__title",
    // URL matching patterns for LinkedIn post permalinks
    permalinkPatterns: ["/posts/", "/feed/update/"],
  },
};

// ============================================================================
// UI TOAST NOTIFICATION
// ============================================================================
function showToast(message, isError = false) {
  let toast = document.getElementById("resurface-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "resurface-toast";
    toast.style.cssText = `
      position: fixed;
      bottom: 28px;
      right: 28px;
      z-index: 2147483647;
      padding: 14px 24px;
      border-radius: 50px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.2px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45);
      transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1), transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      opacity: 0;
      transform: translateY(16px);
      pointer-events: none;
    `;
    document.body.appendChild(toast);
  }

  toast.style.backgroundColor = isError ? "#ef4444" : "#10b981";
  toast.style.color = "#ffffff";
  toast.innerText = message;

  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(16px)";
  }, 2800);
}

// ============================================================================
// EXTRACTION HELPERS
// ============================================================================
function getSiteType() {
  const host = window.location.hostname;
  if (host.includes("instagram.com")) return "instagram";
  if (host.includes("linkedin.com")) return "linkedin";
  return null;
}

function findInstagramContainer(target) {
  // 1. Standard feed post (<article>)
  const article = target.closest("article");
  if (article) return article;

  // 2. Reels viewer: walk up ancestors to find the container housing the reel's video
  let curr = target;
  let videoContainer = null;
  while (curr && curr !== document.body) {
    if (curr.querySelector && curr.querySelector("video")) {
      videoContainer = curr;
      break;
    }
    curr = curr.parentElement;
  }
  if (videoContainer) return videoContainer;

  // 3. Fallback to dialog, section, main, or document.body
  return target.closest("div[role='dialog'], section, main") || document.body;
}

function findPermalink(container, patterns) {
  if (container && container !== document.body) {
    const links = container.querySelectorAll("a[href]");
    for (const a of links) {
      const href = a.getAttribute("href") || "";
      for (const pattern of patterns) {
        if (href.includes(pattern)) {
          return new URL(href, window.location.origin).href;
        }
      }
    }
  }

  // If currently on a reel or post page directly
  const curHref = window.location.href;
  for (const pattern of patterns) {
    if (curHref.includes(pattern)) {
      return curHref;
    }
  }

  return curHref;
}

function extractPostData(container, site) {
  if (!container) return null;

  const config = SELECTORS[site];

  // Extract author if available
  const authorEl = container.querySelector(config.author);
  const author = authorEl ? authorEl.innerText.trim() : "";

  // Extract text
  let rawText = "";
  if (container === document.body) {
    // When falling back to body (single reel view), grab title and main text
    const mainEl = document.querySelector("main") || document.body;
    rawText = mainEl.innerText || document.title || "";
  } else {
    rawText = container.innerText || "";
  }

  if (author && !rawText.startsWith(author)) {
    rawText = `Author: ${author}\n\n${rawText}`;
  }

  // Truncate to 3000 chars
  if (rawText.length > 3000) {
    rawText = rawText.slice(0, 3000) + "...";
  }

  const url = findPermalink(container, config.permalinkPatterns);

  return {
    raw_text: rawText.trim() || `Saved ${site} item at ${url}`,
    url: url,
    source: site,
  };
}

// Track last hovered/active LinkedIn post
let lastHoveredPost = null;
if (getSiteType() === "linkedin") {
  document.addEventListener("mouseover", (e) => {
    const post = e.target.closest(SELECTORS.linkedin.postContainer);
    if (post) lastHoveredPost = post;
  });
}

// ============================================================================
// DOCUMENT-LEVEL CLICK LISTENER (Capture Phase)
// ============================================================================
document.addEventListener(
  "click",
  (event) => {
    const site = getSiteType();
    if (!site) return;

    const target = event.target;
    let isSaveClick = false;
    let postContainer = null;

    if (site === "instagram") {
      // Find closest interactive control or svg
      const control = target.closest("button, svg, [role='button'], span, div, a");
      if (control) {
        const aria = (
          control.getAttribute("aria-label") ||
          control.querySelector("[aria-label]")?.getAttribute("aria-label") ||
          control.getAttribute("title") ||
          ""
        ).trim().toLowerCase();

        const text = (control.innerText || "").trim().toLowerCase();
        const combined = `${aria} ${text}`;

        const matchesSave = SELECTORS.instagram.saveKeywords.some((w) =>
          combined.includes(w)
        );
        const isIgnored = SELECTORS.instagram.ignoredKeywords.some((w) =>
          combined.includes(w)
        );

        if (matchesSave && !isIgnored) {
          isSaveClick = true;
          postContainer = findInstagramContainer(target);
        }
      }
    } else if (site === "linkedin") {
      const control = target.closest("button, li, div[role='button'], a, span");
      if (control) {
        const text = (control.innerText || "").trim().toLowerCase();
        const aria = (control.getAttribute("aria-label") || "").trim().toLowerCase();
        const combined = `${text} ${aria}`;

        const matchesSave = SELECTORS.linkedin.saveKeywords.some((w) =>
          combined.includes(w)
        );
        const isIgnored = SELECTORS.linkedin.ignoredKeywords.some((w) =>
          combined.includes(w)
        );

        if (matchesSave && !isIgnored) {
          isSaveClick = true;
          postContainer =
            target.closest(SELECTORS.linkedin.postContainer) || lastHoveredPost || document.body;
        }
      }
    }

    if (isSaveClick) {
      console.log(`[Resurface] Detected Save action on ${site}. Target:`, target);
      const payload = extractPostData(postContainer, site);
      console.log("[Resurface] Extracted payload:", payload);

      if (payload && payload.raw_text) {
        chrome.runtime.sendMessage(
          { action: "SAVE_POST", payload },
          (response) => {
            if (chrome.runtime.lastError) {
              console.error(
                "[Resurface] Extension runtime error:",
                chrome.runtime.lastError.message
              );
              showToast("Resurface error: Is backend running?", true);
              return;
            }

            if (response && response.success) {
              console.log("[Resurface] Backend confirmed save:", response.data);
              showToast("⚡ Sent to Resurface");
            } else {
              console.error("[Resurface] Backend returned error:", response?.error);
              showToast("Failed to save to Resurface", true);
            }
          }
        );
      }
    }
  },
  true // Capture phase
);
