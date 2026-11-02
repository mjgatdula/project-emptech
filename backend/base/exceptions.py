from django.db import DatabaseError, IntegrityError, InterfaceError
from django.core.exceptions import (ValidationError as ModelValidationError, RequestDataTooBig, TooManyFilesSent, TooManyFieldsSent)
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, (RequestDataTooBig, TooManyFilesSent, TooManyFieldsSent)):
        return Response({'message': 'The upload/request exceeds the allowed size or number of fields/files.'}, status=413)
    if isinstance(exc, ModelValidationError):
        return Response({'message': ' '.join(exc.messages)}, status=400)
    if isinstance(exc, IntegrityError):
        return Response({'message': 'This action conflicts with an existing record. Refresh and try again.'}, status=409)
    if isinstance(exc, (DatabaseError, InterfaceError)):
        return Response({'message': 'The database is temporarily unavailable. Please try again.'}, status=503)
    response = exception_handler(exc, context)
    if response is not None:
        original = response.data
        def first(value):
            if isinstance(value, dict):
                return next((first(v) for v in value.values()), 'The request could not be completed.')
            if isinstance(value, list):
                return first(value[0]) if value else 'Check the submitted fields.'
            return str(value)
        response.data = {'message': first(original), 'errors': original}
    return response
