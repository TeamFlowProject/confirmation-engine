from fastapi import APIRouter

from src.controller.rest.v1.protocols import ConfirmationService


def create_confirmation_router(service: ConfirmationService) -> APIRouter:
    router = APIRouter()

    return router
