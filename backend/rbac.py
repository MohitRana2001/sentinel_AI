from sqlalchemy.orm import Query, Session

import models


def get_analyst_manager(db: Session, analyst: models.User) -> models.User:
    """Get the manager of an analyst"""
    if analyst.rbac_level != models.RBACLevel.ANALYST:
        return None
    
    if not analyst.manager_id:
        return None
    
    return db.query(models.User).filter(
        models.User.id == analyst.manager_id
    ).first()


def user_can_manage_analyst(manager: models.User, analyst: models.User) -> bool:
    """Check if a manager can manage a specific analyst"""
    if manager.rbac_level != models.RBACLevel.MANAGER:
        return False
    
    if analyst.rbac_level != models.RBACLevel.ANALYST:
        return False
    
    return analyst.manager_id == manager.id


def user_has_job_access(user: models.User, job: models.ProcessingJob) -> bool:
    """
    Verify that the user can access the given job based on role-based RBAC.
    - Admin: No access to documents/jobs (user management only)
    - Manager: Can access all jobs from their analysts
    - Analyst: Can only access their own jobs
    """
    if user.rbac_level == models.RBACLevel.ADMIN:
        return False  # Admins cannot access job documents
    
    if user.rbac_level == models.RBACLevel.ANALYST:
        # Analysts can only access their own jobs
        return job.user_id == user.id
    
    if user.rbac_level == models.RBACLevel.MANAGER:
        # Managers can access jobs from their analysts
        if job.user_id == user.id:
            return True  # Manager's own job
        
        # Check if job belongs to one of their analysts
        job_owner = job.user
        if job_owner and job_owner.manager_id == user.id:
            return True
    
    return False


def user_has_document_access(user: models.User, document: models.Document) -> bool:
    """
    Verify that user can view the document.
    Access is inherited from job ownership.
    """
    return user_has_job_access(user, document.job)


def filter_jobs_scope(query: Query, user: models.User) -> Query:
    """
    Apply RBAC filters to a ProcessingJob query.
    - Admin: No jobs (returns empty)
    - Manager: All jobs from their analysts + their own jobs
    - Analyst: Only their own jobs
    """
    if user.rbac_level == models.RBACLevel.ADMIN:
        # Admins have no access to jobs
        return query.filter(models.ProcessingJob.id == None)
    
    if user.rbac_level == models.RBACLevel.ANALYST:
        # Analysts see only their own jobs
        return query.filter(models.ProcessingJob.user_id == user.id)
    
    if user.rbac_level == models.RBACLevel.MANAGER:
        # Managers see their own jobs and their analysts' jobs
        # Get all analyst IDs under this manager
        analyst_ids = [analyst.id for analyst in user.analysts]
        analyst_ids.append(user.id)  # Include manager's own jobs
        
        return query.filter(models.ProcessingJob.user_id.in_(analyst_ids))
    
    return query.filter(models.ProcessingJob.id == None)


def filter_documents_scope(query: Query, user: models.User) -> Query:
    """
    Apply RBAC filters to a Document query.
    Documents are filtered via their associated jobs.
    """
    if user.rbac_level == models.RBACLevel.ADMIN:
        return query.filter(models.Document.id == None)
    
    if user.rbac_level == models.RBACLevel.ANALYST:
        # Filter to documents from jobs owned by this analyst
        return query.join(models.ProcessingJob).filter(
            models.ProcessingJob.user_id == user.id
        )
    
    if user.rbac_level == models.RBACLevel.MANAGER:
        # Filter to documents from jobs owned by manager or their analysts
        analyst_ids = [analyst.id for analyst in user.analysts]
        analyst_ids.append(user.id)
        
        return query.join(models.ProcessingJob).filter(
            models.ProcessingJob.user_id.in_(analyst_ids)
        )
    
    return query.filter(models.Document.id == None)
