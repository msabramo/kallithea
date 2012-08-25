"""
Set of generic validators
"""
import os
import re
import formencode
import logging
from pylons.i18n.translation import _
from webhelpers.pylonslib.secure_form import authentication_token

from formencode.validators import (
    UnicodeString, OneOf, Int, Number, Regex, Email, Bool, StringBoolean, Set,
    NotEmpty
)
from rhodecode.lib.utils import repo_name_slug
from rhodecode.model.db import RepoGroup, Repository, UsersGroup, User,\
    ChangesetStatus
from rhodecode.lib.exceptions import LdapImportError
from rhodecode.config.routing import ADMIN_PREFIX

# silence warnings and pylint
UnicodeString, OneOf, Int, Number, Regex, Email, Bool, StringBoolean, Set, \
    NotEmpty

log = logging.getLogger(__name__)


class UniqueList(formencode.FancyValidator):
    """
    Unique List !
    """
    messages = dict(
        empty=_('Value cannot be an empty list'),
        missing_value=_('Value cannot be an empty list'),
    )

    def _to_python(self, value, state):
        if isinstance(value, list):
            return value
        elif isinstance(value, set):
            return list(value)
        elif isinstance(value, tuple):
            return list(value)
        elif value is None:
            return []
        else:
            return [value]

    def empty_value(self, value):
        return []


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


def ValidUsername(edit=False, old_data={}):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'username_exists': _(u'Username "%(username)s" already exists'),
            'system_invalid_username':
                _(u'Username "%(username)s" is forbidden'),
            'invalid_username':
                _(u'Username may only contain alphanumeric characters '
                  'underscores, periods or dashes and must begin with '
                  'alphanumeric character')
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

            if re.match(r'^[a-zA-Z0-9]{1}[a-zA-Z0-9\-\_\.]+$', value) is None:
                msg = M(self, 'invalid_username', state)
                raise formencode.Invalid(msg, value, state)
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


def ValidUsersGroup(edit=False, old_data={}):
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_group': _(u'Invalid users group name'),
            'group_exist': _(u'Users group "%(usersgroup)s" already exists'),
            'invalid_usersgroup_name':
                _(u'users group name may only contain  alphanumeric '
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
                old_ugname = UsersGroup.get(old_id).users_group_name

            if old_ugname != value or not edit:
                is_existing_group = UsersGroup.get_by_group_name(value,
                                                        case_insensitive=True)
                if is_existing_group:
                    msg = M(self, 'group_exist', state, usersgroup=value)
                    raise formencode.Invalid(msg, value, state,
                        error_dict=dict(users_group_name=msg)
                    )

            if re.match(r'^[a-zA-Z0-9]{1}[a-zA-Z0-9\-\_\.]+$', value) is None:
                msg = M(self, 'invalid_usersgroup_name', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(users_group_name=msg)
                )

    return _validator


def ValidReposGroup(edit=False, old_data={}):
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


def ValidPasswordsMatch():
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'password_mismatch': _(u'Passwords do not match'),
        }

        def validate_python(self, value, state):

            pass_val = value.get('password') or value.get('new_password')
            if pass_val != value['password_confirmation']:
                msg = M(self, 'password_mismatch', state)
                raise formencode.Invalid(msg, value, state,
                     error_dict=dict(password_confirmation=msg)
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
            from rhodecode.lib.auth import authenticate

            password = value['password']
            username = value['username']

            if not authenticate(username, password):
                user = User.get_by_username(username)
                if user and user.active is False:
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
            'same_group_exists': _(u'Repositories group with name "%(repo)s" '
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
    from rhodecode.lib.utils import make_ui

    def url_handler(repo_type, url, ui=None):
        if repo_type == 'hg':
            from rhodecode.lib.vcs.backends.hg.repository import MercurialRepository
            from mercurial.httppeer import httppeer
            if url.startswith('http'):
                ## initially check if it's at least the proper URL
                ## or does it pass basic auth
                MercurialRepository._check_url(url)
                httppeer(ui, url)._capabilities()
            elif url.startswith('svn+http'):
                from hgsubversion.svnrepo import svnremoterepo
                svnremoterepo(ui, url).capabilities
            elif url.startswith('git+http'):
                raise NotImplementedError()

        elif repo_type == 'git':
            from rhodecode.lib.vcs.backends.git.repository import GitRepository
            if url.startswith('http'):
                ## initially check if it's at least the proper URL
                ## or does it pass basic auth
                GitRepository._check_url(url)
            elif url.startswith('svn+http'):
                raise NotImplementedError()
            elif url.startswith('hg+http'):
                raise NotImplementedError()

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


def ValidPerms(type_='repo'):
    if type_ == 'group':
        EMPTY_PERM = 'group.none'
    elif type_ == 'repo':
        EMPTY_PERM = 'repository.none'

    class _validator(formencode.validators.FancyValidator):
        messages = {
            'perm_new_member_name':
                _(u'This username or users group name is not valid')
        }

        def to_python(self, value, state):
            perms_update = []
            perms_new = []
            # build a list of permission to update and new permission to create
            for k, v in value.items():
                # means new added member to permissions
                if k.startswith('perm_new_member'):
                    new_perm = value.get('perm_new_member', False)
                    new_member = value.get('perm_new_member_name', False)
                    new_type = value.get('perm_new_member_type')

                    if new_member and new_perm:
                        if (new_member, new_perm, new_type) not in perms_new:
                            perms_new.append((new_member, new_perm, new_type))
                elif k.startswith('u_perm_') or k.startswith('g_perm_'):
                    member = k[7:]
                    t = {'u': 'user',
                         'g': 'users_group'
                    }[k[0]]
                    if member == 'default':
                        if value.get('private'):
                            # set none for default when updating to
                            # private repo
                            v = EMPTY_PERM
                    perms_update.append((member, v, t))

            value['perms_updates'] = perms_update
            value['perms_new'] = perms_new

            # update permissions
            for k, v, t in perms_new:
                try:
                    if t is 'user':
                        self.user_db = User.query()\
                            .filter(User.active == True)\
                            .filter(User.username == k).one()
                    if t is 'users_group':
                        self.user_db = UsersGroup.query()\
                            .filter(UsersGroup.users_group_active == True)\
                            .filter(UsersGroup.users_group_name == k).one()

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
            # settings  form can't edit user
            if 'user' in value:
                del value['user']
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
    class _validator(formencode.validators.FancyValidator):
        messages = {
            'invalid_cn':
                  _(u'The LDAP Login attribute of the CN must be specified - '
                    'this is the name of the attribute that is equivalent '
                    'to "username"')
        }

        def validate_python(self, value, state):
            if not value or not isinstance(value, (str, unicode)):
                msg = M(self, 'invalid_cn', state)
                raise formencode.Invalid(msg, value, state,
                    error_dict=dict(ldap_attr_login=msg)
                )

    return _validator


def NotReviewedRevisions():
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
                .filter(ChangesetStatus.revision.in_(value)).all()
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