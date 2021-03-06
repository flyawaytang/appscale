#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Describe ProtoRPC Messages in JSON Schema.

Add protorpc.message subclasses to MessageTypeToJsonSchema and get a JSON
Schema description of all the messages.
"""


import re

import google

from protorpc import messages

__all__ = ['MessageTypeToJsonSchema']


class MessageTypeToJsonSchema(object):
  """Describe ProtoRPC messages in JSON Schema.

  Add protorpc.message subclasses to MessageTypeToJsonSchema and get a JSON
  Schema description of all the messages. MessageTypeToJsonSchema handles
  all the types of fields that can appear in a message.
  """

  __FIELD_TO_SCHEMA_TYPE_MAP = {
      messages.IntegerField: 'integer',
      messages.FloatField: 'number',
      messages.BooleanField: 'boolean',
      messages.BytesField: 'string',
      messages.StringField: 'string',
      messages.MessageField: 'object',
      messages.EnumField: 'string',
  }

  __DEFAULT_SCHEMA_TYPE = 'string'

  def __init__(self):

    self.__schemas = {}


    self.__normalized_names = {}

  def add_message(self, message_type):
    """Add a new message.

    Args:
      message_type: protorpc.message.Message class to be parsed.

    Returns:
      string, The JSON Schema id.

    Raises:
      KeyError if the Schema id for this message_type would collide with the
      Schema id of a different message_type that was already added.
    """
    name = self.__normalized_name(message_type)
    if name not in self.__schemas:
      schema = self.__message_to_schema(message_type)
      self.__schemas[name] = schema
    return name

  def ref_for_message_type(self, message_type):
    """Returns the JSON Schema id for the given message.

    Args:
      message_type: protorpc.message.Message class to be parsed.

    Returns:
      string, The JSON Schema id.

    Raises:
      KeyError: if the message hasn't been parsed via add_message().
    """
    name = self.__normalized_name(message_type)
    if name not in self.__schemas:
      raise KeyError('Message has not been parsed: %s', name)
    return name

  def schemas(self):
    """Returns the JSON Schema of all the messages.

    Returns:
      object: JSON Schema description of all messages.
    """
    return self.__schemas.copy()

  def __normalized_name(self, message_type):
    """Normalized schema name.

    Generate a normalized schema name, taking the class name and stripping out
    everything but alphanumerics, and camel casing the remaining words.
    A normalized schema name is a name that matches [a-zA-Z][a-zA-Z0-9]*

    Args:
      message_type: protorpc.message.Message class being parsed.

    Returns:
      A string, the normalized schema name.

    Raises:
      KeyError if a collision is found between normalized names.
    """


    name = message_type.definition_name()

    split_name = re.split(r'[^0-9a-zA-Z]', name)
    normalized = ''.join(
        part[0].upper() + part[1:] for part in split_name if part)

    previous = self.__normalized_names.get(normalized)
    if previous:
      if previous != name:
        raise KeyError('Both %s and %s normalize to the same schema name: %s' %
                       (name, previous, normalized))
    else:
      self.__normalized_names[normalized] = name

    return normalized

  def __message_to_schema(self, message_type):
    """Parse a single message into JSON Schema.

    Will recursively descend the message structure
    and also parse other messages references via MessageFields.

    Args:
      message_type: protorpc.messages.Message class to parse.

    Returns:
      An object representation of the schema.
    """
    name = self.__normalized_name(message_type)
    schema = {
        'id': name,
        'type': 'object',
        }
    if message_type.__doc__:
      schema['description'] = message_type.__doc__
    properties = {}
    for field in message_type.all_fields():
      descriptor = {}

      if type(field) == messages.MessageField:
        field_type = field.type().__class__
        descriptor['$ref'] = self.add_message(field_type)
        if field_type.__doc__:
          descriptor['description'] = field_type.__doc__
      else:
        descriptor['type'] = self.__FIELD_TO_SCHEMA_TYPE_MAP.get(
            type(field), self.__DEFAULT_SCHEMA_TYPE)
      if field.required:
        descriptor['required'] = True

      if field.default:
        if type(field) == messages.EnumField:
          descriptor['default'] = str(field.default)
        else:
          descriptor['default'] = field.default

      if field.repeated:
        if '$ref' in descriptor:
          descriptor['items'] = {
              '$ref': descriptor['$ref']
              }
          del descriptor['$ref']
        else:
          descriptor['items'] = {
              'type': descriptor['type']
              }
        descriptor['type'] = 'array'

      properties[field.name] = descriptor

    schema['properties'] = properties

    return schema
