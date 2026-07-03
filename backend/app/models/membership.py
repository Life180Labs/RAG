"""Shared enums for the multi-tenant hierarchy (Organization -> Workspace
-> Project), per docs/02-architecture.md section 121 and section 126.

Defined once and reused by every membership/resource table so the
Postgres enum types (member_role, resource_status) aren't redefined per
table.
"""

import enum


class MemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


_ROLE_RANK = {
    MemberRole.VIEWER: 0,
    MemberRole.DEVELOPER: 1,
    MemberRole.ADMIN: 2,
    MemberRole.OWNER: 3,
}


def role_meets_minimum(role: "MemberRole", minimum: "MemberRole") -> bool:
    """True if `role` grants at least as much access as `minimum`
    (Owner > Admin > Developer > Viewer)."""
    return _ROLE_RANK[role] >= _ROLE_RANK[minimum]


class ResourceStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
