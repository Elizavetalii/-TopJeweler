# Lumieres Secrete

## Project Overview
Lumieres Secrete is an online clothing store application built using Django. The application provides a platform for users to browse products, manage their shopping cart, and place orders. It also includes features for managers to analyze sales data and generate reports, as well as administrative tools for managing users and roles.

## Features
- **User Registration and Authentication**: Users can create accounts, log in, and manage their profiles.
- **Product Catalog**: Users can view a wide range of clothing items organized by categories.
- **Shopping Cart**: Users can add items to their cart, modify quantities, and proceed to checkout.
- **Order Management**: Users can place orders and track their status.
- **Admin Dashboard**: Admins can manage users, roles, and perform database backups.
- **Reporting Tools**: Managers can generate reports on sales, inventory, and user activity.

## Installation
1. Clone the repository:
   ```
   git clone https://github.com/yourusername/lumieresecrete.git
   cd lumieresecrete
   ```

2. Set up a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up the database:
   - Update the database settings in `lumieresecrete/settings/development.py`.
   - Run migrations:
     ```
     python manage.py migrate
     ```

5. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```
   python manage.py runserver
   ```

## Usage
- Access the application at `http://127.0.0.1:8000/`.
- Admin panel can be accessed at `http://127.0.0.1:8000/admin/`.

## API Documentation
API endpoints are defined in the `apps/api/urls.py` file. For detailed API usage, refer to the `docs/api_schema.yaml`.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.