.. _api:

===
API
===


Kallithea has a simple JSON RPC API with a single schema for calling all api
methods. Everything is available by sending JSON encoded http(s) requests to
<your_server>/_admin/api .


API ACCESS FOR WEB VIEWS
++++++++++++++++++++++++

API access can also be turned on for each web view in Kallithea that is
decorated with the `@LoginRequired` decorator. Some views use
`@LoginRequired(api_access=True)` and are always available. By default only
RSS/ATOM feed views are enabled. Other views are
only available if they have been white listed. Edit the
`api_access_controllers_whitelist` option in your .ini file and define views
that should have API access enabled.

For example, to enable API access to patch/diff raw file and archive::

    api_access_controllers_whitelist =
        ChangesetController:changeset_patch,
        ChangesetController:changeset_raw,
        FilesController:raw,
        FilesController:archivefile

After this change, a Kallithea view can be accessed without login by adding a
GET parameter `?api_key=<api_key>` to url.

Exposing raw diffs is a good way to integrate with
3rd party services like code review, or build farms that could download archives.


API ACCESS
++++++++++

Clients must send JSON encoded JSON-RPC requests::

    {
        "id: "<id>",
        "api_key": "<api_key>",
        "method": "<method_name>",
        "args": {"<arg_key>": "<arg_val>"}
    }

For example, to pull to a local "CPython" mirror using curl::

    curl https://server.com/_admin/api -X POST -H 'content-type:text/plain' --data-binary '{"id":1,"api_key":"xe7cdb2v278e4evbdf5vs04v832v0efvcbcve4a3","method":"pull","args":{"repo":"CPython"}}'

In general, provide
 - *id*, a value of any type, can be used to match the response with the request that it is replying to.
 - *api_key*, for authentication and permission validation.
 - *method*, the name of the method to call - a list of available methods can be found below.
 - *args*, the arguments to pass to the method.

.. note::

    api_key can be found or set on the user account page

The response to the JSON-RPC API call will always be a JSON structure::

    {
        "id":<id>, # the id that was used in the request
        "result": "<result>"|null, # JSON formatted result, null if any errors
        "error": "null"|<error_message> # JSON formatted error (if any)
    }

All responses from API will be `HTTP/1.0 200 OK`. If there is an error,
the reponse will have a failure description in *error* and
*result* will be null.


API CLIENT
++++++++++

Kallithea comes with a `kallithea-api` command line tool providing a convenient
way to call the JSON-RPC API.

For example, to call `get_repo`::

 kallithea-api --apihost=<your.kallithea.server.url> --apikey=<yourapikey> get_repo

 calling {"api_key": "<apikey>", "id": 75, "args": {}, "method": "get_repo"} to http://127.0.0.1:5000
 Kallithea said:
 {'error': 'Missing non optional `repoid` arg in JSON DATA',
  'id': 75,
  'result': None}

Oops, looks like we forgot to add an argument. Let's try again, now providing the repoid as parameter::

    kallithea-api get_repo repoid:myrepo

    calling {"api_key": "<apikey>", "id": 39, "args": {"repoid": "myrepo"}, "method": "get_repo"} to http://127.0.0.1:5000
    Kallithea said:
    {'error': None,
     'id': 39,
     'result': <json data...>}

To avoid specifying apihost and apikey every time, run::

  kallithea-api --save-config --apihost=<your.kallithea.server.url> --apikey=<yourapikey>

This will create a `~/.config/kallithea` with the specified hostname and apikey
so you don't have to specify them every time.


API METHODS
+++++++++++


pull
----

