/** @odoo-module **/

import { Component } from "@odoo/owl";

export class PlanningPopover extends Component {

    static template = "of_web_planning_view.PlanningPopover";
    static props = ["title", "template?", "context", "close", "button?"];
    static defaultProps = {
        template: "of_web_planning_view.PlanningPopover",
    }

    onClick() {
        this.props.button.onClick();
        this.props.close();
    }
}
