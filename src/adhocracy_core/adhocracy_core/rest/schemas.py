"""Data structures / validation specific to rest api requests."""
from datetime import datetime

import colander
from colander import SchemaNode
from hypatia.interfaces import IIndexSort
from multipledispatch import dispatch
from pyramid.registry import Registry
from pyramid.request import Request
from pyramid.util import DottedNameResolver
from substanced.catalog.indexes import SDIndex
from substanced.util import find_catalog
from substanced.util import find_service
from hypatia.field import FieldIndex
from hypatia.keyword import KeywordIndex
from zope import interface
from adhocracy_core.interfaces import FieldComparator
from adhocracy_core.interfaces import FieldSequenceComparator
from adhocracy_core.interfaces import IResource
from adhocracy_core.interfaces import IUserLocator
from adhocracy_core.interfaces import KeywordComparator
from adhocracy_core.interfaces import KeywordSequenceComparator
from adhocracy_core.interfaces import Reference as ReferenceTuple
from adhocracy_core.interfaces import SearchQuery
from adhocracy_core.interfaces import SheetToSheet
from adhocracy_core.resources.principal import IPasswordReset
from adhocracy_core.resources.base import Base
from adhocracy_core.schema import AbsolutePath
from adhocracy_core.schema import AdhocracySchemaNode
from adhocracy_core.schema import Boolean
from adhocracy_core.schema import Booleans
from adhocracy_core.schema import ContentType
from adhocracy_core.schema import DateTime
from adhocracy_core.schema import DateTimes
from adhocracy_core.schema import Email
from adhocracy_core.schema import Integer
from adhocracy_core.schema import Integers
from adhocracy_core.schema import Interface
from adhocracy_core.schema import Interfaces
from adhocracy_core.schema import Password
from adhocracy_core.schema import Reference
from adhocracy_core.schema import References
from adhocracy_core.schema import Resource
from adhocracy_core.schema import ResourcePathAndContentSchema
from adhocracy_core.schema import ResourcePathSchema
from adhocracy_core.schema import Resources
from adhocracy_core.schema import SingleLine
from adhocracy_core.schema import SingleLines
from adhocracy_core.schema import Text
from adhocracy_core.schema import URL
from adhocracy_core.sheets.metadata import IMetadata
from adhocracy_core.sheets.principal import IPasswordAuthentication
from adhocracy_core.sheets.principal import IUserExtended
from adhocracy_core.catalog import ICatalogsService
from adhocracy_core.catalog.index import ReferenceIndex
from adhocracy_core.utils import get_sheet
from adhocracy_core.utils import now
from adhocracy_core.utils import raise_colander_style_error
from adhocracy_core.utils import unflatten_multipart_request

resolver = DottedNameResolver()


INDEX_EXAMPLE_VALUES = {
    'default': 'str',
    'reference': Base(),
    'creator': Base(),
    'item_creation_date': datetime.now(),
    'rate': 1,
    'rates': 1,
    'interfaces': interface.Interface,
}

class UpdatedResourcesSchema(colander.Schema):

    """List the resources affected by a transaction."""

    created = Resources()
    modified = Resources()
    removed = Resources()
    changed_descendants = Resources()


class ResourceResponseSchema(ResourcePathSchema):

    """Data structure for responses of Resource requests."""

    updated_resources = UpdatedResourcesSchema()


class ItemResponseSchema(ResourceResponseSchema):

    """Data structure for responses of IItem requests."""

    first_version_path = Resource()


class GETResourceResponseSchema(ResourcePathAndContentSchema):

    """Data structure for Resource GET requests."""


class GETItemResponseSchema(ResourcePathAndContentSchema):

    """Data structure for responses of IItem requests."""

    first_version_path = Resource()


def add_put_data_subschemas(node: colander.Schema, kw: dict):
    """Add the resource sheet colander schemas that are 'editable'."""
    context = kw.get('context', None)
    request = kw.get('request', None)
    sheets = request.registry.content.get_sheets_edit(context, request)
    if request.content_type == 'multipart/form-data':
        body = unflatten_multipart_request(request)
    else:
        body = request.json_body
    data = body.get('data', {})
    for sheet in sheets:
        name = sheet.meta.isheet.__identifier__
        if name not in data:
            continue
        subschema = sheet.meta.schema_class(name=name)
        node.add(subschema.bind(**kw))


