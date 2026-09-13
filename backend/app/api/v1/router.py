from fastapi import APIRouter

from app.api.v1 import (
    admin_auth,
    applications,
    aptitude,
    ats,
    auth,
    companies,
    email_tracking,
    health,
    intelligence,
    interview,
    jobs,
    me,
    profile,
    scholarships,
    webhooks,
)
from app.api.v1.admin import aptitude as admin_aptitude
from app.api.v1.admin import companies as admin_companies
from app.api.v1.admin import intelligence as admin_intelligence
from app.api.v1.admin import interview as admin_interview
from app.api.v1.admin import jobs as admin_jobs
from app.api.v1.admin import scholarships as admin_scholarships
from app.api.v1.admin import uploads as admin_uploads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(scholarships.router, prefix="/scholarships", tags=["scholarships"])
api_router.include_router(ats.router, prefix="/ats", tags=["ats"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["intelligence"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(aptitude.router, prefix="/aptitude", tags=["aptitude"])
api_router.include_router(interview.router, prefix="/interview", tags=["interview"])
api_router.include_router(interview.star_router, prefix="/star-stories", tags=["star-stories"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(email_tracking.router, prefix="/email-tracking", tags=["email-tracking"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

api_router.include_router(admin_auth.router, prefix="/admin/auth", tags=["admin-auth"])
api_router.include_router(admin_companies.router, prefix="/admin/companies", tags=["admin-companies"])
api_router.include_router(admin_jobs.router, prefix="/admin/jobs", tags=["admin-jobs"])
api_router.include_router(
    admin_scholarships.router, prefix="/admin/scholarships", tags=["admin-scholarships"]
)
api_router.include_router(
    admin_intelligence.router, prefix="/admin/intelligence", tags=["admin-intelligence"]
)
api_router.include_router(admin_uploads.router, prefix="/admin/uploads", tags=["admin-uploads"])
api_router.include_router(admin_aptitude.router, prefix="/admin/aptitude", tags=["admin-aptitude"])
api_router.include_router(admin_interview.router, prefix="/admin/interview", tags=["admin-interview"])
