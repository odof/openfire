/** @odoo-module */

import { registry } from "@web/core/registry";
import { MapArchParser } from "./map_arch_parser";
import { MapController } from "./map_controller";
import { MapRenderer } from "./map_renderer";
import { MapModel } from "./map_model";

export const mapView = {
    type: "map",
    display_name: "Map",
    icon: "fa fa-map-marker",
    multiRecord: true,
    ArchParser: MapArchParser,
    Controller: MapController,
    Renderer: MapRenderer,
    Model: MapModel,

    props(props, view, config) {
        let modelParams = props.state;
        if (!modelParams) {
            const {arch, resModel, fields, context} = props;
            const parser = new view.ArchParser();
            const archInfo = parser.parse(arch);

            let formViewId = archInfo.formViewId;
            if (!formViewId) {
                const formView = config.views.find((v) => v[1] === "form");
                if (formView) {
                    formViewId = formView[0];
                }
            }

            modelParams = {
                ...archInfo,
                resModel: resModel,
                context: context,
                fields: fields,
                domain: [],
                orderBy: [],
            };
        }

        return {
            ...props,
            modelParams,
            Model: view.Model,
            Renderer: view.Renderer,
        };
    },
};

registry.category("views").add("map", mapView);