class BlockExplanationResponseSchema(colander.Schema):

    """Data structure explaining a 410 Gone response."""

    reason = SingleLine()
    modified_by = Reference()
    modification_date = DateTime(default=colander.null)


class PUTResourceRequestSchema(colander.Schema):

    """Data structure for Resource PUT requests.

    The subschemas for the Resource Sheets
    """

    data = SchemaNode(colander.Mapping(unknown='raise'),
                      after_bind=add_put_data_subschemas,
                      default={})


def add_post_data_subschemas(node: SchemaNode, kw: dict):
    """Add the resource sheet colander schemas that are 'creatable'."""
    context = kw['context']
    request = kw['request']
    content_type = _get_resource_type_based_on_request_type(request)
    try:
        iresource = ContentType().deserialize(content_type)
    except colander.Invalid:
        return  # the content type is validated later, so we just ignore errors
    registry = request.registry.content
    creates = registry.get_sheets_create(context, request, iresource)
    for sheet in creates:
        name = sheet.meta.isheet.__identifier__
        is_mandatory = sheet.meta.create_mandatory
        missing = colander.required if is_mandatory else colander.drop
        schema = sheet.meta.schema_class(name=name, missing=missing)
        node.add(schema.bind(**kw))


def _get_resource_type_based_on_request_type(request: Request) -> str:
    if request.content_type == 'application/json':
        return request.json_body.get('content_type')
    elif request.content_type == 'multipart/form-data':
        return request.POST['content_type']
    else:
        raise RuntimeError('Unsupported request content_type: {}'.format(
            request.content_type))


@colander.deferred
def deferred_validate_post_content_type(node, kw):
    """Validate the addable content type for post requests."""
    context = kw['context']
    request = kw['request']
    addables = request.registry.content.get_resources_meta_addable(context,
                                                                   request)
    addable_iresources = [r.iresource for r in addables]
    return colander.OneOf(addable_iresources)


class POSTResourceRequestSchema(PUTResourceRequestSchema):

    """Data structure for Resource POST requests."""

    content_type = ContentType(validator=deferred_validate_post_content_type,
                               missing=colander.required)

    data = SchemaNode(colander.Mapping(unknown='raise'),
                      after_bind=add_post_data_subschemas,
                      default={})


class AbsolutePaths(colander.SequenceSchema):

    """List of resource paths."""

    path = AbsolutePath()


class POSTItemRequestSchema(POSTResourceRequestSchema):

    """Data structure for Item and ItemVersion POST requests."""

    root_versions = Resources(missing=[])


class POSTResourceRequestSchemaList(colander.List):

    """Overview of POST request/response data structure."""

    request_body = POSTResourceRequestSchema()


class GETLocationMapping(colander.Schema):

    """Overview of GET request/response data structure."""

    request_querystring = SchemaNode(colander.Mapping(), default={})
    request_body = SchemaNode(colander.Mapping(), default={})
    response_body = GETResourceResponseSchema()


class PUTLocationMapping(colander.Schema):

    """Overview of PUT request/response data structure."""

    request_body = PUTResourceRequestSchema()
    response_body = ResourceResponseSchema()


class POSTLocationMapping(colander.Schema):

    """Overview of POST request/response data structure."""

    request_body = SchemaNode(POSTResourceRequestSchemaList(), default=[])
    response_body = ResourceResponseSchema()


class POSTLoginUsernameRequestSchema(colander.Schema):

    """Schema for login requests via username and password."""

    name = SchemaNode(colander.String(), missing=colander.required)
    password = Password(missing=colander.required)


class POSTActivateAccountViewRequestSchema(colander.Schema):

    """Schema for account activation."""

    path = SchemaNode(colander.String(),
                      missing=colander.required,
                      validator=colander.Regex('^/activate/'))


