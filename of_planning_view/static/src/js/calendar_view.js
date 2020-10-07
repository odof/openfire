odoo.define('of_planning_view.calendar_view', function (require) {
"use strict";
/*---------------------------------------------------------
 * OpenFire calendar - créneaux dispos
 *---------------------------------------------------------*/

var CalendarView = require('web_calendar.CalendarView');
var Model = require('web.DataModel');

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

CalendarView.include({
    set_res_horaires_data: function(res_ids=false, start=false, end=false, get_segments=false) {
        var self = this;
        this._super.apply(this,arguments);
        if (this.model == "of.planning.intervention" && this.show_creneau_dispo) {
            var dfd = $.Deferred();
            var p = dfd.promise()
            res_ids = res_ids || self.now_filter_ids;
            start = start || self.range_start;
            end = moment(start).endOf(this.mode || "week")._d;

            var Planning = new Model(self.model);
            Planning.call('get_emp_horaires_info', [res_ids, start, end, get_segments, false])
            .then(function (result) {
                if (isNullOrUndef(self.res_horaires_info)) {
                    self.res_horaires_info = result;
                }else{
                    for (var i=0; i<res_ids.length; i++) {
                        self.res_horaires_info[res_ids[i]] = result[res_ids[i]];
                    }
                }

                dfd.resolve();
            });
            return $.when(p).then(function() {
                self.events_dispo = [];
                var attendee_data, creneaux_dispo_jour, creneau_dispo, cmpt_id = -1;
                for (var k in self.now_filter_ids) {

                    var now_filter_id = self.now_filter_ids[k]
                    attendee_data = self.res_horaires_info[now_filter_id];
                    for (var i=0; i<attendee_data.creneaux_dispo.length; i++) {
                        creneaux_dispo_jour = attendee_data.creneaux_dispo[i];
                        for (var j=0; j<creneaux_dispo_jour.length; j++) {
                            creneau_dispo = creneaux_dispo_jour[j];
                            creneau_dispo["calendar_name"] = "Dispo";
                            creneau_dispo["color_filter_id"] = now_filter_id;
                            creneau_dispo["employee_ids"] = [now_filter_id];
                            creneau_dispo["id"] = cmpt_id;
                            creneau_dispo["of_color_bg"] = "#FFFFFF";
                            creneau_dispo["of_color_ft"] = "#000000";
                            creneau_dispo["state"] = "Dispo";
                            creneau_dispo["state_int"] = 0;
                            creneau_dispo["virtuel"] = true;
                            self.events_dispo.push(creneau_dispo)
                            cmpt_id--;
                        }
                    }
                }
                return $.when();
            });
        }
        return $.when();
    },
});
});