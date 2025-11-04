# -*- coding: utf-8 -*-
{
    'name': "Vehicle Documentation Manager",
    'summary': """
        Management of documentation and expirations for fleet vehicles.
    """,
    'description': """
        This module extends the functionality of the Fleet module to allow
        the control of documents such as SOAT, technical review, property card
        and insurance policies, including PDF attachments, calendar events
        and expiration notifications.
    """,
    'author': "Carlos",
    'website': "https://www.odoo.com",
    'category': 'Productivity',
    'version': '18.0.1.0.0',
    'depends': ['fleet', 'mail', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_vehicle_document_views.xml',
        'report/fleet_report_templates.xml',
        'views/fleet_vehicle_views.xml',
        'views/fleet_manager_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}