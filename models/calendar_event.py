# -*- coding: utf-8 -*-

from odoo import models, api

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        for event in events:
            if event.res_model == 'fleet.vehicle.document' and event.res_id:
                doc = self.env['fleet.vehicle.document'].browse(event.res_id)
                if not doc.calendar_event_id:
                    doc.write({'calendar_event_id': event.id})
        return events