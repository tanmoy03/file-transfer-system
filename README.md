# FileFlow

## Overview
FileFlow is a multi-user file sharing application that allows users to register, login, upload files, view their own files, download, delete and send files to other users through a central server.

The project combines a web frontend with a Python backend and demonstrates client-server design, user authentication, file storage, and multi-user file transfer.

---

## Main Features

- User registration and login
- Password-based authentication
- Logout and session handling
- File upload with progress tracking
- File download
- File deletion
- Per-user file storage
- Send files to other users
- Inbox / received files view
- Online users list
- Shareable download links
- Separate authentication page and main application page

---

## System Architecture

The system is divided into two main parts:

### Frontend
Built using:
- HTML
- CSS
- JavaScript

The frontend provides:
- Authentication page
- File upload interface
- File list view
- Online users display
- File sending controls

### Backend
Built using:
- Python
- Flask
- SQLite

The backend provides:
- User registration and login API
- Session token management
- File metadata storage
- Per-user file storage directories
- File transfer between users
- Online user tracking

---

## Project Structure

file-transfer-system/
│
├── README.md
├── ui/
│   ├── auth.html
│   ├── index.html
│   └── assets/
│       ├── auth.js
│       ├── app.js
│       └── styles.css
│
├── web/
│   ├── app.py
│   ├── users.db
│   └── api_storage/
│
├── legacy_socket/
│
└── legacy_udp/


## How the System Works

### 1. Authentication
Users register with a username and password. Passwords are stored securely as hashes in a SQLite database.

After login, the backend generates a session token. This token is stored in the browser and is used for authenticated API requests.

### 2. Uploading Files
A user logged in can upload a file through the web interface. The file is stored on the server inside a folder named after the user.

The backend also stores file metadata such as:
- file id
- filename
- file size
- owner
- upload time
- saved path

### 3. Viewing Files
Each user only sees their own files. The frontend loads file data from the backend and displays:
- filename
- size
- upload time

### 4. Sending Files
A user can send a file to another user. The backend copies the selected file into the recipient's storage directory and inserts a new metadata record for that user.

### 5. Inbox / Received Files
When a file is sent to another user, it appears in that user's inbox or received files view.  
This allows recipients to clearly distinguish between files they uploaded themselves and files received from other users.

The inbox improves usability by making file sharing more similar to a real-world messaging or cloud sharing system.

### 6. Downloading and Deleting
Users can download or delete files from their own account through the interface.

---

## API Endpoints

### Authentication
- `POST /register`
- `POST /login`
- `POST /logout`

### Files
- `GET /files`
- `POST /files`
- `GET /files/<id>/download`
- `DELETE /files/<id>`
- `POST /files/<id>/send`

### Users
- `GET /users/online`

---

## Database

The project uses SQLite for persistence.

### Users table
Stores:
- username
- hashed password

### Files table
Stores:
- file id
- filename
- size
- uploaded_at
- owner
- saved_path

This allows the system to keep user accounts and file metadata even after the server restarts.

---

## How to Run the Project

### 1. Install dependencies
From the project root:

```bash
pip install flask flask-cors
```

### 2. Start the backend
```bash
python -m web.app
```

### 3. Start the frontend
In a separate terminal:

```bash
cd ui
python -m http.server 5173
```

### 4. Open the application
Go to:

http://127.0.0.1:5173/auth.html

---

## Example Demo Flow

1. Register a new user
2. Log in
3. Upload a file
4. View the uploaded file in the file list
5. Send the file to another online user
6. Log in as the second user
7. Open the inbox / received files view
8. View the received file
9. Download or delete the file

---

## Development Progress

This project originally began as a socket-based file transfer system using UDP. That earlier implementation is kept in the `legacy_udp` folder.

The final version evolved into a web-based multi-user file sharing system with:
- separate frontend and backend
- database-backed authentication
- persistent file metadata
- user-to-user file transfer

This progression demonstrates both low-level networking work and higher-level web application development.

---

## Future Improvements

Possible future extensions include:
- file activity log
- expiring share links
- encryption for uploaded files
- password reset functionality
- admin controls
- real-time updates without refresh

---

## Authors

Group Members:
- Tanmoy Debnath
- Faruq Ayinla

Areas of work included:
- backend development
- frontend development
- authentication system
- file transfer logic
- system testing and debugging