class POSTLoginEmailRequestSchema(colander.Schema):

    """Schema for login requests via email and password."""

    email = Email(missing=colander.required)
    password = Password(missing=colander.required)


class POSTReportAbuseViewRequestSchema(colander.Schema):

    """Schema for abuse reports."""

    url = URL(missing=colander.required)
    remark = Text(missing='')


class MessageUserReference(SheetToSheet):

    """Dummy reference to validate user resources."""

    target_isheet = IUserExtended


class POSTMessageUserViewRequestSchema(colander.Schema):

    """Schema for messages to a user."""

    recipient = Reference(missing=colander.required,
                          reftype=MessageUserReference)
    title = SingleLine(missing=colander.required)
    text = Text(missing=colander.required)


class BatchHTTPMethod(SchemaNode):

    """An HTTP method in a batch request."""

    schema_type = colander.String
    validator = colander.OneOf(['GET', 'POST', 'PUT', 'OPTIONS'])
    missing = colander.required


class BatchRequestPath(AdhocracySchemaNode):

    """A path in a batch request.

    Either a resource url or a preliminary resource path (a relative path
    preceded by '@') or an absolute path.

    Example values: '@item/v1', 'http://a.org/adhocracy/item/v1', '/item/v1/'
    """

    schema_type = colander.String
    default = ''
    missing = colander.required
    absolutpath = AbsolutePath.relative_regex
    preliminarypath = '[a-zA-Z0-9\_\-\.\/]+'
    validator = colander.All(colander.Regex('^(' + colander.URL_REGEX + '|'
                                            + absolutpath + '|@'
                                            + preliminarypath + ')$'),
                             colander.Length(min=1, max=8192))


class POSTBatchRequestItem(colander.Schema):

    """A single item in a batch request, encoding a single request."""

    method = BatchHTTPMethod()
    path = BatchRequestPath()
    body = SchemaNode(colander.Mapping(unknown='preserve'),
                      missing={})
    result_path = BatchRequestPath(missing='')
    result_first_version_path = BatchRequestPath(missing='')


class POSTBatchRequestSchema(colander.SequenceSchema):

    """Schema for batch requests (list of POSTBatchRequestItem's)."""

    items = POSTBatchRequestItem()


class PoolElementsForm(SchemaNode):

    """The form of the elements attribute returned by the pool sheet."""

    schema_type = colander.String
    validator = colander.OneOf(['paths', 'content', 'omit'])
    missing = 'paths'


class PoolQueryDepth(SchemaNode):

    """The nesting depth of descendants in a pool response.

    Either a positive number or the string 'all' to return descendants of
    arbitrary depth.
    """

    schema_type = colander.Integer
    missing = 1
    validator=colander.Range(min=1)


@colander.deferred
def deferred_validate_aggregateby(node: SchemaNode, kw):
    """Validate if `value` is an catalog index name`."""
    # TODO In the future we may have indexes where aggregateby doesn't make
    # sense, e.g. username or email. We should have a blacklist to prohibit
    # calling aggregateby on such indexes.
    context = kw['context']
    indexes = _get_indexes(context)
    index_names = [x.__name__ for x in indexes
                   if hasattr(x, 'unique_values')]
    return colander.OneOf(index_names)


@colander.deferred
def deferred_validate_sort(node: SchemaNode, kw: dict):
    """Validate if value is an index name that support sorting."""
    context = kw['context']
    indexes = _get_indexes(context)
    # Check that the index has the IIndexSort interfaces or at least a sort
    # method
    valid_indexes = [x.__name__ for x in indexes
                     if IIndexSort.providedBy(x)
                     or 'sort' in x.__dir__()]
    return colander.OneOf(valid_indexes)


def _get_indexes(context) -> list:
    indexes = []
    system = find_catalog(context, 'system') or {}
    indexes.extend(system.values())
    adhocracy = find_catalog(context, 'adhocracy') or {}
    indexes.extend(adhocracy.values())
    return indexes


