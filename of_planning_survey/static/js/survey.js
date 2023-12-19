odoo.define('of_crm_project.of_survey_form', function (require) {
'use strict';

    var OFSurveyFormWidget = require('of_survey.form');

    OFSurveyFormWidget.include({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var show_start = $('.show_start').attr('data-show');

                if (show_start=='no'){
                    self._submitForm({});
                }

            });
        },
        _onNextScreenDone: function (options) {
            // A chaque changement d'écran, on vérifie si nous sommes ou pas sur la dernière page
            this._super.apply(this, arguments);
            var show_end = $('.show_end').attr('data-show');
            var crm_lead_id = $('.show_end').attr('calendar-event-id');
            var action_id = $('.show_end').attr('action-id');
            var survey_id = $('.show_end').attr('survey-id');
            if (show_end=='no'){
                if (crm_lead_id){
                    window.location = "/web/#id="+crm_lead_id+"&model=calendar.event&view_type=form&action="+action_id;
                } else {
                    window.location = "/web/#id="+survey_id+"&model=of.survey.survey&view_type=form";
                }
            }

        },

    });

    return OFSurveyFormWidget;

});
