/**
 * Resurface Content Script
 * Detects Save actions on Instagram and LinkedIn and sends extracted data
 * to background.js for local processing.
 */

// ============================================================================
// SELECTORS CONFIGURATION (Easily inspectable and editable in DevTools)
// ============================================================================
const SELECTORS = {
  instagram: {
    // Target Save control: button or svg with aria-label="Save"
    saveAria: "Save",
    // Ignore unsave / remove toggles
    ignoredAriaKeywords: ["remove", "unsave", "saved"],
    // Enclosing post container
    postContainer: "article, div[role='dialog'] article, main article",
    // Author element
    author: "header a, a[role='link'] span, h2 a",
    // URL matching patterns for Instagram post permalinks
    permalinkPatterns: ["/p/", "/reel/"],
  },
  linkedin: {
    // Button or dropdown menu item with "Save" text / label
    saveKeywords: ["save", "save for later"],
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
      bottom: 24px;
      right: 24px;
      z-index: 2147483647;
      padding: 12px 20px;
      border-radius: 9999px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      font-size: 14px;
      font-weight: 600;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
      transition: opacity 0.3s ease, transform 0.3s ease;
      opacity: 0;
      transform: translateY(12px);
      pointer-events: none;
    `;
    document.body.appendChild(toast);
  }

  toast.style.backgroundColor = isError ? "#ef4444" : "#10b981";
  toast.style.color = "#ffffff";
  toast.innerText = message;

  // Trigger animation
  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(12px)";
  }, 2500);
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

function findPermalink(container, patterns) {
  if (container) {
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
  return window.location.href;
}

function extractPostData(container, site) {
  if (!container) return null;

  const config = SELECTORS[site];

  // Extract author if available
  const authorEl = container.querySelector(config.author);
  const author = authorEl ? authorEl.innerText.trim() : "";

  // Extract main text
  let rawText = container.innerText || "";
  if (author && !rawText.startsWith(author)) {
    rawText = `Author: ${author}\n\n${rawText}`;
  }

  // Cap at 3000 chars as specified
  if (rawText.length > 3000) {
    rawText = rawText.slice(0, 3000) + "...";
  }

  // Find permalink URL
  const url = findPermalink(container, config.permalinkPatterns);

  return {
    raw_text: rawText.trim(),
    url: url,
    source: site,
  };
}

// Track last hovered/active LinkedIn post in case menu is rendered in a portal
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
      // Check aria-label on clicked element, button, or svg
      const control = target.closest("button, svg, [role='button'], span");
      if (control) {
        const aria = (
          control.getAttribute("aria-label") ||
          control.querySelector("[aria-label]")?.getAttribute("aria-label") ||
          ""
        ).trim().toLowerCase();

        const isIgnored = SELECTORS.instagram.ignoredAriaKeywords.some((w) =>
          aria.includes(w)
        );

        if (aria === SELECTORS.instagram.saveAria.toLowerCase() && !isIgnored) {
          isSaveClick = true;
          postContainer = target.closest(SELECTORS.instagram.postContainer);
        }
      }
    } else if (site === "linkedin") {
      // Check text or aria-label for Save action (direct button or dropdown item)
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
            target.closest(SELECTORS.linkedin.postContainer) || lastHoveredPost;
        }
      }
    }

    if (isSaveClick && postContainer) {
      console.log(`[Resurface] Detected Save action on ${site}. Extracting...`);
      const payload = extractPostData(postContainer, site);

      if (payload && payload.raw_text) {
        // Send to background service worker (avoids page CSP & mixed content)
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
  true // Capture phase as specified
);
