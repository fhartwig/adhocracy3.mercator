"""Root type to create initial object hierarchy and set global Permissions."""

# flake8: noqa

from pyramid.registry import Registry
from pyramid.security import Allow
from substanced.interfaces import IRoot
from substanced.objectmap import ObjectMap
from substanced.util import set_acl
from substanced.util import find_service

from adhocracy_core.interfaces import IPool
from adhocracy_core.resources import add_resource_type_to_registry
from adhocracy_core.resources.organisation import IOrganisation
from adhocracy_core.resources.organisation import organisation_meta
from adhocracy_core.resources.principal import IPrincipalsService
from adhocracy_core.resources.principal import IUser
from adhocracy_core.resources.principal import IGroup
from adhocracy_core.resources.process import IProcess
from adhocracy_core.authorization import acm_to_acl
from adhocracy_core.authorization import set_god_all_permissions
from adhocracy_core.schema import ACM
from adhocracy_core.resources.geo import add_locations_service
from adhocracy_core.catalog import ICatalogsService
import adhocracy_core.sheets.principal
import adhocracy_core.sheets.name


# Access Control Matrix. Permissions are mapped to a role.
# Every role should only have the permission for the specific actions it is
# meant to enable.
root_acm = ACM().deserialize(
    {'principals':                                   ['anonymous', 'authenticated', 'participant', 'moderator',  'creator', 'initiator', 'admin'],
     'permissions': [  # general
                     ['view',                          Allow,      Allow,          Allow,         Allow,        Allow,     Allow,       Allow],
                     ['create',                        None,       None,           Allow,         Allow,        None,      Allow,       Allow],
                     ['edit',                          None,       None,           None,          None,         Allow,     None,        Allow],
                     ['edit_some',                     None,       None,           Allow,         Allow,        Allow,     Allow,       Allow],
                     ['delete',                        None,       None,           None,          Allow,        Allow,     None,        Allow],
                     ['hide',                          None,       None,           None,          Allow,        None,      Allow,       Allow],
                     ['do_transition',                 None,       None,           None,          None,         None,      Allow,       Allow],
                     ['message_to_user',               None,       None,           Allow,         Allow,        None,      Allow,       Allow],
                     # structure resources
                     ['create_pool',                   None,       None,           None,          None,         None,      None,        Allow],
                     ['create_organisation',           None,       None,           None,          None,         None,      None,        Allow],
                     ['create_process',                None,       None,           None,          None,         None,      Allow,       Allow],
                     # simple content resources
                     ['create_asset',                  None,       None,           Allow,         None,         None,      None,        Allow],
                     ['create_external',               None,       None,           Allow,         None,         None,      None,        Allow],
                     ['create_badge',                  None,       None,           None,          Allow,        None,      Allow,       Allow],
                     ['create_badge_assignment',       None,       None,           None,          Allow,        None,      Allow,       Allow],
                     ['create_badge_group',            None,       None,           None,          Allow,        None,      Allow,       Allow],
                     ['assign_badge',                  None,       None,           None,          Allow,        None,      Allow,       Allow],
                     # versioned content resources
                     ['create_proposal',               None,       None,           None,          None,         None,      None,        Allow],
                     ['edit_proposal',                 None,       None,           None,          None,         None,      None,        Allow],
                     ['create_document',               None,       None,           None,          None,         None,      None,        Allow],
                     ['edit_document',                 None,       None,           None,          None,         None,      None,        Allow],
                     ['create_comment',                None,       None,           None,          None,         None,      None,        Allow],
                     ['edit_comment',                  None,       None,           None,          None,         None,      None,        None],
                     ['create_rate',                   None,       None,           None,          None,         None,      None,        None],
                     ['edit_rate',                     None,       None,           None,          None,         None,      None,        None],
                     # user, groups, permissions
                     ['create_user',                   Allow,      None,          None,          None,         None,      None,        Allow],
                     ['edit_userextended',             None,       None,          None,          None,         Allow,     None,        Allow],
                     ['view_userextended',             None,       None,          None,          None,         Allow,     None,        Allow],
                     ['create_edit_sheet_permissions', None,       None,          None,          None,         None,      None,        Allow],
                     ['create_group',                  None,       None,          None,          None,         None,      None,        Allow],
                     ]})


