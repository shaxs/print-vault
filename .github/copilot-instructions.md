# GitHub Copilot Instructions for Print Vault

## Overview

This repository is a self-hosted 3D printing management application built with Django (backend) and Vue.js (frontend). The following instructions are tailored to help GitHub Copilot generate accurate and context-aware code suggestions for this project.

## Project Structure

- **Backend**: Located in the `backend/` directory, built with Django and Django REST Framework.
- **Frontend**: Located in the `frontend/` directory, built with Vue.js and styled using Tailwind CSS.
- **Database**: Uses PostgreSQL for production and SQLite for development.
- **Media Files**: Stored in the `data/media/` directory.

## Coding Standards

### Python (Backend)

- Follow PEP 8 guidelines.
- Use Django ORM for database queries.
- API endpoints are defined in `urls.py` and implemented in `views.py`.
- Models are located in `models.py`.
- Serializers are located in `serializers.py`.
- Use `python manage.py makemigrations` and `python manage.py migrate` for database migrations.

### JavaScript (Frontend)

- Use single quotes for strings.
- Use arrow functions for callbacks.
- API calls are centralized in `APIService.js`.
- Use Prettier for code formatting.

### Vue.js

- Use function-based components.
- Organize components and views logically.

## Development Guidelines

### Backend

- Ensure all API endpoints are well-documented.
- Write unit tests for views and serializers.
- Use environment variables for sensitive configurations.

### Frontend

- Keep components modular and reusable.
- Use Tailwind CSS for consistent styling.
- Ensure proper error handling for API calls.

## Deployment Notes

- Use Docker Compose for containerized deployment.
- Configure environment variables in `.env` files for both backend and frontend.
- Use Nginx as a reverse proxy for production deployment.

## Tips for Copilot

- When working on the backend, suggest Django ORM queries and REST Framework serializers.
- When working on the frontend, suggest Vue.js components and API integration patterns.
- For database-related tasks, prioritize PostgreSQL for production and SQLite for development.
- Follow the existing folder structure and naming conventions.

## Design System (NON-NEGOTIABLE)

- **ALWAYS** refer to `DESIGN_SYSTEM.md` before creating or modifying UI components.
- **NEVER** create custom modals - use `BaseModal.vue` component.
- **ALWAYS** use CSS variables for colors - never hardcode colors.
- **ALWAYS** test in both light and dark modes.
- Follow existing component patterns - check similar components for reference.

## Additional Notes

- Refer to `AGENTS.md` for more detailed instructions applicable to both AI agents and human developers.
- Refer to `DESIGN_SYSTEM.md` for UI/UX patterns and component standards.
- Ensure that code suggestions align with the project's coding standards and best practices.