Pull the given repo from remote location. Can be used to automatically keep
remote repos up to date.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "pull"
    args :    {
                "repoid" : "<reponame or repo_id>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : "Pulled from `<reponame>`"
    error :  null


rescan_repos
------------

Rescan repositories. If remove_obsolete is set,
Kallithea will delete repos that are in database but not in the filesystem.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "rescan_repos"
    args :    {
                "remove_obsolete" : "<boolean = Optional(False)>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : "{'added': [<list of names of added repos>],
               'removed': [<list of names of removed repos>]}"
    error :  null


invalidate_cache
----------------

Invalidate cache for repository.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with admin or write access to the repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "invalidate_cache"
    args :    {
                "repoid" : "<reponame or repo_id>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : "Caches of repository `<reponame>`"
    error :  null


lock
----

Set the locking state on the given repository by the given user.
If param 'userid' is skipped, it is set to the id of the user who is calling this method.
If param 'locked' is skipped, the current lock state of the repository is returned.
This command can only be executed using the api_key of a user with admin rights, or that of a regular user with admin or write access to the repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "lock"
    args :    {
                "repoid" : "<reponame or repo_id>"
                "userid" : "<user_id or username = Optional(=apiuser)>",
                "locked" : "<bool true|false = Optional(=None)>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : {
                 "repo": "<reponame>",
                 "locked": "<bool true|false>",
                 "locked_since": "<float lock_time>",
                 "locked_by": "<username>",
                 "msg": "User `<username>` set lock state for repo `<reponame>` to `<false|true>`"
             }
    error :  null


get_ip
------

Return IP address as seen from Kallithea server, together with all
defined IP addresses for given user.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_ip"
    args :    {
                "userid" : "<user_id or username>",
              }

OUTPUT::

    id : <id_given_in_input>
    result : {
                 "ip_addr_server": <ip_from_clien>",
                 "user_ips": [
                                {
                                   "ip_addr": "<ip_with_mask>",
                                   "ip_range": ["<start_ip>", "<end_ip>"],
                                },
                                ...
                             ]
             }

    error :  null


get_user
--------

Get a user by username or userid. The result is empty if user can't be found.
If userid param is skipped, it is set to id of user who is calling this method.
Any userid can be specified when the command is executed using the api_key of a user with admin rights.
Regular users can only speicy their own userid.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_user"
    args :    {
                "userid" : "<username or user_id Optional(=apiuser)>"
              }

OUTPUT::

    id : <id_given_in_input>
    result: None if user does not exist or
            {
                "user_id" :     "<user_id>",
                "api_key" :     "<api_key>",
                "username" :    "<username>",
                "firstname":    "<firstname>",
                "lastname" :    "<lastname>",
                "email" :       "<email>",
                "emails":       "<list_of_all_additional_emails>",
                "ip_addresses": "<list_of_ip_addresses_for_user>",
                "active" :      "<bool>",
                "admin" :       "<bool>",
                "ldap_dn" :     "<ldap_dn>",
                "last_login":   "<last_login>",
                "permissions": {
                    "global": ["hg.create.repository",
                               "repository.read",
                               "hg.register.manual_activate"],
                    "repositories": {"repo1": "repository.none"},
                    "repositories_groups": {"Group1": "group.read"}
                 },
            }

    error:  null


get_users
---------

List all existing users.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_users"
    args :    { }

OUTPUT::

    id : <id_given_in_input>
    result: [
              {
                "user_id" :     "<user_id>",
                "api_key" :     "<api_key>",
                "username" :    "<username>",
                "firstname":    "<firstname>",
                "lastname" :    "<lastname>",
                "email" :       "<email>",
                "emails":       "<list_of_all_additional_emails>",
                "ip_addresses": "<list_of_ip_addresses_for_user>",
                "active" :      "<bool>",
                "admin" :       "<bool>",
                "ldap_dn" :     "<ldap_dn>",
                "last_login":   "<last_login>",
              },
              …
            ]
    error:  null


create_user
-----------

Create new user.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "create_user"
    args :    {
                "username" :  "<username>",
                "email" :     "<useremail>",
                "password" :  "<password = Optional(None)>",
                "firstname" : "<firstname> = Optional(None)",
                "lastname" :  "<lastname> = Optional(None)",
                "active" :    "<bool> = Optional(True)",
                "admin" :     "<bool> = Optional(False)",
                "ldap_dn" :   "<ldap_dn> = Optional(None)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "created new user `<username>`",
              "user": {
                "user_id" :  "<user_id>",
                "username" : "<username>",
                "firstname": "<firstname>",
                "lastname" : "<lastname>",
                "email" :    "<email>",
                "emails":    "<list_of_all_additional_emails>",
                "active" :   "<bool>",
                "admin" :    "<bool>",
                "ldap_dn" :  "<ldap_dn>",
                "last_login": "<last_login>",
              },
            }
    error:  null


update_user
-----------

Update the given user if such user exists.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "update_user"
    args :    {
                "userid" : "<user_id or username>",
                "username" :  "<username> = Optional(None)",
                "email" :     "<useremail> = Optional(None)",
                "password" :  "<password> = Optional(None)",
                "firstname" : "<firstname> = Optional(None)",
                "lastname" :  "<lastname> = Optional(None)",
                "active" :    "<bool> = Optional(None)",
                "admin" :     "<bool> = Optional(None)",
                "ldap_dn" :   "<ldap_dn> = Optional(None)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "updated user ID:<userid> <username>",
              "user": {
                "user_id" :  "<user_id>",
                "api_key" :  "<api_key>",
                "username" : "<username>",
                "firstname": "<firstname>",
                "lastname" : "<lastname>",
                "email" :    "<email>",
                "emails":    "<list_of_all_additional_emails>",
                "active" :   "<bool>",
                "admin" :    "<bool>",
                "ldap_dn" :  "<ldap_dn>",
                "last_login": "<last_login>",
              },
            }
    error:  null


delete_user
-----------

Delete given user if such user exists.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "delete_user"
    args :    {
                "userid" : "<user_id or username>",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "deleted user ID:<userid> <username>",
              "user": null
            }
    error:  null


get_user_group
--------------

Get an existing user group.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_user_group"
    args :    {
                "usergroupid" : "<user group id or name>"
              }

OUTPUT::

    id : <id_given_in_input>
    result : None if group not exist
             {
               "users_group_id" : "<id>",
               "group_name" :     "<groupname>",
               "active":          "<bool>",
               "members" :  [
                              {
                                "user_id" :  "<user_id>",
                                "api_key" :  "<api_key>",
                                "username" : "<username>",
                                "firstname": "<firstname>",
                                "lastname" : "<lastname>",
                                "email" :    "<email>",
                                "emails":    "<list_of_all_additional_emails>",
                                "active" :   "<bool>",
                                "admin" :    "<bool>",
                                "ldap_dn" :  "<ldap_dn>",
                                "last_login": "<last_login>",
                              },
                              …
                            ]
             }
    error : null


get_user_groups
---------------

List all existing user groups.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_user_groups"
    args :    { }

OUTPUT::

    id : <id_given_in_input>
    result : [
               {
               "users_group_id" : "<id>",
               "group_name" :     "<groupname>",
               "active":          "<bool>",
               },
               …
              ]
    error : null


create_user_group
-----------------

Create a new user group.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "create_user_group"
    args:     {
                "group_name": "<groupname>",
                "owner" :     "<onwer_name_or_id = Optional(=apiuser)>",
                "active":     "<bool> = Optional(True)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "created new user group `<groupname>`",
              "users_group": {
                     "users_group_id" : "<id>",
                     "group_name" :     "<groupname>",
                     "active":          "<bool>",
               },
            }
    error:  null


add_user_to_user_group
----------------------

Addsa user to a user group. If the user already is in that group, success will be
`false`.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "add_user_user_group"
    args:     {
                "usersgroupid" : "<user group id or name>",
                "userid" : "<user_id or username>",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "success": True|False # depends on if member is in group
              "msg": "added member `<username>` to a user group `<groupname>` |
                      User is already in that group"
            }
    error:  null


remove_user_from_user_group
---------------------------

Remove a user from a user group. If the user isn't in the given group, success will
be `false`.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "remove_user_from_user_group"
    args:     {
                "usersgroupid" : "<user group id or name>",
                "userid" : "<user_id or username>",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "success":  True|False,  # depends on if member is in group
              "msg": "removed member <username> from user group <groupname> |
                      User wasn't in group"
            }
    error:  null


get_repo
--------

Get an existing repository by its name or repository_id. Members will contain
either users_group or user associated to that repository.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with at least read access to the repository.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_repo"
    args:     {
                "repoid" : "<reponame or repo_id>"
              }

OUTPUT::

    id : <id_given_in_input>
    result: None if repository does not exist or
            {
                "repo_id" :          "<repo_id>",
                "repo_name" :        "<reponame>"
                "repo_type" :        "<repo_type>",
                "clone_uri" :        "<clone_uri>",
                "enable_downloads":  "<bool>",
                "enable_locking":    "<bool>",
                "enable_statistics": "<bool>",
                "private":           "<bool>",
                "created_on" :       "<date_time_created>",
                "description" :      "<description>",
                "landing_rev":       "<landing_rev>",
                "last_changeset":    {
                                       "author":   "<full_author>",
                                       "date":     "<date_time_of_commit>",
                                       "message":  "<commit_message>",
                                       "raw_id":   "<raw_id>",
                                       "revision": "<numeric_revision>",
                                       "short_id": "<short_id>"
                                     }
                "owner":             "<repo_owner>",
                "fork_of":           "<name_of_fork_parent>",
                "members" :     [
                                  {
                                    "type":        "user",
                                    "user_id" :    "<user_id>",
                                    "api_key" :    "<api_key>",
                                    "username" :   "<username>",
                                    "firstname":   "<firstname>",
                                    "lastname" :   "<lastname>",
                                    "email" :      "<email>",
                                    "emails":      "<list_of_all_additional_emails>",
                                    "active" :     "<bool>",
                                    "admin" :      "<bool>",
                                    "ldap_dn" :    "<ldap_dn>",
                                    "last_login":  "<last_login>",
                                    "permission" : "repository.(read|write|admin)"
                                  },
                                  …
                                  {
                                    "type":      "users_group",
                                    "id" :       "<usersgroupid>",
                                    "name" :     "<usersgroupname>",
                                    "active":    "<bool>",
                                    "permission" : "repository.(read|write|admin)"
                                  },
                                  …
                                ]
                 "followers":   [
                                  {
                                    "user_id" :     "<user_id>",
                                    "username" :    "<username>",
                                    "api_key" :     "<api_key>",
                                    "firstname":    "<firstname>",
                                    "lastname" :    "<lastname>",
                                    "email" :       "<email>",
                                    "emails":       "<list_of_all_additional_emails>",
                                    "ip_addresses": "<list_of_ip_addresses_for_user>",
                                    "active" :      "<bool>",
                                    "admin" :       "<bool>",
                                    "ldap_dn" :     "<ldap_dn>",
                                    "last_login":   "<last_login>",
                                  },
                                  …
                 ]
            }
    error:  null


get_repos
---------

List all existing repositories.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with at least read access to the repository.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_repos"
    args:     { }

OUTPUT::

    id : <id_given_in_input>
    result: [
              {
                "repo_id" :          "<repo_id>",
                "repo_name" :        "<reponame>"
                "repo_type" :        "<repo_type>",
                "clone_uri" :        "<clone_uri>",
                "private": :         "<bool>",
                "created_on" :       "<datetimecreated>",
                "description" :      "<description>",
                "landing_rev":       "<landing_rev>",
                "owner":             "<repo_owner>",
                "fork_of":           "<name_of_fork_parent>",
                "enable_downloads":  "<bool>",
                "enable_locking":    "<bool>",
                "enable_statistics": "<bool>",
              },
              …
            ]
    error:  null


get_repo_nodes
--------------

Return a list of files and directories for a given path at the given revision.
It's possible to specify ret_type to show only `files` or `dirs`.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "get_repo_nodes"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "revision"  : "<revision>",
                "root_path" : "<root_path>",
                "ret_type"  : "<ret_type> = Optional('all')"
              }

OUTPUT::

    id : <id_given_in_input>
    result: [
              {
                "name" :        "<name>"
                "type" :        "<type>",
              },
              …
            ]
    error:  null


create_repo
-----------

Create a repository. If repository name contains "/", all needed repository
groups will be created. For example "foo/bar/baz" will create repository groups
"foo", "bar" (with "foo" as parent), and create "baz" repository with
"bar" as group.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with create repository permission.
Regular users cannot specify owner parameter.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "create_repo"
    args:     {
                "repo_name" :        "<reponame>",
                "owner" :            "<onwer_name_or_id = Optional(=apiuser)>",
                "repo_type" :        "<repo_type> = Optional('hg')",
                "description" :      "<description> = Optional('')",
                "private" :          "<bool> = Optional(False)",
                "clone_uri" :        "<clone_uri> = Optional(None)",
                "landing_rev" :      "<landing_rev> = Optional('tip')",
                "enable_downloads":  "<bool> = Optional(False)",
                "enable_locking":    "<bool> = Optional(False)",
                "enable_statistics": "<bool> = Optional(False)",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "Created new repository `<reponame>`",
              "repo": {
                "repo_id" :          "<repo_id>",
                "repo_name" :        "<reponame>"
                "repo_type" :        "<repo_type>",
                "clone_uri" :        "<clone_uri>",
                "private": :         "<bool>",
                "created_on" :       "<datetimecreated>",
                "description" :      "<description>",
                "landing_rev":       "<landing_rev>",
                "owner":             "<username or user_id>",
                "fork_of":           "<name_of_fork_parent>",
                "enable_downloads":  "<bool>",
                "enable_locking":    "<bool>",
                "enable_statistics": "<bool>",
              },
            }
    error:  null


fork_repo
---------

Create a fork of given repo. If using celery, this will
return success message immidiatelly and fork will be created
asynchronously.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with fork permission and at least read access to the repository.
Regular users cannot specify owner parameter.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "fork_repo"
    args:     {
                "repoid" :          "<reponame or repo_id>",
                "fork_name":        "<forkname>",
                "owner":            "<username or user_id = Optional(=apiuser)>",
                "description":      "<description>",
                "copy_permissions": "<bool>",
                "private":          "<bool>",
                "landing_rev":      "<landing_rev>"

              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "Created fork of `<reponame>` as `<forkname>`",
              "success": true
            }
    error:  null


delete_repo
-----------

Delete a repository.
This command can only be executed using the api_key of a user with admin rights,
or that of a regular user with admin access to the repository.
When `forks` param is set it's possible to detach or delete forks of the deleted repository.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "delete_repo"
    args:     {
                "repoid" : "<reponame or repo_id>",
                "forks"  : "`delete` or `detach` = Optional(None)"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg": "Deleted repository `<reponame>`",
              "success": true
            }
    error:  null


grant_user_permission
---------------------

Grant permission for user on given repository, or update existing one if found.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "grant_user_permission"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "userid" : "<username or user_id>"
                "perm" :       "(repository.(none|read|write|admin))",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "Granted perm: `<perm>` for user: `<username>` in repo: `<reponame>`",
              "success": true
            }
    error:  null


revoke_user_permission
----------------------

Revoke permission for user on given repository.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method  : "revoke_user_permission"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "userid" : "<username or user_id>"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "Revoked perm for user: `<username>` in repo: `<reponame>`",
              "success": true
            }
    error:  null


grant_user_group_permission
---------------------------

Grant permission for user group on given repository, or update
existing one if found.
This command can only be executed using the api_key of a user with admin rights.


INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method :  "grant_user_group_permission"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "usersgroupid" : "<user group id or name>"
                "perm" : "(repository.(none|read|write|admin))",
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "Granted perm: `<perm>` for group: `<usersgroupname>` in repo: `<reponame>`",
              "success": true
            }
    error:  null


revoke_user_group_permission
----------------------------

Revoke permission for user group on given repository.
This command can only be executed using the api_key of a user with admin rights.

INPUT::

    id : <id_for_response>
    api_key : "<api_key>"
    method  : "revoke_user_group_permission"
    args:     {
                "repoid" : "<reponame or repo_id>"
                "usersgroupid" : "<user group id or name>"
              }

OUTPUT::

    id : <id_given_in_input>
    result: {
              "msg" : "Revoked perm for group: `<usersgroupname>` in repo: `<reponame>`",
              "success": true
            }
    error:  null
