/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
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
        onWillStart(async () => {
            await Promise.all([this.loadChecklists(), this.loadTemplates()]);
        });
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
     * checklist_progress (there is currently nothing else, but this keeps
     * it correct if that ever changes) picks up the new numbers too. The
     * widget's own display never depends on this succeeding - it always
     * uses the state loaded straight from loadChecklists() above. */
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
        if (ev.key === "Enter") {
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
        name = (name || "").trim();
        if (!name || name === checklist.name) {
            return;
        }
        checklist.name = name;
        await this.orm.write("project.task.checklist", [checklist.id], { name });
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
        await this.orm.create("project.task.checklist.line", [
            { checklist_id: checklist.id, name },
        ]);
        await this.loadChecklists();
        await this.refreshParent();
    }

    async renameItem(item, name) {
        name = (name || "").trim();
        if (!name || name === item.name) {
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
