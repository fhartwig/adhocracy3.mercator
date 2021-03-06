"""Common fixtures for adhocracy_mercator."""
from pytest import fixture


@fixture(scope='class')
def app(app_settings):
    """Return the adhocracy_spd test wsgi application."""
    from pyramid.config import Configurator
    from adhocracy_core.testing import add_create_test_users_subscriber
    import adhocracy_spd
    configurator = Configurator(settings=app_settings,
                                root_factory=adhocracy_spd.root_factory)
    configurator.include(adhocracy_spd)
    configurator.commit()
    add_create_test_users_subscriber(configurator)
    app = configurator.make_wsgi_app()
    return app


@fixture
def integration(integration):
    """Include resource types and sheets."""
    integration.include('adhocracy_spd.sheets')
    integration.include('adhocracy_spd.resources')
    integration.include('adhocracy_spd.workflows')
    return integration
