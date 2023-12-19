/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { scrollSymbol } from "@web/webclient/actions/action_hook";
import { PlanningArchParser } from "./planning_arch_parser";
import { PlanningModel } from "./planning_model";
import { PlanningController } from "./planning_controller";
import { PlanningRenderer } from "./planning_renderer";

export const PlanningView = {
    type: "planning",
    display_name: _lt("Planning"),
    icon: "fa fa-tasks",
    multiRecord: true,
    ArchParser: PlanningArchParser,
    Controller: PlanningController,
    Model: PlanningModel,
    Renderer: PlanningRenderer,

    buttonTemplate: "of_web_planning_view.PlanningController.controlButtons",

    props: (props, view) => {
        const modelParams = {};
        let scrollPosition;
        if (props.state) {
            scrollPosition = props.state[scrollSymbol];
            modelParams.metaData = props.state.metaData;
        } else {
            const { arch, fields, resModel } = props;
            const parser = new view.ArchParser();
            const archInfo = parser.parse(arch);

            let formViewId = archInfo.formViewId;
            if (!formViewId) {
                const formView = config.views.find((v) => v[1] === "form");
                if (formView) {
                    formViewId = formView[0];
                }
            }

            modelParams.metaData = {
                ...archInfo,
                fields,
                resModel,
                formViewId,
            };
        }

        return {
            ...props,
            modelParams,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            scrollPosition: props.state ? props.state[scrollSymbol] : undefined,
        };
    },
};

registry.category("views").add("planning", PlanningView);
