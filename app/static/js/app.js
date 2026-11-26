/* CSP-compliant progressive enhancement for intro Lottie splash, confirmations, counters, and password toggles. */
document.addEventListener("DOMContentLoaded", () => {
    const splashEl = document.getElementById("intro-splash");
    if (splashEl) {
        const lottieContainer = document.getElementById("lottie-intro");
        const skipBtn = document.getElementById("skip-splash");
        const lottiePath = splashEl.getAttribute("data-lottie-path");
        let dismissed = false;

        const dismissSplash = () => {
            if (dismissed) {
                return;
            }
            dismissed = true;
            splashEl.classList.add("splash-hidden");
            window.setTimeout(() => {
                splashEl.hidden = true;
            }, 420);
        };

        if (skipBtn) {
            skipBtn.addEventListener("click", dismissSplash);
        }

        const prefersReduced =
            window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        if (prefersReduced) {
            dismissSplash();
        } else {
            if (window.lottie && lottieContainer && lottiePath) {
                const anim = window.lottie.loadAnimation({
                    container: lottieContainer,
                    renderer: "svg",
                    loop: false,
                    autoplay: true,
                    path: lottiePath,
                });
                anim.addEventListener("complete", () => {
                    window.setTimeout(dismissSplash, 220);
                });
            }
            window.setTimeout(dismissSplash, 1900);
        }
    }

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
