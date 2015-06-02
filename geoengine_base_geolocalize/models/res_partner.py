# -*- coding: utf-8 -*-
##############################################################################
#
#   Author: Laurent Mignon
#   Copyright (c) 2015 Acsone SA/NV (http://www.acsone.eu)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from openerp import api, fields
from openerp import exceptions
from openerp.tools.translate import _
from openerp.addons.base_geoengine import geo_model
from openerp.addons.base_geoengine import fields as geo_fields

try:
    import requests
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning('Shapely or geojson are not available in the sys path')

_logger = logging.getLogger(__name__)


class ResPartner(geo_model.GeoModel):
    """Add geo_point to partner using a function field"""
    _inherit = "res.partner"

    @api.model
    def _get_mapquest_key(self):
        config_parameter_obj = self.env['ir.config_parameter']
        key = config_parameter_obj.get_param(
            'geoengine_maquestapi_key')
        if not key:
            raise exceptions.ValidationError(
                _("In order to use the "
                  "`Open MapQuest API <http://open.mapquestapi.com/>`_ you "
                  " must be registered for services at at the "
                  "`MapQuest Developer Network "
                  "<http://developer.mapquest.com/>`_ site. The key you you "
                  "received when you registered must be specify in the System "
                  "Parameters under the key 'geoengine_maquestapi_key'."))
        return key

    @api.one
    def geocode_address(self):
        """Get the latitude and longitude by requesting "mapquestapi"
        see http://open.mapquestapi.com/geocoding/
        """
        key = self._get_mapquest_key()
        url = 'http://open.mapquestapi.com/geocoding/v1/address?key=%s' % key
        json_request = {
            'locations': [
                {'street': self.street,
                 'postalCode': self.zip,
                 'city': self.city,
                 'state': self.state_id.name,
                 'country': self.country_id.name}
            ]
        }
        r = requests.post(url, data=json_request)
        try:
            r.raise_for_status()
        except Exception as e:
            _logger.exception('Geocoding error')
            raise exceptions.Warning(_(
                'Geocoding error. \n %s') % e.message)
        vals = r.json()
        latLng = vals.get('latLng', {'lng': 0.0, 'lat': 0.0})
        self.write({
            'partner_latitude': latLng.get('lat'),
            'partner_longitude': latLng.get('lng'),
            'date_localization': fields.Date.today()})

    @api.one
    def geo_localize(self):
        self.geocode_address()
        return True

    @api.one
    @api.depends('partner_latitude', 'partner_longitude')
    def _get_geo_point(self):
        if not self.partner_latitude or not self.partner_longitude:
            self.geo_point = False
        self.geo_point = geo_fields.GeoPoint.from_latlon(
            self.env.cr, self.partner_latitude, self.partner_longitude)

    geo_point = geo_fields.GeoPoint(
        readonly=True, store=True, compute='_get_geo_point')
