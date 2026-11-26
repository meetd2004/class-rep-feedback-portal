/* CSP-compliant progressive enhancement for confirmations, counters, and demo login autofill. */
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form[data-confirm-message]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const message = form.getAttribute("data-confirm-message") || "Are you sure?";
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll("button[data-fill-email]").forEach((button) => {
        button.addEventListener("click", () => {
            const emailInput = document.getElementById("email");
            const passwordInput = document.getElementById("password");
            if (emailInput && passwordInput) {
                emailInput.value = button.getAttribute("data-fill-email") || "";
                passwordInput.value = button.getAttribute("data-fill-password") || "";
                emailInput.focus();
            }
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
