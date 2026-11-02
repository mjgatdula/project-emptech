"""API mutations accept JSON objects, matching multipart/form field semantics."""
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class ObjectJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(stream, media_type=media_type, parser_context=parser_context)
        if not isinstance(data, dict):
            raise ParseError('Send a JSON object with named fields.')
        return data
