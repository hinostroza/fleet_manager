# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, time
import pytz

class FleetVehicleDocument(models.Model):
    _name = 'fleet.vehicle.document'
    _description = 'Vehicle Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Document Description", required=True, tracking=True)
    document_type = fields.Selection([
        ('property_card', 'Property Card'),
        ('soat', 'SOAT'),
        ('technical_review', 'Technical Review'),
        ('insurance_policy', 'Insurance Policy'),
        ('other', 'Other'),
    ], string="Document Type", required=True, tracking=True)
    expiration_date = fields.Date(string="Expiration Date", tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True, ondelete='cascade', tracking=True, index=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string="License Plate", store=True, readonly=True)
    attachment = fields.Binary(string="PDF Attachment", help="Attach the document in PDF format.")
    attachment_name = fields.Char(string="Attachment Name")
    calendar_event_id = fields.Many2one('calendar.event', string="Calendar Event", tracking=True,
                                        help="Calendar event associated with the document's expiration.")
    is_expired = fields.Boolean(string="Expired", compute='_compute_is_expired', store=True, search='_search_is_expired')
    days_to_expire = fields.Integer(string="Days to Expire", compute='_compute_days_to_expire', store=True)

    @api.depends('expiration_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for doc in self:
            doc.is_expired = doc.expiration_date and doc.expiration_date < today

    @api.depends('expiration_date')
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for doc in self:
            if doc.expiration_date:
                delta = doc.expiration_date - today
                doc.days_to_expire = delta.days
            else:
                doc.days_to_expire = 0

    def _search_is_expired(self, operator, value):
        today = fields.Date.today()
        if operator == '=' and value is True:
            return [('expiration_date', '<', today)]
        if operator in ('=', '!=') and value is False:
            return [('expiration_date', '>=', today)]
        return []

    def action_create_calendar_event(self):
        """
        Creates a calendar event automatically for the document's expiration at 9:00 AM.
        If an event already exists, it opens it.
        """
        for doc in self:
            if not doc.expiration_date:
                raise UserError(_("The document must have an expiration date to create a calendar event."))

            # If an event already exists, open it
            if doc.calendar_event_id:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'calendar.event',
                    'res_id': doc.calendar_event_id.id,
                    'view_mode': 'form',
                    'target': 'new',
                }

            # Combine date with 9:00 AM time. This creates a "naive" datetime object.
            start_datetime_naive = datetime.combine(doc.expiration_date, time(9, 0, 0))
            stop_datetime_naive = start_datetime_naive + relativedelta(hours=1)

            # Create the event
            event_vals = {
                'name': _('Expiration: %s - %s') % (doc.name, doc.vehicle_id.name),
                # Pass the naive datetime. The ORM will interpret it in the user's timezone
                # and convert it to UTC for storage.
                'start': start_datetime_naive,
                'stop': stop_datetime_naive,
                'allday': False, # It's not an all-day event anymore
                'partner_ids': [(4, doc.vehicle_id.driver_id.id)] if doc.vehicle_id.driver_id else [],
                'res_model_id': self.env['ir.model']._get(self._name).id,
                'res_id': doc.id,
            }
            event = self.env['calendar.event'].create(event_vals)

            # Link the new event to the document
            doc.calendar_event_id = event.id

        # After creating the event, open it in a new window for confirmation.
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'res_id': self.calendar_event_id.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def _cron_check_document_expirations(self):
        """
        Scheduled task to notify about documents that are about to expire or are already expired.
        """
        today = fields.Date.today()
        limit_date = today + relativedelta(days=30)
        # Search for documents that are already expired or will expire in the next 30 days.
        expiring_docs = self.search([
            ('expiration_date', '!=', False),
            ('expiration_date', '<=', limit_date),
        ])
        
        for doc in expiring_docs:
            if doc.is_expired:
                message = _("ATTENTION! The document '%s' for vehicle '%s' expired on %s.") % (
                    doc.name, doc.vehicle_id.name, doc.expiration_date.strftime('%d/%m/%Y'))
            else:
                message = _("The document '%s' for vehicle '%s' expires on %s (in %d days).") % (
                    doc.name, doc.vehicle_id.name, doc.expiration_date.strftime('%d/%m/%Y'), doc.days_to_expire)

            # Assign activity to the fleet manager or the driver's user.
            user_to_notify = doc.vehicle_id.manager_id or doc.vehicle_id.driver_id.user_id
            
            # If no specific user is found, don't create the activity to avoid assigning it to the admin running the cron.
            if not user_to_notify:
                doc.vehicle_id.message_post(body=message, subtype_xmlid='mail.mt_note')
                continue

            # Post in the vehicle's chatter
            doc.vehicle_id.message_post(body=message, subtype_xmlid='mail.mt_note')
            # Create an activity for follow-up
            doc.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=doc.expiration_date,
                summary=message,
                user_id=user_to_notify.id
            )