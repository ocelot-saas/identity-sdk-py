"""Validation for inventory entities."""

import re

import validation
import validation_common


class Auth0UserValidator(validation.Validator):
    """Validator for Auth0 user JSON."""

    SCHEMA = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'title': 'Auth0 user response',
        'description': 'JSON returned by Auth0 to describe a particular user',
        'type': 'object',
        'properties': {
            'user_id': {
                'description': 'The unique id assigned by Auth0 for this user',
                'type': 'string',
            },
            'name': {
                'description': 'The name of the user, as best extracted by Auth0',
                'type': 'string',
            },
            'picture': validation_common.URLValidator.SCHEMA
        },
        'required': ['user_id', 'name', 'picture'],
        'additionalProperties': True
    }

    def __init__(self, url_validator):
        self._url_validator = url_validator

    def validate(self, auth0_user_raw):
        try:
            auth0_user = json.loads(auth0_user_raw)
            jsonschema.validate(auth0_user, self.SCHEMA)
            auth0_user['picture'] = self._url_validator.validate(auth0_user['picture'])
            return auth0_user
        except ValueError as e:
            raise validation.Error('Could not decode Auth0 JSON response') from e
        except jsonschema.ValidationError as e:
            raise validation.Error('Could not validate Auth0 user data') from e
        except Exception as e:
            raise validation.Error('Other error') from e


class AccessTokenHeaderValidator(validation.Validator):
    """Validator for the access token header."""

    SCHEMA = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'title': 'Access Token',
        'description': 'The Auth0 access token',
        'type': 'string'
    }

    def __init__(self):
        self._auth_re = re.compile('Bearer (.+)')

    def validate(self, auth_header):
        if not isinstance(auth_header, str):
            raise validation.Error('Missing Authorization header')

        match = self._auth_re.match(auth_header)

        if match is None:
            raise validation.Error('Invalid Authorization header')

        return match.group(1)


class UserValidator(validation.Validator):
    """Validator for the user entity."""

    SCHEMA = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'title': 'User',
        'description': 'Externally visible user info',
        'type': 'object',
        'properties': {
            'id': validation_common.IdValidator.SCHEMA,
            'timeJoinedTs': validation_common.DateTimeTsValidator.SCHEMA,
            'name': {
                'description': 'The user\'s human name',
                'type': 'string'
            },
            'pictureUrl': validation_common.URLValidator.SCHEMA
        },
        'required': ['id', 'timeJoinedTs', 'name', 'pictureUrl'],
        'addtionalProperties': False
    }

    def __init__(self, id_validator, datetime_ts_validator, url_validator):
        self._id_validator = id_validator
        self._datetime_ts_validator = datetime_ts_validator
        self._url_validator = url_validator

    def _post_schema_validate(self, user_raw):
        user = dict(user_raw)

        user['id'] = self._id_validator.validate(user['id'])
        user['timeJoinedTs'] = self._datetime_ts_validator.validate(user['timeJoinedTs'])
        user['pictureUrl'] = self._url_validator.validate(user['pictureUrl'])

        return user


class UserResponseValidator(validation.Validator):
    """User response validator."""

    SCHEMA = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'title': 'Users resouces response',
        'description': 'Response from the user resource',
        'type': 'object',
        'properties': {
            'user': UserValidator.SCHEMA,
        },
        'required': ['user'],
        'additionalProperties': False
    }

    def __init__(self, user_validator):
        self._user_validator = user_validator

    def _post_schema_validation(self, user_response_raw):
        user_response = dict(user_response_raw)

        user_response['user'] = self._user_validator.validate(user_response['user'])

        return user_response
