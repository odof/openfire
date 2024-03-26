/** @odoo-module **/

import { registry } from "@web/core/registry";
import { MapModel } from "./map_model";
import { MapArchParser } from "./map_arch_parser";
import { MapController } from "./map_controller";
import { MapRenderer } from "./map_renderer";

export const mapView = {
    type: "map",
    display_name: "Map",
    icon: "fa fa-map-marker",
    multiRecord: true,
    Controller: MapController,
    Renderer: MapRenderer,
    ArchParser: MapArchParser,
    Model: MapModel,
    searchMenuTypes: ["filter", "favorite"],
    buttonTemplate: "of_map_view.MapView.Buttons",

    props: (genericProps, view) => {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
        };
    },
};

registry.category("views").add("map", mapView);
