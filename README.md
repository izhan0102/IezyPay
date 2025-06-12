# IezyPay - Digital Payment Project

IezyPay is a Flask-based digital payment application created as a student project. It demonstrates concepts of secure money transfers between users with features like PIN verification, QR code payments, and real-time transaction updates.


## Overview

IezyPay is a robust digital payment platform designed for seamless money transfers and transaction management. Built with Flask and SQLAlchemy, it demonstrates implementation of secure authentication, real-time updates, and modern UI design.

## Features

- **Secure Authentication**: Multi-layered authentication with password and PIN verification
- **Real-time Transaction Updates**: Automatic refreshing of transaction data
- **QR Code Payment Support**: Scan and pay functionality for quick transfers
- **Phone Number Transfers**: Send money directly to registered phone numbers
- **Transaction History**: Detailed record of all financial activities
- **Responsive Design**: Optimized user interface for all devices
- **Session Management**: Secure session handling for protected routes

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLAlchemy with SQLite
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Security**: Werkzeug for password hashing, PIN verification
- **Session Management**: Flask-Login

## Installation

1. Clone the repository:
```bash
git clone https://github.com/izhan0102/iezypay.git
cd iezypay
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python app.py
```

4. Access the application:
```
http://localhost:5000
```

## Security Features

- Password hashing using SHA-256
- 4-digit PIN verification for all transactions
- Session-based authentication
- CSRF protection
- Secure cookie handling

## API Documentation

IezyPay provides several API endpoints for transaction management:

- `GET /get-latest-transactions`: Retrieve recent transactions
- `POST /send-money/phone`: Send money to a phone number
- `POST /send-money/qr`: Send money via QR code

All endpoints require authentication and return JSON responses.

## Project Structure

```
iezypay/
├── app.py                 # Main application file
├── templates/             # HTML templates
│   ├── base.html          # Base template
│   ├── dashboard.html     # User dashboard
│   ├── send_money.html    # Money transfer interface
│   └── ...                # Other templates
├── static/                # Static files (CSS, JS, images)
├── requirements.txt       # Project dependencies
└── README.md              # Project documentation
```



## License

This project is licensed under the MIT License - see the LICENSE file for details.


---

© 2025 IezyPay. All Rights Reserved. 
