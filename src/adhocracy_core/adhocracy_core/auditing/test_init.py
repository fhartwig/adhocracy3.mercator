from pyramid import testing

from unittest.mock import Mock
from pytest import fixture
from pytest import mark


@fixture()
def integration(config):
    config.include('adhocracy_core.content')
    config.include('adhocracy_core.events')
    config.include('adhocracy_core.changelog')
    config.include('adhocracy_core.sheets')


@fixture
def user():
    from adhocracy_core.sheets.principal import IUserBasic
    user = testing.DummyResource(__provides__=IUserBasic)
    user.name = 'god'
    return user


@fixture
def mock_get_user_info(monkeypatch):
    import adhocracy_core.auditing
    mock_get_user_info = Mock(spec=adhocracy_core.auditing)
    mock_get_user_info.return_value = ('god',
                                       '/principals/users/000001')
    monkeypatch.setattr(adhocracy_core.auditing,
                        '_get_user_info',
                        mock_get_user_info)
    return mock_get_user_info


def _get_event_name(index):
    return 'event_{}'.format(index)


def _get_resource_path(index):
    return '/value1_{}'.format(index)


def _get_user_name(index):
    return 'user{}'.format(index)


def _get_user_path(index):
    return '/principals/users/user{}'.format(index)


@fixture
def context(context):
    mocked_conn = Mock()
    mocked_auditconn = Mock()
    mocked_auditconn.root.return_value = {}
    mocked_conn.get_connection.return_value = mocked_auditconn
    context._p_jar = mocked_conn
    return context


@fixture()
def request_(registry, context):
    request = testing.DummyResource(registry=registry)
    request.context = context
    return request


def test_set_auditlog_no_audit_connection(context):
    from . import get_auditlog
    from . import set_auditlog

    context._p_jar.get_connection \
        = Mock(name='method', side_effect=KeyError('audit'))

    set_auditlog(context)

    assert get_auditlog(context) is None


@mark.usefixtures('integration')
def test_audit_resources_changes_callback_empty_changelog(registry, request_):
    from . import audit_resources_changes_callback
    from . import get_auditlog
    from . import set_auditlog

    request_.registry = registry

    set_auditlog(request_.context)
    response = Mock()
    audit_resources_changes_callback(request_, response)

    all_entries = get_auditlog(request_.context).values()
    assert len(all_entries) == 0


@mark.usefixtures('integration')
def test_audit_resource_changes_callback(registry, request_, changelog,
                                         mock_get_user_info):
    from . import audit_resources_changes_callback
    from . import get_auditlog
    from . import set_auditlog

    request_.registry = registry
    changelog = registry.changelog
    set_auditlog(request_.context)

    changelog['/blublu'] \
        = changelog['/blublu']._replace(resource=testing.DummyResource())
    changelog['/'] = changelog['/']._replace(resource=context, created=True)
    changelog['/blabla'] \
        = changelog['/blabla']._replace(resource=context, modified=True)
    registry.changelog = changelog

    response = Mock()
    audit_resources_changes_callback(request_, response)

    all_entries = get_auditlog(request_.context).values()
    assert len(all_entries) == 2


@mark.usefixtures('integration')
def test_get_user_info(context, registry, request_, user):
    from adhocracy_core.auditing import _get_user_info

    request_.root = context
    request_.root['user1'] = user
    request_.registry = registry
    request_.authenticated_userid = '/user1'

    (user_name, user_path) = _get_user_info(request_)
    assert user_name == 'god'
    assert user_path == '/user1'


@mark.usefixtures('integration')
def test_get_user_info_nouser_in_request(context, registry, request_, user):
    from adhocracy_core.auditing import _get_user_info

    request_.root = context
    request_.registry = registry
    request_.authenticated_userid = None

    (user_name, user_path) = _get_user_info(request_)
    assert user_name == ''
    assert user_path == ''


class TestAuditlog:

    @fixture
    def inst(self):
        from . import AuditLog
        return AuditLog()

    def test_create(self, inst):
        from BTrees.OOBTree import OOBTree
        assert isinstance(inst, OOBTree)

    def test_add(self, inst):
        import datetime
        from . import AuditEntry
        name = 'created'
        resource_path = '/resource1'
        user_name = 'user1'
        user_path = '/user1'
        inst.add(name, resource_path, user_name, user_path)
        key, value = inst.items()[0]
        assert isinstance(key, datetime.datetime)
        assert isinstance(value, AuditEntry)
        assert value.name == name
        assert value.resource_path == resource_path
        assert value.user_name == user_name
        assert value.user_path == user_path


class TestSetAuditlog:
    """ TODO public function called from root factory"""


class TestGetAuditlog:
    """ not really needed, we could use substanced.util.get_auditlog for now"""


class TestAddAuditEvent:

    @fixture
    def user(self):
        return testing.DummyResource(__name__='user',
                                     name='name')

    @fixture
    def mock_auditlog(self):
        from . import AuditLog
        mock = Mock(spec=AuditLog)
        return mock

    @fixture
    def mock_get_auditlog(self, monkeypatch):
        from adhocracy_core import auditing
        mock = Mock()
        monkeypatch.setattr(auditing, 'get_auditlog', mock)
        return mock

    def call_fut(self, context, name, resource_path, user_name, user_path):
        from . import log_auditevent
        return log_auditevent(context,
                              name, resource_path, user_name, user_path)

    def test_ignore_if_no_auditlog(self, context, mock_get_auditlog,
                                   mock_auditlog):
        mock_get_auditlog.return_value = None
        self.call_fut(context, 'created', '/resource1', 'user1', '/user1')
        assert mock_auditlog.add.called is False

    def test_add_if_auditlog(self, context, mock_auditlog,
                             mock_get_auditlog):
        mock_get_auditlog.return_value = mock_auditlog
        self.call_fut(context, 'created', '/resource1', 'user1', '/user1')
        assert mock_auditlog.add.called_with('/',
                                             'created',
                                             '/resource1',
                                             'user1',
                                             '/user1')