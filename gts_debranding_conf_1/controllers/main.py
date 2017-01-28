# -*- coding: utf-8 -*-

import ast
import base64
import csv
import functools
import glob
import itertools
import jinja2
import logging
import operator
import datetime
import hashlib
import os
import re
import simplejson
import sys
import time
import urllib2
import zlib
from xml.etree import ElementTree
from cStringIO import StringIO

import babel.messages.pofile
import werkzeug.utils
import werkzeug.wrappers
try:
    import xlwt
except ImportError:
    xlwt = None

import openerp
import openerp.modules.registry
from openerp.addons.base.ir.ir_qweb import AssetsBundle, QWebTemplateNotFound
from openerp.modules import get_module_resource
from openerp.tools import topological_sort
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp import http
import os

from openerp.http import request, serialize_exception as _serialize_exception


_logger = logging.getLogger(__name__)
if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('openerp.addons.gts_debranding_conf_1', "views")

env = jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = simplejson.dumps

# 1 week cache for asset bundles as advised by Google Page Speed
BUNDLE_MAXAGE = 60 * 60 * 24 * 7

#----------------------------------------------------------
# OpenERP Web helpers
#----------------------------------------------------------

db_list = http.db_list

db_monodb = http.db_monodb


def get_my_conf():
    f = open('%s/%s' % (os.path.dirname(__file__), 'abc.dung'), 'r')
    abc = ""
    for line in f:
       abc += line
    abc = eval(abc or '{}')
    return abc[request.db] if request.db and request.db in abc else {}


class Session(openerp.addons.web.controllers.main.Session):

    def session_info(self):
        request.session.ensure_valid()
        return {
            "my_config": get_my_conf(),
            "session_id": request.session_id,
            "uid": request.session.uid,
            "user_context": request.session.get_context() if request.session.uid else {},
            "db": request.session.db,
            "username": request.session.login,
            "company_id": request.env.user.company_id.id if request.session.uid else None,
        }


class Database(openerp.addons.web.controllers.main.Database):

    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):
        abc = get_my_conf()
        try:
            dbs = http.db_list()
            if not dbs:
                return http.local_redirect('/web/database/manager')
        except openerp.exceptions.AccessDenied:
            dbs = False
        return env.get_template("gts_database_selector.html").render({
            'databases': dbs,
            'debug': request.debug,
            'error': kw.get('error'),
            'power_by': abc.get('power_by'),
            'title': abc.get('title')
        })


class GTSHome(openerp.addons.web.controllers.main.Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        openerp.addons.web.controllers.main.ensure_db()
        if request.session.uid:
            if kw.get('redirect'):
                return werkzeug.utils.redirect(kw.get('redirect'), 303)
            if not request.uid:
                request.uid = request.session.uid

            menu_data = request.registry['ir.ui.menu'].load_menus(request.cr, request.uid, context=request.context)
            abc = get_my_conf()
            return request.render('web.webclient_bootstrap', qcontext={'menu_data': menu_data,
                                                                       'title_conf': abc.get('title')})
        else:
            return openerp.addons.web.controllers.main.login_redirect()

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        openerp.addons.web.controllers.main.ensure_db()

        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = openerp.SUPERUSER_ID

        abc = get_my_conf()
        values = request.params.copy()
        values['title'] = abc.get('title')
        values['power_by'] = abc.get('power_by')
        logo = abc.get('logo')
        icon = abc.get('icon') or ""
        if logo:
            fh = open('%s/%s' % (os.path.dirname(__file__).replace('controllers', ""),
                                 'static/src/img/company_logo.gif'), 'wb')
            fh.write(logo.decode('base64'))
            fh.close()
        # if icon:
        fh = open('%s/%s' % (os.path.dirname(__file__).replace('controllers', ""),
                             'static/src/img/favicon.ico'), 'wb')
        fh.write(icon.decode('base64'))
        fh.close()
        values['logo'] = abc.get('logo')
        if not redirect:
            redirect = '/web?' + request.httprequest.query_string
        values['redirect'] = redirect

        try:
            values['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                return http.redirect_with_hash(redirect)
            request.uid = old_uid
            values['error'] = "Wrong login/password"
        if request.env.ref('web.login', False):
            return request.render('web.login', values)
        else:
            # probably not an odoo compatible database
            error = 'Unable to login on database %s' % request.session.db
            return werkzeug.utils.redirect('/web/database/selector?error=%s' % error, 303)
