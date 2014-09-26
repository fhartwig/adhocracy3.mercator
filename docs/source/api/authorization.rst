Permission system:
------------------

Principals (global/local mapping to Roles):
...........................................

- groups
   - Authenticated (all authenticated user, pyramid internal name)
   - Everyone (all authenticated and anonymous user, pyramid internal name)
   - managers (custom group)
   - admins (custom group)
   - gods (custom group, no permssion checks)
   ...

- users
   - god
   ...

Roles (global mapping to permissions):
......................................

  local (inheritance):

    - reader: can read:
        read the proposal

    - contributor: can add content:
        add comment to the proposal

    - editor: can edit content:
        edit proposal

    - manager: edit meta stuff: permissions, workflow state, ...:
        accept/deny proposal

    - admin: create an configure the participation process
             manage principals

  local (no inheritance):

    - creator: principal who created the local context:
        ....

ACL (Access Control List):
...........................

List with aces (Access Control Entry): [<Action>, <Principal>, <Permission>]

Action: Allow | Deny
Principal: UserId | group:GroupID | role:RoleID
Permission: view, edit, add, ...

Every resource in the object hierarchy has a local ACL.
A resource aggregates all acls of his parents.
To check permission all aces are searched starting with the local ones.
The Action of the first ace with matching permission is returned.


Customizing:
............

1. map users to group
2. map roles to group/(user)
3. use workflow system to locally change:
        - mapping role to principals
        - mapping permission to role
4. locally change mapping role to principals
5. map permissions to roles:
        - use only configuration for this
        - default mapping should just work for most use cases)
