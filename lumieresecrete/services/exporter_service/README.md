# Exporter Service

The Exporter Service is responsible for generating and exporting reports in various formats, such as CSV and Excel. This service interacts with the main application to fetch data and format it for export.

## Features

- **Data Export**: Ability to export data related to products, orders, and user activity.
- **Format Support**: Supports multiple formats for export, including CSV and Excel.
- **Integration**: Seamlessly integrates with other services in the Lumieresecrete application.

## Installation

To install the necessary dependencies for the Exporter Service, run:

```
pip install -r requirements.txt
```

## Usage

To run the Exporter Service, execute the following command:

```
python app.py
```

Make sure to configure the necessary environment variables as specified in the `.env.example` file.

## API Endpoints

The Exporter Service exposes the following API endpoints:

- `/export/products`: Exports product data.
- `/export/orders`: Exports order data.
- `/export/users`: Exports user activity data.

Refer to the API documentation for detailed information on request and response formats.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.