class IRootPool(IOrganisation, IRoot):

    """The application root object."""


def create_initial_content_for_app_root(context: IPool, registry: Registry,
                                        options: dict):
    """Add the Catalog, principals services to the context."""
    _add_objectmap_to_app_root(context)
    _add_graph(context, registry)
    _add_catalog_service(context, registry)
    _add_principals_service(context, registry)
    _add_acl_to_app_root(context, registry)
    _add_default_group(context, registry)
    _add_initial_user_and_group(context, registry)
    add_locations_service(context, registry, {})


def _add_objectmap_to_app_root(root):
    root.__objectmap__ = ObjectMap(root)
    root.__objectmap__.add(root, ('',))


def _add_graph(context, registry):
    graph = registry.content.create('Graph', context)
    context.__graph__ = graph


def _add_catalog_service(context, registry):
    registry.content.create(ICatalogsService.__identifier__, parent=context,
                            registry=registry)


def _add_principals_service(context, registry):
    registry.content.create(IPrincipalsService.__identifier__,
                            parent=context,
                            registry=registry)


def _add_acl_to_app_root(context, registry):
    acl = acm_to_acl(root_acm, registry)
    set_acl(context, acl, registry=registry)
    set_god_all_permissions(context, registry)


def add_example_process(context: IPool, registry: Registry, options: dict):
    """Add example organisation and process."""
    appstructs = {adhocracy_core.sheets.name.IName.__identifier__:
                  {'name': 'adhocracy'}}
    registry.content.create(IProcess.__identifier__,
                            parent=context,
                            appstructs=appstructs,
                            registry=registry)


def _add_default_group(context, registry):
    if not registry.settings.get('adhocracy.add_default_group',
                                 True):  # pragma: no cover
        return
    # the 'app' fixture in adhocracy_core.testing does not work with
    # setting a default group. So we allow to disable here.
    group_name = 'authenticated'
    group_roles = ['participant']
    groups = find_service(context, 'principals', 'groups')
    appstructs = {adhocracy_core.sheets.principal.IGroup.__identifier__:
                  {'roles': group_roles},
                  adhocracy_core.sheets.name.IName.__identifier__:
                  {'name': group_name},
                  }
    registry.content.create(IGroup.__identifier__, groups,
                            appstructs=appstructs,
                            registry=registry)


def _add_initial_user_and_group(context, registry):

    user_name = registry.settings.get('adhocracy.initial_login', 'god')
    user_password = registry.settings.get('adhocracy.initial_password',
                                          'password')
    user_email = registry.settings.get('adhocracy.initial_email',
                                       'sysadmin@test.de')
    group_name = registry.settings.get('adhocracy.initial_group_name', 'gods')
    group_roles = ['god']
    groups = find_service(context, 'principals', 'groups')
    appstructs = {adhocracy_core.sheets.principal.IGroup.__identifier__:
                  {'roles': group_roles},
                  adhocracy_core.sheets.name.IName.__identifier__:
                  {'name': group_name},
                  }
    group = registry.content.create(IGroup.__identifier__, groups,
                                    appstructs=appstructs,
                                    registry=registry)
    users = find_service(context, 'principals', 'users')
    password_sheet = adhocracy_core.sheets.principal.IPasswordAuthentication
    appstruct = {adhocracy_core.sheets.principal.IUserBasic.__identifier__:
                 {'name': user_name},
                 adhocracy_core.sheets.principal.IUserExtended.__identifier__:
                 {'email': user_email},
                 adhocracy_core.sheets.principal.IPermissions.__identifier__:
                 {'groups': [group]},
                 password_sheet.__identifier__:
                 {'password': user_password},
                 }
    user = registry.content.create(IUser.__identifier__,
                                   users,
                                   appstruct,
                                   run_after_creation=False,
                                   send_event=False,
                                   registry=registry)
    user.activate()


root_meta = organisation_meta._replace(
    iresource=IRootPool,
    after_creation=(create_initial_content_for_app_root,
                    add_example_process),
    is_implicit_addable=False,
)


def includeme(config):
    """Add resource types to registry."""
    add_resource_type_to_registry(root_meta, config)
