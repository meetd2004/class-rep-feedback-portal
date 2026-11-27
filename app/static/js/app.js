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

    // 4. Student Dashboard live search, topic filter, status filter, sort, and clickable stats
    const searchInput = document.getElementById("student-search");
    const categorySelect = document.getElementById("student-category-filter");
    const sortSelect = document.getElementById("student-sort");
    const statusFilterButtons = document.querySelectorAll("[data-status-filter]");
    const statFilterButtons = document.querySelectorAll("[data-student-stat-filter]");
    const clearFiltersBtn = document.getElementById("student-clear-filters");
    const resetFiltersEmptyBtn = document.getElementById("student-reset-filters-empty");
    const matchSummaryEl = document.getElementById("student-match-summary");
    const filterEmptyEl = document.getElementById("student-filter-empty");
    const studentTableWrap = document.getElementById("student-table-wrap");
    let activeStudentStatus = "all";

    const activeStatusBtn = document.querySelector("[data-status-filter].active");
    if (activeStatusBtn) {
        activeStudentStatus = activeStatusBtn.getAttribute("data-status-filter") || "all";
    }

    const syncStatusButtonHighlights = (statusKey) => {
        statusFilterButtons.forEach((btn) => {
            btn.classList.toggle(
                "active",
                (btn.getAttribute("data-status-filter") || "all") === statusKey
            );
        });
        statFilterButtons.forEach((btn) => {
            btn.classList.toggle(
                "stat-active",
                (btn.getAttribute("data-student-stat-filter") || "all") === statusKey
            );
        });
    };

    const sortStudentRows = () => {
        const tbody = document.getElementById("student-submissions-tbody");
        if (!tbody || !sortSelect) {
            return;
        }
        const sortBy = sortSelect.value || "newest";
        const rows = Array.from(tbody.querySelectorAll("[data-feedback-row]"));
        const statusOrder = { new: 1, "in-review": 2, resolved: 3 };

        rows.sort((a, b) => {
            const idA = parseInt(a.getAttribute("data-id") || "0", 10);
            const idB = parseInt(b.getAttribute("data-id") || "0", 10);
            if (sortBy === "oldest") {
                return idA - idB;
            }
            if (sortBy === "status") {
                const rankA = statusOrder[a.getAttribute("data-status") || ""] || 9;
                const rankB = statusOrder[b.getAttribute("data-status") || ""] || 9;
                return rankA !== rankB ? rankA - rankB : idB - idA;
            }
            return idB - idA;
        });

        rows.forEach((row) => tbody.appendChild(row));
    };

    const applyStudentFilters = () => {
        sortStudentRows();
        const feedbackRows = document.querySelectorAll("[data-feedback-row]");
        const term = searchInput ? searchInput.value.trim().toLowerCase() : "";
        const selectedCategory = categorySelect ? categorySelect.value : "";
        const sortBy = sortSelect ? sortSelect.value : "newest";
        const hasActiveFilter =
            Boolean(term) ||
            Boolean(selectedCategory) ||
            activeStudentStatus !== "all" ||
            sortBy !== "newest";

        if (clearFiltersBtn) {
            clearFiltersBtn.hidden = !hasActiveFilter;
        }

        if (!feedbackRows.length) {
            if (filterEmptyEl) {
                filterEmptyEl.hidden = true;
            }
            if (matchSummaryEl) {
                matchSummaryEl.textContent = "Showing 0 of 0 submissions";
            }
            return;
        }

        let visibleCount = 0;
        feedbackRows.forEach((row) => {
            const rowStatus = row.getAttribute("data-status") || "";
            const rowCategory = row.getAttribute("data-category") || "";
            const rowSearch = row.getAttribute("data-search") || "";
            const statusMatch = activeStudentStatus === "all" || rowStatus === activeStudentStatus;
            const categoryMatch = !selectedCategory || rowCategory === selectedCategory;
            const textMatch = !term || rowSearch.includes(term);
            const visible = statusMatch && categoryMatch && textMatch;
            row.hidden = !visible;
            if (visible) {
                visibleCount += 1;
            }
        });

        if (matchSummaryEl) {
            matchSummaryEl.textContent = `Showing ${visibleCount} of ${feedbackRows.length} submissions`;
        }
        if (studentTableWrap) {
            studentTableWrap.hidden = visibleCount === 0;
        }
        if (filterEmptyEl) {
            filterEmptyEl.hidden = visibleCount > 0;
        }
    };

    const resetAllStudentFilters = () => {
        activeStudentStatus = "all";
        if (searchInput) searchInput.value = "";
        if (categorySelect) categorySelect.value = "";
        if (sortSelect) sortSelect.value = "newest";
        syncStatusButtonHighlights("all");
        applyStudentFilters();
    };

    if (searchInput) {
        searchInput.addEventListener("input", applyStudentFilters);
    }
    if (categorySelect) {
        categorySelect.addEventListener("change", applyStudentFilters);
    }
    if (sortSelect) {
        sortSelect.addEventListener("change", applyStudentFilters);
    }
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener("click", resetAllStudentFilters);
    }
    if (resetFiltersEmptyBtn) {
        resetFiltersEmptyBtn.addEventListener("click", resetAllStudentFilters);
    }

    statusFilterButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            activeStudentStatus = btn.getAttribute("data-status-filter") || "all";
            syncStatusButtonHighlights(activeStudentStatus);
            applyStudentFilters();
        });
    });

    statFilterButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            activeStudentStatus = btn.getAttribute("data-student-stat-filter") || "all";
            syncStatusButtonHighlights(activeStudentStatus);
            applyStudentFilters();
        });
    });

    const studentToolbarEl = document.getElementById("student-toolbar");
    if (studentToolbarEl) {
        studentToolbarEl.addEventListener("submit", (event) => {
            event.preventDefault();
            applyStudentFilters();
        });
        applyStudentFilters();
    }

    // 5. Accessible In-Page Delete Confirmation Modal (event-delegated for dynamically synced rows)
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
        document.addEventListener("submit", (event) => {
            const target = event.target;
            if (!(target instanceof HTMLFormElement)) {
                return;
            }
            const confirmMsg = target.getAttribute("data-confirm-message");
            if (!confirmMsg || target.getAttribute("data-confirmed") === "true") {
                return;
            }
            event.preventDefault();
            pendingForm = target;
            modalMsg.textContent = confirmMsg;
            modal.hidden = false;
            modalCancel.focus();
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

        window.setInterval(syncAdminQueue, 2500);
        window.addEventListener("focus", syncAdminQueue);
        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) {
                syncAdminQueue();
            }
        });
        syncAdminQueue();
    }

    // 10. Student Portal Quick Request Composer & Real-Time Sync
    const studentShell = document.getElementById("student-dashboard-shell");
    if (studentShell) {
        const studentPollUrl = studentShell.getAttribute("data-student-poll-url");
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.getAttribute("content") || "" : "";

        const toggleBtn = document.getElementById("toggle-quick-composer");
        const composerBody = document.getElementById("quick-composer-body");
        if (toggleBtn && composerBody) {
            toggleBtn.addEventListener("click", () => {
                const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
                toggleBtn.setAttribute("aria-expanded", expanded ? "false" : "true");
                composerBody.hidden = expanded;
                toggleBtn.textContent = expanded ? "+ Raise Request" : "Hide Form";
            });
        }

        const catInput = document.getElementById("quick-category-input");
        const catPills = document.querySelectorAll("[data-quick-cat]");
        if (catInput && catPills.length) {
            catPills.forEach((pill) => {
                pill.addEventListener("click", () => {
                    const chosen = pill.getAttribute("data-quick-cat") || "";
                    catInput.value = chosen;
                    catPills.forEach((btn) => {
                        btn.classList.remove("active");
                        btn.setAttribute("aria-pressed", "false");
                    });
                    pill.classList.add("active");
                    pill.setAttribute("aria-pressed", "true");
                });
            });
        }

        const studentTbody = document.getElementById("student-submissions-tbody");
        const studentToolbar = document.getElementById("student-toolbar");
        const studentEmpty = document.getElementById("student-empty-state");
        const studentLiveAlert = document.getElementById("student-live-alert");
        const studentLiveText = document.getElementById("student-live-alert-text");
        const studentLiveLink = document.getElementById("student-live-alert-link");
        const studentLiveDismiss = document.getElementById("student-live-alert-dismiss");

        if (studentLiveDismiss && studentLiveAlert) {
            studentLiveDismiss.addEventListener("click", () => {
                studentLiveAlert.hidden = true;
            });
        }

        const snapshotMap = new Map();
        document.querySelectorAll("#student-submissions-tbody tr").forEach((tr) => {
            const idBadge = tr.querySelector(".ticket-id-badge");
            const statusPill = tr.querySelector(".status-pill");
            const cells = tr.querySelectorAll("td");
            if (idBadge && statusPill && cells.length >= 5) {
                const idNum = parseInt(idBadge.textContent.replace("#", ""), 10);
                snapshotMap.set(idNum, {
                    status: statusPill.textContent.trim(),
                    responses: parseInt(cells[4].textContent.trim(), 10) || 0,
                });
            }
        });

        const buildStudentStatusClass = (statusText) =>
            "status-pill status-" + statusText.toLowerCase().replace(/\s+/g, "-");

        const renderStudentRows = (items) => {
            if (!studentTbody || !studentTableWrap || !studentEmpty || !studentToolbar) {
                return;
            }
            studentTbody.replaceChildren();

            if (!items.length) {
                studentTableWrap.hidden = true;
                studentToolbar.hidden = true;
                studentEmpty.hidden = false;
                if (filterEmptyEl) {
                    filterEmptyEl.hidden = true;
                }
                return;
            }

            studentTableWrap.hidden = false;
            studentToolbar.hidden = false;
            studentEmpty.hidden = true;

            items.forEach((item) => {
                const replyText = item.latest_reply ? item.latest_reply.message : "";
                const tr = document.createElement("tr");
                tr.setAttribute("data-feedback-row", "");
                tr.setAttribute("data-id", String(item.id));
                tr.setAttribute("data-category", item.category);
                tr.setAttribute("data-status", item.status.toLowerCase().replace(/\s+/g, "-"));
                tr.setAttribute(
                    "data-search",
                    `${item.title} ${item.category} #${item.id} ${replyText}`.toLowerCase()
                );

                const tdId = document.createElement("td");
                const idBadge = document.createElement("span");
                idBadge.className = "ticket-id-badge";
                idBadge.textContent = "#" + String(item.id);
                tdId.appendChild(idBadge);
                tr.appendChild(tdId);

                const tdTitle = document.createElement("td");
                const link = document.createElement("a");
                link.className = "row-link";
                link.href = item.view_url;
                link.textContent = item.title;
                tdTitle.appendChild(link);
                if (item.latest_reply && item.latest_reply.message) {
                    const replyDiv = document.createElement("div");
                    replyDiv.className = "inline-reply-preview";

                    const repNameEl = document.createElement("strong");
                    repNameEl.textContent = `${item.latest_reply.rep_name}: `;
                    replyDiv.appendChild(repNameEl);

                    const repMsgEl = document.createElement("span");
                    const truncated =
                        item.latest_reply.message.length > 120
                            ? `${item.latest_reply.message.slice(0, 120)}…`
                            : item.latest_reply.message;
                    repMsgEl.textContent = truncated;
                    replyDiv.appendChild(repMsgEl);

                    tdTitle.appendChild(replyDiv);
                }
                tr.appendChild(tdTitle);

                const tdCat = document.createElement("td");
                const catSpan = document.createElement("span");
                catSpan.className = "badge-category";
                catSpan.textContent = item.category;
                tdCat.appendChild(catSpan);
                tr.appendChild(tdCat);

                const tdStatus = document.createElement("td");
                const statusSpan = document.createElement("span");
                statusSpan.className = buildStudentStatusClass(item.status);
                statusSpan.textContent = item.status;
                tdStatus.appendChild(statusSpan);
                tr.appendChild(tdStatus);

                const tdResp = document.createElement("td");
                tdResp.textContent = String(item.response_count);
                tr.appendChild(tdResp);

                const tdUpdated = document.createElement("td");
                tdUpdated.className = "muted nowrap";
                tdUpdated.textContent = item.updated_at;
                tr.appendChild(tdUpdated);

                const tdActions = document.createElement("td");
                tdActions.className = "actions-cell";

                const viewBtn = document.createElement("a");
                viewBtn.className = "btn btn-secondary btn-sm";
                viewBtn.href = item.view_url;
                viewBtn.textContent = "View";
                tdActions.appendChild(viewBtn);

                if (item.status === "New") {
                    const editBtn = document.createElement("a");
                    editBtn.className = "btn btn-secondary btn-sm";
                    editBtn.href = item.edit_url;
                    editBtn.textContent = "Edit";
                    tdActions.appendChild(editBtn);

                    if (csrfToken) {
                        const delForm = document.createElement("form");
                        delForm.method = "post";
                        delForm.action = item.delete_url;
                        delForm.className = "inline-form";
                        delForm.setAttribute(
                            "data-confirm-message",
                            `Delete '${item.title}'? This action cannot be undone.`
                        );

                        const csrfInput = document.createElement("input");
                        csrfInput.type = "hidden";
                        csrfInput.name = "csrf_token";
                        csrfInput.value = csrfToken;
                        delForm.appendChild(csrfInput);

                        const delBtn = document.createElement("button");
                        delBtn.type = "submit";
                        delBtn.className = "btn btn-danger btn-sm";
                        delBtn.textContent = "Delete";
                        delForm.appendChild(delBtn);

                        tdActions.appendChild(delForm);
                    }
                } else {
                    const lockedSpan = document.createElement("span");
                    lockedSpan.className = "locked-tag";
                    lockedSpan.textContent = "Locked";
                    tdActions.appendChild(lockedSpan);
                }

                tr.appendChild(tdActions);
                studentTbody.appendChild(tr);
            });

            applyStudentFilters();
        };

        const syncStudentFeedback = async () => {
            if (!studentPollUrl) {
                return;
            }
            try {
                const resp = await fetch(studentPollUrl, {
                    headers: { Accept: "application/json" },
                    cache: "no-store",
                });
                if (!resp.ok) {
                    return;
                }
                const data = await resp.json();
                const counts = data.counts || {};
                document.querySelectorAll("[data-student-stat]").forEach((el) => {
                    const key = el.getAttribute("data-student-stat");
                    if (key && key in counts) {
                        el.textContent = String(counts[key]);
                    }
                });

                const items = Array.isArray(data.submissions) ? data.submissions : [];
                items.forEach((item) => {
                    const prev = snapshotMap.get(item.id);
                    if (prev && (prev.status !== item.status || item.response_count > prev.responses)) {
                        if (studentLiveAlert && studentLiveText && studentLiveLink) {
                            if (item.response_count > prev.responses && item.latest_reply) {
                                studentLiveText.textContent =
                                    `New reply from ${item.latest_reply.rep_name} on Ticket #${item.id} "${item.title}": "${item.latest_reply.message}"`;
                            } else {
                                studentLiveText.textContent =
                                    `Ticket #${item.id} "${item.title}" updated — Status: ${item.status}, Replies: ${item.response_count}`;
                            }
                            studentLiveLink.href = item.view_url;
                            studentLiveAlert.hidden = false;
                        }
                    }
                    snapshotMap.set(item.id, {
                        status: item.status,
                        responses: item.response_count,
                    });
                });

                renderStudentRows(items);
            } catch (_err) {
                // Ignore transient network hiccups silently
            }
        };

        const quickForm = document.getElementById("quick-request-form");
        const quickTitle = document.getElementById("quick-title");
        const quickDesc = document.getElementById("quick-description");
        const quickBanner = document.getElementById("quick-composer-banner");
        const quickSubmitBtn = document.getElementById("quick-submit-btn");
        const errTitle = document.getElementById("quick-error-title");
        const errCat = document.getElementById("quick-error-category");
        const errDesc = document.getElementById("quick-error-description");

        const clearQuickErrors = () => {
            [errTitle, errCat, errDesc].forEach((el) => {
                if (el) {
                    el.hidden = true;
                    el.textContent = "";
                }
            });
            if (quickTitle) quickTitle.classList.remove("input-error");
            if (quickDesc) quickDesc.classList.remove("input-error");
        };

        if (quickForm && quickTitle && quickDesc) {
            quickForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                clearQuickErrors();
                if (quickBanner) {
                    quickBanner.hidden = true;
                }
                if (quickSubmitBtn) {
                    quickSubmitBtn.disabled = true;
                    quickSubmitBtn.textContent = "Submitting...";
                }

                try {
                    const formData = new FormData(quickForm);
                    const resp = await fetch(quickForm.action, {
                        method: "POST",
                        headers: {
                            "X-Requested-With": "fetch",
                            Accept: "application/json",
                        },
                        body: formData,
                    });
                    const payload = await resp.json();

                    if (!resp.ok || !payload.ok) {
                        const errors = (payload && payload.errors) || {};
                        if (errors.title && errTitle) {
                            errTitle.textContent = errors.title;
                            errTitle.hidden = false;
                            quickTitle.classList.add("input-error");
                        }
                        if (errors.category && errCat) {
                            errCat.textContent = errors.category;
                            errCat.hidden = false;
                        }
                        if (errors.description && errDesc) {
                            errDesc.textContent = errors.description;
                            errDesc.hidden = false;
                            quickDesc.classList.add("input-error");
                        }
                    } else {
                        quickTitle.value = "";
                        quickDesc.value = "";
                        quickDesc.dispatchEvent(new Event("input"));
                        if (quickBanner && payload.ticket) {
                            quickBanner.textContent =
                                `Ticket #${payload.ticket.id} ("${payload.ticket.title}") raised with status New and sent to the Class Rep Admin queue.`;
                            quickBanner.hidden = false;
                        }
                        await syncStudentFeedback();
                    }
                } catch (_err) {
                    quickForm.submit();
                } finally {
                    if (quickSubmitBtn) {
                        quickSubmitBtn.disabled = false;
                        quickSubmitBtn.textContent = "Submit Request";
                    }
                }
            });
        }

        window.setInterval(syncStudentFeedback, 2500);
        window.addEventListener("focus", syncStudentFeedback);
        window.addEventListener("pageshow", syncStudentFeedback);
        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) {
                syncStudentFeedback();
            }
        });
        syncStudentFeedback();
    }

    // 11. Student Ticket Detail Real-Time Reply & Status Sync
    const detailShell = document.getElementById("student-detail-shell");
    if (detailShell) {
        const detailPollUrl = detailShell.getAttribute("data-detail-poll-url");
        let lastStatus = detailShell.getAttribute("data-detail-status") || "";
        let lastCount = parseInt(detailShell.getAttribute("data-detail-count") || "0", 10);

        const detailAlert = document.getElementById("detail-live-alert");
        const detailAlertText = document.getElementById("detail-live-alert-text");
        const detailAlertDismiss = document.getElementById("detail-live-alert-dismiss");
        const responseList = document.getElementById("detail-response-list");
        const responseEmpty = document.getElementById("detail-response-empty");
        const studentActions = document.getElementById("detail-student-actions");
        const lockRuleText = document.getElementById("detail-lock-rule-text");

        if (detailAlertDismiss && detailAlert) {
            detailAlertDismiss.addEventListener("click", () => {
                detailAlert.hidden = true;
            });
        }

        const updateDetailStepper = (status) => {
            const step1 = document.getElementById("detail-step-1");
            const step2 = document.getElementById("detail-step-2");
            const step3 = document.getElementById("detail-step-3");
            const line1 = document.getElementById("detail-line-1");
            const line2 = document.getElementById("detail-line-2");
            if (!step1 || !step2 || !step3 || !line1 || !line2) {
                return;
            }
            step1.className = "step step-done" + (status === "New" ? " step-current" : "");
            line1.className = "step-line" + (status === "In Review" || status === "Resolved" ? " step-line-active" : "");
            step2.className =
                "step" +
                (status === "In Review" || status === "Resolved" ? " step-done" : "") +
                (status === "In Review" ? " step-current" : "");
            line2.className = "step-line" + (status === "Resolved" ? " step-line-active" : "");
            step3.className =
                "step" +
                (status === "Resolved" ? " step-done step-current" : "");
        };

        const renderDetailResponses = (responses) => {
            if (!responseList || !responseEmpty) {
                return;
            }
            responseList.replaceChildren();
            if (!responses.length) {
                responseList.hidden = true;
                responseEmpty.hidden = false;
                return;
            }
            responseList.hidden = false;
            responseEmpty.hidden = true;

            responses.forEach((resp) => {
                const card = document.createElement("div");
                card.className = "response-item";

                const meta = document.createElement("div");
                meta.className = "response-meta";

                const nameEl = document.createElement("strong");
                nameEl.textContent = resp.rep_name;
                meta.appendChild(nameEl);

                const badge = document.createElement("span");
                badge.className = "role-pill role-rep";
                badge.textContent = "Class Rep";
                meta.appendChild(badge);

                const ts = document.createElement("span");
                ts.className = "muted";
                ts.textContent = resp.created_at;
                meta.appendChild(ts);

                const msg = document.createElement("p");
                msg.className = "response-text";
                msg.textContent = resp.message;

                card.appendChild(meta);
                card.appendChild(msg);
                responseList.appendChild(card);
            });
        };

        const syncDetailLive = async () => {
            if (!detailPollUrl) {
                return;
            }
            try {
                const resp = await fetch(detailPollUrl, {
                    headers: { Accept: "application/json" },
                    cache: "no-store",
                });
                if (!resp.ok) {
                    return;
                }
                const data = await resp.json();
                const statusChanged = data.status !== lastStatus;
                const repliesAdded = data.response_count > lastCount;

                if (!statusChanged && !repliesAdded) {
                    return;
                }

                document.querySelectorAll("[data-detail-status-pill]").forEach((el) => {
                    el.className = "status-pill status-" + data.status.toLowerCase().replace(/\s+/g, "-");
                    el.textContent = data.status;
                });
                document.querySelectorAll("[data-detail-updated-at]").forEach((el) => {
                    el.textContent = data.updated_at;
                });
                document.querySelectorAll("[data-detail-reply-count]").forEach((el) => {
                    el.textContent = String(data.response_count);
                });

                updateDetailStepper(data.status);
                renderDetailResponses(Array.isArray(data.responses) ? data.responses : []);

                if (data.status !== "New" && studentActions) {
                    const lockedSpan = document.createElement("span");
                    lockedSpan.className = "locked-banner";
                    lockedSpan.textContent = `Locked (${data.status})`;
                    studentActions.replaceChildren(lockedSpan);
                    if (lockRuleText) {
                        lockRuleText.textContent =
                            `Editing and deletion are locked once status moves to ${data.status} so your review history stays intact.`;
                    }
                }

                if (detailAlert && detailAlertText) {
                    const newestReply =
                        Array.isArray(data.responses) && data.responses.length
                            ? data.responses[data.responses.length - 1]
                            : null;
                    if (repliesAdded && newestReply) {
                        detailAlertText.textContent =
                            `New response from ${newestReply.rep_name} (Status: ${data.status}).`;
                    } else {
                        detailAlertText.textContent =
                            `Ticket status updated to ${data.status}.`;
                    }
                    detailAlert.hidden = false;
                }

                lastStatus = data.status;
                lastCount = data.response_count;
            } catch (_err) {
                // Ignore transient network hiccups silently
            }
        };

        window.setInterval(syncDetailLive, 2500);
        window.addEventListener("focus", syncDetailLive);
        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) {
                syncDetailLive();
            }
        });
    }
});
