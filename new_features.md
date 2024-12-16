# New-Feature Built:  🔍 User Search and Filtering

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
    - Added /users/search new endpoint to router, implement the code to enable the query parameters to accept a variety of search and filter options to give administrators flexibility. 

## Step 1: Review Existing User Management Code and API Endpoints
- Added invited_by_user_id and is_converted columns to app/models/user_model.py to facilitate the new functionalities, the invited_by_user_id will track which user invited a specific user, useful for analytics and filtering by user relationships; the is_converted tracks whether an anonymous user has been converted to an authenticated user. 
- Added a retention_analytics table to enable tracking user retention

## Step 2: API-level Enhancement to Search and Filtering features:
- Update the user management API endpoints in app/routers/user_routes.py to:
    - Accept query parameters for search (nickname, email, role) and filtering (is_locked, email_verified, created_at range).
    - Query the database using these parameters.
- Add pagination and sorting capabilities to the results for better usability.
