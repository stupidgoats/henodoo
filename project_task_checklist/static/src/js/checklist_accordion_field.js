/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const RESOLVED_STATES = ["done", "not_needed"];

/**
 * Renders a task's checklists as a list of collapsible groups - visually
 * similar to a "group by" list view: each checklist is a header row you
 * click to expand/collapse, showing its items indented underneath.
 *
 * This widget deliberately does NOT lean on the standard one2many list
 * renderer or the record's own onchange-driven relational data. Instead it
 * fetches its own data straight from the ORM and re-fetches after every
 * change. That sidesteps the one thing this module's checklist model was
 * already restructured once to work around: Odoo's client-side onchange
 * reliably updates a field that aggregates its own direct children, but
 * propagating a change back up through several nested one2many hops while
 * everything stays "unsaved" in one big form is a much less certain bet.
 * Talking straight to the ORM after each action and re-reading is slower
 * per click, but it is always correct, and every checklist action here
 * (add/rename/delete/check/reorder/apply template/reset all) already needs
 * a server round trip anyway, so there is no real cost to also treating the
 * server as the source of truth for what to show afterward.
 *
 * One consequence: a brand new, never-yet-saved task has no id, so there's
 * nowhere to attach a checklist to yet - the widget shows a short note
 * asking you to save the task first, the same constraint the old "Add
 * Checklist from Template" button already had.
 */
