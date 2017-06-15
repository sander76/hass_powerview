import asyncio
import os
import logging

from homeassistant.config import load_yaml_config_file
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = 'powerview'
ENTITY_ID_FORMAT = DOMAIN + ".{}"
_LOGGER = logging.getLogger(__name__)
ENTITY_SCENE = 'scene'
ENTITY_HUB = 'hub'
SERVICE_PV_SCENES_REFRESH = 'scenes_refresh'
SERVICE_PV_SCENES_ACTIVATE = 'scene_activate'

SERVICE_TO_METHOD = {
    SERVICE_PV_SCENES_REFRESH: {'method': 'async_refresh', 'schema': None},
    SERVICE_PV_SCENES_ACTIVATE: {'method': 'async_activate',
                                 'schema': {ATTR_ENTITY_ID: ATTR_ENTITY_ID}}
}
from aiopvapi.hub import Hub
from aiopvapi.scenes import Scenes


class PowerViewBase(Entity):
    @asyncio.coroutine
    def refresh(self):
        return


@asyncio.coroutine
def async_setup(hass, config):
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    _host = config.get(CONF_HOST)
    _websession = async_get_clientsession(hass)
    _hub = PvHub(hass, _host, _websession)
    _components = [_hub,
                   Scenes(hass, _hub.hub)]

    @asyncio.coroutine
    def async_handle_cover_service(service):
        comps = component.extract_from_service(service)
        method = SERVICE_TO_METHOD.get(service.service)
        params = service.data.copy()
        params.pop(ATTR_ENTITY_ID, None)

        for comp in comps:
            yield from getattr(comp, method['method'])(**params)

    descriptions = yield from hass.async_add_job(
        load_yaml_config_file, os.path.join(
            os.path.dirname(__file__), 'services.yaml'))

    for service_name in SERVICE_TO_METHOD:
        schema = SERVICE_TO_METHOD[service_name].get('schema')
        hass.services.async_register(
            DOMAIN, service_name, async_handle_cover_service,
            descriptions.get(service_name), schema=schema)

    yield from component.async_add_entities()


class PvHub(PowerViewBase):
    def __init__(self, hass, pv_ip, session):
        self._hub = Hub(pv_ip, hass.loop, websession=session)
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            ENTITY_HUB,
            hass=hass
        )

    @property
    def hub(self):
        return self._hub


class Scenes(PowerViewBase):
    def __init__(self, hass, pv_scenes: Scenes):
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            ENTITY_SCENE,
            hass=hass)
        self._scenes = pv_scenes

    @asyncio.coroutine
    def scenes_refresh(self):
        _response = yield from self._scenes.get_scenes()
        return _response

    @asyncio.coroutine
    def scene_activate(self, scene_id):
        _response = yield from self._scenes.activate_scene(scene_id)
        return _response
