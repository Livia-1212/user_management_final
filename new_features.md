# This is the Feature requirement
## New-Feature Built:  🔍 User Search and Filtering

- **Feature Description:** Implement search and filtering capabilities to allow administrators to easily find and manage users based on various criteria.
- **User Story:** As an administrator, I want to be able to search for users based on their username, email, role, or other relevant attributes and filter the user list accordingly.
- **Difficulty Level:** Medium
- **Minimum Viable Feature:**
  - Add search functionality to allow administrators to search for users by username, email, or role.
  - Implement filtering options to allow administrators to filter users based on criteria like account status or registration date range.
  - Update the user management API endpoints to support search and filtering.
- **Optional Enhancements:**
  - Implement advanced search using full-text search or ElasticSearch integration.
  - Add pagination and sorting options to the user search results.
  - Provide a user-friendly interface for administrators to perform user search and filtering.
- **Getting Started:**
  - Review the existing user management code and API endpoints.
  - Design and implement the search and filtering functionality, considering the search criteria and filtering options.
  - Update the user management API endpoints to accept search and filtering parameters.
  - Write unit tests to verify the user search and filtering functionality.


# Key Feature Mini Milestones

**The User Search and Filtering feature requires:**
- Search functionality:
    - Ability to search for users by nickname, email, or role.
- Filtering options:
    - Filter users based on account status (is_locked, email_verified).
    - Filter users by registration date range (created_at).
- API endpoints:
    - Added `/users/search` new endpoint to router, implementing the code to enable the query parameters to accept a variety of search and filter options to give administrators flexibility. 

## Step 1: Review Existing User Management Code and API Endpoints
- Added `invited_by_user_id` and `is_converted` columns to `app/models/user_model.py` to facilitate the new functionalities. 
    - `invited_by_user_id`: Tracks which user invited a specific user, useful for analytics and filtering by user relationships.  
    - `is_converted`: Tracks whether an anonymous user has been converted to an authenticated user. 
- Added a `retention_analytics` table to enable tracking user retention.

## Step 2: Implement Analytics Logic and Add API-level Enhancement to Search and Filtering Features
- Updated the user management API endpoints in `app/routers/user_routes.py` to:
    - Accept query parameters for search (`nickname`, `email`, `role`) and filtering (`is_locked`, `email_verified`, `created_at` range).
    - Query the database dynamically based on these parameters.
- Added **pagination and sorting capabilities** to enhance usability and performance for administrators when searching or filtering user data.
- **Enhanced role-based access control (RBAC):**
    - Only ADMIN users can modify the role of other users. 
    - Implemented changes in the `UserService.update` method to enforce RBAC, logging and denying unauthorized role changes.
- **Logging Improvements:** Unauthorized attempts to update roles or sensitive user data are now logged for security auditing.

## Step 3: Unit Testing and Quality Assurance
- Added unit tests to verify:
    - Search and filter functionalities for various query parameters (`nickname`, `email`, `role`, date ranges).
    - Pagination and sorting for large datasets.
    - RBAC enforcement when attempting to update roles (ADMIN-only access).
    - Edge cases such as invalid query parameters and empty datasets.
- Ensure the endpoints implementation bugs free
    - implemented analytics_routes into user_route.py
    - implemented RetentionAnalytics instance in tests/test_services/test_analytics_service.py includes fields such as conversion_rate and inactive_users_*, and fixed API Endpoint codes. 

## Step 4: Include Tasks for User Invitations

## Step 5: Visualize Analytics
