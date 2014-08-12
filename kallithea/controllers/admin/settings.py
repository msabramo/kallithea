# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
kallithea.controllers.admin.settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

settings controller for Kallithea admin

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jul 14, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback
import formencode

from formencode import htmlfill
from pylons import request, tmpl_context as c, url, config
from pylons.controllers.util import redirect
from pylons.i18n.translation import _

from kallithea.lib import helpers as h
from kallithea.lib.auth import LoginRequired, HasPermissionAllDecorator
from kallithea.lib.base import BaseController, render
from kallithea.lib.celerylib import tasks, run_task
from kallithea.lib.exceptions import HgsubversionImportError
from kallithea.lib.utils import repo2db_mapper, set_app_settings
from kallithea.model.db import Ui, Repository, Setting
from kallithea.model.forms import ApplicationSettingsForm, \
    ApplicationUiSettingsForm, ApplicationVisualisationForm
from kallithea.model.scm import ScmModel
from kallithea.model.notification import EmailNotificationModel
from kallithea.model.meta import Session
from kallithea.lib.utils2 import str2bool, safe_unicode
log = logging.getLogger(__name__)


class SettingsController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""
    # To properly map this controller, ensure your config/routing.py
    # file has a resource setup:
    #     map.resource('setting', 'settings', controller='admin/settings',
    #         path_prefix='/admin', name_prefix='admin_')

    @LoginRequired()
    def __before__(self):
        super(SettingsController, self).__before__()

    def _get_hg_ui_settings(self):
        ret = Ui.query().all()

        if not ret:
            raise Exception('Could not get application ui settings !')
        settings = {}
        for each in ret:
            k = each.ui_key
            v = each.ui_value
            if k == '/':
                k = 'root_path'

            if k == 'push_ssl':
                v = str2bool(v)

            if k.find('.') != -1:
                k = k.replace('.', '_')

            if each.ui_section in ['hooks', 'extensions']:
                v = each.ui_active

            settings[each.ui_section + '_' + k] = v
        return settings

    @HasPermissionAllDecorator('hg.admin')
    def settings_vcs(self):
        """GET /admin/settings: All items in the collection"""
        # url('admin_settings')
        c.active = 'vcs'
        if request.POST:
            application_form = ApplicationUiSettingsForm()()
            try:
                form_result = application_form.to_python(dict(request.POST))
            except formencode.Invalid, errors:
                return htmlfill.render(
                     render('admin/settings/settings.html'),
                     defaults=errors.value,
                     errors=errors.error_dict or {},
                     prefix_error=False,
                     encoding="UTF-8"
                )

            try:
                sett = Ui.get_by_key('push_ssl')
                sett.ui_value = form_result['web_push_ssl']
                Session().add(sett)
                if c.visual.allow_repo_location_change:
                    sett = Ui.get_by_key('/')
                    sett.ui_value = form_result['paths_root_path']
                    Session().add(sett)

                #HOOKS
                sett = Ui.get_by_key(Ui.HOOK_UPDATE)
                sett.ui_active = form_result['hooks_changegroup_update']
                Session().add(sett)

                sett = Ui.get_by_key(Ui.HOOK_REPO_SIZE)
                sett.ui_active = form_result['hooks_changegroup_repo_size']
                Session().add(sett)

                sett = Ui.get_by_key(Ui.HOOK_PUSH)
                sett.ui_active = form_result['hooks_changegroup_push_logger']
                Session().add(sett)

                sett = Ui.get_by_key(Ui.HOOK_PULL)
                sett.ui_active = form_result['hooks_outgoing_pull_logger']

                Session().add(sett)

                ## EXTENSIONS
                sett = Ui.get_by_key('largefiles')
                if not sett:
                    #make one if it's not there !
                    sett = Ui()
                    sett.ui_key = 'largefiles'
                    sett.ui_section = 'extensions'
                sett.ui_active = form_result['extensions_largefiles']
                Session().add(sett)

                sett = Ui.get_by_key('hgsubversion')
                if not sett:
                    #make one if it's not there !
                    sett = Ui()
                    sett.ui_key = 'hgsubversion'
                    sett.ui_section = 'extensions'

                sett.ui_active = form_result['extensions_hgsubversion']
                if sett.ui_active:
                    try:
                        import hgsubversion  # pragma: no cover
                    except ImportError:
                        raise HgsubversionImportError
                Session().add(sett)

