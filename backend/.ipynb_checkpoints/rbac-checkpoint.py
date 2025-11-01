"""
RBAC utilities for hierarchical access control
"""
from sqlalchemy.orm import Query

import models


def user_has_job_access(user: models.User, job: models.ProcessingJob) -> bool:
    """Verify that the user can access the given job based on RBAC hierarchy"""
    if user.rbac_level == models.RBACLevel.STATE:
        return user.state_id == job.state_id

    if user.rbac_level == models.RBACLevel.DISTRICT:
        if user.state_id != job.state_id:
            return False
        return user.district_id == job.district_id

    if user.rbac_level == models.RBACLevel.STATION:
        if user.state_id != job.state_id or user.district_id != job.district_id:
            return False
        return user.station_id == job.station_id

    return False


def user_has_document_access(user: models.User, document: models.Document) -> bool:
    """Verify that user can view the document derived from a job"""
    if user.rbac_level == models.RBACLevel.STATE:
        return user.state_id == document.state_id

    if user.rbac_level == models.RBACLevel.DISTRICT:
        if user.state_id != document.state_id:
            return False
        return user.district_id == document.district_id

    if user.rbac_level == models.RBACLevel.STATION:
        if user.state_id != document.state_id or user.district_id != document.district_id:
            return False
        return user.station_id == document.station_id

    return False


def filter_jobs_scope(query: Query, user: models.User) -> Query:
    """Apply RBAC filters to a ProcessingJob query"""
    if user.rbac_level == models.RBACLevel.STATE:
        return query.filter(models.ProcessingJob.state_id == user.state_id)
    if user.rbac_level == models.RBACLevel.DISTRICT:
        return query.filter(
            models.ProcessingJob.state_id == user.state_id,
            models.ProcessingJob.district_id == user.district_id,
        )
    # Station level
    return query.filter(
        models.ProcessingJob.state_id == user.state_id,
        models.ProcessingJob.district_id == user.district_id,
        models.ProcessingJob.station_id == user.station_id,
    )


def filter_documents_scope(query: Query, user: models.User) -> Query:
    """Apply RBAC filters to a Document query"""
    if user.rbac_level == models.RBACLevel.STATE:
        return query.filter(models.Document.state_id == user.state_id)
    if user.rbac_level == models.RBACLevel.DISTRICT:
        return query.filter(
            models.Document.state_id == user.state_id,
            models.Document.district_id == user.district_id,
        )
    return query.filter(
        models.Document.state_id == user.state_id,
        models.Document.district_id == user.district_id,
        models.Document.station_id == user.station_id,
    )
