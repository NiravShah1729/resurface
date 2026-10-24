/**
 * Resurface Background Service Worker (Manifest V3)
 * Proxies save requests from content scripts to the local backend to bypass page CSP/mixed-content.
 */

const BACKEND_URL = "http://localhost:8000/saves";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "SAVE_POST") {
    fetch(BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(message.payload),
    })
      .then(async (response) => {
        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`Server status ${response.status}: ${errText}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("[Resurface Background] Post saved successfully:", data);
        sendResponse({ success: true, data });
      })
      .catch((error) => {
        console.error("[Resurface Background] Failed to save post:", error);
        sendResponse({ success: false, error: error.message });
      });

    // Return true to allow asynchronous sendResponse
    return true;
  }
});
