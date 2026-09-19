/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Compact, directly-checkable checklist for kanban cards.
 *
 * Shows every item across all of the task's checklists as a small row.
 * Clicking anywhere on the row cycles the item Pending -> Complete -> Not
 * Needed -> Pending, so every state is reachable with at most two clicks.
 * A separate "cancel" (ban) button sits at the far end of the row, well
 * apart from the checkbox on the other side - a one-click shortcut straight
 * to Not Needed <-> Pending, for a chore that turns out not to apply,
 * without cycling through Complete first. Both controls stay on the same
 * row so an item never gets much taller than a single line.
 *
 * Every click handler below calls stopPropagation() first - the kanban
 * card's own click-to-open handler lives on an ancestor element, and a
 * click meant to change an item's state must never also open the task.
 *
 * Like the form's accordion widget, this talks to the ORM directly and
 * re-fetches its own data on load rather than trusting the kanban record's
 * in-memory one2many state - kanban cards re-render constantly as the
 * board scrolls or regroups, which makes leaning on that state even less
 * reliable here than it already was on the form. Once loaded, a click
 * mutates the item in place (instant feedback) and writes to the server in
 * the background; there's no need to re-fetch the whole list after every
 * single click the way the form widget does, since the write itself is the
 * only thing that can fail, and the item just written is already known to
 * be correct locally.
 */
export class ChecklistKanbanField extends Component {
    static template = "project_task_checklist.ChecklistKanbanField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ items: [], loading: true });
        onWillStart(() => this.loadItems());
    }

    get taskId() {
        return this.props.record.resId;
    }

    async loadItems() {
        if (!this.taskId) {
            this.state.items = [];
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        const checklists = await this.orm.searchRead(
            "project.task.checklist",
            [["task_id", "=", this.taskId]],
            ["id"],
            { order: "sequence, id" }
        );
        let items = [];
        if (checklists.length) {
            items = await this.orm.searchRead(
                "project.task.checklist.line",
                [["checklist_id", "in", checklists.map((c) => c.id)]],
                ["name", "sequence", "state"],
                { order: "sequence, id" }
            );
        }
        this.state.items = items;
        this.state.loading = false;
    }

    isResolved(item) {
        return item.state === "done" || item.state === "not_needed";
    }

    /* Row click (anywhere except the cancel button): Pending -> Complete ->
     * Not Needed -> Pending. */
    async cycleItem(item, ev) {
        ev.stopPropagation();
        const next = { pending: "done", done: "not_needed", not_needed: "pending" };
        await this.setItemState(item, next[item.state]);
    }

    /* The cancel button always targets Not Needed specifically, regardless
     * of the item's current state - a direct shortcut that doesn't depend
     * on where the row-click cycle above happens to be. Clicking it again
     * clears back to Pending, same as the form's dedicated button. */
    async cancelItem(item, ev) {
        ev.stopPropagation();
        const newState = item.state === "not_needed" ? "pending" : "not_needed";
        await this.setItemState(item, newState);
    }

    async setItemState(item, newState) {
        item.state = newState;
        await this.orm.write("project.task.checklist.line", [item.id], { state: newState });
        this.refreshParent();
    }

    /* Best-effort: lets the card's own summary badges (checklist_done_count
     * and friends, used for the small done/not-needed/pending counts above
     * this widget, and for the top-of-form placement) catch up after a
     * change. Not awaited by the click handlers - the row should update
     * instantly - and non-fatal if it fails. */
    refreshParent() {
        this.props.record.load().catch(() => {});
    }
}

registry.category("fields").add("checklist_kanban", {
    component: ChecklistKanbanField,
    supportedTypes: ["one2many"],
});
