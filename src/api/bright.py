import abc
import os

import requests
from flask import current_app

from src.models.bright import HealthCheck


class BrightBase(abc.ABC):
    """Base class for Bright API."""

    default_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    def __init__(
            self,
            url=None,
            session=None,
            basic_auth=None,
            cert_auth=None,
            verify=True,
            timeout=5
    ):
        """
        :param session: an already existing session session.
        :param basic_auth: a tuple of username and password to use when establishing a session via HTTP BASIC
        authentication.
        :param cert_auth: a tuple of cert and key to use when establishing a session. The pair is used for both
        authentication and encryption.
        :param verify: check whether verify SSL connection
        :param timeout: how much time until connection is dropped, in seconds
        """
        self.url = url
        if session is None:
            self._session = requests.Session()
        else:
            self._session = session
        if basic_auth:
            self._create_basic_session(basic_auth)
        elif cert_auth is not None:
            self._create_cert_session(cert_auth)
        self._session.headers.update(self.default_headers)
        self.verify = verify
        self.timeout = timeout

    def _create_basic_session(self, basic_auth):
        self._session.auth = basic_auth

    def _create_cert_session(self, cert_auth):
        self._session.cert = cert_auth

    @property
    def version(self):
        url = "{0}/{1}".format(self.url, 'json')
        params = {
            'service': 'cmmain',
            'call': 'getVersion',
        }
        response = self._session.post(
            url=url,
            json=params,
            verify=self.verify,
            timeout=self.timeout
        ).json()
        return response.get('cmVersion')

    @abc.abstractmethod
    def measurable(self, name):
        pass


class Bright(BrightBase):
    """Generic Bright implementation."""

    def measurable(self, name):
        raise NotImplementedError('use a specific Bright version')


class Bright7(BrightBase):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = "{0}/{1}".format(self.url, 'json')

    def entity(self, name):
        url = "{0}/{1}".format(self.url, 'json')
        params = {
            'service': 'cmdevice',
            'call': 'getDevice',
            'arg': name
        }
        return self._session.post(
            url=url,
            json=params,
            verify=self.verify,
            timeout=self.timeout
        ).json() or {}

    def measurable(self, name):
        url = "{0}/{1}".format(self.url, 'json')
        params = {
            'service': 'cmmon',
            'call': 'getHealthcheck',
            'arg': name
        }
        return self._session.post(
            url=url,
            json=params,
            verify=self.verify,
            timeout=self.timeout
        ).json() or {}


class Bright8(BrightBase):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = "{0}/{1}/{2}".format(self.url, 'rest', 'v1')

    def measurable(self, name):
        url = "{0}/{1}".format(self.url, 'json')
        params = {
            'service': 'cmmon',
            'call': 'getMonitoringMeasurable',
            'arg': name
        }
        return self._session.post(
            url,
            json=params,
            verify=self.verify,
            timeout=self.timeout
        ).json() or {}


class BrightAPI:

    def __init__(
            self,
            host=None,
            port=None,
            cert_auth=None,
            version=None,
            **kwargs
    ):
        host = host or current_app.config['BRIGHT_COMPUTING_HOST']
        port = port or current_app.config['BRIGHT_COMPUTING_PORT']
        url = f"https://{host}:{port}"

        if not cert_auth:
            cert = current_app.config['BRIGHT_COMPUTING_CERT_PATH']
            key = current_app.config['BRIGHT_COMPUTING_KEY_PATH']

            # handle relative paths
            if not os.path.isabs(cert) and not os.path.isabs(key):
                instance_path = os.path.dirname(current_app.instance_path)
                cert = os.path.join(instance_path, cert)
                key = os.path.join(instance_path, key)
            cert_auth = (cert, key)

        version = version or Bright(url=url).version
        self.instance = self.factory(version)(
            url=url,
            cert_auth=cert_auth,
            **kwargs
        )

    @staticmethod
    def factory(version):
        if isinstance(version, str):
            version = int(float(version))
        elif isinstance(version, float):
            version = int(version)
        if version == 7:
            return Bright7
        elif version == 8:
            return Bright8
        else:
            raise ValueError('Unsupported version')

    def __getattr__(self, name):
        return self.instance.__getattribute__(name)