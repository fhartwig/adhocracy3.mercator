"""Resources for managing badges."""

from pyramid.registry import Registry

from adhocracy_core.interfaces import IPool
from adhocracy_core.interfaces import IServicePool
from adhocracy_core.interfaces import ISimple
from adhocracy_core.resources import add_resource_type_to_registry
from adhocracy_core.resources.simple import simple_meta
from adhocracy_core.resources.service import service_meta
from adhocracy_core.resources.pool import pool_meta
import adhocracy_core.sheets.badge
import adhocracy_core.sheets.description
import adhocracy_core.sheets.metadata
import adhocracy_core.sheets.name
import adhocracy_core.sheets.title


class IBadge(ISimple):

    """A generic badge."""


badge_meta = simple_meta._replace(
    iresource=IBadge,
    extended_sheets=(
        adhocracy_core.sheets.description.IDescription,
        adhocracy_core.sheets.badge.IBadge,
    ),
    permission_create='create_badge',
)


class IBadgeGroup(IPool):

    """A generic badge group pool."""


badge_group_meta = pool_meta._replace(
    iresource=IBadgeGroup,
    extended_sheets=(
        adhocracy_core.sheets.description.IDescription,
    ),
    permission_create='create_badge_group',
    element_types=(IBadge,
                   IBadgeGroup,
                   ),
)


class IBadgesService(IServicePool):

    """The 'badges' ServicePool."""


badges_service_meta = service_meta._replace(
    iresource=IBadgesService,
    content_name='badges',
    element_types=(IBadge,
                   IBadgeGroup,
                   ),
)


def add_badges_service(context: IPool, registry: Registry, options: dict):
    """Add `badge` service to context."""
    registry.content.create(IBadgesService.__identifier__, parent=context,
                            registry=registry)


class IBadgeAssignment(ISimple):

    """A generic badge assignment."""


badge_assignment_meta = simple_meta._replace(
    iresource=IBadgeAssignment,
    basic_sheets=(
        adhocracy_core.sheets.metadata.IMetadata,
        adhocracy_core.sheets.badge.IBadgeAssignment,
        adhocracy_core.sheets.description.IDescription
    ),
    autonaming_prefix='',
    use_autonaming=True,
    permission_create='create_badge_assignment',
)


class IBadgeAssignmentsService(IServicePool):

    """The 'badge_assignments' ServicePool."""


badge_assignments_service_meta = service_meta._replace(
    iresource=IBadgeAssignmentsService,
    content_name='badge_assignments',
    element_types=(IBadgeAssignment,),
)


def add_badge_assignments_service(context: IPool, registry: Registry,
                                  options: dict):
    """Add `badge_assignments` service to context."""
    registry.content.create(IBadgeAssignmentsService.__identifier__,
                            parent=context, registry=registry)


def includeme(config):
    """Add resource type to registry."""
    add_resource_type_to_registry(badge_meta, config)
    add_resource_type_to_registry(badge_group_meta, config)
    add_resource_type_to_registry(badges_service_meta, config)
    add_resource_type_to_registry(badge_assignment_meta, config)
    add_resource_type_to_registry(badge_assignments_service_meta, config)
