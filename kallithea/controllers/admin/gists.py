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
kallithea.controllers.admin.gist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

gist controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 9, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import time
import logging
import traceback
import formencode

from pylons import request, response, tmpl_context as c, url
from pylons.controllers.util import redirect
from pylons.i18n.translation import _

from kallithea.model.forms import GistForm
from kallithea.model.gist import GistModel
from kallithea.model.meta import Session
from kallithea.model.db import Gist, User
from kallithea.lib import helpers as h
from kallithea.lib.base import BaseController, render
from kallithea.lib.auth import LoginRequired, NotAnonymous
from kallithea.lib.utils import jsonify
from kallithea.lib.utils2 import safe_int, time_to_datetime
from kallithea.lib.helpers import Page
from webob.exc import HTTPNotFound, HTTPForbidden
from sqlalchemy.sql.expression import or_
from kallithea.lib.vcs.exceptions import VCSError, NodeNotChangedError

log = logging.getLogger(__name__)


class GistsController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""

    def __load_defaults(self, extra_values=None):
        c.lifetime_values = [
            (str(-1), _('forever')),
            (str(5), _('5 minutes')),
            (str(60), _('1 hour')),
            (str(60 * 24), _('1 day')),
            (str(60 * 24 * 30), _('1 month')),
        ]
        if extra_values:
            c.lifetime_values.append(extra_values)
        c.lifetime_options = [(c.lifetime_values, _("Lifetime"))]

    @LoginRequired()
    def index(self):
        """GET /admin/gists: All items in the collection"""
        # url('gists')
        not_default_user = c.authuser.username != User.DEFAULT_USER
        c.show_private = request.GET.get('private') and not_default_user
        c.show_public = request.GET.get('public') and not_default_user

        gists = Gist().query()\
            .filter(or_(Gist.gist_expires == -1, Gist.gist_expires >= time.time()))\
            .order_by(Gist.created_on.desc())

        # MY private
        if c.show_private and not c.show_public:
            gists = gists.filter(Gist.gist_type == Gist.GIST_PRIVATE)\
                             .filter(Gist.gist_owner == c.authuser.user_id)
        # MY public
        elif c.show_public and not c.show_private:
            gists = gists.filter(Gist.gist_type == Gist.GIST_PUBLIC)\
                             .filter(Gist.gist_owner == c.authuser.user_id)

        # MY public+private
        elif c.show_private and c.show_public:
            gists = gists.filter(or_(Gist.gist_type == Gist.GIST_PUBLIC,
                                     Gist.gist_type == Gist.GIST_PRIVATE))\
                             .filter(Gist.gist_owner == c.authuser.user_id)

        # default show ALL public gists
        if not c.show_public and not c.show_private:
            gists = gists.filter(Gist.gist_type == Gist.GIST_PUBLIC)

        c.gists = gists
        p = safe_int(request.GET.get('page', 1), 1)
        c.gists_pager = Page(c.gists, page=p, items_per_page=10)
        return render('admin/gists/index.html')

    @LoginRequired()
    @NotAnonymous()
    def create(self):
        """POST /admin/gists: Create a new item"""
        # url('gists')
        self.__load_defaults()
        gist_form = GistForm([x[0] for x in c.lifetime_values])()
        try:
            form_result = gist_form.to_python(dict(request.POST))
            #TODO: multiple files support, from the form
            filename = form_result['filename'] or Gist.DEFAULT_FILENAME
            nodes = {
                filename: {
                    'content': form_result['content'],
                    'lexer': form_result['mimetype']  # None is autodetect
                }
            }
            _public = form_result['public']
            gist_type = Gist.GIST_PUBLIC if _public else Gist.GIST_PRIVATE
            gist = GistModel().create(
                description=form_result['description'],
                owner=c.authuser.user_id,
                gist_mapping=nodes,
                gist_type=gist_type,
                lifetime=form_result['lifetime']
            )
            Session().commit()
            new_gist_id = gist.gist_access_id
        except formencode.Invalid, errors:
            defaults = errors.value

            return formencode.htmlfill.render(
                render('admin/gists/new.html'),
                defaults=defaults,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8"
            )

        except Exception, e:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during gist creation'), category='error')
            return redirect(url('new_gist'))
        return redirect(url('gist', gist_id=new_gist_id))

    @LoginRequired()
    @NotAnonymous()
    def new(self, format='html'):
        """GET /admin/gists/new: Form to create a new item"""
        # url('new_gist')
        self.__load_defaults()
        return render('admin/gists/new.html')

    @LoginRequired()
    @NotAnonymous()
    def update(self, gist_id):
        """PUT /admin/gists/gist_id: Update an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="PUT" />
        # Or using helpers:
        #    h.form(url('gist', gist_id=ID),
        #           method='put')
        # url('gist', gist_id=ID)

    @LoginRequired()
    @NotAnonymous()
    def delete(self, gist_id):
        """DELETE /admin/gists/gist_id: Delete an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="DELETE" />
        # Or using helpers:
        #    h.form(url('gist', gist_id=ID),
        #           method='delete')
        # url('gist', gist_id=ID)
        gist = GistModel().get_gist(gist_id)
        owner = gist.gist_owner == c.authuser.user_id
        if h.HasPermissionAny('hg.admin')() or owner:
            GistModel().delete(gist)
            Session().commit()
            h.flash(_('Deleted gist %s') % gist.gist_access_id, category='success')
        else:
            raise HTTPForbidden()

        return redirect(url('gists'))

    @LoginRequired()
    def show(self, gist_id, revision='tip', format='html', f_path=None):
        """GET /admin/gists/gist_id: Show a specific item"""
        # url('gist', gist_id=ID)
        c.gist = Gist.get_or_404(gist_id)

        #check if this gist is not expired
        if c.gist.gist_expires != -1:
            if time.time() > c.gist.gist_expires:
                log.error('Gist expired at %s' %
                          (time_to_datetime(c.gist.gist_expires)))
                raise HTTPNotFound()
        try:
            c.file_changeset, c.files = GistModel().get_gist_files(gist_id,
                                                            revision=revision)
        except VCSError:
            log.error(traceback.format_exc())
            raise HTTPNotFound()
        if format == 'raw':
            content = '\n\n'.join([f.content for f in c.files if (f_path is None or f.path == f_path)])
            response.content_type = 'text/plain'
            return content
        return render('admin/gists/show.html')

    @LoginRequired()
    @NotAnonymous()
    def edit(self, gist_id, format='html'):
        """GET /admin/gists/gist_id/edit: Form to edit an existing item"""
        # url('edit_gist', gist_id=ID)
        c.gist = Gist.get_or_404(gist_id)

        #check if this gist is not expired
        if c.gist.gist_expires != -1:
            if time.time() > c.gist.gist_expires:
                log.error('Gist expired at %s' %
                          (time_to_datetime(c.gist.gist_expires)))
                raise HTTPNotFound()
        try:
            c.file_changeset, c.files = GistModel().get_gist_files(gist_id)
        except VCSError:
            log.error(traceback.format_exc())
            raise HTTPNotFound()

        self.__load_defaults(extra_values=('0', _('unmodified')))
        rendered = render('admin/gists/edit.html')

        if request.POST:
            rpost = request.POST
            nodes = {}
            for org_filename, filename, mimetype, content in zip(
                                                    rpost.getall('org_files'),
                                                    rpost.getall('files'),
                                                    rpost.getall('mimetypes'),
                                                    rpost.getall('contents')):

                nodes[org_filename] = {
                    'org_filename': org_filename,
                    'filename': filename,
                    'content': content,
                    'lexer': mimetype,
                }
            try:
                GistModel().update(
                    gist=c.gist,
                    description=rpost['description'],
                    owner=c.gist.owner,
                    gist_mapping=nodes,
                    gist_type=c.gist.gist_type,
                    lifetime=rpost['lifetime']
                )

                Session().commit()
                h.flash(_('Successfully updated gist content'), category='success')
            except NodeNotChangedError:
                # raised if nothing was changed in repo itself. We anyway then
                # store only DB stuff for gist
                Session().commit()
                h.flash(_('Successfully updated gist data'), category='success')
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during update of gist %s') % gist_id,
                        category='error')

            return redirect(url('gist', gist_id=gist_id))

        return rendered

    @LoginRequired()
    @NotAnonymous()
    @jsonify
    def check_revision(self, gist_id):
        c.gist = Gist.get_or_404(gist_id)
        last_rev = c.gist.scm_instance.get_changeset()
        success = True
        revision = request.POST.get('revision')

        ##TODO: maybe move this to model ?
        if revision != last_rev.raw_id:
            log.error('Last revision %s is different then submited %s'
                      % (revision, last_rev))
            # our gist has newer version than we
            success = False

        return {'success': success}
