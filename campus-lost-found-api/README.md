# Campus Lost & Found API

A FastAPI-based REST API for managing lost and found items on a college campus.

The application uses SQLite as the database and SQLModel as the ORM/database modeling library.

---

## Features

- Create lost/found item reports
- View all reported items
- View a specific item by ID
- Update item details and status
- Delete item reports
- Filter items by status
- Filter items by category
- Input validation using FastAPI and SQLModel
- Proper HTTP error handling
- SQLite database storage

---

## Technologies Used

- Python
- FastAPI
- SQLModel
- SQLite
- Uvicorn
- REST API
- Swagger UI

---

## Project Structure

```text
campus-lost-found-api/
│
├── main.py
├── database.db
├── requirements.txt
├── README.md
├── .gitignore
│
└── screenshots/
    ├── 01-post-item.png
    ├── 02-get-items.png
    ├── 03-get-item-by-id.png
    ├── 04-put-item.png
    ├── 05-delete-item.png
    ├── 06-status-filter.png
    ├── 07-category-filter.png
    └── 08-validation-error.png