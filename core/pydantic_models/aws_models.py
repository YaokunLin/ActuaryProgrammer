from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class AccessKey(BaseModel):
    AccessKeyId: str
    CreateDate: datetime
    SecretAccessKey: str
    Status: str
    UserName: str


class PermissionsBoundary(BaseModel):
    PermissionsBoundaryType: str
    PermissionsBoundaryArn: str


class User(BaseModel):
    Path: str
    UserName: str
    UserId: str
    Arn: str
    CreateDate: datetime
    PasswordLastUsed: Optional[datetime]
    PermissionsBoundary: Optional[PermissionsBoundary]
    Tags: Optional[List[Dict]]  # arbitrary key-value pairs


class IAMPolicy(BaseModel):
    PolicyName: str
    PolicyId: str
    Arn: str
    Path: str
    DefaultVersionId: str
    AttachmentCount: int
    PermissionsBoundaryUsageCount: int
    IsAttachable: bool
    Description: Optional[str]
    CreateDate: datetime
    UpdateDate: datetime
    Tags: Optional[List[Dict]]  # arbitrary key-value pairs
