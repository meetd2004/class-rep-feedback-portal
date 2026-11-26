/* CSP-compliant interactive behaviors: Lottie intro splash, topic/workflow explorers, live filters, modal confirm, counters, and password toggle. */
document.addEventListener("DOMContentLoaded", () => {
    // 1. Lottie intro splash screen
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

    // 2. Interactive Feedback Topic Explorer on landing page
    const topicData = {
        lectures: {
            title: "Lectures & Session Delivery",
            desc: "Report pacing issues, recording audio/video problems, or requests for extra worked examples across Group B modules.",
        },
        assessments: {
            title: "Assessments & Coursework",
            desc: "Ask for clarity on brief guidelines, referencing expectations, submission formatting, or formative feedback timelines.",
        },
        timetables: {
            title: "Timetables & Room Scheduling",
            desc: "Flag lab slot overlaps, room clashes, or missing calendar updates before upcoming teaching weeks.",
        },
        resources: {
            title: "Learning Resources & Lab Environments",
            desc: "Highlight broken Moodle links, unavailable lab VM mirrors, or missing slide decks and reading materials.",
        },
    };

    const topicTabs = document.querySelectorAll("[data-topic-tab]");
    const topicTitle = document.getElementById("topic-panel-title");
    const topicDesc = document.getElementById("topic-panel-desc");
    if (topicTabs.length && topicTitle && topicDesc) {
        topicTabs.forEach((tab) => {
            tab.addEventListener("click", () => {
                const key = tab.getAttribute("data-topic-tab") || "lectures";
                const info = topicData[key];
                if (!info) {
                    return;
                }
                topicTabs.forEach((btn) => {
                    btn.classList.remove("active");
                    btn.setAttribute("aria-selected", "false");
                });
                tab.classList.add("active");
                tab.setAttribute("aria-selected", "true");
                topicTitle.textContent = info.title;
                topicDesc.textContent = info.desc;
            });
        });
    }

    // 3. Interactive Workflow Lifecycle Explorer on landing page
    const stageData = {
        new: {
            badge: "New",
            badgeClass: "status-pill status-new",
            progressClass: "workflow-progress-fill stage-1",
            title: "Submitted & Editable by Author",
            desc: "Newly created feedback is immediately routed to Group B class representatives while remaining private to the author and reps.",
            rules: [
                "Author can edit details or delete the submission",
                "Invisible to all other students in the cohort",
                "Ready for class rep triage and response",
            ],
        },
        review: {
            badge: "In Review",
            badgeClass: "status-pill status-in-review",
            progressClass: "workflow-progress-fill stage-2",
            title: "Under Class Rep Investigation",
            desc: "Once a class rep responds or starts triage, the submission advances to In Review and locks against retroactive student edits.",
            rules: [
                "Student editing and deletion are locked for audit integrity",
                "Class rep replies appear immediately on the author's thread",
                "Filterable by topic and status in the rep queue",
            ],
        },
        resolved: {
            badge: "Resolved",
            badgeClass: "status-pill status-resolved",
            progressClass: "workflow-progress-fill stage-3",
            title: "Action Completed & Documented",
            desc: "The issue or suggestion has been addressed and closed with official class representative notes visible to the author.",
            rules: [
                "Full reply history remains accessible to author and reps",
                "Cannot revert backward to New once resolved",
                "Preserves a transparent record of cohort outcomes",
            ],
        },
    };

    const stageTabs = document.querySelectorAll("[data-stage-tab]");
    const stageBadge = document.getElementById("stage-badge");
    const stageTitle = document.getElementById("stage-title");
    const stageDesc = document.getElementById("stage-desc");
    const stageRules = document.getElementById("stage-rules");
    const stageProgress = document.getElementById("workflow-progress-fill");

    if (stageTabs.length && stageBadge && stageTitle && stageDesc && stageRules && stageProgress) {
        stageTabs.forEach((tab) => {
            tab.addEventListener("click", () => {
                const key = tab.getAttribute("data-stage-tab") || "new";
                const info = stageData[key];
                if (!info) {
                    return;
                }
                stageTabs.forEach((btn) => {
                    btn.classList.remove("active");
                    btn.setAttribute("aria-selected", "false");
                });
                tab.classList.add("active");
                tab.setAttribute("aria-selected", "true");

                stageBadge.textContent = info.badge;
                stageBadge.className = info.badgeClass;
                stageProgress.className = info.progressClass;
                stageTitle.textContent = info.title;
                stageDesc.textContent = info.desc;

                stageRules.replaceChildren();
                info.rules.forEach((ruleText) => {
                    const li = document.createElement("li");
                    li.textContent = ruleText;
                    stageRules.appendChild(li);
                });
            });
        });
    }

    // 4. Student Dashboard live search & status filter
    const searchInput = document.getElementById("student-search");
    const statusFilterButtons = document.querySelectorAll("[data-status-filter]");
    const feedbackRows = document.querySelectorAll("[data-feedback-row]");
    const filterEmptyEl = document.getElementById("student-filter-empty");

    if (feedbackRows.length && (searchInput || statusFilterButtons.length)) {
        let activeStatus = "all";

        const applyStudentFilters = () => {
            const term = searchInput ? searchInput.value.trim().toLowerCase() : "";
            let visibleCount = 0;

            feedbackRows.forEach((row) => {
                const rowStatus = row.getAttribute("data-status") || "";
                const rowSearch = row.getAttribute("data-search") || "";
                const statusMatch = activeStatus === "all" || rowStatus === activeStatus;
                const textMatch = !term || rowSearch.includes(term);
                const visible = statusMatch && textMatch;
                row.hidden = !visible;
                if (visible) {
                    visibleCount += 1;
                }
            });

            if (filterEmptyEl) {
                filterEmptyEl.hidden = visibleCount > 0;
            }
        };

        if (searchInput) {
            searchInput.addEventListener("input", applyStudentFilters);
        }

        statusFilterButtons.forEach((btn) => {
            btn.addEventListener("click", () => {
                activeStatus = btn.getAttribute("data-status-filter") || "all";
                statusFilterButtons.forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                applyStudentFilters();
            });
        });
    }

    // 5. Accessible In-Page Delete Confirmation Modal
    const modal = document.getElementById("confirm-modal");
    const modalMsg = document.getElementById("confirm-modal-message");
    const modalCancel = document.getElementById("confirm-modal-cancel");
    const modalProceed = document.getElementById("confirm-modal-proceed");
    let pendingForm = null;

    const closeModal = () => {
        if (modal) {
            modal.hidden = true;
        }
        pendingForm = null;
    };

    if (modal && modalMsg && modalCancel && modalProceed) {
        document.querySelectorAll("form[data-confirm-message]").forEach((form) => {
            form.addEventListener("submit", (event) => {
                if (form.getAttribute("data-confirmed") === "true") {
                    return;
                }
                event.preventDefault();
                pendingForm = form;
                modalMsg.textContent = form.getAttribute("data-confirm-message") || "Are you sure?";
                modal.hidden = false;
                modalCancel.focus();
            });
        });

        modalCancel.addEventListener("click", closeModal);
        modal.addEventListener("click", (event) => {
            if (event.target === modal) {
                closeModal();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !modal.hidden) {
                closeModal();
            }
        });
        modalProceed.addEventListener("click", () => {
            if (pendingForm) {
                const formToSubmit = pendingForm;
                formToSubmit.setAttribute("data-confirmed", "true");
                closeModal();
                formToSubmit.submit();
            }
        });
    }

    // 6. Dismissible flash alerts
    document.querySelectorAll("[data-dismiss-alert]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const alertBox = btn.closest(".alert");
            if (alertBox) {
                alertBox.remove();
            }
        });
    });

    // 7. Password visibility toggle
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

    // 8. Textarea live character counter
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
