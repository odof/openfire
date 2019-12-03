odoo.define('of_web_widgets.of_form_common', function (require) {
"use strict";

var form_common = require('web.form_common');
var utils = require('web.utils');
var core = require('web.core');
var Model = require('web.DataModel');
var _t = core._t;

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

function isNUF (value) {
    return _.isUndefined(value) || _.isNull(value) || value === false;
}

form_common.CompletionFieldMixin.init = function(){
	this.limit = 7;
	this.orderer = new utils.DropMisordered();
	this.can_create = this.node.attrs.can_write == "false" ? false : true;
	this.can_write = this.node.attrs.can_write == "false" ? false : true;
	this.options.no_quick_create = true;
	//console.log(" test : ", this.options);
};

var FieldMany2One = core.form_widget_registry.get('many2one');

/**
    This widget is intended to display a warning near a label of any many2one field
    indicating if the record is archived.
*/
FieldMany2One.include({
    set_active: function () {
        var self = this;

        var record_id = this.field_manager.get_field_value(this.name)
        var type = self.field.type;
        if (!isNUF(record_id) && type == "many2one" && !self.get("invisible")) {
            var OFWebWidgetsUtils = new Model("of.web.widgets.utils");
            OFWebWidgetsUtils.call("est_actif", [record_id, self.field.relation]) // retrieve active from db
                .then(function (active) {
                    if (!self.get("id") || !self.get("class_id")) {
                        self.set({
                            "id": record_id,
                            "class_id": "of_m2o_" + record_id
                        });
                    }
                    if(!active) {
                        // est désactivé
                        var options = _.extend({
                            delay: { show: 501, hide: 0 },
                            title: _t("Cet enregistrement est archivé."),
                        });
                        if (isNullOrUndef(self.$active_warning)) {
                            self.$active_warning = $('<span/>').addClass('fa fa-archive of_ws_l of_red ' + self.get("class_id"))
                            .insertAfter(self.$label).tooltip(options);
                        }
                    }else if (active) {
                        $("." + self.get("class_id")).remove();
                        self.$active_warning = undefined;
                    }
                    return active
                })
        }else if (!isNullOrUndef(self.$active_warning)) {
            $("." + self.get("class_id")).remove();
            self.$active_warning = undefined;
        }

    },
    render_value: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.set_active();
    },
});


/**
    This widget is intended to display a warning near a label of a 'res.partner' many2one field
    indicating if the partner is not geolocalized.
    This widget depends on a field given with the param 'geo_lat_field', which contains
    the time difference between UTC time and local time, in minutes.
*/
var Localizable = FieldMany2One.extend({
    initialize_content: function() {
        this._super.apply(this, arguments);
        this.geo_lat_field = (this.options && this.options.geo_lat_field) || this.geo_lat_field || 'geo_lat';
        this.set({"geo_lat": this.field_manager.get_field_value(this.geo_lat_field)});
        this.on("change:geo_lat", this, this.render_value);
    },
    start: function() {
        this._super.apply(this, arguments);
        // trigger a render_value when geo_lat field change
        this.field_manager.on("field_changed:" + this.geo_lat_field, this, function() {
            this.set({"geo_lat": this.field_manager.get_field_value(this.geo_lat_field)});
        });
    },
    check_localized: function() {
        var partner_lat = this.get('geo_lat');
        if (!partner_lat) {
            return false;
        }
        return true;
    },
    render_value: function() {
        this._super.apply(this, arguments);
        this.$label.next('.o_tz_warning').remove();
        if(!this.check_localized()){
            var options = _.extend({
                delay: { show: 501, hide: 0 },
                title: _t("This partner is not geolocalized"),
            });
            $('<span/>').addClass('fa fa-exclamation-triangle o_tz_warning').insertAfter(this.$label).tooltip(options);
        }
    }
});

core.form_widget_registry.add('localizable', Localizable)

});
