Permission system:
------------------

Principals (global/local mapping to Roles):
...........................................

- groups
   - Authenticated (all authenticated users, pyramid internal name)
   - Everyone (all authenticated and anonymous users, pyramid internal name)
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

List with ACEs (Access Control Entry): [<Action>, <Principal>, <Permission>]

Action: Allow | Deny
Principal: UserId | group:GroupID | role:RoleID
Permission: view, edit, add, ...

Every resource in the object hierarchy has a local ACL.

To check permission all ACEs are searched starting with the ACL of the
requested resource, and then searching the parent's ACLs recursively.
The Action of the first ACE with matching permission is returned.


Customizing
...........

1. map users to group
2. map roles to group/(user)
3. use workflow system to locally change:
        - mapping role to principals
        - mapping permission to role
4. locally change mapping role to principals
5. map permissions to roles:
        - use only configuration for this
        - default mapping should just work for most use cases)