class GETPoolRequestSchema(colander.Schema):

    """GET parameters accepted for pool queries."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Raise if unknown to tell client the query parameters are wrong.
        self.typ.unknown = 'raise'

    # TODO For now we don't have a way to specify GET parameters that can
    # be repeated, e.g. 'sheet=Blah&sheet=Blub'. The querystring is converted
    # by Cornice into a MultiDict (http://docs.pylonsproject.org/projects
    # /pyramid/en/master/api/interfaces.html#pyramid.interfaces.IMultiDict),
    # which by default will only return the LAST value if a key is specified
    # several times. One possible workaround is to allow specifying multiple
    # values as a comma-separated list instead of repeated key=value pairs,
    # e.g. 'sheet=Blah,Blub'. This would require a custom Multiple SchemaNode
    # that wraps a SchemaType, e.g.
    # sheet = Multiple(Interface(), missing=None, sep=',')
    # Elements in this schema were multiple values should be allowed:
    # sheet, aggregateby, tag.

    depth = PoolQueryDepth()
    elements = PoolElementsForm(missing=colander.drop)
    count = SchemaNode(colander.Boolean(), missing=colander.drop)
    sort = SchemaNode(colander.String(),
                      missing=colander.drop,
                      validator=deferred_validate_sort)
    reverse = SchemaNode(colander.Boolean(), missing=colander.drop)
    # TODO: validate limit, offset to be multiple of 10, 20, 50, 100, 200, 500
    limit = SchemaNode(colander.Int(), missing=colander.drop)
    offset = SchemaNode(colander.Int(), missing=colander.drop)
    aggregateby = SchemaNode(colander.String(),
                             missing=colander.drop,
                             validator=deferred_validate_aggregateby)

    def deserialize(self, cstruct=colander.null):  # noqa
        """ Deserialize the :term:`cstruct` into an :term:`appstruct`.

        Adapt key/values to :class:`adhocracy_core.interfaces.SearchQuery`. for
        BBB.
        TODO: CHANGE API according to internal SearchQuery api.
             refactor to follow coding guideline better.
        """
        depth_cstruct = cstruct.get('depth', None)
        if depth_cstruct == 'all':
            cstruct['depth'] = 100
        appstruct = super().deserialize(cstruct)
        search_query = {}
        if appstruct:
            search_query['root'] = self.bindings['context']
        if 'depth' in appstruct:
            depth = appstruct['depth']
            if depth == 100:
                depth = None
            search_query['depth'] = depth
        if 'elements' in appstruct:
            elements = appstruct.get('elements')
            search_query['serialization_form'] = elements
            if elements == 'omit':
                search_query['resolve'] = False
        interfaces = ()
        if 'sheet' in appstruct:
            interfaces = appstruct['sheet']
        if interfaces:
            search_query['interfaces'] = interfaces
        if 'aggregateby' in appstruct:
            search_query['frequency_of'] = appstruct['aggregateby']
            search_query['show_frequency'] = True
        if 'sort' in appstruct:
            search_query['sort_by'] = appstruct['sort']
        if 'limit' in appstruct:
            search_query['limit'] = appstruct['limit']
        if 'offset' in appstruct:
            search_query['offset'] = appstruct['offset']
        if 'reverse' in appstruct:
            search_query['reverse'] = appstruct['reverse']
        if 'count' in appstruct:
            search_query['show_count'] = appstruct['count']
        fields = tuple([x.name for x in GETPoolRequestSchema().children])
        fields += ('sheet',)
        for filter, query in appstruct.items():
            if filter in fields + SearchQuery._fields:
                continue
            if ':' in filter:
                if 'references' not in search_query:  # pragma: no branch
                    search_query['references'] = []
                isheet_name, isheet_field = filter.split(':')
                isheet = resolver.resolve(isheet_name)
                target = appstruct[filter]
                reference = ReferenceTuple(None, isheet, isheet_field, target)
                search_query['references'].append(reference)
            else:
                if 'indexes' not in search_query:
                    search_query['indexes'] = {}
                if filter == 'content_type':
                    search_query['indexes']['interfaces'] = appstruct['content_type']
                    continue
                search_query['indexes'][filter] = query
        return search_query


def add_arbitrary_filter_nodes(cstruct: dict,
                                       schema: GETPoolRequestSchema,
                                       context: IResource,
                                       registry) -> GETPoolRequestSchema:
    """Add schema nodes for arbitrary/references filters to `schema`."""
    extra_filters = [(k, v) for k, v in cstruct.items() if k not in schema]
    if extra_filters:
        schema = schema.clone()
    catalogs = find_service(context, 'catalogs')
    for filter_name, query in extra_filters:
        if _is_reference_filter(filter_name, registry):
            index_name = 'reference'
        elif filter_name == 'sheet':
            index_name = 'interfaces'
        elif filter_name == 'content_type':
            index_name = 'interfaces'
        elif _is_arbitrary_filter(filter_name, catalogs):
            index_name = filter_name
        else:
            continue  # pragma: no cover
        index = catalogs.get_index(index_name)
        example_value = _get_index_example_value(index)
        node = create_arbitrary_filter_node(index, example_value, query)
        _add_node(schema, node, filter_name)
    return schema


def _is_reference_filter(name: str, registry: Registry) -> bool:
    """
    Check whether a name refers to a reference node in a sheet.

    Raises an error if `name` contains a colon but is not a reference node.
    """
    if ':' not in name:
        return False
    resolve = registry.content.resolve_isheet_field_from_dotted_string
    try:
        isheet, field, node = resolve(name)
    except ValueError:
        raise_colander_style_error(None, name, 'No such sheet or field')
    if isinstance(node, (Reference, References)):
        return True
    else:
        raise_colander_style_error(None, name, 'Not a reference node')


def _is_arbitrary_filter(name: str, catalogs: ICatalogsService) -> bool:
    """
    Return True if `name' refers to an public arbitrary catalog index.
    """

    if name.startswith('private_'):
        return False
    else:
        index = catalogs.get_index(name)
        return index is not None


def _get_index_example_value(index: SDIndex) -> object:
    """Return example entry from `index` or None if `index` is None."""
    if index is None:
        return None
    if index.__name__ in INDEX_EXAMPLE_VALUES:
        return INDEX_EXAMPLE_VALUES[index.__name__]
    else:
        return INDEX_EXAMPLE_VALUES['default']


def _add_node(schema: SchemaNode, node: SchemaNode, name: str):
    node = node.bind(**schema.bindings)
    node.name = name
    schema.add(node)


@dispatch((FieldIndex, KeywordIndex), str, str)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    return SingleLine()


@dispatch((FieldIndex, KeywordIndex), int, (int, str))  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    return Integer()


@dispatch((FieldIndex, KeywordIndex), bool, (bool, str))  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    return Boolean()


@dispatch(FieldIndex, bool, list)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    if query[0] in FieldSequenceComparator.__members__:
        return FieldComparableBooleans()
    else:
        return FieldComparableBoolean()


@dispatch((FieldIndex, KeywordIndex), datetime, str)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    return DateTime()


@dispatch(FieldIndex, datetime, list)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    if query[0] in FieldSequenceComparator.__members__:
        return FieldComparableDateTimes()
    else:
        return FieldComparableDateTime()


@dispatch(KeywordIndex, interface.interface.InterfaceClass, str)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    return Interface()


@dispatch(ReferenceIndex, object, str)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    return Resource()


@dispatch(KeywordIndex, int, list)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    if query[0] in KeywordSequenceComparator.__members__:
        return KeywordComparableIntegers()
    else:
        return KeywordComparableInteger()


@dispatch(FieldIndex, int, list)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    if query[0] in FieldSequenceComparator.__members__:
        return FieldComparableIntegers()
    else:
        return FieldComparableInteger()


@dispatch(KeywordIndex, str, list)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    if query[0] in KeywordSequenceComparator.__members__:
        return KeywordComparableSingleLines()
    else:
        return KeywordComparableSingleLine()


@dispatch(FieldIndex, str, list)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    if query[0] in FieldSequenceComparator.__members__:
        return FieldComparableSingleLines()
    else:
        return FieldComparableSingleLine()


@dispatch(KeywordIndex, interface.interface.InterfaceClass, list)  # flake8: noqa
def create_arbitrary_filter_node(index, example_value, query):
    if query[0] in KeywordSequenceComparator.__members__:
        return KeywordComparableInterfaces()
    else:
        return KeywordComparableInterface()


class KeywordComparableSchema(SingleLine):

    """SingleLine of KeywordComparable value."""

    validator = colander.OneOf(
        [x for x in KeywordComparator.__members__])


class FieldComparableSchema(SingleLine):

    """SingleLine of FieldComparable value."""

    validator = colander.OneOf(
        [x for x in FieldComparator.__members__])


class KeywordSequenceComparableSchema(SingleLine):

    """SingleLine of KeywordSequenceComparable value."""

    validator = colander.OneOf(
        [x for x in KeywordSequenceComparator.__members__])


class FieldSequenceComparableSchema(SingleLine):

    """SingleLine of FieldSequenceComparable value."""

    validator = colander.OneOf(
        [x for x in FieldSequenceComparator.__members__])


class KeywordComparableSequenceBase(colander.TupleSchema):

    """Tuple with value KeywordSequenceComparable."""

    comparable = KeywordSequenceComparableSchema()


class KeywordComparableIntegers(KeywordComparableSequenceBase):

    """Tuple with values KeywordSequenceComparable and Integers."""

    value = Integers()


class KeywordComparableInterfaces(KeywordComparableSequenceBase):

    """Tuple with values KeywordSequenceComparable and Interfaces."""

    value = Interfaces()


class KeywordComparableSingleLines(KeywordComparableSequenceBase):

    """Tuple with values KeywordSequenceComparable and SingleLines."""

    value = SingleLines()


class KeywordComparableDateTimes(KeywordComparableSequenceBase):

    """Tuple with values KeywordSequenceComparable and DateTimes."""

    value = DateTimes()


class KeywordComparableBooleans(KeywordComparableSequenceBase):

    """Tuple with values KeywordSequenceComparable and Booleans."""

    value = Booleans()


class KeywordComparableBase(colander.TupleSchema):

    """Tuple with value KeywordComparable."""

    comparable = KeywordComparableSchema()


class KeywordComparableInteger(KeywordComparableBase):

    """Tuple with values KeywordComparable and Integer."""

    value = Integer()


class KeywordComparableInterface(KeywordComparableBase):

    """Tuple with values KeywordComparable and Interface."""

    value = Interface()


class KeywordComparableSingleLine(KeywordComparableBase):

    """Tuple with values KeywordComparable and SingleLine."""

    value = SingleLine()


class KeywordComparableBoolean(KeywordComparableBase):

    """Tuple with values KeywordComparable and Boolean."""

    value = Boolean()


class KeywordComparableDateTime(KeywordComparableBase):

    """Tuple with values KeywordComparable and DateTime."""

    value = DateTime()


class FieldComparableSchema(SingleLine):

    """SingleLine of FieldComparable value."""

    validator = colander.OneOf(
        [x for x in FieldComparator.__members__])


class FieldComparableSchema(SingleLine):

    """SingleLine of FieldComparable value."""

    validator = colander.OneOf(
        [x for x in FieldComparator.__members__])


class FieldSequenceComparableSchema(SingleLine):

    """SingleLine of FieldSequenceComparable value."""

    validator = colander.OneOf(
        [x for x in FieldSequenceComparator.__members__])


class FieldSequenceComparableSchema(SingleLine):

    """SingleLine of FieldSequenceComparable value."""

    validator = colander.OneOf(
        [x for x in FieldSequenceComparator.__members__])


class FieldComparableSequenceBase(colander.TupleSchema):

    """Tuple with value FieldSequenceComparable."""

    comparable = FieldSequenceComparableSchema()


class FieldComparableIntegers(FieldComparableSequenceBase):

    """Tuple with values FieldSequenceComparable and Integers."""

    value = Integers()


class FieldComparableInterfaces(FieldComparableSequenceBase):

    """Tuple with values FieldSequenceComparable and Interfaces."""

    value = Interfaces()


class FieldComparableSingleLines(FieldComparableSequenceBase):

    """Tuple with values FieldSequenceComparable and SingleLines."""

    value = SingleLines()


class FieldComparableDateTimes(FieldComparableSequenceBase):

    """Tuple with values FieldSequenceComparable and DateTimes."""

    value = DateTimes()


class FieldComparableBooleans(FieldComparableSequenceBase):

    """Tuple with values FieldSequenceComparable and Booleans."""

    value = Booleans()


class FieldComparableBase(colander.TupleSchema):

    """Tuple with value FieldComparable."""

    comparable = FieldComparableSchema()


class FieldComparableInteger(FieldComparableBase):

    """Tuple with values FieldComparable and Integer."""

    value = Integer()


class FieldComparableInterface(FieldComparableBase):

    """Tuple with values FieldComparable and Interface."""

    value = Interface()


class FieldComparableSingleLine(FieldComparableBase):

    """Tuple with values FieldComparable and SingleLine."""

    value = SingleLine()


class FieldComparableBoolean(FieldComparableBase):

    """Tuple with values FieldComparable and Boolean."""

    value = Boolean()


class FieldComparableDateTime(FieldComparableBase):

    """Tuple with values FieldComparable and DateTime."""

    value = DateTime()


options_resource_response_data_dict =\
    {'GET': {'request_body': {},
             'request_querystring': {},
             'response_body': {'content_type': '',
                               'data': {},
                               'path': ''}},
     'HEAD': {},
     'OPTIONS': {},
     'POST': {'request_body': [],
              'response_body': {'content_type': '',
                                'path': ''}},
     'PUT': {'request_body': {'content_type': '',
                              'data': {}},
             'response_body': {'content_type': '',
                               'path': ''}}}


@colander.deferred
def deferred_validate_password_reset_email(node: SchemaNode, kw: dict):
    """Validate the email address of a password reset request.

    If valid, the user object is added as 'user' to
    `request.validated`.

    :raise colander.Invalid: if no user with this email exists.
    """
    context = kw['context']
    request = kw['request']

    def validate_email(node, value):
        locator = request.registry.getMultiAdapter((context, request),
                                                   IUserLocator)
        user = locator.get_user_by_email(value)
        if user is None:
            msg = 'No user exists with this email: {0}'.format(value)
            raise colander.Invalid(node, msg)
        if not IPasswordAuthentication.providedBy(user):
            msg = 'This user has no password to reset: {0}'.format(value)
            raise colander.Invalid(node, msg)
        if not user.active:
            user.activate()
        request.validated['user'] = user
    return validate_email


class POSTCreatePasswordResetRequestSchema(colander.Schema):

    """Schema to create a user password reset."""

    email = Email(missing=colander.required,
                  validator=deferred_validate_password_reset_email)


@colander.deferred
def validate_password_reset_path(node, kw):
    """Validate password reset and add the user needing password reset."""
    request = kw['request']

    def validate_path(node, value):
        if value is None:
            return
        _raise_if_no_password_reset(node, value)
        metadata = get_sheet(value, IMetadata).get()
        _raise_if_outdated(node, value, metadata['creation_date'])
        request.validated['user'] = metadata['creator']
    return validate_path


def _raise_if_no_password_reset(node: SchemaNode, value: IPasswordReset):
    if not IPasswordReset.providedBy(value):
        raise colander.Invalid(node, 'This is not a valid password reset.')


def _raise_if_outdated(node: SchemaNode, value: IPasswordReset,
                       creation_date: datetime):
        if (now() - creation_date).days >= 7:
            value.__parent__ = None  # commit_suicide
            msg = 'This password reset is older than 7 days.'
            raise colander.Invalid(node, msg)


class POSTPasswordResetRequestSchema(colander.Schema):

    """Schema to get a user password reset resource."""

    path = Resource(missing=colander.required,
                    validator=validate_password_reset_path,
                    )
    password = Password(missing=colander.required)
