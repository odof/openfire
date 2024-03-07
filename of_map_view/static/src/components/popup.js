/** @odoo-module */
import {Component, useState} from "@odoo/owl";

export class PopupMap extends Component {
    static template = "of_map_view.PopupMap";

    static props = {
        record: Object,
        map: Object,
    };

    setup() {
        this.value = this.props.record;
        this.state = useState({
            show: false,
            color: 'white',
            width: this.props.map.model.metaData.width,
        });
        this.props.map.popups[this.value.id] = this;
        this.model = this.props.map.model.metaData.resModel;
    }

    onClick(evt) {
        this.props.map.switchView(this.value.id);
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

    setIconMarker(icon) {
        let newIcon = this.props.map.iconMarker[icon];
        this.props.map.markers[this.value.id].setIcon(newIcon);
    }
}

export class ListPopupMap extends Component {
    static template = "of_map_view.ListPopupMap";

    static components = {
        PopupMap,
    };

    static props = {
        map: Object,
    };

    setup() {
        this.state = useState({
            width: this.props.map.model.metaData.width,
        });
    }

    get rendererProps() {
        return {
            map: this.props.map,
        };
    }
}
