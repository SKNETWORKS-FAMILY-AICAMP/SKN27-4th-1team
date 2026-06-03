from django.http import JsonResponse


def success_response(data=None, message='OK', status_code=200, meta=None):
    body = {
        'success': True,
        'message': message,
        'data': data,
    }

    if meta is not None:
        body['meta'] = meta

    return JsonResponse(body, status=status_code, json_dumps_params={'ensure_ascii': False})


def error_response(message='Bad request', errors=None, code='BAD_REQUEST', status_code=400):
    body = {
        'success': False,
        'message': message,
        'code': code,
        'errors': errors or {},
    }

    return JsonResponse(body, status=status_code, json_dumps_params={'ensure_ascii': False})


def validation_error_response(errors, message='Validation failed'):
    return error_response(
        message=message,
        errors=errors,
        code='VALIDATION_ERROR',
        status_code=400,
    )
