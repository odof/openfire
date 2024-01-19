/** @odoo-module */

import {registry} from "@web/core/registry";
import {MapController} from "./map_controller";
import {MapRenderer} from "./map_renderer";
import {MapModel} from "./map_model";

export const mapView = {
    type: "map",
    display_name: "Map",
    icon: "fa fa-map-marker",
    multiRecord: true,
    Controller: MapController,
    Renderer: MapRenderer,
    Model: MapModel,
    props(genericProps, view, config) {
        let modelParams = genericProps.state;
        if (!modelParams) {
            const {arch, resModel, fields, context} = genericProps;
            modelParams = {
                resModel: resModel,
                context: context,
                fields: fields,
                domain: [],
                orderBy: [],
            };
        }
        return {
            ...genericProps,
            Renderer: view.Renderer,
            Model: view.Model,
            modelParams,
        };
    },
};

registry.category("views").add("map", mapView);
