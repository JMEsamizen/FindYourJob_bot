from .analysis import router as analysis_router
from .learning import router as learning_router
from .profile import router as profile_router
from .registration import router as registration_router
from .start import router as start_router
from .stats import router as stats_router
from .vacancies import router as vacancies_router

__all__ = [
    "analysis_router",
    "learning_router",
    "profile_router",
    "registration_router",
    "start_router",
    "stats_router",
    "vacancies_router",
]
