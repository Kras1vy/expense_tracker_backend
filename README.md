# Expense Tracker API

## Overview
The Expense Tracker API is built using FastAPI, providing a robust backend for tracking expenses and managing budgets. It includes various features such as authentication, account management, transaction tracking, budgeting, and more.

## Project Structure
- **`src/app.py`**: Main entry point of the application.
- **Routers**: Modularized functionalities including:
  - **`auth`**: Authentication and authorization.
  - **`account`**: User account management.
  - **`categories`**: Expense categories management.
  - **`transactions`**: Transaction records handling.
  - **`budget`**: Budget management.
  - **`ai`**: AI-related functionalities.
  - **`analytics`**: Analytics features.
  - **`payment_methods`**: Payment methods management.
  - **`plaid`**: Integration with Plaid for financial data.

## Key Components
- **Database Initialization**: `init_db` function sets up the database during app lifespan.
- **Custom JSON Encoder**: Handles `PydanticObjectId` objects.
- **Environment Configuration**: Uses `dotenv` to load environment variables.

## API Overview
- **Title**: Expense Tracker API
- **Version**: 1.0.0
- **Description**: API for tracking expenses and managing budgets.

## Getting Started
1. **Installation**: Set up the environment and install dependencies.
2. **Running the Application**: Start the FastAPI server.
3. **Environment Variables**: Configure necessary environment variables.

## Additional Files
- **`pyproject.toml`**: Project dependencies and configuration.
- **`postman_collection.json`**: Postman collection for API testing.

## License
This project is licensed under the MIT License.
