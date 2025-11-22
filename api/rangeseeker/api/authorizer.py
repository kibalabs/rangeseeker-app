import functools
import typing

from core import logging
from core.api.api_request import KibaApiRequest
from core.exceptions import ForbiddenException
from core.exceptions import UnauthorizedException
from core.http.basic_authentication import BasicAuthentication
from mypy_extensions import Arg
from pydantic import BaseModel

_P = typing.ParamSpec('_P')


class Authorizer:
    async def retrieve_signature_signer(self, signatureString: str) -> str:
        raise NotImplementedError


ApiRequest = typing.TypeVar('ApiRequest', bound=BaseModel)


async def get_basic_authentication_from_authorization_signature(request: KibaApiRequest[ApiRequest], authorizer: Authorizer) -> BasicAuthentication:  # noqa: UP047
    authorization = request.headers.get('Authorization')
    if not authorization:
        raise ForbiddenException(message='AUTH_NOT_PROVIDED')
    if not authorization.startswith('Signature '):
        raise ForbiddenException(message='AUTH_INVALID')
    signatureString = authorization.replace('Signature ', '', 1)
    try:
        signerId = await authorizer.retrieve_signature_signer(signatureString=signatureString)
    except UnauthorizedException:
        raise
    except BaseException as exception:  # noqa: BLE001
        logging.exception(exception)  # type: ignore[arg-type]
        raise ForbiddenException(message='AUTH_INVALID')
    return BasicAuthentication(username=signerId, password=signatureString)


def authorize_signature(  # type: ignore[explicit-any]
    authorizer: Authorizer,
) -> typing.Callable[[typing.Callable[[Arg(KibaApiRequest[ApiRequest], 'request')], typing.Awaitable[typing.Any]]], typing.Callable[_P, typing.Any]]:
    def decorator(func: typing.Callable[[Arg(KibaApiRequest[ApiRequest], 'request')], typing.Awaitable[typing.Any]]) -> typing.Callable[_P, typing.Any]:  # type: ignore[explicit-any]
        @functools.wraps(func)
        async def async_wrapper(request: KibaApiRequest[ApiRequest]) -> typing.Any:  # type: ignore[misc, explicit-any]
            request.authBasic = await get_basic_authentication_from_authorization_signature(request=request, authorizer=authorizer)
            return await func(request=request)

        # TODO(krishan711): figure out correct typing here
        return async_wrapper  # type: ignore[return-value]

    return decorator
