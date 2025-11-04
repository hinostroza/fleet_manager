# -*- coding: utf-8 -*-

from odoo import models, fields

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    document_ids = fields.One2many('fleet.vehicle.document', 'vehicle_id', string='Documents')