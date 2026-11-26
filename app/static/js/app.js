/* CSP-compliant progressive enhancement for confirmations, counters, and password toggles. */
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form[data-confirm-message]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const message = form.getAttribute("data-confirm-message") || "Are you sure?";
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll("button[data-toggle-password]").forEach((button) => {
        button.addEventListener("click", () => {
            const targetId = button.getAttribute("data-toggle-password");
            const input = targetId ? document.getElementById(targetId) : null;
            if (!input) {
                return;
            }
            const showing = input.type === "text";
            input.type = showing ? "password" : "text";
            button.textContent = showing ? "Show" : "Hide";
            button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
        });
    });

    document.querySelectorAll("textarea[data-char-count]").forEach((textarea) => {
        const counterId = textarea.getAttribute("data-char-count");
        const counterEl = counterId ? document.getElementById(counterId) : null;
        if (!counterEl) {
            return;
        }
        const maxLength = textarea.getAttribute("maxlength") || "";
        const updateCount = () => {
            counterEl.textContent = maxLength
                ? `${textarea.value.length} / ${maxLength} characters`
                : `${textarea.value.length} characters`;
        };
        textarea.addEventListener("input", updateCount);
        updateCount();
    });
});
