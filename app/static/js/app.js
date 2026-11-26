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

    // 9. Class Rep Admin Console Live Ticket Sync
    const adminShell = document.getElementById("admin-shell");
    if (adminShell) {
        const pollUrl = adminShell.getAttribute("data-rep-poll-url");
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.getAttribute("content") || "" : "";
        const queueCard = document.getElementById("rep-queue-card");
        const queueTbody = document.getElementById("rep-queue-tbody");
        const queueTableWrap = document.getElementById("rep-queue-table-wrap");
        const queueEmpty = document.getElementById("rep-queue-empty");
        const filteredCountEl = document.getElementById("rep-filtered-count");
        const liveAlert = document.getElementById("admin-live-alert");
        const liveAlertText = document.getElementById("admin-live-alert-text");
        const liveAlertLink = document.getElementById("admin-live-alert-link");
        const liveAlertDismiss = document.getElementById("admin-live-alert-dismiss");

        let knownLatestId = queueCard
            ? parseInt(queueCard.getAttribute("data-latest-ticket-id") || "0", 10)
            : 0;

        if (liveAlertDismiss && liveAlert) {
            liveAlertDismiss.addEventListener("click", () => {
                liveAlert.hidden = true;
            });
        }

        const buildStatusClass = (statusText) =>
            "status-pill status-" + statusText.toLowerCase().replace(/\s+/g, "-");

        const renderQueueRows = (tickets) => {
            if (!queueTbody || !queueTableWrap || !queueEmpty) {
                return;
            }
            queueTbody.replaceChildren();

            if (!tickets.length) {
                queueTableWrap.hidden = true;
                queueEmpty.hidden = false;
                return;
            }

            queueTableWrap.hidden = false;
            queueEmpty.hidden = true;

            tickets.forEach((ticket) => {
                const tr = document.createElement("tr");

                const tdId = document.createElement("td");
                const idSpan = document.createElement("span");
                idSpan.className = "ticket-id-badge";
                idSpan.textContent = "#" + String(ticket.id);
                tdId.appendChild(idSpan);
                tr.appendChild(tdId);

                const tdTitle = document.createElement("td");
                const titleLink = document.createElement("a");
                titleLink.className = "row-link";
                titleLink.href = ticket.detail_url;
                titleLink.textContent = ticket.title;
                tdTitle.appendChild(titleLink);
                tr.appendChild(tdTitle);

                const tdAuthor = document.createElement("td");
                tdAuthor.textContent = ticket.author_name;
                tr.appendChild(tdAuthor);

                const tdCat = document.createElement("td");
                const catSpan = document.createElement("span");
                catSpan.className = "badge-category";
                catSpan.textContent = ticket.category;
                tdCat.appendChild(catSpan);
                tr.appendChild(tdCat);

                const tdStatus = document.createElement("td");
                const stSpan = document.createElement("span");
                stSpan.className = buildStatusClass(ticket.status);
                stSpan.textContent = ticket.status;
                tdStatus.appendChild(stSpan);
                tr.appendChild(tdStatus);

                const tdResp = document.createElement("td");
                tdResp.textContent = String(ticket.response_count);
                tr.appendChild(tdResp);

                const tdUpdated = document.createElement("td");
                tdUpdated.className = "muted nowrap";
                tdUpdated.textContent = ticket.updated_at;
                tr.appendChild(tdUpdated);

                const tdActions = document.createElement("td");
                tdActions.className = "actions-cell";

                const reviewLink = document.createElement("a");
                reviewLink.className = "btn btn-secondary btn-sm";
                reviewLink.href = ticket.detail_url;
                reviewLink.textContent = "Review";
                tdActions.appendChild(reviewLink);

                if (ticket.status === "New" && csrfToken) {
                    const form = document.createElement("form");
                    form.method = "post";
                    form.action = ticket.status_url;
                    form.className = "inline-form";

                    const csrfInput = document.createElement("input");
                    csrfInput.type = "hidden";
                    csrfInput.name = "csrf_token";
                    csrfInput.value = csrfToken;
                    form.appendChild(csrfInput);

                    const statusInput = document.createElement("input");
                    statusInput.type = "hidden";
                    statusInput.name = "status";
                    statusInput.value = "In Review";
                    form.appendChild(statusInput);

                    const nextInput = document.createElement("input");
                    nextInput.type = "hidden";
                    nextInput.name = "next";
                    nextInput.value = "dashboard";
                    form.appendChild(nextInput);

                    const startBtn = document.createElement("button");
                    startBtn.type = "submit";
                    startBtn.className = "btn btn-primary btn-sm";
                    startBtn.textContent = "Start Review";
                    form.appendChild(startBtn);

                    tdActions.appendChild(form);
                }

                tr.appendChild(tdActions);
                queueTbody.appendChild(tr);
            });
        };

        const syncAdminQueue = async () => {
            if (!pollUrl) {
                return;
            }
            const params = new URLSearchParams();
            if (queueCard) {
                const cat = queueCard.getAttribute("data-active-category") || "";
                const st = queueCard.getAttribute("data-active-status") || "";
                const q = queueCard.getAttribute("data-active-query") || "";
                if (cat) params.set("category", cat);
                if (st) params.set("status", st);
                if (q) params.set("q", q);
            }
            const targetUrl = params.toString() ? `${pollUrl}?${params.toString()}` : pollUrl;

            try {
                const response = await fetch(targetUrl, {
                    headers: { Accept: "application/json" },
                    cache: "no-store",
                });
                if (!response.ok) {
                    return;
                }
                const data = await response.json();
                const counts = data.counts || {};

                document.querySelectorAll("[data-sidebar-count]").forEach((el) => {
                    const key = el.getAttribute("data-sidebar-count");
                    if (key && key in counts) {
                        el.textContent = String(counts[key]);
                    }
                });
                document.querySelectorAll("[data-stat-count]").forEach((el) => {
                    const key = el.getAttribute("data-stat-count");
                    if (key && key in counts) {
                        el.textContent = String(counts[key]);
                    }
                });
                const catCounts = counts.categories || {};
                document.querySelectorAll("[data-sidebar-cat]").forEach((el) => {
                    const cat = el.getAttribute("data-sidebar-cat");
                    if (cat && cat in catCounts) {
                        el.textContent = String(catCounts[cat]);
                    }
                });

                if (filteredCountEl && Array.isArray(data.tickets)) {
                    filteredCountEl.textContent = String(data.tickets.length);
                }

                if (Array.isArray(data.tickets)) {
                    renderQueueRows(data.tickets);
                }

                const latest = data.latest_ticket;
                if (latest && latest.id) {
                    if (knownLatestId === 0) {
                        knownLatestId = latest.id;
                    } else if (latest.id > knownLatestId) {
                        knownLatestId = latest.id;
                        if (liveAlert && liveAlertText && liveAlertLink) {
                            liveAlertText.textContent =
                                `New student ticket #${latest.id} (${latest.category}) from ${latest.author_name}: "${latest.title}"`;
                            liveAlertLink.href = latest.detail_url;
                            liveAlert.hidden = false;
                        }
                    }
                }
            } catch (_err) {
                // Ignore transient polling hiccups silently
            }
        };

        window.setInterval(syncAdminQueue, 4000);
        syncAdminQueue();
    }
});
