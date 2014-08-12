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
kallithea.controllers.feed
~~~~~~~~~~~~~~~~~~~~~~~~~~

Feed controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 23, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging

from pylons import response, tmpl_context as c
from pylons.i18n.translation import _

from beaker.cache import cache_region, region_invalidate
from webhelpers.feedgenerator import Atom1Feed, Rss201rev2Feed

from kallithea.lib import helpers as h
from kallithea.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from kallithea.lib.base import BaseRepoController
from kallithea.lib.diffs import DiffProcessor, LimitedDiffContainer
from kallithea.model.db import CacheInvalidation
from kallithea.lib.utils2 import safe_int, str2bool, safe_unicode

log = logging.getLogger(__name__)


class FeedController(BaseRepoController):

    @LoginRequired(api_access=True)
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def __before__(self):
        super(FeedController, self).__before__()
        #common values for feeds
        self.description = _('Changes on %s repository')
        self.title = self.title = _('%s %s feed') % (c.site_name, '%s')
        self.language = 'en-us'
        self.ttl = "5"
        import kallithea
        CONF = kallithea.CONFIG
        self.include_diff = str2bool(CONF.get('rss_include_diff', False))
        self.feed_nr = safe_int(CONF.get('rss_items_per_page', 20))
        # we need to protect from parsing huge diffs here other way
        # we can kill the server
        self.feed_diff_limit = safe_int(CONF.get('rss_cut_off_limit', 32 * 1024))

    def _get_title(self, cs):
        return "%s" % (
            h.shorter(cs.message, 160)
        )

    def __changes(self, cs):
        changes = []
        diff_processor = DiffProcessor(cs.diff(),
                                       diff_limit=self.feed_diff_limit)
        _parsed = diff_processor.prepare(inline_diff=False)
        limited_diff = False
        if isinstance(_parsed, LimitedDiffContainer):
            limited_diff = True

        for st in _parsed:
            st.update({'added': st['stats']['added'],
                       'removed': st['stats']['deleted']})
            changes.append('\n %(operation)s %(filename)s '
                           '(%(added)s lines added, %(removed)s lines removed)'
                            % st)
        if limited_diff:
            changes = changes + ['\n ' +
                                 _('Changeset was too big and was cut off...')]
        return diff_processor, changes

    def __get_desc(self, cs):
        desc_msg = [(_('%s committed on %s')
                     % (h.person(cs.author), h.fmt_date(cs.date))) + '<br/>']
        #branches, tags, bookmarks
        if cs.branch:
            desc_msg.append('branch: %s<br/>' % cs.branch)
        if h.is_hg(c.db_repo_scm_instance):
            for book in cs.bookmarks:
                desc_msg.append('bookmark: %s<br/>' % book)
        for tag in cs.tags:
            desc_msg.append('tag: %s<br/>' % tag)
        diff_processor, changes = self.__changes(cs)
        # rev link
        _url = h.canonical_url('changeset_home', repo_name=c.db_repo.repo_name,
                   revision=cs.raw_id)
        desc_msg.append('changeset: <a href="%s">%s</a>' % (_url, cs.raw_id[:8]))

        desc_msg.append('<pre>')
        desc_msg.append(cs.message)
        desc_msg.append('\n')
        desc_msg.extend(changes)
        if self.include_diff:
            desc_msg.append('\n\n')
            desc_msg.append(diff_processor.as_raw())
        desc_msg.append('</pre>')
        return map(safe_unicode, desc_msg)

    def atom(self, repo_name):
        """Produce an atom-1.0 feed via feedgenerator module"""

        @cache_region('long_term')
        def _get_feed_from_cache(key, kind):
            feed = Atom1Feed(
                 title=self.title % repo_name,
                 link=h.canonical_url('summary_home', repo_name=repo_name),
                 description=self.description % repo_name,
                 language=self.language,
                 ttl=self.ttl
            )

            for cs in reversed(list(c.db_repo_scm_instance[-self.feed_nr:])):
                feed.add_item(title=self._get_title(cs),
                              link=h.canonical_url('changeset_home', repo_name=repo_name,
                                       revision=cs.raw_id),
                              author_name=cs.author,
                              description=''.join(self.__get_desc(cs)),
                              pubdate=cs.date,
                              )

            response.content_type = feed.mime_type
            return feed.writeString('utf-8')

        kind = 'ATOM'
        valid = CacheInvalidation.test_and_set_valid(repo_name, kind)
        if not valid:
            region_invalidate(_get_feed_from_cache, None, repo_name, kind)
        return _get_feed_from_cache(repo_name, kind)

    def rss(self, repo_name):
        """Produce an rss2 feed via feedgenerator module"""

        @cache_region('long_term')
        def _get_feed_from_cache(key, kind):
            feed = Rss201rev2Feed(
                title=self.title % repo_name,
                link=h.canonical_url('summary_home', repo_name=repo_name),
                description=self.description % repo_name,
                language=self.language,
                ttl=self.ttl
            )

            for cs in reversed(list(c.db_repo_scm_instance[-self.feed_nr:])):
                feed.add_item(title=self._get_title(cs),
                              link=h.canonical_url('changeset_home', repo_name=repo_name,
                                       revision=cs.raw_id),
                              author_name=cs.author,
                              description=''.join(self.__get_desc(cs)),
                              pubdate=cs.date,
                             )

            response.content_type = feed.mime_type
            return feed.writeString('utf-8')

        kind = 'RSS'
        valid = CacheInvalidation.test_and_set_valid(repo_name, kind)
        if not valid:
            region_invalidate(_get_feed_from_cache, None, repo_name, kind)
        return _get_feed_from_cache(repo_name, kind)
