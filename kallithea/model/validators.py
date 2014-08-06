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
Set of generic validators
"""

import os
import re
import formencode
import logging
from collections import defaultdict
from pylons.i18n.translation import _
from webhelpers.pylonslib.secure_form import authentication_token

from formencode.validators import (
    UnicodeString, OneOf, Int, Number, Regex, Email, Bool, StringBoolean, Set,
    NotEmpty, IPAddress, CIDR, String, FancyValidator
)
from kallithea.lib.compat import OrderedSet
from kallithea.lib import ipaddr
from kallithea.lib.utils import repo_name_slug
from kallithea.lib.utils2 import safe_int, str2bool, aslist
from kallithea.model.db import RepoGroup, Repository, UserGroup, User,\
    ChangesetStatus
from kallithea.lib.exceptions import LdapImportError
from kallithea.config.routing import ADMIN_PREFIX
from kallithea.lib.auth import HasRepoGroupPermissionAny, HasPermissionAny

# silence warnings and pylint
UnicodeString, OneOf, Int, Number, Regex, Email, Bool, StringBoolean, Set, \
    NotEmpty, IPAddress, CIDR, String, FancyValidator

log = logging.getLogger(__name__)

class _Missing(object):
    pass

Missing = _Missing()


class StateObj(object):
    """
    this is needed to translate the messages using _() in validators
    """
    _ = staticmethod(_)


def M(self, key, state=None, **kwargs):
    """
    returns string from self.message based on given key,
    passed kw params are used to substitute %(named)s params inside
    translated strings

    :param msg:
    :param state:
    """
    if state is None:
        state = StateObj()
    else:
        state._ = staticmethod(_)
    #inject validator into state object
    return self.message(key, state, **kwargs)


def UniqueListFromString():
    class _UniqueListFromString(formencode.FancyValidator):
        """
        Split value on ',' and make unique while preserving order
        """
        messages = dict(
            empty=_('Value cannot be an empty list'),
            missing_value=_('Value cannot be an empty list'),
        )

        def _to_python(self, value, state):
            value = aslist(value, ',')
            seen = set()
            return [c for c in value if not (c in seen or seen.add(c))]
    
        def empty_value(self, value):
            return []

    return _UniqueListFromString


def ValidUsername(edit=False, old_data={}):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'username_exists': _(u'Username "%(username)s" already exists'),
            'system_invalid_username':
                _(u'Username "%(username)s" is forbidden'),
            'invalid_username':
                _(u'Username may only contain alphanumeric characters '
                    'underscores, periods or dashes and must begin with '
                    'alphanumeric character or underscore')
        }

        def validate_python(self, value, state):
            if value in ['default', 'new_user']:
                msg = M(self, 'system_invalid_username', state, username=value)
                raise formencode.Invalid(msg, value, state)
            #check if user is unique
            old_un = None
            if edit:
                old_un = User.get(old_data.get('user_id')).username

            if old_un != value or not edit:
                if User.get_by_username(value, case_insensitive=True):
                    msg = M(self, 'username_exists', state, username=value)
                    raise formencode.Invalid(msg, value, state)

            if re.match(r'^[a-zA-Z0-9\_]{1}[a-zA-Z0-9\-\_\.]*$', value) is None:
                msg = M(self, 'invalid_username', state)
                raise formencode.Invalid(msg, value, state)
    return _validator


def ValidRegex(msg=None):
    class _validator(formencode.validators.Regex):
        messages = dict(invalid=msg or _('The input is not valid'))
    return _validator


def ValidRepoUser():
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_username': _(u'Username %(username)s is not valid')
        }

        def validate_python(self, value, state):
            try:
                User.query().filter(User.active == True)\
                    .filter(User.username == value).one()
            except Exception:
                msg = M(self, 'invalid_username', state, username=value)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(username=msg)
                )

    return _validator


def ValidUserGroup(edit=False, old_data={}):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_group': _(u'Invalid user group name'),
            'group_exist': _(u'User group "%(usergroup)s" already exists'),
            'invalid_usergroup_name':
                _(u'user group name may only contain alphanumeric '
                  'characters underscores, periods or dashes and must begin '
                  'with alphanumeric character')
        }

        def validate_python(self, value, state):
            if value in ['default']:
                msg = M(self, 'invalid_group', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(users_group_name=msg)
                )
            #check if group is unique
            old_ugname = None
            if edit:
                old_id = old_data.get('users_group_id')
                old_ugname = UserGroup.get(old_id).users_group_name

            if old_ugname != value or not edit:
                is_existing_group = UserGroup.get_by_group_name(value,
                                                        case_insensitive=True)
                if is_existing_group:
                    msg = M(self, 'group_exist', state, usergroup=value)
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(users_group_name=msg)
                    )

            if re.match(r'^[a-zA-Z0-9]{1}[a-zA-Z0-9\-\_\.]+$', value) is None:
                msg = M(self, 'invalid_usergroup_name', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(users_group_name=msg)
                )

    return _validator


def ValidRepoGroup(edit=False, old_data={}):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'group_parent_id': _(u'Cannot assign this group as parent'),
            'group_exists': _(u'Group "%(group_name)s" already exists'),
            'repo_exists':
                _(u'Repository with name "%(group_name)s" already exists')
        }

        def validate_python(self, value, state):
            # TODO WRITE VALIDATIONS
            group_name = value.get('group_name')
            group_parent_id = value.get('group_parent_id')

            # slugify repo group just in case :)
            slug = repo_name_slug(group_name)

            # check for parent of self
            parent_of_self = lambda: (
                old_data['group_id'] == int(group_parent_id)
                if group_parent_id else False
            )
            if edit and parent_of_self():
                msg = M(self, 'group_parent_id', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(group_parent_id=msg)
                )

            old_gname = None
            if edit:
                old_gname = RepoGroup.get(old_data.get('group_id')).group_name

            if old_gname != group_name or not edit:

                # check group
                gr = RepoGroup.query()\
                      .filter(RepoGroup.group_name == slug)\
                      .filter(RepoGroup.group_parent_id == group_parent_id)\
                      .scalar()

                if gr:
                    msg = M(self, 'group_exists', state, group_name=slug)
                    raise formencode.Invalid(msg, value, state,
                            error_dict=dict(group_name=msg)
                    )

                # check for same repo
                repo = Repository.query()\
                      .filter(Repository.repo_name == slug)\
                      .scalar()

                if repo:
                    msg = M(self, 'repo_exists', state, group_name=slug)
                    raise formencode.Invalid(msg, value, state,
                            error_dict=dict(group_name=msg)
                    )

    return _validator


def ValidPassword():
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_password':
                _(u'Invalid characters (non-ascii) in password')
        }

        def validate_python(self, value, state):
            try:
                (value or '').decode('ascii')
            except UnicodeError:
                msg = M(self, 'invalid_password', state)
                raise formencode.Invalid(msg, value, state,)
    return _validator


def ValidOldPassword(username):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_password': _(u'Invalid old password')
        }

        def validate_python(self, value, state):
            from kallithea.lib import auth_modules
            if not auth_modules.authenticate(username, value, ''):
                msg = M(self, 'invalid_password', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(current_password=msg)
                )
    return _validator


def ValidPasswordsMatch(passwd='new_password', passwd_confirmation='password_confirmation'):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'password_mismatch': _(u'Passwords do not match'),
        }

        def validate_python(self, value, state):

            pass_val = value.get('password') or value.get(passwd)
            if pass_val != value[passwd_confirmation]:
                msg = M(self, 'password_mismatch', state)
                raise formencode.Invalid(msg, value, state,
                     error_dict={passwd:msg, passwd_confirmation: msg}
                )
    return _validator


def ValidAuth():
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_password': _(u'invalid password'),
            'invalid_username': _(u'invalid user name'),
            'disabled_account': _(u'Your account is disabled')
        }

        def validate_python(self, value, state):
            from kallithea.lib import auth_modules

            password = value['password']
            username = value['username']

            if not auth_modules.authenticate(username, password):
                user = User.get_by_username(username)
                if user and not user.active:
                    log.warning('user %s is disabled' % username)
                    msg = M(self, 'disabled_account', state)
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(username=msg)
                    )
                else:
                    log.warning('user %s failed to authenticate' % username)
                    msg = M(self, 'invalid_username', state)
                    msg2 = M(self, 'invalid_password', state)
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(username=msg, password=msg2)
                    )
    return _validator


def ValidAuthToken():
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_token': _(u'Token mismatch')
        }

        def validate_python(self, value, state):
            if value != authentication_token():
                msg = M(self, 'invalid_token', state)
                raise formencode.Invalid(msg, value, state)
    return _validator


def ValidRepoName(edit=False, old_data={}):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_repo_name':
                _(u'Repository name %(repo)s is disallowed'),
            'repository_exists':
                _(u'Repository named %(repo)s already exists'),
            'repository_in_group_exists': _(u'Repository "%(repo)s" already '
                                            'exists in group "%(group)s"'),
            'same_group_exists': _(u'Repository group with name "%(repo)s" '
                                   'already exists')
        }

        def _to_python(self, value, state):
            repo_name = repo_name_slug(value.get('repo_name', ''))
            repo_group = value.get('repo_group')
            if repo_group:
                gr = RepoGroup.get(repo_group)
                group_path = gr.full_path
                group_name = gr.group_name
                # value needs to be aware of group name in order to check
                # db key This is an actual just the name to store in the
                # database
                repo_name_full = group_path + RepoGroup.url_sep() + repo_name
            else:
                group_name = group_path = ''
                repo_name_full = repo_name

            value['repo_name'] = repo_name
            value['repo_name_full'] = repo_name_full
            value['group_path'] = group_path
            value['group_name'] = group_name
            return value

        def validate_python(self, value, state):

            repo_name = value.get('repo_name')
            repo_name_full = value.get('repo_name_full')
            group_path = value.get('group_path')
            group_name = value.get('group_name')

            if repo_name in [ADMIN_PREFIX, '']:
                msg = M(self, 'invalid_repo_name', state, repo=repo_name)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(repo_name=msg)
                )

            rename = old_data.get('repo_name') != repo_name_full
            create = not edit
            if rename or create:

                if group_path != '':
                    if Repository.get_by_repo_name(repo_name_full):
                        msg = M(self, 'repository_in_group_exists', state,
                                repo=repo_name, group=group_name)
                        raise formencode.Invalid(msg, value, state,
                            error_dict=dict(repo_name=msg)
                        )
                elif RepoGroup.get_by_group_name(repo_name_full):
                        msg = M(self, 'same_group_exists', state,
                                repo=repo_name)
                        raise formencode.Invalid(msg, value, state,
                            error_dict=dict(repo_name=msg)
                        )

                elif Repository.get_by_repo_name(repo_name_full):
                        msg = M(self, 'repository_exists', state,
                                repo=repo_name)
                        raise formencode.Invalid(msg, value, state,
                            error_dict=dict(repo_name=msg)
                        )
            return value
    return _validator


def ValidForkName(*args, **kwargs):
    return ValidRepoName(*args, **kwargs)


def SlugifyName():
    class _validator(formencode.validators.FancyValidator):

        def _to_python(self, value, state):
            return repo_name_slug(value)

        def validate_python(self, value, state):
            pass

    return _validator


def ValidCloneUri():
    from kallithea.lib.utils import make_ui

    def url_handler(repo_type, url, ui):
        if repo_type == 'hg':
            from kallithea.lib.vcs.backends.hg.repository import MercurialRepository
            if url.startswith('http'):
                # initially check if it's at least the proper URL
                # or does it pass basic auth
                MercurialRepository._check_url(url, ui)
            elif url.startswith('svn+http'):
                from hgsubversion.svnrepo import svnremoterepo
                svnremoterepo(ui, url).svn.uuid
            elif url.startswith('git+http'):
                raise NotImplementedError()
            else:
                raise Exception('clone from URI %s not allowed' % (url,))

        elif repo_type == 'git':
            from kallithea.lib.vcs.backends.git.repository import GitRepository
            if url.startswith('http'):
                # initially check if it's at least the proper URL
                # or does it pass basic auth
                GitRepository._check_url(url)
            elif url.startswith('svn+http'):
                raise NotImplementedError()
            elif url.startswith('hg+http'):
                raise NotImplementedError()
            else:
                raise Exception('clone from URI %s not allowed' % (url))

    class _validator(formencode.validators.FancyValidator):
        messages = {
            'clone_uri': _(u'invalid clone url'),
            'invalid_clone_uri': _(u'Invalid clone url, provide a '
                                    'valid clone http(s)/svn+http(s) url')
        }

        def validate_python(self, value, state):
            repo_type = value.get('repo_type')
            url = value.get('clone_uri')

            if not url:
                pass
            else:
                try:
                    url_handler(repo_type, url, make_ui('db', clear_session=False))
                except Exception:
                    log.exception('Url validation failed')
                    msg = M(self, 'clone_uri')
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(clone_uri=msg)
                    )
    return _validator


def ValidForkType(old_data={}):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_fork_type': _(u'Fork have to be the same type as parent')
        }

        def validate_python(self, value, state):
            if old_data['repo_type'] != value:
                msg = M(self, 'invalid_fork_type', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(repo_type=msg)
                )
    return _validator


def CanWriteGroup(old_data=None):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'permission_denied': _(u"You don't have permissions "
                                   "to create repository in this group"),
            'permission_denied_root': _(u"no permission to create repository "
                                        "in root location")
        }

        def _to_python(self, value, state):
            #root location
            if value in [-1, "-1"]:
                return None
            return value

        def validate_python(self, value, state):
            gr = RepoGroup.get(value)
            gr_name = gr.group_name if gr else None  # None means ROOT location
            # create repositories with write permission on group is set to true
            create_on_write = HasPermissionAny('hg.create.write_on_repogroup.true')()
            group_admin = HasRepoGroupPermissionAny('group.admin')(gr_name,
                                            'can write into group validator')
            group_write = HasRepoGroupPermissionAny('group.write')(gr_name,
                                            'can write into group validator')
            forbidden = not (group_admin or (group_write and create_on_write))
            can_create_repos = HasPermissionAny('hg.admin', 'hg.create.repository')
            gid = (old_data['repo_group'].get('group_id')
                   if (old_data and 'repo_group' in old_data) else None)
            value_changed = gid != safe_int(value)
            new = not old_data
            # do check if we changed the value, there's a case that someone got
            # revoked write permissions to a repository, he still created, we
            # don't need to check permission if he didn't change the value of
            # groups in form box
            if value_changed or new:
                #parent group need to be existing
                if gr and forbidden:
                    msg = M(self, 'permission_denied', state)
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(repo_type=msg)
                    )
                ## check if we can write to root location !
                elif gr is None and not can_create_repos():
                    msg = M(self, 'permission_denied_root', state)
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(repo_type=msg)
                    )

    return _validator


def CanCreateGroup(can_create_in_root=False):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'permission_denied': _(u"You don't have permissions "
                                   "to create a group in this location")
        }

        def to_python(self, value, state):
            #root location
            if value in [-1, "-1"]:
                return None
            return value

        def validate_python(self, value, state):
            gr = RepoGroup.get(value)
            gr_name = gr.group_name if gr else None  # None means ROOT location

            if can_create_in_root and gr is None:
                #we can create in root, we're fine no validations required
                return

            forbidden_in_root = gr is None and not can_create_in_root
            val = HasRepoGroupPermissionAny('group.admin')
            forbidden = not val(gr_name, 'can create group validator')
            if forbidden_in_root or forbidden:
                msg = M(self, 'permission_denied', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(group_parent_id=msg)
                )

    return _validator


def ValidPerms(type_='repo'):
    if type_ == 'repo_group':
        EMPTY_PERM = 'group.none'
    elif type_ == 'repo':
        EMPTY_PERM = 'repository.none'
    elif type_ == 'user_group':
        EMPTY_PERM = 'usergroup.none'

    class _validator(formencode.validators.FancyValidator):
        messages = {
            'perm_new_member_name':
                _(u'This username or user group name is not valid')
        }

        def to_python(self, value, state):
            perms_update = OrderedSet()
            perms_new = OrderedSet()
            # build a list of permission to update and new permission to create

            #CLEAN OUT ORG VALUE FROM NEW MEMBERS, and group them using
            new_perms_group = defaultdict(dict)
            for k, v in value.copy().iteritems():
                if k.startswith('perm_new_member'):
                    del value[k]
                    _type, part = k.split('perm_new_member_')
                    args = part.split('_')
                    if len(args) == 1:
                        new_perms_group[args[0]]['perm'] = v
                    elif len(args) == 2:
                        _key, pos = args
                        new_perms_group[pos][_key] = v

            # fill new permissions in order of how they were added
            for k in sorted(map(int, new_perms_group.keys())):
                perm_dict = new_perms_group[str(k)]
                new_member = perm_dict.get('name')
                new_perm = perm_dict.get('perm')
                new_type = perm_dict.get('type')
                if new_member and new_perm and new_type:
                    perms_new.add((new_member, new_perm, new_type))

            for k, v in value.iteritems():
                if k.startswith('u_perm_') or k.startswith('g_perm_'):
                    member = k[7:]
                    t = {'u': 'user',
                         'g': 'users_group'
                    }[k[0]]
                    if member == User.DEFAULT_USER:
                        if str2bool(value.get('repo_private')):
                            # set none for default when updating to
                            # private repo protects agains form manipulation
                            v = EMPTY_PERM
                    perms_update.add((member, v, t))

            value['perms_updates'] = list(perms_update)
            value['perms_new'] = list(perms_new)

            # update permissions
            for k, v, t in perms_new:
                try:
                    if t is 'user':
                        self.user_db = User.query()\
                            .filter(User.active == True)\
                            .filter(User.username == k).one()
                    if t is 'users_group':
                        self.user_db = UserGroup.query()\
                            .filter(UserGroup.users_group_active == True)\
                            .filter(UserGroup.users_group_name == k).one()

                except Exception:
                    log.exception('Updated permission failed')
                    msg = M(self, 'perm_new_member_type', state)
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(perm_new_member_name=msg)
                    )
            return value
    return _validator


def ValidSettings():
    class _validator(formencode.validators.FancyValidator):
        def _to_python(self, value, state):
            # settings  form for users that are not admin
            # can't edit certain parameters, it's extra backup if they mangle
            # with forms

            forbidden_params = [
                'user', 'repo_type', 'repo_enable_locking',
                'repo_enable_downloads', 'repo_enable_statistics'
            ]

            for param in forbidden_params:
                if param in value:
                    del value[param]
            return value

        def validate_python(self, value, state):
            pass
    return _validator


def ValidPath():
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_path': _(u'This is not a valid path')
        }

        def validate_python(self, value, state):
            if not os.path.isdir(value):
                msg = M(self, 'invalid_path', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(paths_root_path=msg)
                )
    return _validator


def UniqSystemEmail(old_data={}):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'email_taken': _(u'This e-mail address is already taken')
        }

        def _to_python(self, value, state):
            return value.lower()

        def validate_python(self, value, state):
            if (old_data.get('email') or '').lower() != value:
                user = User.get_by_email(value, case_insensitive=True)
                if user:
                    msg = M(self, 'email_taken', state)
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(email=msg)
                    )
    return _validator


def ValidSystemEmail():
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'non_existing_email': _(u'e-mail "%(email)s" does not exist.')
        }

        def _to_python(self, value, state):
            return value.lower()

        def validate_python(self, value, state):
            user = User.get_by_email(value, case_insensitive=True)
            if user is None:
                msg = M(self, 'non_existing_email', state, email=value)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(email=msg)
                )

    return _validator


def LdapLibValidator():
    class _validator(formencode.validators.FancyValidator):
        messages = {

        }

        def validate_python(self, value, state):
            try:
                import ldap
                ldap  # pyflakes silence !
            except ImportError:
                raise LdapImportError()

    return _validator


def AttrLoginValidator():
    class _validator(formencode.validators.UnicodeString):
        messages = {
            'invalid_cn':
                  _(u'The LDAP Login attribute of the CN must be specified - '
                    'this is the name of the attribute that is equivalent '
                    'to "username"')
        }
        messages['empty'] = messages['invalid_cn']

    return _validator


def NotReviewedRevisions(repo_id):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'rev_already_reviewed':
                  _(u'Revisions %(revs)s are already part of pull request '
                    'or have set status')
        }

        def validate_python(self, value, state):
            # check revisions if they are not reviewed, or a part of another
            # pull request
            statuses = ChangesetStatus.query()\
                .filter(ChangesetStatus.revision.in_(value))\
                .filter(ChangesetStatus.repo_id == repo_id)\
                .all()

            errors = []
            for cs in statuses:
                if cs.pull_request_id:
                    errors.append(['pull_req', cs.revision[:12]])
                elif cs.status:
                    errors.append(['status', cs.revision[:12]])

            if errors:
                revs = ','.join([x[1] for x in errors])
                msg = M(self, 'rev_already_reviewed', state, revs=revs)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(revisions=revs)
                )

    return _validator


def ValidIp():
    class _validator(CIDR):
        messages = dict(
            badFormat=_('Please enter a valid IPv4 or IpV6 address'),
            illegalBits=_('The network size (bits) must be within the range'
                ' of 0-32 (not %(bits)r)')
        )

        def to_python(self, value, state):
            v = super(_validator, self).to_python(value, state)
            v = v.strip()
            net = ipaddr.IPNetwork(address=v)
            if isinstance(net, ipaddr.IPv4Network):
                #if IPv4 doesn't end with a mask, add /32
                if '/' not in value:
                    v += '/32'
            if isinstance(net, ipaddr.IPv6Network):
                #if IPv6 doesn't end with a mask, add /128
                if '/' not in value:
                    v += '/128'
            return v

        def validate_python(self, value, state):
            try:
                addr = value.strip()
                #this raises an ValueError if address is not IpV4 or IpV6
                ipaddr.IPNetwork(address=addr)
            except ValueError:
                raise formencode.Invalid(self.message('badFormat', state),
                                         value, state)

    return _validator


def FieldKey():
    class _validator(formencode.validators.FancyValidator):
        messages = dict(
            badFormat=_('Key name can only consist of letters, '
                        'underscore, dash or numbers')
        )

        def validate_python(self, value, state):
            if not re.match('[a-zA-Z0-9_-]+$', value):
                raise formencode.Invalid(self.message('badFormat', state),
                                         value, state)
    return _validator


def BasePath():
    class _validator(formencode.validators.FancyValidator):
        messages = dict(
            badPath=_('Filename cannot be inside a directory')
        )

        def _to_python(self, value, state):
            return value

        def validate_python(self, value, state):
            if value != os.path.basename(value):
                raise formencode.Invalid(self.message('badPath', state),
                                         value, state)
    return _validator


def ValidAuthPlugins():
    class _validator(formencode.validators.FancyValidator):
        messages = dict(
            import_duplicate=_('Plugins %(loaded)s and %(next_to_load)s both export the same name')
        )

        def _to_python(self, value, state):
            # filter empty values
            return filter(lambda s: s not in [None, ''], value)

        def validate_python(self, value, state):
            from kallithea.lib import auth_modules
            module_list = value
            unique_names = {}
            try:
                for module in module_list:
                    plugin = auth_modules.loadplugin(module)
                    plugin_name = plugin.name
                    if plugin_name in unique_names:
                        msg = M(self, 'import_duplicate', state,
                                loaded=unique_names[plugin_name],
                                next_to_load=plugin_name)
                        raise formencode.Invalid(msg, value, state)
                    unique_names[plugin_name] = plugin
            except (ImportError, AttributeError, TypeError), e:
                raise formencode.Invalid(str(e), value, state)

    return _validator
