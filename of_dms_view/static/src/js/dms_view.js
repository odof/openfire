/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DmsModel } from "./dms_model";
import { DmsArchParser } from "./dms_arch_parser";
import { DmsController } from "./dms_controller";
import { DmsRenderer } from "./dms_renderer";

export const dmsView = {
    type: "dms",
    display_name: "DMS",
    icon: "fa fa-folder-tree",
    multiRecord: true,
    Controller: DmsController,
    Renderer: DmsRenderer,
    ArchParser: DmsArchParser,
    Model: DmsModel,

    props: (genericProps, view) => {
        const { ArchParser } = view;
        const { arch } = genericProps;
        const archInfo = new ArchParser().parse(arch);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },
};

registry.category("views").add("dms", dmsView);
