/** @odoo-module */
import {Layout} from "@web/search/layout";
import {useModel} from "@web/views/model";
import {standardViewProps} from "@web/views/standard_view_props";
import {loadJS, loadCSS} from "@web/core/assets";

const {Component, onWillStart} = owl;

export class MapController extends Component {
    static template = "of_map_view.MapController";

    static components = {
        Layout,
    };

    static props = {
        ...standardViewProps,
        Model: Function,
        modelParams: Object,
        Renderer: Function,
    };

    setup() {
        const {Model} = this.props;
        const model = useModel(Model, this.props.modelParams);
        this.model = model;

        onWillStart(async () => {
            // Loading leaflet
            await Promise.all([
                await loadCSS("/of_map_view/static/lib/leaflet/leaflet.css"),
                await loadJS(["/of_map_view/static/lib/leaflet/leaflet.js"]),
            ]);
            // Loading awesome markers
            await Promise.all([
                await loadCSS(
                    "/of_map_view/static/lib/awesome-markers/leaflet.awesome-markers.css"
                ),
                await loadJS([
                    "/of_map_view/static/lib/awesome-markers/leaflet.awesome-markers.js",
                ]),
            ]);
        });
    }

    get rendererProps() {
        return {
            model: this.model,
        };
    }
}
