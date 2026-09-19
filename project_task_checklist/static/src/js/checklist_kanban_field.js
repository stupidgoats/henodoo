/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Compact, directly-checkable checklist for kanban cards.
 *
 * Shows every item across all of the task's checklists as a small row with
 * its own checkbox, so an item can be checked off (Pending <-> Complete)
 * right on the card - no need to open the task. "Not Needed" items still
 * show (struck through, in red) but aren't toggleable from here: that
 * state stays a form-only action, so the card interaction stays to one
 * obvious click per item.
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

    /* Every handler here calls stopPropagation first - the kanban card's
     * own click-to-open handler lives on an ancestor element, and a click
     * meant to check off an item must never also open the task. */
    async toggleItem(item, ev) {
        ev.stopPropagation();
        if (item.state === "not_needed") {
            return;
        }
        const newState = item.state === "done" ? "pending" : "done";
        item.state = newState;
        await this.orm.write("project.task.checklist.line", [item.id], { state: newState });
        this.refreshParent();
    }

    /* Best-effort: lets the card's own summary badges (checklist_done_count
     * and friends, used for the small done/not-needed/pending counts above
     * this widget, and for the top-of-form placement) catch up after a
     * toggle. Not awaited by the click handler - the checkbox should flip
     * instantly - and non-fatal if it fails. */
    refreshParent() {
        this.props.record.load().catch(() => {});
    }
}

registry.category("fields").add("checklist_kanban", {
    component: ChecklistKanbanField,
    supportedTypes: ["one2many"],
});