#                sett = Ui.get_by_key('hggit')
#                if not sett:
#                    #make one if it's not there !
#                    sett = Ui()
#                    sett.ui_key = 'hggit'
#                    sett.ui_section = 'extensions'
#
#                sett.ui_active = form_result['extensions_hggit']
#                Session().add(sett)

                Session().commit()

                h.flash(_('Updated VCS settings'), category='success')

            except HgsubversionImportError:
                log.error(traceback.format_exc())
                h.flash(_('Unable to activate hgsubversion support. '
                          'The "hgsubversion" library is missing'),
                        category='error')

            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during updating '
                          'application settings'), category='error')

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    @HasPermissionAllDecorator('hg.admin')
    def settings_mapping(self):
        """GET /admin/settings/mapping: All items in the collection"""
        # url('admin_settings_mapping')
        c.active = 'mapping'
        if request.POST:
            rm_obsolete = request.POST.get('destroy', False)
            install_git_hooks = request.POST.get('hooks', False)
            invalidate_cache = request.POST.get('invalidate', False)
            log.debug('rescanning repo location with destroy obsolete=%s and '
                      'install git hooks=%s' % (rm_obsolete,install_git_hooks))

            if invalidate_cache:
                log.debug('invalidating all repositories cache')
                for repo in Repository.get_all():
                    ScmModel().mark_for_invalidation(repo.repo_name, delete=True)

            filesystem_repos = ScmModel().repo_scan()
            added, removed = repo2db_mapper(filesystem_repos, rm_obsolete,
                                            install_git_hook=install_git_hooks)
            _repr = lambda l: ', '.join(map(safe_unicode, l)) or '-'
            h.flash(_('Repositories successfully '
                      'rescanned added: %s ; removed: %s') %
                    (_repr(added), _repr(removed)),
                    category='success')
            return redirect(url('admin_settings_mapping'))

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    @HasPermissionAllDecorator('hg.admin')
    def settings_global(self):
        """GET /admin/settings/global: All items in the collection"""
        # url('admin_settings_global')
        c.active = 'global'
        if request.POST:
            application_form = ApplicationSettingsForm()()
            try:
                form_result = application_form.to_python(dict(request.POST))
            except formencode.Invalid, errors:
                return htmlfill.render(
                    render('admin/settings/settings.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8")

            try:
                sett1 = Setting.create_or_update('title',
                                            form_result['title'])
                Session().add(sett1)

                sett2 = Setting.create_or_update('realm',
                                            form_result['realm'])
                Session().add(sett2)

                sett3 = Setting.create_or_update('ga_code',
                                            form_result['ga_code'])
                Session().add(sett3)

                sett4 = Setting.create_or_update('captcha_public_key',
                                    form_result['captcha_public_key'])
                Session().add(sett4)

                sett5 = Setting.create_or_update('captcha_private_key',
                                    form_result['captcha_private_key'])
                Session().add(sett5)

                Session().commit()
                set_app_settings(config)
                h.flash(_('Updated application settings'), category='success')

            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during updating '
                          'application settings'),
                          category='error')

            return redirect(url('admin_settings_global'))

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    @HasPermissionAllDecorator('hg.admin')
    def settings_visual(self):
        """GET /admin/settings/visual: All items in the collection"""
        # url('admin_settings_visual')
        c.active = 'visual'
        if request.POST:
            application_form = ApplicationVisualisationForm()()
            try:
                form_result = application_form.to_python(dict(request.POST))
            except formencode.Invalid, errors:
                return htmlfill.render(
                    render('admin/settings/settings.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8"
                )

            try:
                settings = [
                    ('show_public_icon', 'show_public_icon', 'bool'),
                    ('show_private_icon', 'show_private_icon', 'bool'),
                    ('stylify_metatags', 'stylify_metatags', 'bool'),
                    ('repository_fields', 'repository_fields', 'bool'),
                    ('dashboard_items', 'dashboard_items', 'int'),
                    ('admin_grid_items', 'admin_grid_items', 'int'),
                    ('show_version', 'show_version', 'bool'),
                    ('use_gravatar', 'use_gravatar', 'bool'),
                    ('gravatar_url', 'gravatar_url', 'unicode'),
                    ('clone_uri_tmpl', 'clone_uri_tmpl', 'unicode'),
                ]
                for setting, form_key, type_ in settings:
                    sett = Setting.create_or_update(setting,
                                        form_result[form_key], type_)
                    Session().add(sett)

                Session().commit()
                set_app_settings(config)
                h.flash(_('Updated visualisation settings'),
                        category='success')

            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during updating '
                          'visualisation settings'),
                        category='error')

            return redirect(url('admin_settings_visual'))

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    @HasPermissionAllDecorator('hg.admin')
    def settings_email(self):
        """GET /admin/settings/email: All items in the collection"""
        # url('admin_settings_email')
        c.active = 'email'
        if request.POST:
            test_email = request.POST.get('test_email')
            test_email_subj = 'Kallithea test email'
            test_email_body = ('Kallithea Email test, '
                               'Kallithea version: %s' % c.kallithea_version)
            if not test_email:
                h.flash(_('Please enter email address'), category='error')
                return redirect(url('admin_settings_email'))

            test_email_html_body = EmailNotificationModel()\
                .get_email_tmpl(EmailNotificationModel.TYPE_DEFAULT,
                                body=test_email_body)

            recipients = [test_email] if test_email else None

            run_task(tasks.send_email, recipients, test_email_subj,
                     test_email_body, test_email_html_body)

            h.flash(_('Send email task created'), category='success')
            return redirect(url('admin_settings_email'))

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

        import kallithea
        c.ini = kallithea.CONFIG

        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    @HasPermissionAllDecorator('hg.admin')
    def settings_hooks(self):
        """GET /admin/settings/hooks: All items in the collection"""
        # url('admin_settings_hooks')
        c.active = 'hooks'
        if request.POST:
            if c.visual.allow_custom_hooks_settings:
                ui_key = request.POST.get('new_hook_ui_key')
                ui_value = request.POST.get('new_hook_ui_value')

                hook_id = request.POST.get('hook_id')

                try:
                    ui_key = ui_key and ui_key.strip()
                    if ui_value and ui_key:
                        Ui.create_or_update_hook(ui_key, ui_value)
                        h.flash(_('Added new hook'), category='success')
                    elif hook_id:
                        Ui.delete(hook_id)
                        Session().commit()

                    # check for edits
                    update = False
                    _d = request.POST.dict_of_lists()
                    for k, v in zip(_d.get('hook_ui_key', []),
                                    _d.get('hook_ui_value_new', [])):
                        Ui.create_or_update_hook(k, v)
                        update = True

                    if update:
                        h.flash(_('Updated hooks'), category='success')
                    Session().commit()
                except Exception:
                    log.error(traceback.format_exc())
                    h.flash(_('Error occurred during hook creation'),
                            category='error')

                return redirect(url('admin_settings_hooks'))

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

        c.hooks = Ui.get_builtin_hooks()
        c.custom_hooks = Ui.get_custom_hooks()

        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    @HasPermissionAllDecorator('hg.admin')
    def settings_search(self):
        """GET /admin/settings/search: All items in the collection"""
        # url('admin_settings_search')
        c.active = 'search'
        if request.POST:
            repo_location = self._get_hg_ui_settings()['paths_root_path']
            full_index = request.POST.get('full_index', False)
            run_task(tasks.whoosh_index, repo_location, full_index)
            h.flash(_('Whoosh reindex task scheduled'), category='success')
            return redirect(url('admin_settings_search'))

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    @HasPermissionAllDecorator('hg.admin')
    def settings_system(self):
        """GET /admin/settings/system: All items in the collection"""
        # url('admin_settings_system')
        c.active = 'system'

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())

        import kallithea
        c.ini = kallithea.CONFIG
        c.update_url = defaults.get('update_url')
        server_info = Setting.get_server_info()
        for key, val in server_info.iteritems():
            setattr(c, key, val)

        return htmlfill.render(
            render('admin/settings/settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    @HasPermissionAllDecorator('hg.admin')
    def settings_system_update(self):
        """GET /admin/settings/system/updates: All items in the collection"""
        # url('admin_settings_system_update')
        import json
        import urllib2
        from kallithea.lib.verlib import NormalizedVersion
        from kallithea import __version__

        defaults = Setting.get_app_settings()
        defaults.update(self._get_hg_ui_settings())
        _update_url = defaults.get('update_url', '')
        _update_url = "" # FIXME: disabled

        _err = lambda s: '<div style="color:#ff8888; padding:4px 0px">%s</div>' % (s)
        try:
            import kallithea
            ver = kallithea.__version__
            log.debug('Checking for upgrade on `%s` server' % _update_url)
            opener = urllib2.build_opener()
            opener.addheaders = [('User-agent', 'Kallithea-SCM/%s' % ver)]
            response = opener.open(_update_url)
            response_data = response.read()
            data = json.loads(response_data)
        except urllib2.URLError, e:
            log.error(traceback.format_exc())
            return _err('Failed to contact upgrade server: %r' % e)
        except ValueError, e:
            log.error(traceback.format_exc())
            return _err('Bad data sent from update server')

        latest = data['versions'][0]

        c.update_url = _update_url
        c.latest_data = latest
        c.latest_ver = latest['version']
        c.cur_ver = __version__
        c.should_upgrade = False

        if NormalizedVersion(c.latest_ver) > NormalizedVersion(c.cur_ver):
            c.should_upgrade = True
        c.important_notices = latest['general']

        return render('admin/settings/settings_system_update.html'),
