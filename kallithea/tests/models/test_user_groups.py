import pytest

from kallithea.model.db import User

from kallithea.tests import TEST_USER_REGULAR_LOGIN
from kallithea.tests.fixture import Fixture

from kallithea.model.user_group import UserGroupModel
from kallithea.model.meta import Session


fixture = Fixture()


def teardown_function(function):
    # delete all groups
    for gr in UserGroupModel.get_all():
        fixture.destroy_user_group(gr)
    Session().commit()


@pytest.mark.parametrize("pre_existing,regular_should_be,external_should_be,groups,expected", [
    ([], [], [], [], []),
    ([], ['regular'], [], [], ['regular']),  # no changes of regular
    (['some_other'], [], [], ['some_other'], []),   # not added to regular group
    ([], ['regular'], ['container'], ['container'], ['regular', 'container']),
    ([], ['regular'], [], ['container', 'container2'], ['regular', 'container', 'container2']),
    ([], ['regular'], ['other'], [], ['regular']),  # remove not used
    (['some_other'], ['regular'], ['other', 'container'], ['container', 'container2'], ['regular', 'container', 'container2']),
])
def test_enforce_groups(pre_existing, regular_should_be,
                        external_should_be, groups, expected):
    # delete all groups
    for gr in UserGroupModel.get_all():
        fixture.destroy_user_group(gr)
    Session().commit()

    user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
    for gr in pre_existing:
        gr = fixture.create_user_group(gr)
    Session().commit()

    # make sure use is just in those groups
    for gr in regular_should_be:
        gr = fixture.create_user_group(gr)
        Session().commit()
        UserGroupModel().add_user_to_group(gr, user)
        Session().commit()

    # now special external groups created by auth plugins
    for gr in external_should_be:
        gr = fixture.create_user_group(gr, user_group_data={'extern_type': 'container'})
        Session().commit()
        UserGroupModel().add_user_to_group(gr, user)
        Session().commit()

    UserGroupModel().enforce_groups(user, groups, 'container')
    Session().commit()

    user = User.get_by_username(TEST_USER_REGULAR_LOGIN)
    in_groups = user.group_member
    assert expected == [x.users_group.users_group_name for x in in_groups]
