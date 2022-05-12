from functools import partial
from typing import Any, Callable, Dict, Optional, Tuple

from .errors import UndefinedPermission
from .permission import Permission


class PermissionAlreadyDefined(Exception):
    """Error raised while using the @authorize() decorator with the same Permission
    twice in the same Policy object.
    """

    def __init__(self, permission: Permission) -> None:
        """
        Args:
            permission (Permission): a permission
        """
        super().__init__(f"Permission {permission.name} already defined")
        self.permission = permission


AccessMethod = Callable[..., bool]


class PolicyMetaclass(type):
    """Metaclass used by the Policy class.
    It's used to register all the access methods defined by the @authorize() decorator.
    """

    def __new__(cls, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any]) -> type:
        """Callback called when a Policy class is created.
        Loop over all the attributes and check if a `_authorized_permission` has
        been defined on it.
        If `_authorized_permission` is found we register the method
        in a dictionary in order to access it later using the
        permission being authorized.

        Args:
            cls: a Policy class
            name (str): class name
            bases (Tuple[type, ...]): base classes
            attrs (Dict[str, Any]): class attributes
        """
        access_methods: Dict[Permission, AccessMethod] = {}
        for val in attrs.values():
            permission: Optional[Permission] = getattr(
                val, "_authorized_permission", None
            )
            if not permission:
                continue

            if permission in access_methods:
                raise PermissionAlreadyDefined(permission)
            access_methods[permission] = val

        attrs["_access_methods"] = access_methods
        return super().__new__(cls, name, bases, attrs)


def authorize(permission: Permission) -> Callable[[AccessMethod], AccessMethod]:
    def decorator(func: AccessMethod) -> AccessMethod:
        """Add an `_authorized_permission` attribute to the method
        in order for the metaclass to recognize it as an AccessMethod.

        Args:
            func (AccessMethod): method used to grant access

        Returns:
            AccessMethod: access method received as input
        """
        setattr(func, "_authorized_permission", permission)
        return func

    return decorator


class Policy(metaclass=PolicyMetaclass):
    _access_methods: Dict[Permission, AccessMethod]

    def get_access_method(self, permission: Permission) -> AccessMethod:
        """Returns the AccessMethod that was registered for the permission
        received as input.
        If no AccessMethod is found it raises a UndefinedPermission error.

        Args:
            permission (Permission): a permission

        Returns:
            AccessMethod: access method registered for permission
        """
        try:
            return partial(self._access_methods[permission], self)
        except KeyError:
            raise UndefinedPermission(permission)