export class ChecklistAccordionField extends Component {
    static template = "project_task_checklist.ChecklistAccordionField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            checklists: [],
            templates: [],
            loading: true,
            expanded: {},
            newChecklistName: "",
            newItemName: {},
        });
        // Odoo 18 runs on Owl 2, which - unlike Owl 1 - does not expose a
        // component's root DOM element as `this.el` automatically. A
        // `useRef` + `t-ref` on the template's outer div is the only
        // reliable way to reach it; code written as if `this.el` just
        // exists (as an earlier version of this file did, for
        // focusNewItemInput() below) silently does nothing instead of
        // erroring, which is what let that bug hide for a while.
        this.rootRef = useRef("root");
        onWillStart(async () => {
            await Promise.all([this.loadChecklists(), this.loadTemplates()]);
        });
        onMounted(() => this.widenFormSheet());
    }

    /* The task form caps its sheet's width (max-width: 1400px, set by an
     * earlier version of this file via a CSS `:has()` override) for
     * general readability - which works against a checklist meant to be
     * scanned and tapped through quickly on a wide screen. Verified live
     * against the actual site: `.o_form_sheet_bg` (the sheet's immediate
     * parent) already flexes to fill all the width the chatter panel
     * isn't using - e.g. at a 2560px-wide window it was 1664px wide - but
     * the *sheet itself* stayed capped at exactly 1400px, leaving a
     * ~250px dead gap between the sheet and the chatter. That gap is
     * exactly the "did not adapt to the window width" symptom: raising
     * the cap to a bigger fixed number just moves the same problem to a
     * wider screen, so this removes the cap entirely instead and lets
     * the sheet fill 100% of whatever `.o_form_sheet_bg` gives it, on any
     * window size - confirmed live to close the gap down to its normal
     * ~16px padding. Reaching up from this widget's own root and setting
     * inline `!important` styles directly on the actual ancestor elements
     * sidesteps needing to win a specificity fight with Odoo's own CSS at
     * all - inline `!important` beats any stylesheet rule regardless of
     * selector or load order, which a plain CSS `:has()` rule (the
     * earlier approach) evidently wasn't managing to do. Runs once on
     * mount: the sheet/sheet-bg ancestors themselves are never torn down
     * by this widget's own re-renders, only its own inner content is. */
    widenFormSheet() {
        const root = this.rootRef.el;
        if (!root) {
            return;
        }
        // The actual cause of the checklist looking narrower than the form
        // fields below it: Odoo's per-field wrapper div (the element
        // directly around this widget) is a shrink-to-fit inline block for
        // a field outside a <group>, so it only grew as wide as its
        // content. Make it - and anything else between this widget and
        // the sheet - a full-width block. The stylesheet does the same;
        // this is the belt-and-braces version that doesn't depend on
        // guessing Odoo's wrapper class name.
        for (let el = root.parentElement; el && !el.classList.contains("o_form_sheet"); el = el.parentElement) {
            if (el.classList.contains("o_notebook") || el.classList.contains("tab-pane")) {
                break;
            }
            el.style.setProperty("display", "block", "important");
            el.style.setProperty("width", "100%", "important");
            el.style.setProperty("max-width", "none", "important");
            if (el.classList.contains("o_checklist_form_top")) {
                break;
            }
        }
        const sheet = root.closest(".o_form_sheet");
        if (sheet) {
            sheet.style.setProperty("max-width", "none", "important");
            sheet.style.setProperty("width", "100%", "important");
        }
        const sheetBg = root.closest(".o_form_sheet_bg");
        if (sheetBg) {
            sheetBg.style.setProperty("max-width", "none", "important");
        }
    }

    get taskId() {
        return this.props.record.resId;
    }

    get totalCount() {
        return this.state.checklists.reduce((sum, c) => sum + c.total_count, 0);
    }

    get doneCount() {
        return this.state.checklists.reduce((sum, c) => sum + c.done_count, 0);
    }

    get notNeededCount() {
        return this.state.checklists.reduce((sum, c) => sum + c.not_needed_count, 0);
    }

    get pendingCount() {
        return this.state.checklists.reduce((sum, c) => sum + c.pending_count, 0);
    }

    get overallProgress() {
        const resolved = this.doneCount + this.notNeededCount;
        return this.totalCount ? (resolved / this.totalCount) * 100 : 0;
    }

    async loadTemplates() {
        this.state.templates = await this.orm.searchRead(
            "project.checklist.template",
            [],
            ["name"],
            { order: "name" }
        );
    }

    async loadChecklists(taskId = this.taskId) {
        if (!taskId) {
            this.state.checklists = [];
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        const checklists = await this.orm.searchRead(
            "project.task.checklist",
            [["task_id", "=", taskId]],
            [
                "name",
                "sequence",
                "template_id",
                "total_count",
                "done_count",
                "not_needed_count",
                "pending_count",
                "progress",
                "progress_label",
            ],
            { order: "sequence, id" }
        );
        const linesByChecklist = {};
        if (checklists.length) {
            const lines = await this.orm.searchRead(
                "project.task.checklist.line",
                [["checklist_id", "in", checklists.map((c) => c.id)]],
                ["name", "sequence", "state", "checklist_id"],
                { order: "sequence, id" }
            );
            for (const line of lines) {
                const checklistId = line.checklist_id[0];
                if (!linesByChecklist[checklistId]) {
                    linesByChecklist[checklistId] = [];
                }
                linesByChecklist[checklistId].push(line);
            }
        }
        for (const checklist of checklists) {
            checklist.lines = linesByChecklist[checklist.id] || [];
        }
        this.state.checklists = checklists;
        this.state.loading = false;
    }

    /* Best-effort refresh of the task record itself, so anything elsewhere
     * on the form reading checklist_total_count / checklist_done_count /
     * checklist_progress (the top-of-form placement and the kanban badges
     * both depend on these) picks up the new numbers too. The widget's own
     * display never depends on this succeeding - it always uses the state
     * loaded straight from loadChecklists() above. */
    async refreshParent() {
        try {
            await this.props.record.load();
        } catch {
            // Non-fatal: the accordion itself is still accurate.
        }
    }

    isExpanded(checklistId) {
        return !!this.state.expanded[checklistId];
    }

    toggle(checklistId) {
        this.state.expanded[checklistId] = !this.state.expanded[checklistId];
    }

    onChecklistKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.addChecklist();
        }
    }

    onItemKeydown(ev, checklist) {
        // Enter always adds (if there's text) and stays put for the next
        // item. Tab does the same *only* when there's text to add - an
        // empty box on Tab is left alone so Tab can still move focus away
        // normally once you're done adding items, instead of ever
        // trapping the cursor in this field. Together this is what lets
        // someone type an item, hit Tab (or Enter), type the next one, hit
        // Tab, and so on without ever touching the mouse.
        const hasText = !!(this.state.newItemName[checklist.id] || "").trim();
        if (ev.key === "Enter" || (ev.key === "Tab" && !ev.shiftKey && hasText)) {
            ev.preventDefault();
            this.addItem(checklist);
        }
    }

    async addChecklist() {
        const name = (this.state.newChecklistName || "").trim();
        if (!name) {
            return;
        }
        this.state.newChecklistName = "";
        const [id] = await this.orm.create("project.task.checklist", [
            { task_id: this.taskId, name },
        ]);
        this.state.expanded[id] = true;
        await this.loadChecklists();
        await this.refreshParent();
    }

    async renameChecklist(checklist, name) {
        // Note: checklist.name is bound two-way via t-model on the input,
        // so it is already live-updated to this same value by the time
        // this onChange handler runs (t-model syncs on every keystroke,
        // before the blur-triggered "change" event that calls this). A
        // `name === checklist.name` guard here would therefore always be
        // true and would silently skip the write on every real edit - so
        // the only thing worth guarding against is an empty name, which
        // the required field wouldn't accept.
        name = (name || "").trim();
        if (!name) {
            await this.loadChecklists();
            return;
        }
        checklist.name = name;
        await this.orm.write("project.task.checklist", [checklist.id], { name });
    }

    /* Saves this checklist's current items as a new reusable template, and
     * links this checklist to it - which is also what hides the "save as
     * template" button afterward (see checklist.template_id below), the
     * same signal used when a checklist is created the other way around,
     * via "From template". */
    async saveAsTemplate(checklist) {
        const name = (checklist.name || "").trim();
        if (!name) {
            return;
        }
        const [templateId] = await this.orm.create("project.checklist.template", [
            {
                name,
                line_ids: checklist.lines.map((line) => [
                    0,
                    0,
                    { name: line.name, sequence: line.sequence },
                ]),
            },
        ]);
        await this.orm.write("project.task.checklist", [checklist.id], {
            template_id: templateId,
        });
        await Promise.all([this.loadChecklists(), this.loadTemplates()]);
    }

    async deleteChecklist(checklist) {
        await this.orm.unlink("project.task.checklist", [checklist.id]);
        delete this.state.expanded[checklist.id];
        await this.loadChecklists();
        await this.refreshParent();
    }

    async moveChecklist(checklist, direction) {
        const list = this.state.checklists;
        const idx = list.findIndex((c) => c.id === checklist.id);
        const swapIdx = idx + direction;
        if (swapIdx < 0 || swapIdx >= list.length) {
            return;
        }
        const reordered = [...list];
        [reordered[idx], reordered[swapIdx]] = [reordered[swapIdx], reordered[idx]];
        await Promise.all(
            reordered.map((c, i) =>
                this.orm.write("project.task.checklist", [c.id], { sequence: (i + 1) * 10 })
            )
        );
        await this.loadChecklists();
    }

    async addItem(checklist) {
        const name = (this.state.newItemName[checklist.id] || "").trim();
        if (!name) {
            return;
        }
        this.state.newItemName[checklist.id] = "";
        const lines = checklist.lines;
        // Items don't already carry a meaningful sequence spacing from the
        // server (every item defaults to 10), so derive the next one here
        // too - keeps a freshly-typed item properly last, and gives
        // moveItem() a sane base to work from afterward.
        const sequence = lines.length ? Math.max(...lines.map((l) => l.sequence)) + 10 : 10;
        const [id] = await this.orm.create("project.task.checklist.line", [
            { checklist_id: checklist.id, name, sequence },
        ]);
        // Previously this called loadChecklists() here, which replaces
        // state.checklists wholesale with freshly-fetched objects. The
        // practical effect (confirmed by report) was that the "add an
        // item" box lost focus after every single item, even after a
        // first attempt at refocusing it - because that attempt relied on
        // `this.el`, which Owl 2 (unlike Owl 1) does not set automatically,
        // so the refocus silently never ran. Rather than lean on refocus
        // working perfectly, push the new line straight into the existing
        // reactive array instead: the "add an item" input isn't inside
        // this t-foreach at all, so it's never torn down in the first
        // place, and there's nothing to refocus.
        lines.push({ id, name, sequence, state: "pending" });
        this.recomputeChecklistCounts(checklist);
        await this.refreshParent();
        // Kept as a defensive fallback (now actually working, via
        // useRef/t-ref instead of the non-existent `this.el`) in case
        // focus ever does end up elsewhere - e.g. a future change that
        // reintroduces a reload, or a browser quirk.
        this.focusNewItemInput(checklist.id);
    }

    /* Mirrors the server's own project.task.checklist._compute_counts(),
     * so an optimistic local change (addItem above) can update a
     * checklist's rolled-up numbers immediately without waiting on a
     * round trip. */
    recomputeChecklistCounts(checklist) {
        const lines = checklist.lines;
        const total = lines.length;
        const done = lines.filter((l) => l.state === "done").length;
        const notNeeded = lines.filter((l) => l.state === "not_needed").length;
        const resolved = done + notNeeded;
        checklist.total_count = total;
        checklist.done_count = done;
        checklist.not_needed_count = notNeeded;
        checklist.pending_count = total - resolved;
        checklist.progress = total ? (resolved / total) * 100 : 0;
        checklist.progress_label = `${resolved}/${total}`;
    }

    focusNewItemInput(checklistId) {
        requestAnimationFrame(() => {
            const root = this.rootRef.el;
            const input =
                root &&
                root.querySelector(
                    `.o_checklist_new_item_input[data-checklist-id="${checklistId}"]`
                );
            if (input) {
                input.focus();
            }
        });
    }

    async renameItem(item, name) {
        // Same reasoning as renameChecklist() above: item.name is already
        // live-synced to this value via t-model by the time this onChange
        // handler runs, so comparing name to item.name here would always
        // be true and would silently skip every real edit.
        name = (name || "").trim();
        if (!name) {
            await this.loadChecklists();
            return;
        }
        item.name = name;
        await this.orm.write("project.task.checklist.line", [item.id], { name });
    }

    /* The main status icon behaves like a plain checkbox: Pending <-> Complete.
     * Clicking it while an item is Not Needed clears that back to Pending
     * too, rather than jumping straight to Complete. */
    async toggleDone(item) {
        const newState = item.state === "pending" ? "done" : "pending";
        await this.setItemState(item, newState);
    }

    /* The separate "Not Needed" button toggles that state on its own,
     * independent of the checkbox above - Not Needed <-> Pending. */
    async toggleNotNeeded(item) {
        const newState = item.state === "not_needed" ? "pending" : "not_needed";
        await this.setItemState(item, newState);
    }

    async setItemState(item, newState) {
        if (newState === item.state) {
            return;
        }
        item.state = newState;
        await this.orm.write("project.task.checklist.line", [item.id], {
            state: newState,
        });
        await this.loadChecklists();
        await this.refreshParent();
    }

    isResolved(item) {
        return RESOLVED_STATES.includes(item.state);
    }

    async deleteItem(item) {
        await this.orm.unlink("project.task.checklist.line", [item.id]);
        await this.loadChecklists();
        await this.refreshParent();
    }

    async moveItem(checklist, item, direction) {
        const lines = checklist.lines;
        const idx = lines.findIndex((l) => l.id === item.id);
        const swapIdx = idx + direction;
        if (swapIdx < 0 || swapIdx >= lines.length) {
            return;
        }
        const reordered = [...lines];
        [reordered[idx], reordered[swapIdx]] = [reordered[swapIdx], reordered[idx]];
        await Promise.all(
            reordered.map((l, i) =>
                this.orm.write("project.task.checklist.line", [l.id], { sequence: (i + 1) * 10 })
            )
        );
        await this.loadChecklists();
    }

    async onTemplateSelect(ev) {
        const templateId = parseInt(ev.target.value, 10);
        ev.target.value = "";
        if (!templateId) {
            return;
        }
        const [wizardId] = await this.orm.create("project.checklist.template.apply", [
            { task_id: this.taskId, template_id: templateId },
        ]);
        await this.orm.call("project.checklist.template.apply", "action_apply", [[wizardId]]);
        await this.loadChecklists();
        await this.refreshParent();
    }
}

registry.category("fields").add("checklist_accordion", {
    component: ChecklistAccordionField,
    supportedTypes: ["one2many"],
});
