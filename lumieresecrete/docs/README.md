# Lumieres Secrete Documentation

## Project Overview
Lumieres Secrete is an online clothing store application built using Django. The project is designed to provide a seamless shopping experience for customers while offering robust management tools for administrators and managers.

## Features
- **User Registration and Authentication**: Users can create accounts, log in, and manage their profiles.
- **Product Catalog**: A comprehensive catalog of clothing items categorized for easy navigation.
- **Shopping Cart**: Users can add items to their cart and manage their orders.
- **Order Management**: Users can place orders and track their status.
- **Admin Dashboard**: Admins can manage users, products, and view analytics.

## Installation
To set up the project locally, follow these steps:

1. **Clone the Repository**
   ```
   git clone <repository-url>
   cd lumieresecrete
   ```

2. **Set Up Virtual Environment**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   ```
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Copy the `.env.example` to `.env` and fill in the required variables.

5. **Run Migrations**
   ```
   python manage.py migrate
   ```

6. **Start the Development Server**
   ```
   python manage.py runserver
   ```

## Usage
- Access the application at `http://127.0.0.1:8000/`.
- Users can register, log in, and start shopping.
- Admins can access the admin panel to manage the application.

## Documentation
Additional documentation can be found in the `docs` directory, including:
- API specifications
- Architecture diagrams
- Security mechanisms

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.