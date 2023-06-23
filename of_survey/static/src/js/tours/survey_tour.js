/** @odoo-module */

import { _t } from 'web.core';
import { Markup } from 'web.utils';
import tour from 'web_tour.tour';

tour.register('of_survey_tour', {
    url: "/web",
    rainbowManMessage: _t("Congratulations! You are now ready to collect feedback like a pro :-)"),
    sequence: 225,
}, [
    ...tour.stepUtils.goToAppSteps('of_survey.menu_surveys', Markup(_t("Ready to change the way you <b>gather data</b>?"))),
{
    trigger: '.btn-outline-primary.o_survey_load_sample',
    content: Markup(_t("Load a <b>sample Survey</b> to get started quickly.")),
    position: 'left',
}, {
    trigger: '.o_survey_start button[type=submit]',
    content: _t("Let's get started!"),
    position: 'bottom',
}, {
    trigger: '.o_survey_simple_choice button[type=submit]',
    extra_trigger: '.js_question-wrapper span:contains("How frequently")',
    content: _t("Whenever you pick an answer, Odoo saves it for you."),
    position: 'bottom',
}, {
    trigger: '.o_survey_numerical_box button[type=submit]',
    extra_trigger: '.js_question-wrapper span:contains("How many")',
    content: _t("Only a single question left!"),
    position: 'bottom',
},{
    trigger: '.o_survey_review a',
    content: _t("Let's have a look at your answers!"),
    position: 'bottom',
}, {
    trigger: '.alert-info a:contains("This is a Test Survey")',
    content: _t("Now, use this shortcut to go back to the survey."),
    position: 'bottom',
}, {
    trigger: 'td[name=survey_id]',
    content: _t("Let's open the survey you just submitted."),
    position: 'bottom',
}, {
    trigger: '.breadcrumb a:contains("Feedback Form")',
    content: _t("Use the breadcrumbs to quickly go back to the dashboard."),
    position: 'bottom',
}
]);
