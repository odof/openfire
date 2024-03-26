/** @odoo-module */
import {Component, useState, useEffect, xml} from "@odoo/owl";
import {renderToMarkup} from "@web/core/utils/render";

export class PopupMap extends Component {
    static template = "of_map_view.PopupMap";

    static props = {
        record: Object,
        map: Object,
        archInfo: Object,
    };

    setup() {
        this.value = this.props.record;
        this.archInfo = this.props.archInfo;
        this.state = useState({
            show: false,
            color: "white",
        });
        this.model = this.props.map.model;
        this.resModel = this.props.record.resModel;
        this.props.map.popups[this.value.id] = this;
    }

    onClick(evt) {
        this.props.map.switchView(this.value.data.id);
    }

    onClose(evt) {
        this.hide();
    }

    onMouseOver(evt) {
        this.highlight();
    }

    onMouseOut(evt) {
        this.lowlight();
    }

    toggle() {
        if (!this.state.show) {
            this.state.show = true;

            if (!this.state.color == "white") {
                this.setIconMarker("selected");
            } else {
                this.setIconMarker("highlight-selected");
            }
        } else {
            this.state.show = false;
            if (!this.state.color == "white") {
                this.setIconMarker("normal");
            } else {
                this.setIconMarker("highlight");
            }
        }
    }

    show() {
        this.state.show = true;
        this.setIconMarker("selected");
    }

    hide() {
        this.state.show = false;
        this.setIconMarker("normal");
    }

    highlight() {
        this.state.color = "red";
        if (this.state.show) {
            this.setIconMarker("highlight-selected");
        } else {
            this.setIconMarker("highlight");
        }
    }

    lowlight() {
        if (this.state.show) {
            this.setIconMarker("selected");
            this.state.color = "white";
        } else {
            this.setIconMarker("normal");
        }
    }

    setIconMarker(type) {
        const {colorField} = this.props.archInfo;
        let icon;
        let color;

        if (["highlight", "highlight-selected"].includes(type)) {
            color = "red";
        } else {
            color = this.value.data[colorField] || "blue";
        }

        if (["selected", "highlight-selected"].includes(type)) {
            icon = "check-circle";
        } else {
            icon = "circle";
        }

        let newIcon = L.AwesomeMarkers.icon({
            icon: icon,
            markerColor: color,
        });
        this.props.map.markers[this.value.id].setIcon(newIcon);
    }

    getPopoverProps(props) {
        const {popoverTemplate} = props.archInfo;
        return renderToMarkup(xml`${popoverTemplate.outerHTML}`, {
            record: props.record.data,
        });
    }
}

export class ListPopupMap extends Component {
    static template = "of_map_view.ListPopupMap";

    static components = {
        PopupMap,
    };

    static props = {
        map: Object,
        archInfo: Object,
    };

    setup() {
        this.archInfo = this.props.archInfo;
        this.map = this.props.map;
        this.state = useState({
            records: [],
        });
        useEffect(
            () => {
                this.state.records = this.props.map.model.root.records;
            },
            () => [this.props.map.model.root.records]
        );
    }

    get rendererProps() {
        return {
            map: this.props.map,
            archInfo: this.props.archInfo,
        };
    }
}
