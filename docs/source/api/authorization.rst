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


FIXME: Open questions
---------------------

what is the difference between role and group, on a conceptual level?
(why do we need both?)  i'm assuming that groups are a pyramid
concept, and roles are something we want to build on top?

is there multiple inheritance?  if yes, which parent's ACL is searched
first?

can groups be members of groups?

draw a graph with all mappings, and mark them as
 - 1:n vs. n:1 vs. n:m
 - dynamic (workflows) vs. static (config files)

identify minimal subset that
 - satisfies requirements for merkator.
 - can be implemented efficiently, and the rest can be added efficiently later.
in particular: do we need workflows at all?  or can we assume ACLs and roles don't change at run time?


API
---

an operation is a tuple (user, resource, permission).  example::

    ( joe,
      /adhocracy/proposals/against_curtains/version_000043,
      edit )

fe wants to
 - ask if an operation is allowed (so it can render an object as non-editable, for instance).
 - try an operation, and get a "denied" error that it can handle gracefully.

mappings from users, groups, roles to each other must be contained in
resources.  (and only visible to authorized users!)  (it is a security
requirement that these resources are in sync with the backend!)
