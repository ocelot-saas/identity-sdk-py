"""Client interface for users of the identity service."""

import json

import falcon
import requests
import validation

import identity_sdk.validation as identity_validation


class Error(Exception):
    """Error raised by the client library."""

    def __init__(self, reason, status_code=None):
        self._reason = reason
        self._status_code = status_code

    def __str__(self):
        return self._reason


class IdentityClient(object):
    """A client for the identity service."""

    def __init__(self, identity_service_domain, user_response_validator, access_token_header_validator=None):
        self._identity_service_user_url = 'http://{}/user'.format(identity_service_domain)
        self._user_response_validator = user_response_validator
        self._access_token_header_validator = access_token_header_validator

    def get_user(self, access_token_raw):
        try:
            access_token = self._access_token_header_validator.validate(access_token_raw)
            user_get_req = requests.get(
                self._identity_service_user_url,
                headers={'Authorization': 'Bearer {access_token}'.format(access_token=access_token)})
            user_get_req.raise_for_status()
            user_json = self._user_response_validator.validate(json.loads(user_get_req.text))
            return user_json['user']
        except validation.Error as e:
            raise Error('Could not validate input/output') from e
        except (requests.ConnectionError, requests.Timeout) as e:
            raise Error('Could not reach identity service') from e
        except requests.HTTPError as e:
            raise Error('HTTP Error', status_code=user_get_req.status_code) from e


class AuthMiddleware(object):
    """Falcon middleware component which makes all routes of the API require auth.

    The component also makes available a `.user` property on the request object which will
    be passed to resource handlers.

    If the user is not valid, a 401 Unauthorized is returned. Other errors raise appropriate
    error responses.
    """

    def __init__(self, identity_client):
        self._identity_client = identity_client

    def process_resource(self, req, resp, resource, params):
        # No auth is expected on the OPTIONS header.
        if req.method == 'OPTIONS':
            return

        if hasattr(resource, 'AUTH_NOT_REQUIRED') and resource.AUTH_NOT_REQUIRED:
            return
        
        try:
            user = self._identity_client.get_user(req.auth)
            req.context['user'] = user_json['user']
        except Error as e:
            try:
                raise e.__context__
            except validation.Error:
                raise falcon.HTTPBadRequest(
                    title='Invalid Authorization header',
                    description='Invalid value "{}" for Authorization header'.format(req.auth)) from e
            except (requests.ConnectionError, requests.Timeout):
                raise falcon.HTTPBadGateway(
                    title='Cannot retrieve data from identity service',
                    description='Could not retrieve data from identity service') from e
            except requests.HTTPError:
                if e.status_code == 401:
                    raise falcon.HTTPUnauthorized(
                        title='Could not retrieve data from identity service',
                        description='Identity service refused to auhtorize ' +
                        'with access token "{}"'.format(access_token),
                        challenges='Bearer') from e
                elif e.status_code == 404:
                    raise falcon.HTTPNotFound(
                        title='User does not exist',
                        description='User does not exist')
                else:
                    raise falcon.HTTPBadGateway(
                        title='Cannot retrieve data from identity service',
                        description='Could not retrieve data from identity service') from e
